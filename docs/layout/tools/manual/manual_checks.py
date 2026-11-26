#!/usr/bin/env python3
"""Manual checks for docs/layout plan tasks 3.4 and 3.5: the real spike-loop skills, run headless against scratch repos.

Each case builds a throwaway git repo, starts `claude -p "/spike-loop:<command> ..."` in a directory of it with this
worktree loaded as the plugin, and prints what happened: the tool calls, permission denials, cost, the final text and
the files left behind. Each case has a heuristic check. The checks do not replace reading the digest: a regex can
pass wrong behaviour. These are paid runs on the user's subscription, one run per case.

Isolation follows evals/harness/runner.py (temporary HOME, CLAUDE_CONFIG_DIR and XDG_CONFIG_HOME, only PATH
inherited). The token is read by the harness helper from an evals-spec checkout and is never printed or saved.
Bash grants are narrow patterns, one per part of a compound command, never a broad `Bash`.

Usage: python3 manual_checks.py --work DIR --out DIR --evals-repo PATH [--only ID ...] [--dry-run] [--suite-cap USD]
"""
import argparse
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE.parents[2].parent  # the worktree root: docs/layout/tools/manual -> repo
if not (PLUGIN / ".claude-plugin" / "plugin.json").is_file():
    PLUGIN = Path(__file__).resolve().parents[4]

GRANTS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash(git *)", "Bash(cd *)", "Bash(date *)", "Bash(chmod *)",
          "Bash(mkdir *)", "Bash(ls *)", "Bash(cat *)", "Bash(tail *)", "Bash(head *)", "Bash(grep *)",
          "Bash(./verify.sh)", "Bash(./run.sh)", "Bash(rsync *)", "Bash(mktemp *)", "Bash(gitleaks *)", "Bash(typos *)"]
NARROW = ["Read", "Bash(git *)", "Bash(cd *)", "Bash(./verify.sh)"]

START_ARGS = ("Webhook signature check. Tier 1. No deal. Private repo, no customer details. "
              "Question: can a small receiver verify an HMAC-SHA256 webhook signature? "
              "Assumptions: 1. the signature header is hex encoded, 2. the secret is a shared string. "
              "Success check: run verify.sh, which must print OK when a known test vector verifies. "
              "In scope: one verify function and one test vector. Out of scope: a real HTTP server. Timebox: 2 hours.")
LOG_ARGS = "Tried an HMAC known vector. Learned the signature matches. Dead ends: none. Decision: none yet."


def started():
    return (datetime.datetime.now() - datetime.timedelta(minutes=20)).strftime("%Y-%m-%d %H:%M")


def poc_md(visibility="private", deal="none"):
    return ("# POC: Fixture webhook check\n\n"
            "Started: %s | Timebox (first pass): 2 hours | Tier: 1 | Deal: %s | Repo visibility: %s\n\n"
            "## Question\nCan a small receiver verify an HMAC signature?\n\n"
            "## Success check\nRun ./verify.sh, it prints OK.\n\n"
            "## Assumptions and risks (riskiest first)\n1. hex encoding, it could be base64\n\n"
            "## In scope\n- a verify function\n\n## Out of scope\n- an HTTP server\n\n"
            "## Manual check (only if verify.sh cannot do it)\nnone\n") % (started(), deal, visibility)


LOG_MD = ("# Log\n\nAppend only. Newest entry last. Format per entry:\n\n"
          "## <YYYY-MM-DD HH:MM> <one-line title>\n- Tried: <>\n- Learned: <>\n- Dead ends: <>\n"
          "- Decision: <iterate | pivot | harden | stop | none yet>\n- Next question: <>\n- Later: <>\n\n"
          "## %s PoC started\n- Tried: nothing yet\n- Learned: nothing yet\n- Dead ends: none\n"
          "- Decision: none yet\n- Next question: none yet\n- Later: none\n")


