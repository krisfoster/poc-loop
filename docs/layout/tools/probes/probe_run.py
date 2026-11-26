#!/usr/bin/env python3
"""Behaviour probes for docs/layout plan tasks 0.2 and 0.3.

Runs a throwaway plugin (./plugin) through headless `claude -p` from several directories of a throwaway repo, one
run per probe, and prints what each run did: the working directory in the init event, every tool call and its
result, permission denials, cost and the final text. These are paid runs on the user's subscription (a few cents
in all). Isolation follows evals/harness/runner.py: temporary HOME, CLAUDE_CONFIG_DIR and XDG_CONFIG_HOME, only
PATH inherited. The token is read by the harness helper and never printed or saved.

Usage: python3 probe_run.py --work DIR --out DIR --evals-repo PATH [--only LABEL ...] [--dry-run]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PLUGIN = HERE / "plugin"
MAX_COST = "0.25"
BLOCK_READS = {"permissions": {"blockReadsOutsideWorkingDirectories": True}}


def build_fixture(work):
    """repo/ with verify.sh, poc-spec/, sub/deep, an untracked nested git repo, and a linked worktree wt/."""
    work = Path(work)
    if work.exists():
        shutil.rmtree(str(work))
    repo = work / "repo"
    (repo / "poc-spec").mkdir(parents=True)
    (repo / "sub" / "deep").mkdir(parents=True)
    (repo / "verify.sh").write_text('#!/usr/bin/env bash\necho "VERIFY_RAN_IN=$(pwd)"\n')
    os.chmod(str(repo / "verify.sh"), 0o755)
    (repo / "poc-spec" / "POC.md").write_text("# POC: probe fixture\n")
    (repo / "poc-spec" / "LOG.md").write_text("# Log\n")
    (repo / "sub" / "deep" / ".keep").write_text("")

    def git(args, cwd):
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(work), "GIT_CONFIG_NOSYSTEM": "1"}
        r = subprocess.run(["git", "-c", "user.email=probe@example.test", "-c", "user.name=probe"] + args,
                           cwd=str(cwd), env=env, capture_output=True, text=True)
        if r.returncode != 0:
            raise SystemExit("git %s failed: %s" % (args[0], r.stderr.strip()[:200]))

    git(["init", "-q", "-b", "main"], repo)
    git(["add", "-A"], repo)
    git(["commit", "-q", "-m", "fixture"], repo)
    nested = repo / "nested"
    nested.mkdir()
    (nested / "README").write_text("nested repo\n")
    git(["init", "-q", "-b", "main"], nested)
    git(["add", "-A"], nested)
    git(["commit", "-q", "-m", "nested"], nested)
    git(["worktree", "add", "-q", "-b", "probe-wt", str(work / "wt")], repo)
    return repo


def runs(work):
    repo = work / "repo"
    deep = repo / "sub" / "deep"
    broad = ["Bash", "Read"]
    root = str(repo)
    # label, cwd, skill, args, allowed tools, extra settings (dict or None)
    return [
        ("R1-main-from-subdir", deep, "probe-main", root, broad, None),
        ("R2-fork-from-subdir", deep, "probe-fork", root, broad, None),
        ("R3-main-from-nested-repo", repo / "nested", "probe-main", "%s %s" % (root, deep), broad, None),
        ("R4-main-from-linked-worktree", work / "wt", "probe-main", "%s %s" % (root, deep), broad, None),
        ("R5-inject-main-from-subdir", deep, "probe-inject", "", ["Read"], None),
        ("R6-inject-fork-from-subdir", deep, "probe-inject-fork", "", broad, None),
        ("R7-inject-main-shell-disabled", deep, "probe-inject", "", ["Read"], {"disableSkillShellExecution": True}),
        ("R8-read-outside-start-dir", deep, "probe-read", root, ["Read"], BLOCK_READS),
        ("R9-grant-verify-only", deep, "probe-grant", root, ["Bash(./verify.sh)"], None),
        ("R10-grant-cd-only", deep, "probe-grant", root, ["Bash(cd *)"], None),
        ("R11-grant-cd-and-verify", deep, "probe-grant", root, ["Bash(cd * && ./verify.sh)"], None),
        # second batch, after the first batch showed cd outside the launch directory is blocked under narrow grants
        ("R2b-fork-sequential", deep, "probe-fork-seq", root, broad, None),
        ("R12-grant-cd-and-verify-separately", deep, "probe-grant", root, ["Bash(cd *)", "Bash(./verify.sh)"], None),
        ("R13-grant-verify-plus-add-dir-root", deep, "probe-grant", root, ["Bash(cd *)", "Bash(./verify.sh)"], {"permissions": {"additionalDirectories": [root]}}),
        ("R14-absolute-path-verify", deep, "probe-abs", root, ["Bash(*verify.sh)"], None),
        ("R15-broad-bash-compound", deep, "probe-grant", root, ["Bash"], None),
        ("R16-read-root-file-default-settings", deep, "probe-read", root, ["Read"], None),
    ]


def isolated_env(home, token):
    home = str(home)
    return {"PATH": os.environ.get("PATH", ""), "TERM": "xterm", "HOME": home,
            "CLAUDE_CONFIG_DIR": os.path.join(home, "cc"), "XDG_CONFIG_HOME": os.path.join(home, "xdg"),
            "TMPDIR": os.path.join(home, "tmp"), "CLAUDE_CODE_OAUTH_TOKEN": token}


def short(value, n=160):
    if isinstance(value, list):
        value = " ".join(b.get("text", "") if isinstance(b, dict) else str(b) for b in value)
    value = str(value).replace("\n", " | ")
    return value if len(value) <= n else value[:n] + "..."


def digest(label, stdout):
    init, calls, results, final = {}, [], {}, {}
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        t = ev.get("type")
        if t == "system" and ev.get("subtype") == "init":
            init = ev
        elif t == "assistant":
            for b in ev.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    inp = b.get("input", {})
                    calls.append((b.get("id"), b.get("name"), inp.get("command") or inp.get("file_path") or json.dumps(inp)[:100],
                                  "sub" if ev.get("parent_tool_use_id") else "main"))
        elif t == "user":
            for b in ev.get("message", {}).get("content", []):
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    results[b.get("tool_use_id")] = ("ERROR " if b.get("is_error") else "") + short(b.get("content", ""))
        elif t == "result":
            final = ev
    print("=== %s" % label)
    print("init cwd=%s model=%s plugins=%s" % (init.get("cwd"), init.get("model"), [p.get("name") for p in init.get("plugins", [])]))
    for cid, name, cmd, who in calls:
        print("  [%s] %s %s\n      -> %s" % (who, name, short(cmd, 140), results.get(cid, "(no result)")))
    print("denials=%s cost=%s turns=%s" % (json.dumps(final.get("permission_denials", []))[:300], final.get("total_cost_usd"), final.get("num_turns")))
    print("FINAL: %s" % (final.get("result") or "(none)")[:1200])
    print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evals-repo", required=True, help="checkout holding evals/ (for the token helper only)")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    work, out = Path(a.work), Path(a.out)
    build_fixture(work)
    out.mkdir(parents=True, exist_ok=True)
    plan = [r for r in runs(work) if not a.only or any(r[0].startswith(o) for o in a.only)]
    if a.dry_run:
        for label, cwd, skill, args, allowed, settings in plan:
            print(label, "| cwd:", str(cwd).replace(str(work), "<work>"), "| /probe:%s" % skill, "|", allowed, "|", settings)
        return
    sys.path.insert(0, str(Path(a.evals_repo) / "evals"))
    from harness import runner  # noqa: E402
    token, _ = runner.load_token(Path(a.evals_repo))
    print("claude --version:", subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip())
    for label, cwd, skill, args, allowed, settings in plan:
        home = Path(tempfile.mkdtemp(prefix="probe-home-"))
        try:
            for sub in ("cc", "xdg", "tmp"):
                (home / sub).mkdir()
            cfg = dict(settings or {})
            cmd = ["claude", "-p", "/probe:%s %s" % (skill, args), "--plugin-dir", str(PLUGIN),
                   "--settings", json.dumps(cfg), "--allowedTools"] + allowed + [
                   "--output-format", "stream-json", "--verbose", "--max-budget-usd", MAX_COST]
            p = subprocess.run(cmd, cwd=str(cwd), env=isolated_env(home, token), capture_output=True, text=True, timeout=240)
            stdout = p.stdout.replace(token, "[REDACTED]")
            (out / (label + ".jsonl")).write_text(stdout)
            digest(label, stdout)
            if p.returncode != 0:
                print("  exit code %s, stderr tail: %s" % (p.returncode, p.stderr.replace(token, "[REDACTED]")[-300:]))
        finally:
            shutil.rmtree(str(home), ignore_errors=True)


if __name__ == "__main__":
    main()
