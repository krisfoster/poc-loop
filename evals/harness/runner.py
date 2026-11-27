"""Run one case in an isolated headless Claude Code session and capture what happened.

Isolation (docs/evals/spec.md, harness requirement 2): a clean environment, a temporary
HOME, CLAUDE_CONFIG_DIR and XDG_CONFIG_HOME, the subscription token passed as
CLAUDE_CODE_OAUTH_TOKEN, a setting that stops file tools reading outside the working
directory, and the plugin loaded from a copy of the working tree that contains only
plugin directories (no evals, docs, tests, .env or .git). The only variable inherited
from the maintainer's environment is PATH. Every run's system/init event is checked
against an allowlist (events.check_isolation).
"""
import copy
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

from . import events as ev
from . import graders as graders_mod
from .cases import Case

TOKEN_VAR = "SPIKE_EVALS_OAUTH_TOKEN"
PLUGIN_DIRS = (".claude-plugin", "agents", "skills", "commands", "hooks", "assets")
SNAPSHOT_SKIP = (".git", ".claude")  # runs create .claude (project config, worktrees); not part of the diff
BROAD_TOOLS = ("Bash", "WebFetch", "WebSearch")
# A Bash pattern that starts with one of these runs arbitrary code, whatever follows it.
INTERPRETERS = {"sh", "bash", "zsh", "dash", "fish", "env", "xargs", "eval", "exec", "sudo", "python", "python3",
                "node", "perl", "ruby", "php", "curl", "wget", "ssh", "scp", "nc", "npx", "uvx", "pipx", "osascript"}
SETTINGS = {"permissions": {"blockReadsOutsideWorkingDirectories": True}}


class RunnerError(RuntimeError):
    pass


