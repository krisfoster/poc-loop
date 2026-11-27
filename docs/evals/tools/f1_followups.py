#!/usr/bin/env python3
"""F1 follow-up checks for /spike-loop:poc-build (docs/evals/findings.md, F1). Paid, headless, one run each.

R1: a repo with no remote, one local commit after the first and one uncommitted file.
R2: a repo with a remote, one unpushed commit, and `worktree.baseRef: "head"` in the settings.
R3: the same with no setting (the control: the worktree should lack the unpushed commit).

Each run reports: the worktrees under .claude/worktrees/, which commit the worktree branch started
from, whether it holds the local commit, whether the main tree was touched, and the final text.
Isolation and token handling are those of docs/layout/tools/probes/probe_run.py.

Usage: python3 f1_followups.py --work DIR --out DIR --evals-repo PATH [--only R1 R2] [--dry-run]
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "docs" / "layout" / "tools" / "probes"))
import probe_run  # noqa: E402

MAX_COST = "0.75"
TOOLS = ["Agent", "Read", "Write", "Edit", "Glob", "Grep", "Bash"]
TASK = "/spike-loop:poc-build Create hello.txt at the repo root containing the single word hi | done when hello.txt exists and contains hi"


def git(cwd, *args):
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(cwd), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull}
    r = subprocess.run(["git", "-c", "user.email=probe@example.test", "-c", "user.name=probe", *args],
                       cwd=str(cwd), env=env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("git %s failed: %s" % (" ".join(args), r.stderr.strip()[:200]))
    return r.stdout.strip()


def fixture(root, remote):
    root.mkdir(parents=True)
    git(root, "init", "-q", "-b", "main")
    (root / "README.md").write_text("# fixture\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "A: first")
    if remote:
        bare = root.parent / "origin.git"
        git(root.parent, "init", "-q", "--bare", "-b", "main", str(bare))
        git(root, "remote", "add", "origin", str(bare))
        git(root, "push", "-q", "-u", "origin", "main")
        git(root, "remote", "set-head", "origin", "main")
    (root / "local.txt").write_text("a local commit, not pushed\n")
    git(root, "add", "local.txt")
    git(root, "commit", "-q", "-m", "B: local, unpushed")
    (root / "dirty.txt").write_text("uncommitted\n")
    return {"A": git(root, "rev-parse", "--short", "HEAD~1"), "B": git(root, "rev-parse", "--short", "HEAD")}


def report(root, shas):
    print("  main tree status: %s" % (git(root, "status", "--porcelain").replace("\n", " | ") or "clean"))
    print("  hello.txt in main tree: %s" % (root / "hello.txt").exists())
    wts = [l[len("worktree "):] for l in git(root, "worktree", "list", "--porcelain").splitlines()
           if l.startswith("worktree ")][1:]
    if not wts:
        print("  NO WORKTREE")
    for wt in wts:
        w = Path(wt)
        branch = git(w, "branch", "--show-current") or "(detached)"
        base = git(w, "merge-base", "HEAD", "main")
        which = {v: k for k, v in shas.items()}.get(base[:len(shas["B"])], base[:9])
        print("  worktree %s on %s" % (w.relative_to(root) if str(w).startswith(str(root)) else w, branch))
        print("    branched from commit %s (A = first, B = local unpushed)" % which)
        print("    holds local.txt: %s, holds dirty.txt: %s, hello.txt: %s" % (
            (w / "local.txt").exists(), (w / "dirty.txt").exists(),
            (w / "hello.txt").read_text().strip() if (w / "hello.txt").exists() else "missing"))
        print("    commits on branch not in main: %s" % (git(root, "log", "--oneline", branch, "--not", "main")
                                                        .replace("\n", " | ") or "none"))
        print("    uncommitted in worktree: %s" % (git(w, "status", "--porcelain").replace("\n", " | ") or "none"))


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
    out.mkdir(parents=True, exist_ok=True)
    runs = [("R1", False, {}), ("R2", True, {"worktree": {"baseRef": "head"}}), ("R3", True, {})]
    runs = [r for r in runs if not a.only or r[0] in a.only]
    roots = {}
    for label, remote, settings in runs:
        roots[label] = (work / label.lower() / "repo", fixture(work / label.lower() / "repo", remote))
    if a.dry_run:
        for label, remote, settings in runs:
            print(label, "remote" if remote else "no remote", settings, roots[label][1])
        return
    sys.path.insert(0, str(Path(a.evals_repo) / "evals"))
    from harness import runner  # noqa: E402
    token, _ = runner.load_token(Path(a.evals_repo))
    print("claude --version:", subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip())
    import json
    for label, remote, settings in runs:
        root, shas = roots[label]
        home = Path(tempfile.mkdtemp(prefix="f1-home-"))
        try:
            for sub in ("cc", "xdg", "tmp"):
                (home / sub).mkdir()
            cmd = ["claude", "-p", TASK, "--plugin-dir", str(REPO), "--settings", json.dumps(settings),
                   "--allowedTools", *TOOLS, "--output-format", "stream-json", "--verbose", "--max-budget-usd", MAX_COST]
            p = subprocess.run(cmd, cwd=str(root), env=probe_run.isolated_env(home, token),
                               capture_output=True, text=True, timeout=600)
            stdout = p.stdout.replace(token, "[REDACTED]")
            (out / (label + ".jsonl")).write_text(stdout)
            probe_run.digest("%s (%s, settings %s)" % (label, "remote" if remote else "no remote", settings), stdout)
            report(root, shas)
            print()
        finally:
            shutil.rmtree(str(home), ignore_errors=True)


if __name__ == "__main__":
    main()
