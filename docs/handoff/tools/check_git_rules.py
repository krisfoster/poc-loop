"""Free check of the git rules in docs/handoff/spec.md (the State line and the staleness check).

It builds scratch repositories for each edge case, runs the exact commands the spec names, and
checks a small reference implementation of the rules against the expected result. No model runs.
The skills describe these rules in prose; this script shows the rules themselves are right.

Run: python3 docs/handoff/tools/check_git_rules.py [--work <empty dir>]
Exit 0 when every check passes. Git's global and system config are ignored, so user hooks and
signing settings do not interfere.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile

# The exclusions, as the spec defines them. Paths are relative to the repo root.
EXCLUDE = {
    "new": ["poc-spec", ".claude", "SUMMARY.md"],
    "old": ["POC.md", "LOG.md", "SUMMARY.md", ".claude"],
}
FIELDS = ["branch", "at", "uncommitted", "unmerged worktrees", "waiting on you", "resume"]
NOT_REPO = "not a git repo"
LISTED = 5

# Every git command the rules use, written exactly as docs/handoff/spec.md writes it. Each runs as
# `git --no-optional-locks -C "<root>" ...` unless it names another -C. The spec must contain each
# one verbatim (checked below), and the skills will be checked against the same list (plan 1.6).
COMMANDS = [
    "rev-parse --is-inside-work-tree",
    "branch --show-current",
    "rev-parse --short HEAD",
    "status --porcelain -- . <exclusions>",
    "worktree list --porcelain",
    "log --oneline <branch or sha> --not HEAD",
    'git --no-optional-locks -C "<worktree path>" status --porcelain',
    'git --no-optional-locks -C "<worktree path>" rev-parse --short HEAD',
    "merge-base --is-ancestor <recorded sha> HEAD",
    "log --oneline <recorded sha>..HEAD -- . <exclusions>",
]
SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "spec.md")

ENV = dict(os.environ)


def git(cwd_root, *args):
    """git --no-optional-locks -C <root> ..., as the spec runs it. Returns (rc, stdout)."""
    p = subprocess.run(["git", "--no-optional-locks", "-C", cwd_root, *args],
                       capture_output=True, text=True, env=ENV)
    return p.returncode, p.stdout


def plain(cwd, *args):
    p = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, env=ENV)
    if p.returncode:
        raise RuntimeError("git %s failed in %s: %s" % (" ".join(args), cwd, p.stderr))
    return p.stdout


def pathspec(layout):
    return ["--", "."] + [":(exclude)" + p for p in EXCLUDE[layout]]


def porcelain_paths(out):
    paths = []
    for line in out.splitlines():
        if not line.strip():
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return paths


def worktree_entries(root):
    rc, out = git(root, "worktree", "list", "--porcelain")
    entries, cur = [], None
    for line in out.splitlines():
        if line.startswith("worktree "):
            cur = {"path": line[len("worktree "):], "branch": None, "head": None, "detached": False}
            entries.append(cur)
        elif cur is not None and line.startswith("branch "):
            cur["branch"] = line[len("branch "):].replace("refs/heads/", "", 1)
        elif cur is not None and line.startswith("HEAD "):
            cur["head"] = line[len("HEAD "):]
        elif cur is not None and line == "detached":
            cur["detached"] = True
    return entries


def gather(root, layout):
    """The State values, plus the full uncommitted list the reader needs for its comparison."""
    rc, out = git(root, "rev-parse", "--is-inside-work-tree")
    if rc or out.strip() != "true":
        return {f: NOT_REPO for f in FIELDS[:4]}, []
    branch = git(root, "branch", "--show-current")[1].strip() or "detached"
    rc, sha = git(root, "rev-parse", "--short", "HEAD")
    at = sha.strip() if rc == 0 else "no commits"
    paths = porcelain_paths(git(root, "status", "--porcelain", *pathspec(layout))[1])
    if paths:
        # A path git prints in quotes (spaces, `;`, other unusual characters) is counted, not listed,
        # so it cannot break the `; ` and `, ` separators.
        listable = [p for p in paths if not p.startswith('"')][:LISTED]
        shown = ", ".join(listable + (["..."] if len(paths) > len(listable) else []))
        uncommitted = "%d paths: %s" % (len(paths), shown) if listable else "%d paths: ..." % len(paths)
    else:
        uncommitted = "none"
    entries = worktree_entries(root)
    main = os.path.realpath(entries[0]["path"])
    under = os.path.join(main, ".claude", "worktrees") + os.sep
    me = os.path.realpath(root)
    names = []
    for e in entries[1:]:
        p = os.path.realpath(e["path"])
        if not p.startswith(under) or p == me:
            continue
        if e["branch"]:
            ref, name = e["branch"], e["branch"]
        else:
            ref = e["head"]
            name = "detached " + git(e["path"], "rev-parse", "--short", "HEAD")[1].strip()
        commits = at != "no commits" and bool(git(root, "log", "--oneline", ref, "--not", "HEAD")[1].strip())
        dirty = bool(git(e["path"], "status", "--porcelain")[1].strip())
        if commits or dirty:
            names.append(name + (" (uncommitted)" if dirty else ""))
    worktrees = ", ".join(names) if names else "none"
    return {"branch": branch, "at": at, "uncommitted": uncommitted, "unmerged worktrees": worktrees}, paths


def state_line(values, waiting="none", resume="/spike-loop:poc-help"):
    v = dict(values, **{"waiting on you": waiting, "resume": resume})
    return "- State: " + "; ".join("%s: %s" % (f, v[f]) for f in FIELDS)


def parse_state(line):
    assert line.startswith("- State: ")
    out = {}
    for part in line[len("- State: "):].split("; "):
        k, _, v = part.partition(": ")
        out[k] = v
    assert list(out) == FIELDS, list(out)
    return out


def recorded_paths(value):
    if value in ("none", NOT_REPO):
        return 0, []
    count, _, rest = value.partition(" paths: ")
    shown = [p for p in rest.split(", ") if p != "..."]
    return int(count), shown


def stale_reasons(recorded, root, layout):
    """What differs between a recorded State and the repo now. Empty means fresh."""
    now, now_paths = gather(root, layout)
    reasons = []
    if recorded["branch"] != now["branch"]:
        reasons.append("branch")
    rec_at, now_at = recorded["at"], now["at"]
    special = ("no commits", NOT_REPO)
    if rec_at in special or now_at in special:
        if rec_at != now_at:
            reasons.append("commit")
    else:
        rc, _ = git(root, "merge-base", "--is-ancestor", rec_at, "HEAD")
        if rc != 0:
            reasons.append("recorded commit not in history")
        elif git(root, "log", "--oneline", "%s..HEAD" % rec_at, *pathspec(layout))[1].strip():
            reasons.append("commits outside the docs folder")
    if now_at != NOT_REPO:
        count, shown = recorded_paths(recorded["uncommitted"])
        if count != len(now_paths) or any(p not in now_paths for p in shown):
            reasons.append("uncommitted")
    return reasons


# ---------- fixtures ----------

def write(path, text="x\n"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def new_repo(base, name, layout="new", commit=True):
    root = os.path.join(base, name)
    os.makedirs(root)
    plain(root, "init", "-q", "-b", "main")
    docs = "poc-spec" if layout == "new" else "."
    write(os.path.join(root, docs, "POC.md"), "# PoC\n")
    write(os.path.join(root, docs, "LOG.md"), "# Log\n")
    write(os.path.join(root, "app.py"), "print(1)\n")
    if commit:
        plain(root, "add", "-A")
        plain(root, "commit", "-qm", "start")
    return root


def commit_all(root, msg):
    plain(root, "add", "-A")
    plain(root, "commit", "-qm", msg)


RESULTS = []


def check(name, cond, detail=""):
    RESULTS.append((name, bool(cond), detail))


def recorded(root, layout):
    return parse_state(state_line(gather(root, layout)[0]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work")
    args = ap.parse_args()
    base = args.work or tempfile.mkdtemp(prefix="handoff-git-")
    os.makedirs(base, exist_ok=True)
    if os.listdir(base):
        sys.exit("--work must be empty: %s" % base)
    empty_cfg = os.path.join(base, "empty-gitconfig")
    write(empty_cfg, "")
    ENV.update({"GIT_CONFIG_GLOBAL": empty_cfg, "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
                "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid"})

    # R3-1 (blocker): older layout. The docs files are excluded by name, code is still seen.
    for layout in ("new", "old"):
        r = new_repo(base, "excl-" + layout, layout)
        docs = "poc-spec" if layout == "new" else "."
        write(os.path.join(r, docs, "LOG.md"), "# Log\nentry\n")
        write(os.path.join(r, "b.py"))
        vals, paths = gather(r, layout)
        check("R3-1 %s layout: uncommitted lists code, not docs" % layout, paths == ["b.py"], paths)
        rec = recorded(r, layout)
        commit_all(r, "log only")  # commits b.py too
        check("R3-1 %s layout: a commit that touches code is stale" % layout,
              "commits outside the docs folder" in stale_reasons(rec, r, layout))
        rec = recorded(r, layout)
        write(os.path.join(r, docs, "LOG.md"), "# Log\nentry\nmore\n")
        commit_all(r, "docs only")
        check("R3-1 %s layout: a docs-only commit is fresh" % layout,
              stale_reasons(rec, r, layout) == [], stale_reasons(rec, r, layout))
    # The old rule, ':(exclude).', hides everything (the defect, kept as evidence).
    r = new_repo(base, "old-rule", "old")
    write(os.path.join(r, "b.py"))
    out = git(r, "status", "--porcelain", "--", ".", ":(exclude).")[1]
    check("R3-1 evidence: ':(exclude).' hides an uncommitted code file", out.strip() == "", out)

    # R3-2: SUMMARY.md written after State does not make it stale, in either layout.
    for layout in ("new", "old"):
        r = new_repo(base, "summary-" + layout, layout)
        rec = recorded(r, layout)
        write(os.path.join(r, "SUMMARY.md"), "# Summary\n")
        check("R3-2 %s layout: SUMMARY.md after State is fresh" % layout,
              stale_reasons(rec, r, layout) == [], stale_reasons(rec, r, layout))
        commit_all(r, "summary")
        check("R3-2 %s layout: committing SUMMARY.md is fresh" % layout,
              stale_reasons(rec, r, layout) == [], stale_reasons(rec, r, layout))

    # R3-3: more than five uncommitted paths. Count plus listed paths detect a change.
    r = new_repo(base, "many")
    for i in range(7):
        write(os.path.join(r, "f%d.py" % i))
    vals, paths = gather(r, "new")
    check("R3-3 value records the count and five paths",
          vals["uncommitted"].startswith("7 paths: ") and vals["uncommitted"].endswith(", ..."), vals["uncommitted"])
    rec = recorded(r, "new")
    check("R3-3 unchanged: fresh", stale_reasons(rec, r, "new") == [])
    write(os.path.join(r, "f9.py"))
    check("R3-3 an added path: stale", "uncommitted" in stale_reasons(rec, r, "new"))
    os.remove(os.path.join(r, "f9.py"))
    os.remove(os.path.join(r, "f0.py"))
    write(os.path.join(r, "g.py"))
    check("R3-3 a listed path swapped for another (same count): stale",
          "uncommitted" in stale_reasons(rec, r, "new"))

    # R3-5: worktrees under the main checkout's .claude/worktrees/.
    r = new_repo(base, "wt")
    wt = os.path.join(r, ".claude", "worktrees")
    plain(r, "worktree", "add", "-q", "-b", "worktree-agent-a", os.path.join(wt, "agent-a"))
    write(os.path.join(wt, "agent-a", "new.py"))  # uncommitted only, no commits
    plain(r, "worktree", "add", "-q", "-b", "worktree-agent-b", os.path.join(wt, "agent-b"))
    write(os.path.join(wt, "agent-b", "c.py"))
    commit_all(os.path.join(wt, "agent-b"), "b work")  # committed, clean
    plain(r, "worktree", "add", "-q", "--detach", os.path.join(wt, "agent-c"))
    write(os.path.join(wt, "agent-c", "d.py"))
    plain(r, "worktree", "add", "-q", "-b", "worktree-agent-d", os.path.join(wt, "agent-d"))  # nothing to report
    plain(r, "worktree", "add", "-q", "-b", "elsewhere", os.path.join(base, "wt-outside"))
    write(os.path.join(base, "wt-outside", "e.py"))
    vals, _ = gather(r, "new")
    v = vals["unmerged worktrees"]
    check("R3-5a uncommitted-only worktree is listed", "worktree-agent-a (uncommitted)" in v, v)
    check("R3-5 committed clean worktree is listed unmarked",
          "worktree-agent-b" in v.split(", "), v)
    check("R3-5b detached worktree stored as 'detached <sha>'", "detached " in v and "(uncommitted)" in v, v)
    check("R3-5 clean worktree with nothing unmerged is not listed", "worktree-agent-d" not in v, v)
    check("R3-5 worktree outside .claude/worktrees/ is not listed", "elsewhere" not in v, v)
    check("R3-5 no path is stored", wt not in v and base not in v, v)
    check("R3-5 main checkout is the first worktree entry",
          os.path.realpath(worktree_entries(os.path.join(wt, "agent-b"))[0]["path"]) == os.path.realpath(r))
    # R3-5c: a session whose root is itself an agent worktree (made dirty, so listing it would show).
    write(os.path.join(wt, "agent-b", "dirty.py"))
    vals_c, _ = gather(os.path.join(wt, "agent-b"), "new")
    vc = vals_c["unmerged worktrees"]
    check("R3-5c root in a linked worktree: siblings found under the main checkout",
          "worktree-agent-a (uncommitted)" in vc, vc)
    check("R3-5c root in a linked worktree: its own worktree is not listed",
          not any(n.startswith("worktree-agent-b") for n in vc.split(", ")), vc)

    # R3-5d and R3-1 edge: a repository with no commits.
    r = new_repo(base, "empty", commit=False)
    vals, paths = gather(r, "new")
    check("no commits: branch read", vals["branch"] == "main", vals)
    check("no commits: at is 'no commits'", vals["at"] == "no commits", vals)
    check("no commits: code files listed, docs not", sorted(paths) == ["app.py"], paths)
    rc, _ = git(r, "log", "--oneline", "main", "--not", "HEAD")
    check("R3-5d evidence: log --not HEAD fails with no commits", rc != 0)
    rec = recorded(r, "new")
    check("no commits: unchanged is fresh", stale_reasons(rec, r, "new") == [])
    commit_all(r, "first")
    check("no commits: a first commit is stale", "commit" in stale_reasons(rec, r, "new"))

    # Not a git repository.
    nr = os.path.join(base, "plain-dir")
    write(os.path.join(nr, "LOG.md"))
    vals, _ = gather(nr, "old")
    check("not a git repo: every git field says so", all(vals[f] == NOT_REPO for f in FIELDS[:4]), vals)

    # Detached HEAD in the main checkout.
    r = new_repo(base, "detached")
    plain(r, "checkout", "-q", "--detach")
    vals, _ = gather(r, "new")
    check("detached HEAD: branch is 'detached'", vals["branch"] == "detached", vals)
    rec = recorded(r, "new")
    plain(r, "checkout", "-q", "main")
    check("detached then back on a branch: stale", "branch" in stale_reasons(rec, r, "new"))

    # R3-6: a reset to before the recorded commit.
    r = new_repo(base, "reset")
    write(os.path.join(r, "b.py"))
    commit_all(r, "two")
    rec = recorded(r, "new")
    plain(r, "reset", "-q", "--hard", "HEAD~1")
    check("R3-6 reset before the recorded commit: stale",
          "recorded commit not in history" in stale_reasons(rec, r, "new"))
    rec_bad = dict(rec, at="0000000")
    check("R3-6 an unknown sha: stale", "recorded commit not in history" in stale_reasons(rec_bad, r, "new"))
    rec = recorded(r, "new")
    check("R3-6 same commit: fresh", stale_reasons(rec, r, "new") == [])

    # R3-9: the same exclusions in both comparisons, so .claude/ never counts.
    r = new_repo(base, "dotclaude")
    rec = recorded(r, "new")
    write(os.path.join(r, ".claude", "settings.json"), "{}\n")
    check("R3-9 untracked .claude/ is fresh", stale_reasons(rec, r, "new") == [])
    commit_all(r, "settings")
    check("R3-9 a commit to .claude/ only is fresh", stale_reasons(rec, r, "new") == [])

    # R3-13: plain `git status` may rewrite the index; --no-optional-locks does not.
    r = new_repo(base, "locks")
    idx = os.path.join(r, ".git", "index")
    st = os.stat(os.path.join(r, "app.py"))
    os.utime(os.path.join(r, "app.py"), (st.st_atime + 100, st.st_mtime + 100))
    before = os.stat(idx).st_mtime_ns
    git(r, "status", "--porcelain")  # with --no-optional-locks
    after_nol = os.stat(idx).st_mtime_ns
    subprocess.run(["git", "-C", r, "status", "--porcelain"], capture_output=True, env=ENV)
    after_plain = os.stat(idx).st_mtime_ns
    check("R3-13 --no-optional-locks status leaves the index alone", after_nol == before)
    RESULTS.append(("R3-13 evidence: plain status rewrote the index (informational)",
                    True, "rewrote" if after_plain != after_nol else "did not rewrite"))

    # R3b-N7: unusual file names are counted, not listed, and the line still parses.
    r = new_repo(base, "names")
    for n in ("c; d.py", "e f.py", "ok.py"):
        write(os.path.join(r, n))
    vals, paths = gather(r, "new")
    line = state_line(vals)
    try:
        st = parse_state(line)
    except AssertionError:
        st = {"uncommitted": None}
    check("R3b-N7 a ';' or space in a file name does not split the line", st["uncommitted"] == vals["uncommitted"], line)
    check("R3b-N7 quoted names counted, plain ones listed", st["uncommitted"] == "3 paths: ok.py, ...", st["uncommitted"])
    if st["uncommitted"] == vals["uncommitted"]:
        rec = parse_state(line)
        check("R3b-N7 unchanged: fresh", stale_reasons(rec, r, "new") == [])
        os.remove(os.path.join(r, "c; d.py"))
        check("R3b-N7 a quoted path removed: stale (count)", "uncommitted" in stale_reasons(rec, r, "new"))

    # R3b-N4: the spec writes every command this script runs, verbatim.
    spec = open(SPEC, encoding="utf-8").read()
    missing = [c for c in COMMANDS if c not in spec]
    check("R3b-N4 every command is written in the spec", not missing, missing)

    # Format: the six fields parse back in order.
    line = state_line(gather(new_repo(base, "fmt"), "new")[0])
    check("format: six fields in order", list(parse_state(line)) == FIELDS, line)

    bad = 0
    for name, ok, detail in RESULTS:
        print("%s  %s%s" % ("ok  " if ok else "FAIL", name, ("  [%s]" % (detail,)) if detail and not ok or
                            name.endswith("(informational)") else ""))
        bad += not ok
    print("%d checks, %d failed. git %s" % (len(RESULTS), bad,
          subprocess.run(["git", "--version"], capture_output=True, text=True).stdout.split()[-1]))
    if not args.work:
        shutil.rmtree(base, ignore_errors=True)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