def load_token(repo_root):
    """Token from the environment, else from the repo .env (a value or an op:// reference). Never printed.

    Returns (token, is_plaintext_in_env_file). The repo rule is that .env holds 1Password references.
    """
    value, from_file = os.environ.get(TOKEN_VAR, ""), False
    if not value:
        env_file = Path(repo_root) / ".env"
        if env_file.is_file():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith(TOKEN_VAR + "="):
                    value = line.split("=", 1)[1].strip().strip("'\"")
                    from_file = True
                    break
    if value.startswith("op://"):
        try:
            value = subprocess.run(["op", "read", value], capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            raise RunnerError("%s is a 1Password reference but `op read` failed" % TOKEN_VAR)
        from_file = False
    if not value:
        raise RunnerError("%s is not set in the environment or in .env" % TOKEN_VAR)
    return value, from_file


def broad_grants(case):
    """Tool grants that run on the maintainer's machine without an OS sandbox."""
    out = []
    for t in case.allowed_tools:
        base = t.split("(", 1)[0]
        if base not in BROAD_TOOLS:
            continue
        if t == base:
            out.append(t)
        elif base == "Bash":
            inner = t[len("Bash("):].rstrip(")").strip()
            word = inner.split()[0] if inner.split() else ""
            if word.startswith("*") or word in INTERPRETERS:
                out.append(t)
        elif t.startswith(base + "(*"):
            out.append(t)
    # A command_exit grader runs files in the workspace, which the model may have written.
    out += ["command_exit grader: %s" % " ".join(gs["argv"]) for gs in case.graders if gs.get("type") == "command_exit"]
    return out


def check_parent_instructions(ws):
    """CLAUDE.md files load from every parent of the working directory. Return any found above ws."""
    found = []
    for parent in Path(os.path.realpath(str(ws))).parents:
        for rel in ("CLAUDE.md", ".claude/CLAUDE.md", "CLAUDE.local.md"):
            if (parent / rel).exists():
                found.append(str(parent / rel))
    return found


def build_plugin_copy(repo_root, dest):
    repo_root, dest = Path(repo_root), Path(dest)
    listed = subprocess.run(["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=str(repo_root),
                            capture_output=True, check=True).stdout.decode("utf-8")
    n = 0
    for rel in listed.split("\0"):
        if not rel or rel.split("/")[0] not in PLUGIN_DIRS or "__pycache__" in rel:
            continue
        src = repo_root / rel
        if src.is_file():
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(target))
            n += 1
    if n == 0:
        raise RunnerError("no plugin files found under %s" % repo_root)
    return dest


def plugin_version(plugin_dir):
    try:
        return json.loads((Path(plugin_dir) / ".claude-plugin" / "plugin.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return None


def snapshot(root):
    snap = {}  # type: Dict[str, str]
    root = Path(root)
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames[:] = [d for d in dirnames if d not in SNAPSHOT_SKIP]
        for name in filenames:
            p = Path(dirpath) / name
            if p.is_symlink() or not p.is_file():
                continue
            snap[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def diff_snapshots(before, after):
    return {
        "added": sorted(set(after) - set(before)),
        "modified": sorted(k for k in before if k in after and before[k] != after[k]),
        "deleted": sorted(set(before) - set(after)),
    }


def _git(args, cwd, home):
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(home), "GIT_CONFIG_NOSYSTEM": "1"}
    return subprocess.run(["git", "-c", "user.email=eval@example.test", "-c", "user.name=eval"] + args,
                          cwd=str(cwd), env=env, capture_output=True, text=True)


def make_workspace(fixture_dir, ws, use_git, home):
    shutil.copytree(str(fixture_dir), str(ws))
    if use_git:
        for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "--allow-empty", "-m", "fixture"]):
            r = _git(args, ws, home)
            if r.returncode != 0:
                raise RunnerError("fixture git step %s failed: %s" % (args[0], r.stderr.strip()[:200]))


def list_worktrees(ws, home):
    r = _git(["worktree", "list", "--porcelain"], ws, home)
    if r.returncode != 0:
        return []
    paths = [l.split(" ", 1)[1] for l in r.stdout.splitlines() if l.startswith("worktree ")]
    out = []
    for p in paths:
        if os.path.realpath(p) == os.path.realpath(str(ws)):
            continue
        status = _git(["status", "--porcelain"], p, home).stdout.splitlines() if os.path.isdir(p) else []
        out.append({"path": os.path.relpath(p, str(ws)) if p.startswith(str(ws)) else p, "status": status})
    return out


def isolated_env(home, token):
    home = str(home)
    return {
        "PATH": os.environ.get("PATH", ""),
        "TERM": "xterm",
        "HOME": home,
        "CLAUDE_CONFIG_DIR": os.path.join(home, "cc"),
        "XDG_CONFIG_HOME": os.path.join(home, "xdg"),
        "TMPDIR": os.path.join(home, "tmp"),
        "CLAUDE_CODE_OAUTH_TOKEN": token,
    }


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _text(value):
    if value is None:
        return ""
    return value.decode("utf-8", "replace") if isinstance(value, bytes) else value


def run_once(case, run_index, repo_root, plugin_dir, token, out_dir, fixtures_dir,
             claude_cmd=("claude",), keep=False):
    """Run the case once. Never raises: any failure becomes a harness_failure result."""
    repo_root, out_dir = Path(repo_root), Path(out_dir)
    tmp = Path(tempfile.mkdtemp(prefix="spike-eval-"))
    home, ws = tmp / "home", tmp / "ws"
    result = {
        "schema": 1, "case": case.name, "stage": case.stage, "set": case.set, "run_index": run_index,
        "started": _now(), "plugin_version": plugin_version(plugin_dir), "prompt": case.prompt,
        "status": "ok", "reason": None, "passed": False, "grader_results": [],
    }
    events_text = None
    started = time.time()
    try:
        for sub in ("cc", "xdg", "tmp"):
            (home / sub).mkdir(parents=True)
        parents = check_parent_instructions(tmp)
        if parents:
            raise RunnerError("instruction files above the workspace would be loaded: %s" % ", ".join(parents))
        make_workspace(Path(fixtures_dir) / case.fixture, ws, case.git, home)
        run_cwd = ws / case.cwd  # the session starts here, the diff and the graders still look at the whole workspace
        settings = copy.deepcopy(SETTINGS)
        if case.add_root_dir:
            settings["permissions"]["additionalDirectories"] = [str(ws)]
        before = snapshot(ws)
        cmd = list(claude_cmd) + [
            "-p", case.prompt, "--plugin-dir", str(plugin_dir),
            "--settings", json.dumps(settings),
            "--allowedTools"] + list(case.allowed_tools) + [
            "--output-format", "stream-json", "--verbose", "--max-budget-usd", str(case.max_cost_usd)]
        stdout, stderr, code, timed_out = "", "", None, False
        try:
            proc = subprocess.run(cmd, cwd=str(run_cwd), env=isolated_env(home, token), capture_output=True,
                                  text=True, timeout=case.timeout_s)
            stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout, stderr = _text(exc.stdout), _text(exc.stderr)

        events, bad_lines = ev.parse_lines(stdout.splitlines())
        summary, init = ev.summarise_events(events)
        summary["non_json_lines"] = bad_lines
        after = snapshot(ws)
        result.update({k: v for k, v in summary.items() if k != "has_init"})
        result["exit_code"] = code
        result["stderr_tail"] = ev.redact(stderr, (token,))[-500:]  # redact first, then cut
        result["workspace_changes"] = diff_snapshots(before, after)
        result["worktrees"] = list_worktrees(ws, home)
        events_text = stdout

        # Order matters: a run with no output is a harness failure, not an isolation violation.
        if timed_out:
            result.update(status="harness_failure", reason="timeout after %ss" % case.timeout_s)
        elif not summary["has_init"] or not summary["has_result"]:
            result.update(status="harness_failure", reason="no init or result event (exit %s)" % code)
        else:
            violations = ev.check_isolation(init, config_dir=str(home / "cc"), cwd=str(run_cwd))
            if violations:
                result.update(status="invalid", reason="; ".join(violations))
            elif summary["result_subtype"] == "error_max_budget_usd" or summary["terminal_reason"] == "budget_exhausted":
                result.update(status="harness_failure", reason="budget_exhausted")
            elif summary["is_error"]:
                result.update(status="harness_failure", reason="result error: %s" % summary["result_subtype"])

        if result["status"] == "ok":
            ctx = {"workspace": ws, "fixture": Path(fixtures_dir) / case.fixture, "summary": summary,
                   "before": before, "after": after, "events_text": ev.redact(stdout, (token,))}
            result["grader_results"] = graders_mod.run_graders(case.graders, ctx)
            result["passed"] = all(g["passed"] for g in result["grader_results"])
    except Exception as exc:  # a harness problem must never abort the suite or look like a stage failure
        result.update(status="harness_failure", reason="%s: %s" % (type(exc).__name__, exc), passed=False, grader_results=[])
    finally:
        result["duration_s"] = round(time.time() - started, 1)
        if keep:
            result["workspace_kept"] = str(tmp)
        else:
            shutil.rmtree(str(tmp), ignore_errors=True)

    # Redact the whole result (final text, tool inputs, denials, reasons), not only the event log.
    result = json.loads(ev.redact(json.dumps(result, indent=2, sort_keys=True), (token,)))
    case_dir = out_dir / case.stage / case.id
    case_dir.mkdir(parents=True, exist_ok=True)
    if events_text is not None:
        (case_dir / ("run%d.events.jsonl" % run_index)).write_text(ev.redact(events_text, (token,)), encoding="utf-8")
    (case_dir / ("run%d.json" % run_index)).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result
