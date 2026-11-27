#!/usr/bin/env python3
"""A stand-in for `claude -p ... --output-format stream-json`, used by the eval harness tests.

The behaviour is chosen by a MODE:<name> token at the start of the prompt. It never calls a model.
It records what it saw (argv, which environment variables exist, the plugin directory contents)
into files in its working directory so the tests can check isolation.
"""
import json
import os
import shutil
import sys
import time


def emit(obj):
    print(json.dumps(obj), flush=True)


def main():
    argv = sys.argv[1:]
    prompt = argv[argv.index("-p") + 1] if "-p" in argv else ""
    mode = prompt.split()[0].replace("MODE:", "") if prompt.startswith("MODE:") else "ok"
    plugin_dir = argv[argv.index("--plugin-dir") + 1] if "--plugin-dir" in argv else ""

    seen = {
        "argv": argv,
        "env_names": sorted(os.environ.keys()),
        "home": os.environ.get("HOME"),
        "has_oauth_token": bool(os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")),
        "plugin_top_level": sorted(os.listdir(plugin_dir)) if plugin_dir and os.path.isdir(plugin_dir) else [],
        "python3_found": shutil.which("python3") is not None,
        "python_found": shutil.which("python") is not None,
        "git_found": shutil.which("git") is not None,
    }
    with open("seen.json", "w") as f:
        json.dump(seen, f)

    token = os.environ.get("CLAUDE_CODE_OAUTH_TOKEN", "")
    if mode == "crash":
        sys.exit(1)  # no output at all, like a bad token or a CLI error
    if mode == "stderrleak":
        sys.stderr.write(token + "y" * 495)  # the last 500 characters start inside the token

    init = {"type": "system", "subtype": "init", "claude_code_version": "9.9.9-fake", "apiKeySource": "none",
            "tools": ["Bash", "Read", "Edit"], "mcp_servers": [],
            "plugins": [{"name": "spike-loop"}, {"name": "cc-plugin-privacy"}],
            "agents": ["claude", "Explore", "spike-loop:researcher"],
            "skills": ["spike-loop:poc-log", "debug"],
            "memory_paths": {"auto": os.path.join(os.environ.get("CLAUDE_CONFIG_DIR", ""), "projects", "x", "memory") + "/"},
            "cwd": os.getcwd(), "session_id": "fake"}
    if mode == "mcp":
        init["mcp_servers"] = [{"name": "some-connector"}]
    if mode == "badskill":
        init["skills"].append("my-own-user-skill")
    if mode == "outside":
        init["memory_paths"] = {"auto": "/somewhere/else/memory/"}
    emit(init)
    if mode == "sleep":
        time.sleep(30)
    if mode == "garbage":
        print("this line is not json", flush=True)

    cmd = "echo " + token if mode == "leak" else "date"
    emit({"type": "assistant", "message": {"model": "fake-model", "content": [
        {"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}})
    emit({"type": "assistant", "parent_tool_use_id": "x", "message": {"model": "fake-model", "content": [
        {"type": "tool_use", "name": "Read", "input": {"file_path": "LOG.md"}}]}})

    if mode != "nowrite":
        with open("LOG.md", "a") as f:
            f.write("\n## 2026-11-25 19:00 HMAC fake entry\n- Tried: HMAC\n")

    base = {"type": "result", "is_error": False, "subtype": "success", "result": "FINAL ANSWER",
            "total_cost_usd": 0.1, "num_turns": 3, "permission_denials": [],
            "usage": {"input_tokens": 1, "output_tokens": 2}, "modelUsage": {"fake-model": {"costUSD": 0.1}},
            "subagent_stats": {"spawned": 0}, "result_index": 0}
    if mode == "budget":
        base.update(is_error=True, subtype="error_max_budget_usd", terminal_reason="budget_exhausted", result="")
    if mode == "twores":
        emit(dict(base, result="STALE FIRST", result_index=0))
        base["result_index"] = 1
    if mode == "denial":
        base["permission_denials"] = [{"tool_name": "Bash", "tool_input": {"command": "printf x"}}]
    if mode == "leak":
        base["result"] = "the token is " + token
        base["permission_denials"] = [{"tool_name": "Bash", "tool_input": {"command": "echo " + token}}]
    emit(base)


if __name__ == "__main__":
    main()
