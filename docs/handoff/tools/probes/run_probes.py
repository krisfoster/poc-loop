#!/usr/bin/env python3
"""Phase 0 probes for docs/handoff/plan.md (P0, P1a, P1b, P1c, P2, P4). Paid, single runs, headless.

Reuses the isolation and the event digest of docs/layout/tools/probes/probe_run.py (temporary HOME,
CLAUDE_CONFIG_DIR and XDG_CONFIG_HOME, only PATH inherited; the token comes from the eval harness
helper and is never printed or saved). The State lines in the fixtures are produced by
docs/handoff/tools/check_git_rules.py, so they are what the spec's rules give for that repo.

Usage: python3 run_probes.py --work DIR --out DIR --evals-repo PATH [--only P1a ...] [--dry-run]
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
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "docs" / "layout" / "tools" / "probes"))
sys.path.insert(0, str(HERE.parent))
import probe_run  # noqa: E402  (isolated_env, digest)
import check_git_rules as rules  # noqa: E402

MAX_COST = "0.25"
READ_ONLY = ["Read", "Glob", "Grep"]
TASK = "Continue with the next step."
STATUS = "Where are we and what should I do next?"
HANDOFF = "2026-11-27-replay-spec.md"

WIRING = ("Docs folder: `poc-spec/`. All paths are relative to the repo root. At session start read "
          "`poc-spec/POC.md` and the last 40 lines of `poc-spec/LOG.md`. Stay within `poc-spec/POC.md`. "
          "Park new ideas in `poc-spec/LOG.md` under Later. Never claim done without the output of "
          "`./verify.sh` or the manual check. Hand-offs, specs and plans for this PoC go under `poc-spec/`.")

POC = """# POC: webhook signature check

Started: 2026-11-26 10:00 | Timebox (first pass): 4 hours | Tier: 2 | Deal: none | Repo visibility: private

## Question
Can we verify the vendor's webhook signatures (HMAC-SHA256 over the raw body) and reject replays?

## Success check
`./verify.sh` passes: the three vendor samples verify, a tampered body fails, a replayed request fails.

## Assumptions and risks (riskiest first)
1. The signature covers the raw body, not parsed JSON.
2. The vendor's timestamp header is usable for replay protection.

## In scope
- verify_signature in app.py

## Out of scope
- Key rotation

## Manual check (only if verify.sh cannot do it)
none
"""

LOG_HEAD = """# Log

Append only. Newest entry last. Format per entry:

## 2026-11-26 10:00 PoC started
- Tried: nothing yet
- Learned: nothing yet
- Dead ends: none
- Decision: none yet
- Next question: does HMAC-SHA256 over the raw body match the vendor samples?
- Later:
"""

ITERATE_ENTRY = """
## 2026-11-26 16:30 HMAC check works on the vendor samples
- Tried: verify_signature against the three vendor samples
- Learned: all three pass with HMAC-SHA256 over the raw body
- Dead ends: hashing re-serialised JSON breaks the signature
- Decision: iterate
- Next question: does a 5-minute timestamp tolerance reject replayed requests?
- Later: key rotation
{state}
"""

PAUSE_ENTRY = """
## 2026-11-27 11:00 Replay protection: spec half written
- Tried: reading the vendor docs on the timestamp header
- Learned: see the hand-off
- Dead ends: none
- Decision: pause
- Next question: what tolerance window, and where is the timestamp checked?
- Later: key rotation
{state}
"""

HANDOFF_TEXT = """# Hand-off: replay protection spec

What was done: read the vendor docs, drafted the first half of poc-spec/spec-replay.md.

Gotcha learned: the vendor sends the timestamp in the `X-Vendor-Ts` header as epoch MILLISECONDS, not seconds.
Comparing it with time.time() directly makes every request look 1000 times too far in the future.

