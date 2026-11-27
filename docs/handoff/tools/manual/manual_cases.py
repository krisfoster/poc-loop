#!/usr/bin/env python3
"""Manual cases for docs/handoff/plan.md task 3.3: the real poc-checkpoint and poc-help, headless.

15 cases, 17 single runs (two cases are two sessions). Paid. Isolation, token handling and the
event digest are those of docs/layout/tools/probes/probe_run.py. Each case builds its own scratch
repo, runs the command, and grades from the files on disk and the final text. The expected State
values come from docs/handoff/tools/check_git_rules.py, so the grade is the spec's rules, not a guess.

Usage: python3 manual_cases.py --work DIR --out DIR --evals-repo PATH [--only M01 ...] [--dry-run]
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "docs" / "layout" / "tools" / "probes"))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent / "probes"))
import probe_run  # noqa: E402
import check_git_rules as rules  # noqa: E402
import run_probes as P  # noqa: E402  (fixture texts)

MAX_COST = "0.25"
HELP_TOOLS = ["Read", "Glob", "Grep", "Bash(git *)", "Bash(date *)", "Bash(date)"]
CP_TOOLS = HELP_TOOLS + ["Edit", "Write", "Bash(tail *)"]
TODAY = datetime.date.today().isoformat()
RESUME = "add a 5-minute timestamp tolerance to verify_signature in app.py, then run ./verify.sh"


def git(root, *args):
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(root), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull}
    r = subprocess.run(["git", "-c", "user.email=probe@example.test", "-c", "user.name=probe", *args],
                       cwd=str(root), env=env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("git %s failed in %s: %s" % (args[0], root, r.stderr.strip()[:200]))
    return r.stdout


def base(root, layout="new", repo=True, commit=True, wiring=True):
    docs = root / "poc-spec" if layout == "new" else root
    docs.mkdir(parents=True, exist_ok=True)
    (root / "app.py").write_text(P.APP)
    (root / "verify.sh").write_text("#!/usr/bin/env bash\npython3 -c 'import app'\n")
    os.chmod(str(root / "verify.sh"), 0o755)
    (docs / "POC.md").write_text(P.POC)
    (docs / "LOG.md").write_text(P.LOG_HEAD)
    if wiring and layout == "new":
        (root / "CLAUDE.md").write_text("# CLAUDE.md\n\n" + P.WIRING + "\n")
    if repo:
        git(root, "init", "-q", "-b", "main")
        if commit:
            git(root, "add", "-A")
            git(root, "commit", "-q", "-m", "PoC start")
            git(root, "checkout", "-q", "-b", "spike-hmac")
    return docs


def add_entry(docs, title, decision, state=None, when="2026-11-27 10:00"):
    lines = ["", "## %s %s" % (when, title), "- Tried: the vendor samples", "- Learned: HMAC over the raw body works",
             "- Dead ends: none", "- Decision: %s" % decision,
             "- Next question: does a 5-minute timestamp tolerance reject replays?", "- Later:"]
    if state:
        lines.append(state)
    with open(str(docs / "LOG.md"), "a") as fh:
        fh.write("\n".join(lines) + "\n")


def record(root, docs, layout="new", decision="iterate", resume=RESUME, title="Signature check works"):
    values, _ = rules.gather(str(root), layout)
    state = rules.state_line(values, resume=resume)
    add_entry(docs, title, decision, state)
    return state


def snapshot(root):
    h = {}
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and ".git" not in p.relative_to(root).parts:
            h[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return h


# ---------- cases: (id, title, setup(root) -> ctx, prompt, tools, grade(root, ctx, final) -> [(ok, what)]) ----------

def last_line(final, prefix="Next:"):
    lines = [l.strip().strip("*") for l in (final or "").splitlines() if l.strip().strip("*").startswith(prefix)]
    return lines[-1] if lines else ""


def help_grade(kind, next_has=None, reason=None):
    def grade(root, ctx, final):
        out = []
        f = final or ""
        low = f.lower()
        unknown = re.search(r"state\W{0,3}(is\W)?unknown", low)
        if kind == "fresh":
            out.append(("may be stale" not in low and not unknown, "fresh: not stale, not unknown"))
            out.append(("resume:" in low, "fresh: prints a Resume: line (wording)"))
        elif kind == "stale":
            out.append(("may be stale" in low, "stale: prints 'may be stale'"))
            if reason:
                out.append((any(r in low for r in reason), "stale reason names one of %s" % (reason,)))
        else:
            out.append((bool(unknown) and "may be stale" not in low, "unknown: says the State is unknown"))
        nxt = last_line(f)
        out.append((bool(nxt), "ends with a Next: line"))
        out.append(("/clear" not in nxt, "Next: has no /clear"))
        if next_has:
            out.append((next_has in nxt, "Next: names %s" % next_has))
        out.append((snapshot(root) == ctx["snap"], "poc-help changed no file"))
        return out
    return grade


def with_snap(setup):
    def wrapped(root):
        ctx = setup(root) or {}
        ctx["snap"] = snapshot(root)
        return ctx
    return wrapped


def s_fresh(root):
    docs = base(root)
    (root / "scratch.py").write_text("x = 1\n")
    record(root, docs)


def s_code_commit(root):
    docs = base(root)
    record(root, docs)
    (root / "app.py").write_text(P.APP + "\nTOLERANCE = 300\n")
    git(root, "add", "app.py")
    git(root, "commit", "-q", "-m", "tolerance")


def s_docs_commit(root):
    docs = base(root)
    record(root, docs)
    git(root, "add", "poc-spec/LOG.md")
    git(root, "commit", "-q", "-m", "log")


def s_later_entry(root):
    docs = base(root)
    record(root, docs)
    add_entry(docs, "Tried a replay", "none yet", when="2026-11-27 12:00")


def s_old_log(root):
    docs = base(root)
    add_entry(docs, "Signature check works", "iterate")


def s_no_commits(root):
    docs = base(root, commit=False)
    record(root, docs)


def s_not_repo(root):
    docs = base(root, repo=False)
    record(root, docs)


def s_detached(root):
    docs = base(root)
    record(root, docs)
    git(root, "checkout", "-q", "--detach")


def s_old_layout(root):
    docs = base(root, layout="old")
    record(root, docs, layout="old")
    (root / "replay.py").write_text("# new code after the checkpoint\n")


def s_harden(root):
    docs = base(root)
    record(root, docs, decision="harden", resume="/spike-loop:poc-harden", title="Ready to harden")
    (root / "SUMMARY.md").write_text("# Summary\n\nThe signature check works.\n")


def s_reset(root):
    docs = base(root)
    (root / "app.py").write_text(P.APP + "\nTOLERANCE = 300\n")
    git(root, "add", "app.py")
    git(root, "commit", "-q", "-m", "two")
    record(root, docs)
    log = (docs / "LOG.md").read_text()  # the uncommitted entry must survive the reset
    git(root, "reset", "-q", "--hard", "HEAD~1")
    (docs / "LOG.md").write_text(log)


# poc-checkpoint cases

def s_iterate(root):
    docs = base(root)
    add_entry(docs, "Signature check works", "none yet")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "log")
    (root / "scratch_vectors.py").write_text("# not committed\n")
    wt = root / ".claude" / "worktrees" / "agent-1"
    git(root, "worktree", "add", "-q", "-b", "worktree-agent-1", str(wt))
    (wt / "replay.py").write_text("# replay check\n")
    git(wt, "add", "replay.py")
    git(wt, "commit", "-q", "-m", "replay")
    return {}


def g_iterate(root, ctx, final):
    out = []
    log = (root / "poc-spec" / "LOG.md").read_text()
    states = [l for l in log.splitlines() if l.startswith("- State: ")]
    out.append((len(states) == 1, "exactly one State line written"))
    if states:
        try:
            st = rules.parse_state(states[0])
        except AssertionError:
            st = None
        out.append((st is not None, "State line parses into the six fields in order"))
        if st:
            want, _ = rules.gather(str(root), "new")
            for f in ("branch", "at", "uncommitted", "unmerged worktrees"):
                out.append((st[f] == want[f], "%s: %r (rules give %r)" % (f, st[f], want[f])))
            out.append(("/" not in st["unmerged worktrees"] or "worktree-agent-1" in st["unmerged worktrees"]
                        and ".claude" not in st["unmerged worktrees"], "no worktree path in State"))
        entries = re.split(r"(?m)^## ", log)
        out.append((entries[-1].rstrip().splitlines()[-1].startswith("- State: "), "State is the last line of the last entry"))
        out.append(("- Decision: iterate" in entries[-1], "last entry's Decision is iterate"))
    nxt = last_line(final)
    out.append(("/clear" in nxt and "/spike-loop:poc-help" in nxt, "Next: /clear, then /spike-loop:poc-help (%r)" % nxt[:80]))
    out.append((not (root / "SUMMARY.md").exists(), "no SUMMARY.md on iterate"))
    out.append((git(root, "log", "--oneline").count("\n") == 2, "made no commit"))
    return out


def s_pause(root):
    docs = base(root)
    add_entry(docs, "Spec started", "none yet")
    (docs / "handoffs").mkdir()
    (docs / "handoffs" / ("%s-replay-spec.md" % TODAY)).write_text("# An earlier hand-off, must not be overwritten\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "log")
    return {"old": (docs / "handoffs" / ("%s-replay-spec.md" % TODAY)).read_text()}


def g_pause(root, ctx, final):
    out = []
    hd = root / "poc-spec" / "handoffs"
    first = hd / ("%s-replay-spec.md" % TODAY)
    second = hd / ("%s-replay-spec-2.md" % TODAY)
    out.append((first.read_text() == ctx["old"], "the existing hand-off was not overwritten"))
    out.append((second.exists(), "hand-off written as %s" % second.name))
    if second.exists():
        n = len(second.read_text().splitlines())
        out.append((n <= 40, "hand-off is at most 40 lines (%d)" % n))
    log = (root / "poc-spec" / "LOG.md").read_text()
    states = [l for l in log.splitlines() if l.startswith("- State: ")]
    out.append((len(states) == 1, "one State line"))
    if states:
        out.append((second.name in states[0], "resume: names the -2 file"))
        resume = states[0].split("; resume: ", 1)[-1]
        out.append(("poc-help" not in resume and "/clear" not in resume, "resume: is the work, not poc-help or /clear (%r)" % resume[-60:]))
    out.append(("- Decision: pause" in re.split(r"(?m)^## ", log)[-1], "Decision is pause"))
    nxt = last_line(final)
    out.append(("/clear" in nxt and "/spike-loop:poc-help" in nxt, "Next: /clear, then /spike-loop:poc-help"))
    return out


def g_pause_help(root, ctx, final):
    out = help_grade("fresh")(root, ctx, final)
    out.append(("/spike-loop:poc-help" not in last_line(final or ""), "Next: is not poc-help itself"))
    out.append(("milli" in (final or "").lower() or "x-vendor-ts" in (final or "").lower() or "replay" in (final or "").lower(),
                "summarises the hand-off"))
    return out


def s_bad_topic(root):
    docs = base(root)
    add_entry(docs, "Spec started", "none yet")
    return {"log": (docs / "LOG.md").read_text()}


def g_bad_topic(root, ctx, final):
    hd = root / "poc-spec" / "handoffs"
    files = list(hd.rglob("*")) if hd.exists() else []
    outside = [p for p in root.rglob("*") if "secrets" in p.name.lower()]
    nxt = last_line(final)
    return [(not files, "no hand-off file written"),
            (not outside, "nothing written outside handoffs/"),
            ("refus" in (final or "").lower() or "another topic" in (final or "").lower()
             or "not allowed" in (final or "").lower() or "invalid" in (final or "").lower(), "the topic is refused"),
            ("/clear" not in nxt, "Next: has no /clear")]


def s_failed_write(root):
    docs = base(root)
    add_entry(docs, "Signature check works", "none yet")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "log")
    os.chmod(str(docs / "LOG.md"), 0o444)
    os.chmod(str(docs), 0o555)  # a write by rename must fail too
    return {"log": (docs / "LOG.md").read_text()}


def g_failed_write(root, ctx, final):
    nxt = last_line(final)
    log = (root / "poc-spec" / "LOG.md").read_text()
    return [(log == ctx["log"], "LOG.md unchanged (it is read-only)"),
            ("/clear" not in (final or ""), "no /clear anywhere in the reply"),
            ("poc-checkpoint" in nxt, "Next: names the checkpoint to try again (%r)" % nxt[:80])]


HELP = "/spike-loop:poc-help"
CASES = [
    # id, title, setup, prompt, tools, grade, chain (reuse the previous case's repo)
    ("M01a", "checkpoint iterate, uncommitted file and an unmerged worktree", s_iterate,
     "/spike-loop:poc-checkpoint iterate", CP_TOOLS, g_iterate, None),
    ("M01b", "fresh session after M01a: poc-help", None, HELP, HELP_TOOLS, help_grade("fresh"), "M01a"),
    ("M02", "poc-help, fresh State", with_snap(s_fresh), HELP, HELP_TOOLS, help_grade("fresh", "5-minute"), None),
    ("M03", "poc-help after a code commit", with_snap(s_code_commit), HELP, HELP_TOOLS,
     help_grade("stale", "/spike-loop:poc-checkpoint iterate", ["commit"]), None),
    ("M04", "poc-help after a docs-only commit", with_snap(s_docs_commit), HELP, HELP_TOOLS, help_grade("fresh"), None),
    ("M05", "poc-help with a later poc-log entry", with_snap(s_later_entry), HELP, HELP_TOOLS, help_grade("unknown"), None),
    ("M06", "poc-help, old log without State", with_snap(s_old_log), HELP, HELP_TOOLS,
     help_grade("unknown", "/spike-loop:poc-checkpoint iterate"), None),
    ("M07", "poc-help, repo with no commits", with_snap(s_no_commits), HELP, HELP_TOOLS, help_grade("fresh"), None),
    ("M08", "poc-help, not a git repo", with_snap(s_not_repo), HELP, HELP_TOOLS, help_grade("fresh"), None),
    ("M09", "poc-help after moving to a detached HEAD", with_snap(s_detached), HELP, HELP_TOOLS,
     help_grade("stale", None, ["branch", "detached"]), None),
    ("M10", "poc-help, older root layout, new uncommitted code file", with_snap(s_old_layout), HELP, HELP_TOOLS,
     help_grade("stale", None, ["uncommitted", "replay.py"]), None),
    ("M11", "poc-help after harden with SUMMARY.md written", with_snap(s_harden), HELP, HELP_TOOLS,
     help_grade("fresh", "/spike-loop:poc-harden"), None),
    ("M12", "poc-help after a reset to before the recorded commit", with_snap(s_reset), HELP, HELP_TOOLS,
     help_grade("stale", None, ["reset", "history", "commit", "ancestor"]), None),
    ("M13a", "checkpoint pause replay-spec, name taken", s_pause, "/spike-loop:poc-checkpoint pause replay-spec",
     CP_TOOLS, g_pause, None),
    ("M13b", "fresh session after M13a: poc-help reads the hand-off", None, HELP, HELP_TOOLS, g_pause_help, "M13a"),
    ("M14", "checkpoint pause with a bad topic", s_bad_topic, "/spike-loop:poc-checkpoint pause ../secrets",
     CP_TOOLS, g_bad_topic, None),
    ("M15", "checkpoint iterate with a read-only LOG.md", s_failed_write, "/spike-loop:poc-checkpoint iterate",
     CP_TOOLS, g_failed_write, None),
]


def final_text(stdout):
    final = None
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        if ev.get("type") == "result":
            final = ev
    return final or {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evals-repo", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    work, out = Path(a.work), Path(a.out)
    if work.exists():
        shutil.rmtree(str(work))
    work.mkdir(parents=True)
    out.mkdir(parents=True, exist_ok=True)
    cases = [c for c in CASES if not a.only or c[0] in a.only or (c[6] and c[6] in a.only)]
    roots, ctxs = {}, {}
    for cid, title, setup, prompt, tools, grade, chain in cases:
        if chain:
            continue
        root = work / cid.lower() / "repo"
        root.mkdir(parents=True)
        ctxs[cid] = setup(root) or {}
        roots[cid] = root
    if a.dry_run:
        for cid, title, setup, prompt, tools, grade, chain in cases:
            r = roots.get(chain or cid)
            last = [l for l in (r / ("poc-spec" if (r / "poc-spec").exists() else ".") / "LOG.md").read_text().splitlines()
                    if l.startswith("- State:")]
            print("%-5s %-60s | %s | %s" % (cid, title, prompt, (last[-1][:110] if last else "(no State)")))
        return
    sys.path.insert(0, str(Path(a.evals_repo) / "evals"))
    from harness import runner  # noqa: E402
    token, _ = runner.load_token(Path(a.evals_repo))
    print("claude --version:", subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip())
    total, summary = 0.0, []
    for cid, title, setup, prompt, tools, grade, chain in cases:
        root = roots[chain or cid]
        ctx = dict(ctxs.get(chain or cid, {}))
        if chain:
            ctx["snap"] = snapshot(root)
        home = Path(tempfile.mkdtemp(prefix="manual-home-"))
        try:
            for sub in ("cc", "xdg", "tmp"):
                (home / sub).mkdir()
            cmd = ["claude", "-p", prompt, "--plugin-dir", str(REPO), "--allowedTools", *tools,
                   "--output-format", "stream-json", "--verbose", "--max-budget-usd", MAX_COST]
            p = subprocess.run(cmd, cwd=str(root), env=probe_run.isolated_env(home, token),
                               capture_output=True, text=True, timeout=420)
            stdout = p.stdout.replace(token, "[REDACTED]")
            (out / (cid + ".jsonl")).write_text(stdout)
            probe_run.digest("%s %s" % (cid, title), stdout)
            res = final_text(stdout)
            total += res.get("total_cost_usd") or 0
            checks = grade(root, ctx, res.get("result"))
            for ok, what in checks:
                print("  %s %s" % ("PASS" if ok else "FAIL", what))
            npass = sum(1 for ok, _ in checks if ok)
            summary.append((cid, title, npass, len(checks), res.get("total_cost_usd")))
            print()
        finally:
            shutil.rmtree(str(home), ignore_errors=True)
            if (root / "poc-spec").exists():
                os.chmod(str(root / "poc-spec"), 0o755)
            if (root / "poc-spec" / "LOG.md").exists():
                os.chmod(str(root / "poc-spec" / "LOG.md"), 0o644)
    print("=== summary")
    for cid, title, npass, n, cost in summary:
        print("%-5s %d/%d  $%.3f  %s" % (cid, npass, n, cost or 0, title))
    print("total cost: $%.3f" % total)


if __name__ == "__main__":
    main()
