"""Parse a claude stream-json event log into a run summary, and redact secrets.

Behaviours this relies on were observed on Claude Code 2.1.325, see
docs/evals/spike-findings.md: the answer is the result event with the highest
result_index (a background subagent can produce an earlier stale one), forked
skills report num_turns 0 so tool calls are counted from events, and agent calls
are counted from subagent_stats.
"""
import json
import os
import re
from typing import Any, Dict, Iterable, List, Tuple

TOKEN_RE = re.compile(r"sk-ant-[A-Za-z0-9_-]+")


def redact(text, secrets=()):
    for s in secrets:
        if s:
            text = text.replace(s, "[REDACTED]")
    return TOKEN_RE.sub("[REDACTED]", text)


def parse_lines(lines):
    """Return (events, count of non-JSON lines). A non-JSON line is kept out of the events, not dropped silently."""
    events = []  # type: List[Dict[str, Any]]
    bad = 0
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            bad += 1
            continue
        if isinstance(obj, dict):
            events.append(obj)
        else:
            bad += 1
    return events, bad


def _short(value, limit=200):
    s = value if isinstance(value, str) else json.dumps(value, sort_keys=True)
    return s if len(s) <= limit else s[:limit] + "..."


def summarise_events(events):
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), None)
    results = [e for e in events if e.get("type") == "result"]
    final = None
    if results:
        final = max(enumerate(results), key=lambda p: (p[1].get("result_index", p[0]), p[0]))[1]

    tool_calls = []
    for e in events:
        if e.get("type") != "assistant":
            continue
        child = bool(e.get("parent_tool_use_id"))
        content = (e.get("message") or {}).get("content") or []
        for item in content if isinstance(content, list) else []:
            if isinstance(item, dict) and item.get("type") == "tool_use":
                tool_calls.append({"name": item.get("name"), "child": child, "input": _short(item.get("input", {}), 600)})

    denials = []
    if final is not None:
        for d in final.get("permission_denials") or []:
            denials.append({"tool_name": d.get("tool_name"), "input": _short(d.get("tool_input", {}))})

    summary = {
        "has_init": init is not None,
        "has_result": final is not None,
        "n_result_events": len(results),
        "result_index": final.get("result_index") if final else None,
        "is_error": bool(final.get("is_error")) if final else None,
        "result_subtype": final.get("subtype") if final else None,
        "terminal_reason": final.get("terminal_reason") if final else None,
        "final_text": (final.get("result") or "") if final else "",
        "cost_usd": final.get("total_cost_usd") if final else None,
        "num_turns": final.get("num_turns") if final else None,
        "usage": _usage(final),
        "models": sorted((final.get("modelUsage") or {}).keys()) if final else [],
        "subagent_stats": final.get("subagent_stats") if final else None,
        "permission_denials": denials,
        "tool_calls": tool_calls,
        "claude_version": init.get("claude_code_version") if init else None,
        "api_key_source": init.get("apiKeySource") if init else None,
    }
    return summary, init


def _usage(final):
    if not final:
        return {}
    u = final.get("usage") or {}
    keys = ("input_tokens", "output_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    return {k: u.get(k) for k in keys if k in u}


# Isolation: what a clean run may contain. Observed on Claude Code 2.1.325 with the account used for the evals.
# Anything else marks the run invalid. A new Claude Code version or account may need this list updated, and the
# violation message names exactly what was unexpected.
ALLOWED_PLUGINS = {
    "spike-loop", "cc-plugin-sec-default", "cc-plugin-agents-md", "cc-plugin-telemetry",
    "cc-plugin-privacy", "cc-plugin-plugin-authoring",
}
ALLOWED_BUILTIN_AGENTS = {"claude", "Explore", "general-purpose", "Plan", "statusline-setup"}
ALLOWED_BUILTIN_SKILLS = {
    "deep-research", "design", "design-sync", "dataviz", "update-config", "verify", "debug", "code-review",
    "simplify", "batch", "fewer-permission-prompts", "doctor", "loop", "schedule", "claude-api",
    "workflow-authoring", "run", "run-skill-generator", "plugin-authoring",
}


def _under(path, root):
    path, root = os.path.realpath(path), os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


def check_isolation(init, config_dir=None, cwd=None):
    """Return a list of violations. Empty means the run saw only the plugin under test and Claude Code built-ins.

    With config_dir and cwd given, also confirms from the init event that the config directory and the working
    directory are the temporary ones, so the maintainer's own configuration cannot have been loaded.
    """
    if init is None:
        return ["no system/init event"]
    problems = []
    if init.get("mcp_servers"):
        problems.append("MCP servers loaded: %s" % _short([m.get("name", m) if isinstance(m, dict) else m for m in init["mcp_servers"]]))
    for t in init.get("tools") or []:
        if isinstance(t, str) and t.startswith("mcp__"):
            problems.append("connector tool present: %s" % t)
    names = set()
    for p in init.get("plugins") or []:
        names.add(p.get("name") if isinstance(p, dict) else str(p))
    extra = sorted(n for n in names if n not in ALLOWED_PLUGINS)
    if extra:
        problems.append("unexpected plugins: %s" % ", ".join(extra))
    for a in init.get("agents") or []:
        if a not in ALLOWED_BUILTIN_AGENTS and not str(a).startswith("spike-loop:"):
            problems.append("unexpected agent: %s" % a)
    extra_skills = sorted(str(k) for k in (init.get("skills") or [])
                          if not str(k).startswith("spike-loop:") and k not in ALLOWED_BUILTIN_SKILLS)
    if extra_skills:
        problems.append("unexpected skills: %s" % ", ".join(extra_skills))
    if init.get("apiKeySource") not in (None, "none"):
        problems.append("unexpected apiKeySource: %s" % init.get("apiKeySource"))
    if config_dir is not None:
        paths = [v for v in (init.get("memory_paths") or {}).values() if isinstance(v, str)]
        if not paths:
            problems.append("init has no memory_paths, so the config directory cannot be confirmed as isolated")
        for v in paths:
            if not _under(v, config_dir) and not (cwd is not None and _under(v, cwd)):
                problems.append("memory path outside the temporary config: %s" % v)
    if cwd is not None and init.get("cwd") and not _under(init["cwd"], cwd):
        problems.append("working directory is not the workspace: %s" % init["cwd"])
    return problems