def git(args, cwd, home):
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1"}
    r = subprocess.run(["git", "-c", "user.email=check@example.test", "-c", "user.name=check"] + args,
                       cwd=str(cwd), env=env, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("git %s failed in %s: %s" % (" ".join(args[:2]), cwd, r.stderr.strip()[:200]))
    return r.stdout


def write(path, text, mode=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if mode:
        os.chmod(str(path), mode)


def make_repo(root, layout="new", visibility="private", deal="none", docs_state="tracked", empty=False):
    """layout: new, old, both, partial, none. docs_state: tracked, untracked, ignored."""
    root = Path(root)
    root.mkdir(parents=True)
    home = root.parent
    write(root / "sub" / "deep" / ".keep", "")
    if not empty:
        write(root / "verify.sh", '#!/usr/bin/env bash\necho "VERIFY_RAN_IN=$(pwd)"\necho OK\n', 0o755)
        write(root / "run.sh", '#!/usr/bin/env bash\necho hello\n', 0o755)
        write(root / "app.txt", "a tiny app\n")
    log = LOG_MD % datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    docs = []
    if layout in ("new", "both"):
        write(root / "poc-spec" / "POC.md", poc_md(visibility, deal))
        write(root / "poc-spec" / "LOG.md", log)
        docs += ["poc-spec"]
    if layout in ("old", "both"):
        write(root / "POC.md", poc_md(visibility, deal))
        write(root / "LOG.md", log)
        docs += ["POC.md", "LOG.md"]
    if layout == "partial":
        write(root / "poc-spec" / "POC.md", poc_md(visibility, deal))
        write(root / "LOG.md", log)
        docs += ["poc-spec", "LOG.md"]
    if docs_state == "ignored" and docs:
        write(root / ".gitignore", "\n".join(d + ("/" if d == "poc-spec" else "") for d in docs) + "\n")
    git(["init", "-q", "-b", "main"], root, home)
    if docs_state in ("tracked", "ignored") or not docs:
        git(["add", "-A"], root, home)  # for "ignored" the .gitignore already keeps the docs out
    else:
        git(["add", "-A", "--"] + [":!" + d for d in docs], root, home)
    git(["commit", "-q", "--allow-empty", "-m", "fixture"], root, home)
    return root


class Ctx:
    def __init__(self, root, cwd, final, calls, denials, cost):
        self.root, self.cwd, self.final, self.calls, self.denials, self.cost = root, cwd, final or "", calls, denials, cost

    def exists(self, rel):
        return (self.root / rel).exists()

    def text(self, rel):
        p = self.root / rel
        return p.read_text() if p.is_file() else ""

    def cmds(self):
        return [c for n, c in self.calls if n == "Bash"]

    def low(self):
        return self.final.lower()


def entries(text):
    return sum(1 for ln in text.splitlines() if ln.startswith("## 20"))


def checks_for(case_id, ctx):
    """Heuristic checks. Each returns a list of (ok, what)."""
    out = []
    f = ctx.low()

    def chk(ok, what):
        out.append((bool(ok), what))

    if case_id == "C01":
        chk(ctx.exists("poc-spec/POC.md") and ctx.exists("poc-spec/LOG.md"), "poc-spec/POC.md and poc-spec/LOG.md written")
        chk(not ctx.exists("POC.md") and not ctx.exists("LOG.md"), "nothing at the root named POC.md or LOG.md")
        chk(ctx.exists("verify.sh") and os.access(str(ctx.root / "verify.sh"), os.X_OK), "verify.sh at the root and executable")
        chk("Docs folder: `poc-spec/`" in ctx.text("CLAUDE.md"), "CLAUDE.md has the wiring block")
        chk("Next:" in ctx.final, "ends with a Next line")
    elif case_id == "C02":
        chk(not ctx.exists("sub/deep/poc-spec"), "nothing written under the start directory")
        chk(ctx.exists("poc-spec/POC.md") or "root" in f, "either wrote to the root or named the root")
    elif case_id in ("C04", "C05"):
        chk(not ctx.exists("poc-spec/POC.md") and not ctx.exists("inner/poc-spec/POC.md"), "wrote no poc-spec/POC.md before asking")
        chk("worktree" in f if case_id == "C05" else ("outer" in f or "another repo" in f or "inside" in f or "nested" in f), "names the situation")
    elif case_id == "C06":
        chk(not ctx.exists("poc-spec/POC.md"), "wrote nothing in a bare repository")
        chk("bare" in f, "says bare repositories are not supported")
    elif case_id == "C07":
        chk(ctx.text("POC.md").startswith("# POC: Fixture"), "existing root POC.md untouched")
        chk(not ctx.exists("poc-spec/POC.md"), "did not create poc-spec/POC.md")
    elif case_id in ("C08", "C09", "C10"):
        chk(entries(ctx.text("poc-spec/LOG.md")) == 2, "poc-spec/LOG.md has two dated entries")
        chk("HMAC" in ctx.text("poc-spec/LOG.md"), "entry mentions the text")
        chk(not ctx.exists("LOG.md") and not ctx.exists("sub/deep/poc-spec") and not ctx.exists("sub/deep/LOG.md"), "no stray LOG.md or poc-spec")
        chk("Next:" in ctx.final, "ends with a Next line")
    elif case_id == "C11":
        chk(entries(ctx.text("LOG.md")) == 2, "root LOG.md has two dated entries")
        chk(not ctx.exists("poc-spec"), "did not create poc-spec/")
    elif case_id in ("C12", "C13"):
        chk(entries(ctx.text("LOG.md")) == 1 and entries(ctx.text("poc-spec/LOG.md")) in (0, 1), "no LOG.md was appended to")
        chk("half" in f or "both" in f or "migrat" in f, "says the PoC is half-migrated")
        chk("Next:" in ctx.final, "ends with a Next line")
    elif case_id == "C14":
        chk("poc-start" in f, "points at poc-start")
        chk("Next:" in ctx.final, "ends with a Next line")
        chk(not ctx.exists("poc-spec") and not ctx.exists("LOG.md"), "created nothing")
    elif case_id == "C15":
        chk("Next:" in ctx.final, "ends with a Next line")
        chk("older layout" not in f, "no older-layout line on the new layout")
        chk(entries(ctx.text("poc-spec/LOG.md")) == 1, "wrote nothing")
    elif case_id == "C16":
        flat = ctx.final.replace("`", "")
        chk("Older layout: POC.md and LOG.md are at the repo root." in flat and "git mv POC.md LOG.md poc-spec/" in flat, "prints the older-layout line (backticks around the file names are ignored, the model sometimes adds them)")
        chk(entries(ctx.text("LOG.md")) == 1 and not ctx.exists("poc-spec"), "changed nothing")
    elif case_id == "C17":
        chk("add-dir" in f or "outside" in f or "blocked" in f or "refused" in f, "explains the refusal")
        chk(not any(c.strip().startswith('"') and "verify.sh" in c and "cd " not in c for c in ctx.cmds()), "did not work around it by an absolute-path run")
    elif case_id == "C18":
        chk("VERIFY_RAN_IN" in ctx.final or "pass" in f, "verified")
        chk(any("cd " in c and "verify.sh" in c for c in ctx.cmds()), "ran verify.sh after a cd to the root")
    elif case_id.startswith("C19") or case_id.startswith("C2"):
        warn_new = "would travel" in f and "poc-spec" in f
        want = {"C19": "new", "C20": "new", "C21": None, "C22": None, "C23": "old"}[case_id]
        if want == "new":
            chk(warn_new, "new-layout warning present")
        elif want == "old":
            chk("would travel" in f and "poc.md and log.md" in f, "older-layout warning present")
        else:
            chk("would travel" not in f, "no warning")
        import re as _re
        chk(not any(_re.search(r"\bgit\b[^;&|\n]*\brm\b", c) for c in ctx.cmds()), "no git rm")
        gi = ctx.text(".gitignore")
        chk("poc-spec" not in gi and "POC.md" not in gi and "LOG.md" not in gi, ".gitignore does not name the docs folder (a .env line is the packager's own job)")
    return out


def cases(work):
    W = Path(work)

    def p(name):
        return W / name / "repo"

    def build(name, **kw):
        def fn():
            return make_repo(p(name), **kw)
        return fn

    def symlinked(name, **kw):
        def fn():
            repo = make_repo(p(name), **kw)
            link = repo.parent / "link"
            link.symlink_to(repo)
            return repo
        return fn

    def nested(name):
        def fn():
            repo = make_repo(p(name), layout="none")
            inner = repo / "inner"
            inner.mkdir()
            write(inner / "README", "inner\n")
            git(["init", "-q", "-b", "main"], inner, repo.parent)
            git(["add", "-A"], inner, repo.parent)
            git(["commit", "-q", "-m", "inner"], inner, repo.parent)
            return repo
        return fn

    def linked(name):
        def fn():
            repo = make_repo(p(name), layout="none", empty=True)
            git(["worktree", "add", "-q", "-b", "wt", str(repo.parent / "wt")], repo, repo.parent)
            return repo
        return fn

    def bare(name):
        def fn():
            root = p(name)
            root.parent.mkdir(parents=True)
            root.mkdir()
            git(["init", "-q", "--bare", "-b", "main"], root, root.parent)
            return root
        return fn

    def add_root(repo):
        return {"permissions": {"additionalDirectories": [str(repo)]}}

    ADDDIR = "adddir"
    # id, command, fixture builder, start dir (relative to the repo, or a callable), grants, settings mode, cap, repo name
    return [
        ("C01", "poc-start new repo from the root", "/spike-loop:poc-start " + START_ARGS, build("c01", layout="none", empty=True), ".", GRANTS, None, "0.6"),
        ("C02", "poc-start from a subdirectory", "/spike-loop:poc-start " + START_ARGS, build("c02", layout="none", empty=True), "sub/deep", GRANTS, ADDDIR, "0.6"),
        ("C04", "poc-start at the root of a repo nested in another", "/spike-loop:poc-start " + START_ARGS, nested("c04"), "inner", GRANTS, None, "0.6"),
        ("C05", "poc-start in a linked worktree", "/spike-loop:poc-start " + START_ARGS, linked("c05"), "../wt", GRANTS, None, "0.6"),
        ("C06", "poc-start in a bare repository", "/spike-loop:poc-start " + START_ARGS, bare("c06"), ".", GRANTS, None, "0.6"),
        ("C07", "poc-start with an older root POC.md present", "/spike-loop:poc-start " + START_ARGS, build("c07", layout="old"), ".", GRANTS, None, "0.6"),
        ("C08", "poc-log new layout from the root", "/spike-loop:poc-log " + LOG_ARGS, build("c08", layout="new"), ".", GRANTS, None, "0.25"),
        ("C09", "poc-log new layout from a subdirectory, root added", "/spike-loop:poc-log " + LOG_ARGS, build("c09", layout="new"), "sub/deep", GRANTS, ADDDIR, "0.25"),
        ("C10", "poc-log new layout from a subdirectory, root not added", "/spike-loop:poc-log " + LOG_ARGS, build("c10", layout="new"), "sub/deep", GRANTS, None, "0.25"),
        ("C11", "poc-log older layout", "/spike-loop:poc-log " + LOG_ARGS, build("c11", layout="old"), ".", GRANTS, None, "0.25"),
        ("C12", "poc-log with both layouts present", "/spike-loop:poc-log " + LOG_ARGS, build("c12", layout="both"), ".", GRANTS, None, "0.25"),
        ("C13", "poc-log after a partial move", "/spike-loop:poc-log " + LOG_ARGS, build("c13", layout="partial"), ".", GRANTS, None, "0.25"),
        ("C14", "poc-log with no PoC files", "/spike-loop:poc-log " + LOG_ARGS, build("c14", layout="none"), ".", GRANTS, None, "0.25"),
        ("C15", "poc-help status on the new layout", "/spike-loop:poc-help", build("c15", layout="new"), ".", GRANTS, None, "0.25"),
        ("C16", "poc-help status on the older layout", "/spike-loop:poc-help", build("c16", layout="old"), ".", GRANTS, None, "0.25"),
        ("C17", "poc-verify from a subdirectory, narrow grants, root not added", "/spike-loop:poc-verify", build("c17", layout="new"), "sub/deep", NARROW, None, "0.25"),
        ("C18", "poc-verify from a subdirectory, narrow grants, root added", "/spike-loop:poc-verify", build("c18", layout="new"), "sub/deep", NARROW, ADDDIR, "0.25"),
        ("C19", "packager warning: public, poc-spec tracked", "/spike-loop:poc-package", build("c19", layout="new", visibility="public", docs_state="tracked"), ".", GRANTS, None, "0.6"),
        ("C20", "packager warning: public, poc-spec untracked and not ignored", "/spike-loop:poc-package", build("c20", layout="new", visibility="public", docs_state="untracked"), ".", GRANTS, None, "0.6"),
        ("C21", "packager quiet: public, poc-spec ignored", "/spike-loop:poc-package", build("c21", layout="new", visibility="public", docs_state="ignored"), ".", GRANTS, None, "0.6"),
        ("C22", "packager quiet: private, Deal none, poc-spec tracked", "/spike-loop:poc-package", build("c22", layout="new", visibility="private", deal="none", docs_state="tracked"), ".", GRANTS, None, "0.6"),
        ("C23", "packager warning: older layout, public, tracked", "/spike-loop:poc-package", build("c23", layout="old", visibility="public", docs_state="tracked"), ".", GRANTS, None, "0.6"),
    ]


def isolated_env(home, token):
    home = str(home)
    return {"PATH": os.environ.get("PATH", ""), "TERM": "xterm", "HOME": home,
            "CLAUDE_CONFIG_DIR": os.path.join(home, "cc"), "XDG_CONFIG_HOME": os.path.join(home, "xdg"),
            "TMPDIR": os.path.join(home, "tmp"), "CLAUDE_CODE_OAUTH_TOKEN": token}


def short(v, n=170):
    if isinstance(v, list):
        v = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in v)
    v = str(v).replace("\n", " | ")
    return v if len(v) <= n else v[:n] + "..."


def parse(stdout):
    calls, results, order, final = [], {}, [], {}
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        t = ev.get("type")
        if t == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    inp = b.get("input", {})
                    arg = inp.get("command") or inp.get("file_path") or json.dumps(inp)[:100]
                    calls.append((b.get("name"), arg))
                    order.append((b.get("id"), b.get("name"), arg, "sub" if ev.get("parent_tool_use_id") else "main"))
        elif t == "user":
            for b in ev.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = ("ERROR " if b.get("is_error") else "") + short(b.get("content", ""))
        elif t == "result":
            final = ev
    return calls, results, order, final


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evals-repo", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--suite-cap", type=float, default=8.0)
    a = ap.parse_args()
    work, out = Path(a.work), Path(a.out)
    if work.exists():
        shutil.rmtree(str(work))
    out.mkdir(parents=True, exist_ok=True)
    plan = [c for c in cases(work) if not a.only or c[0] in a.only]
    if not a.dry_run:
        sys.path.insert(0, str(Path(a.evals_repo) / "evals"))
        from harness import runner  # noqa: E402
        token, _ = runner.load_token(Path(a.evals_repo))
        print("claude --version:", subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip())
    total, summary = 0.0, []
    for cid, label, prompt, build_fn, start, grants, settings_mode, cap in plan:
        root = build_fn()
        cwd = (root / start).resolve() if not start.startswith("../link") else (root.parent / "link")
        if start == "../wt":
            cwd = root.parent / "wt"
        if a.dry_run:
            print("%s | %s | cwd=%s | %s" % (cid, label, str(cwd).replace(str(work), "<work>"), prompt[:50]))
            continue
        if total >= a.suite_cap:
            print("%s skipped: suite cap %.2f reached" % (cid, a.suite_cap))
            continue
        cfg = {"permissions": {"additionalDirectories": [str(root)]}} if settings_mode == "adddir" else {}
        home = Path(tempfile.mkdtemp(prefix="manual-home-"))
        try:
            for sub in ("cc", "xdg", "tmp"):
                (home / sub).mkdir()
            cmd = ["claude", "-p", prompt, "--plugin-dir", str(PLUGIN), "--settings", json.dumps(cfg), "--allowedTools"] + grants + [
                   "--output-format", "stream-json", "--verbose", "--max-budget-usd", cap]
            p = subprocess.run(cmd, cwd=str(cwd), env=isolated_env(home, token), capture_output=True, text=True, timeout=420)
            stdout = p.stdout.replace(token, "[REDACTED]")
            (out / (cid + ".jsonl")).write_text(stdout)
        finally:
            shutil.rmtree(str(home), ignore_errors=True)
        calls, results, order, final = parse(stdout)
        cost = final.get("total_cost_usd") or 0.0
        total += cost
        ctx = Ctx(root, cwd, final.get("result"), calls, final.get("permission_denials", []), cost)
        res = checks_for(cid, ctx)
        ok = all(o for o, _ in res)
        summary.append((cid, label, ok, cost))
        print("=== %s  %s  [%s]  cost=%.4f turns=%s" % (cid, label, "PASS" if ok else "CHECK", cost, final.get("num_turns")))
        for _id, name, arg, who in order:
            print("  [%s] %s %s\n      -> %s" % (who, name, short(arg, 150), results.get(_id, "(no result)")))
        print("  denials: %s" % short(json.dumps(final.get("permission_denials", [])), 300))
        for ok1, what in res:
            print("  %s %s" % ("ok  " if ok1 else "FAIL", what))
        print("  FINAL: %s" % short(final.get("result") or "(none)", 900))
        tree = subprocess.run(["git", "status", "--short"], cwd=str(root), capture_output=True, text=True).stdout.strip().replace("\n", "; ") if (root / ".git").exists() or (root / "HEAD").exists() else "(no work tree)"
        print("  git status after: %s\n" % (tree or "clean"))
        if p.returncode not in (0, None) and not final:
            print("  exit %s stderr: %s" % (p.returncode, p.stderr.replace(token, "[REDACTED]")[-300:]))
    if not a.dry_run:
        print("SUMMARY (heuristic checks only, read the digests): %d runs, %d CHECK, total estimated cost %.4f" %
              (len(summary), sum(1 for _, _, ok, _ in summary if not ok), total))
        for cid, label, ok, cost in summary:
            print("  %s %-5s %s (%.4f)" % (cid, "PASS" if ok else "CHECK", label, cost))


if __name__ == "__main__":
    main()
