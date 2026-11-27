#!/usr/bin/env python3
"""Phase 0 probes for docs/prereqs/plan.md (P1, P2, P3). Paid, single runs, headless, Haiku.

Builds a throwaway plugin (in --work, once at a path with no space and once at a path with one), with a
checker stand-in at scripts/x that prints PROBE_CHECKER_RAN, and runs:

  P1-control   skill with no allowed-tools: the call should be denied (shows the probe can fail)
  P1-quoted    allowed-tools lists both spellings, the body runs the quoted form
  P1-unquoted  same, the body runs the unquoted form
  P1-space-*   the same two, with the plugin under a directory whose name has a space
  P2-fork      context: fork skill with allowed-tools; its agent body says to skip its own check when told
  P3-hidden    no skill; PATH built from symlinks with python3, python3.* and python left out

--allowedTools never grants the checker, so any run of it in P1 and P2 comes from the skill's allowed-tools.
Isolation and the token: docs/layout/tools/probes/probe_run.py. The token is never printed or saved.

Usage: python3 run_probes.py --work DIR --out DIR [--only P1 ...] [--dry-run]
"""
import argparse
import fnmatch
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "docs" / "layout" / "tools" / "probes"))
import probe_run  # noqa: E402

MAX_COST = "0.25"
MODEL = "claude-haiku-5-5"
RULES = ['Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/x *)', 'Bash(sh "${CLAUDE_PLUGIN_ROOT}/scripts/x" *)']
QUOTED = 'sh "${CLAUDE_PLUGIN_ROOT}/scripts/x" %s'
UNQUOTED = 'sh ${CLAUDE_PLUGIN_ROOT}/scripts/x %s'


def skill(name, body, rules=None, fork=False):
    fm = ["---", "name: %s" % name, "description: probe", "disable-model-invocation: true"]
    if fork:
        fm += ["context: fork", "agent: probeplug:probe-agent"]
    if rules:
        fm += ["allowed-tools:"] + ["  - %s" % r for r in rules]
    return "\n".join(fm + ["---", body, ""])


def build_plugin(root):
    if root.exists():
        shutil.rmtree(str(root))
    (root / ".claude-plugin").mkdir(parents=True)
    (root / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "probeplug", "version": "0.0.1"}))
    (root / "scripts").mkdir()
    (root / "scripts" / "x").write_text('#!/bin/sh\necho "PROBE_CHECKER_RAN $*"\n')
    ask = ("Run this exact command with the Bash tool, once, and nothing else: `%s`. "
           "Then report its output verbatim, or the exact error if it was refused.")
    skills = {
        "control": skill("control", ask % (QUOTED % "control")),
        "quoted": skill("quoted", ask % (QUOTED % "quoted"), RULES),
        "unquoted": skill("unquoted", ask % (UNQUOTED % "unquoted"), RULES),
        "fork": skill("fork", (ask % (QUOTED % "fork-skill")) + " Prerequisites checked.", RULES, fork=True),
    }
    for name, text in skills.items():
        (root / "skills" / name).mkdir(parents=True)
        (root / "skills" / name / "SKILL.md").write_text(text)
    (root / "agents").mkdir()
    (root / "agents" / "probe-agent.md").write_text(
        "---\nname: probe-agent\ndescription: probe agent\ntools: Bash, Read\nmodel: haiku\n---\n"
        "**Prerequisites.** Before anything else, run `%s`. Skip this if the command that started you, or your "
        "brief, says prerequisites were checked.\n\nThen do the task you were given.\n" % (QUOTED % "agent"))


def hidden_path(dest, hide):
    """A directory of symlinks to every executable on PATH except names matching a hide pattern."""
    dest.mkdir(parents=True)
    seen = set()
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d or not os.path.isdir(d):
            continue
        for name in sorted(os.listdir(d)):
            p = os.path.join(d, name)
            if name in seen or not os.access(p, os.X_OK) or os.path.isdir(p):
                continue
            seen.add(name)
            if any(fnmatch.fnmatch(name, h) for h in hide):
                continue
            os.symlink(p, str(dest / name))
    return str(dest)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    work, out = Path(a.work), Path(a.out)
    if work.exists():
        shutil.rmtree(str(work))
    plain, spaced = work / "plugin", work / "with space" / "plugin"
    build_plugin(plain)
    build_plugin(spaced)
    ws = work / "ws"
    ws.mkdir()
    (ws / "README.md").write_text("probe workspace\n")
    pathdir = hidden_path(work / "hidden-bin", ["python3", "python3.*", "python", "python[0-9]*"])
    p3_prompt = ("Run these two commands with the Bash tool, one call each, and report each output or error "
                 "verbatim: `command -v python3` and `python3 --version`.")
    runs = [  # label, plugin dir, prompt, allowed tools, PATH override
        ("P1-control", plain, "/probeplug:control", ["Read"], None),
        ("P1-quoted", plain, "/probeplug:quoted", ["Read"], None),
        ("P1-unquoted", plain, "/probeplug:unquoted", ["Read"], None),
        ("P1-space-quoted", spaced, "/probeplug:quoted", ["Read"], None),
        ("P1-space-unquoted", spaced, "/probeplug:unquoted", ["Read"], None),
        ("P2-fork", plain, "/probeplug:fork", ["Read"], None),
        ("P3-hidden", plain, p3_prompt, ["Read", "Bash(command -v *)", "Bash(python3 *)"], pathdir),
    ]
    runs = [r for r in runs if not a.only or any(r[0].startswith(o) for o in a.only)]
    if a.dry_run:
        for r in runs:
            print(r[0], str(r[1]).replace(str(work), "<work>"), r[2][:60], r[3], "hidden PATH" if r[4] else "")
        return
    out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, str(REPO / "evals"))
    from harness import runner  # noqa: E402
    token, _ = runner.load_token(REPO)
    print("claude --version:", subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip())
    for label, plugin, prompt, allowed, path in runs:
        home = Path(tempfile.mkdtemp(prefix="prereq-probe-home-"))
        try:
            for sub in ("cc", "xdg", "tmp"):
                (home / sub).mkdir()
            env = probe_run.isolated_env(home, token)
            if path:
                env["PATH"] = path
            claude = shutil.which("claude")
            cmd = [claude, "-p", prompt, "--plugin-dir", str(plugin), "--model", MODEL, "--settings", "{}",
                   "--allowedTools"] + allowed + ["--output-format", "stream-json", "--verbose",
                                                 "--max-budget-usd", MAX_COST]
            p = subprocess.run(cmd, cwd=str(ws), env=env, capture_output=True, text=True, timeout=240)
            stdout = p.stdout.replace(token, "[REDACTED]")
            (out / (label + ".jsonl")).write_text(stdout)
            probe_run.digest(label, stdout.replace(str(work), "<work>"))
            print("  checker ran: %s" % ("PROBE_CHECKER_RAN" in stdout and "tool_result" in stdout))
            if p.returncode != 0:
                print("  exit %s, stderr tail: %s" % (p.returncode, p.stderr.replace(token, "[REDACTED]")[-300:]))
        finally:
            shutil.rmtree(str(home), ignore_errors=True)


if __name__ == "__main__":
    main()