Decisions waiting: none.
Files to read first: poc-spec/spec-replay.md, app.py.
Next step: write the "Tolerance window" section of poc-spec/spec-replay.md, using milliseconds.
"""

APP = '''import hashlib
import hmac


def verify_signature(secret: bytes, raw_body: bytes, signature_hex: str) -> bool:
    expected = hmac.new(secret, raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_hex)
'''


def git(cwd, *args):
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(cwd), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull}
    r = subprocess.run(["git", "-c", "user.email=probe@example.test", "-c", "user.name=probe", *args],
                       cwd=str(cwd), env=env, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("git %s failed: %s" % (args[0], r.stderr.strip()[:200]))


def poc_repo(root, wiring, kind):
    """A PoC repo on branch spike-hmac with one uncommitted scratch file, whose last log entry has State."""
    (root / "poc-spec").mkdir(parents=True)
    (root / "app.py").write_text(APP)
    (root / "verify.sh").write_text("#!/usr/bin/env bash\npython3 -c 'import app'\n")
    os.chmod(str(root / "verify.sh"), 0o755)
    (root / "poc-spec" / "POC.md").write_text(POC)
    (root / "poc-spec" / "LOG.md").write_text(LOG_HEAD)
    if wiring:
        (root / "CLAUDE.md").write_text("# CLAUDE.md\n\n" + WIRING + "\n")
    if kind == "pause":
        (root / "poc-spec" / "handoffs").mkdir()
        (root / "poc-spec" / "handoffs" / HANDOFF).write_text(HANDOFF_TEXT)
        (root / "poc-spec" / "spec-replay.md").write_text("# Spec: replay protection\n\n## Threat\nReplayed webhooks.\n")
    git(root, "init", "-q", "-b", "main")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "PoC start")
    git(root, "checkout", "-q", "-b", "spike-hmac")
    (root / "scratch_vectors.py").write_text("# vendor sample vectors, not committed\n")
    values, _ = rules.gather(str(root), "new")
    if kind == "pause":
        resume = "read poc-spec/handoffs/%s, then write the Tolerance window section of poc-spec/spec-replay.md" % HANDOFF
        entry = PAUSE_ENTRY
    else:
        resume = "add a 5-minute timestamp tolerance to verify_signature in app.py, then run ./verify.sh"
        entry = ITERATE_ENTRY
    state = rules.state_line(values, resume=resume)
    with open(str(root / "poc-spec" / "LOG.md"), "a") as fh:
        fh.write(entry.format(state=state))
    return state


def write_hook_plugin(path, matcher="startup|clear", word="HERON"):
    (path / ".claude-plugin").mkdir(parents=True)
    (path / "hooks").mkdir()
    (path / ".claude-plugin" / "plugin.json").write_text(json.dumps({"name": "probe-hook", "version": "0.0.1",
                                                                     "description": "SessionStart probe"}))
    hooks = {"hooks": {"SessionStart": [{"matcher": matcher, "hooks": [
        {"type": "command", "command": "echo 'PROBE MARKER: the probe word is %s'" % word}]}]}}
    (path / "hooks" / "hooks.json").write_text(json.dumps(hooks))


def build(work):
    if work.exists():
        shutil.rmtree(str(work))
    work.mkdir(parents=True)
    states = {}
    for name, wiring, kind in (("p1a", True, "iterate"), ("p1b", False, "iterate"), ("p1c", True, "iterate"),
                               ("p2", True, "pause")):
        states[name] = poc_repo(work / name, wiring, kind)
    (work / "p0").mkdir()
    (work / "p4").mkdir()
    write_hook_plugin(work / "p4-plugin")
    (work / "p4b").mkdir()
    write_hook_plugin(work / "p4b-plugin", matcher="clear", word="EGRET")  # fires only after /clear
    return states


def plan(work):
    plugin = ["--plugin-dir", str(REPO)]
    p0_input = "\n".join(json.dumps({"type": "user", "message": {"role": "user", "content": c}}) for c in (
        "Remember the code word PELICAN. Reply with just OK.",
        "/clear",
        "What code word did I ask you to remember? If you do not know, reply with just UNKNOWN.",
    )) + "\n"
    p4b_input = "\n".join(json.dumps({"type": "user", "message": {"role": "user", "content": c}}) for c in (
        "Reply with just OK.",
        "/clear",
        "If your context contains a probe marker with a probe word, reply with that word. Otherwise reply with "
        "just NONE. Do not use any tools.",
    )) + "\n"
    # label, cwd, argv after `claude`, stdin
    return [
        ("P0", work / "p0", ["-p", "--input-format", "stream-json", "--model", "haiku",
                             "--allowedTools", "Read"], p0_input),
        ("P1a", work / "p1a", ["-p", TASK, "--model", "sonnet", "--allowedTools", *READ_ONLY] + plugin, None),
        ("P1b", work / "p1b", ["-p", TASK, "--model", "sonnet", "--allowedTools", *READ_ONLY] + plugin, None),
        ("P1c", work / "p1c", ["-p", STATUS, "--model", "sonnet", "--allowedTools", *READ_ONLY] + plugin, None),
        ("P2", work / "p2", ["-p", TASK, "--model", "sonnet", "--allowedTools", *READ_ONLY] + plugin, None),
        ("P4", work / "p4", ["-p", "If your context contains a probe marker with a probe word, reply with that word. "
                             "Otherwise reply with just NONE. Do not use any tools.", "--model", "haiku",
                             "--plugin-dir", str(work / "p4-plugin")], None),
        ("P4b", work / "p4b", ["-p", "--input-format", "stream-json", "--model", "haiku",
                               "--plugin-dir", str(work / "p4b-plugin")], p4b_input),
    ]


def event_types(stdout):
    seen = []
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        key = ev.get("type") + ("/" + ev["subtype"] if ev.get("subtype") else "")
        if not seen or seen[-1][0] != key:
            seen.append([key, 1])
        else:
            seen[-1][1] += 1
        if ev.get("type") == "result":
            print("  result: %s" % (ev.get("result") or "")[:300].replace("\n", " | "))
        if ev.get("type") == "system" and ev.get("subtype") not in ("init",):
            print("  system event: %s" % json.dumps(ev)[:400])
    print("  event sequence: %s" % ", ".join("%s x%d" % (k, n) if n > 1 else k for k, n in seen))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evals-repo", required=True)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    work, out = Path(a.work), Path(a.out)
    states = build(work)
    out.mkdir(parents=True, exist_ok=True)
    runs = [r for r in plan(work) if not a.only or r[0] in a.only]
    if a.dry_run:
        for name, st in states.items():
            print("%s State: %s" % (name, st))
        for label, cwd, argv, stdin in runs:
            print(label, "| cwd:", str(cwd).replace(str(work), "<work>"), "|",
                  " ".join(x.replace(str(work), "<work>").replace(str(REPO), "<repo>") for x in argv))
        return
    sys.path.insert(0, str(Path(a.evals_repo) / "evals"))
    from harness import runner  # noqa: E402
    token, _ = runner.load_token(Path(a.evals_repo))
    print("claude --version:", subprocess.run(["claude", "--version"], capture_output=True, text=True).stdout.strip())
    for label, cwd, argv, stdin in runs:
        home = Path(tempfile.mkdtemp(prefix="probe-home-"))
        try:
            for sub in ("cc", "xdg", "tmp"):
                (home / sub).mkdir()
            cmd = ["claude", *argv, "--output-format", "stream-json", "--verbose", "--max-budget-usd", MAX_COST]
            p = subprocess.run(cmd, cwd=str(cwd), env=probe_run.isolated_env(home, token), input=stdin,
                               capture_output=True, text=True, timeout=300)
            stdout = p.stdout.replace(token, "[REDACTED]")
            (out / (label + ".jsonl")).write_text(stdout)
            probe_run.digest(label, stdout)
            event_types(stdout)
            if p.returncode != 0:
                print("  exit code %s, stderr tail: %s" % (p.returncode, p.stderr.replace(token, "[REDACTED]")[-300:]))
            print()
        finally:
            shutil.rmtree(str(home), ignore_errors=True)


if __name__ == "__main__":
    main()
