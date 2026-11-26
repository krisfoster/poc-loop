"""Deterministic graders. Each takes (ctx, spec) and returns (passed, explanation).

ctx is a dict: {"workspace": Path, "summary": dict from events.summarise_events,
"before": snapshot, "after": snapshot}. Phase 2 grows this library; Phase 1 only
needs enough graders to score the poc-log smoke case.
"""
import re
from pathlib import Path
from typing import Callable, Dict, List, Tuple

GRADERS = {}  # type: Dict[str, Callable]
REQUIRED_PARAMS = {}  # type: Dict[str, List[str]]


def grader(name, required=()):
    def deco(fn):
        GRADERS[name] = fn
        REQUIRED_PARAMS[name] = list(required)
        return fn
    return deco


def _flags(spec):
    flags = 0
    for ch in spec.get("flags", ""):
        flags |= {"i": re.I, "m": re.M, "s": re.S}.get(ch, 0)
    return flags


@grader("file_exists", required=["path"])
def file_exists(ctx, spec):
    p = Path(ctx["workspace"]) / spec["path"]
    want = spec.get("exists", True)
    ok = p.exists() == want
    return ok, "%s %s (expected %s)" % (spec["path"], "exists" if p.exists() else "missing", "present" if want else "absent")


@grader("file_regex", required=["path", "pattern"])
def file_regex(ctx, spec):
    p = Path(ctx["workspace"]) / spec["path"]
    if not p.is_file():
        return False, "%s is missing" % spec["path"]
    text = p.read_text(encoding="utf-8", errors="replace")
    n = len(re.findall(spec["pattern"], text, _flags(spec)))
    if "count" in spec:
        return n == spec["count"], "%d matches in %s (expected exactly %d)" % (n, spec["path"], spec["count"])
    minimum = spec.get("min", 1)
    return n >= minimum, "%d matches in %s (expected at least %d)" % (n, spec["path"], minimum)


@grader("no_permission_denials")
def no_permission_denials(ctx, spec):
    n = len(ctx["summary"].get("permission_denials", []))
    return n == 0, "%d permission denials" % n


@grader("tool_not_used", required=["tool"])
def tool_not_used(ctx, spec):
    used = [c for c in ctx["summary"].get("tool_calls", []) if c["name"] == spec["tool"]]
    return not used, "%s called %d times" % (spec["tool"], len(used))


def run_graders(specs, ctx):
    out = []
    for spec in specs:
        fn = GRADERS[spec["type"]]
        try:
            passed, why = fn(ctx, spec)
        except Exception as exc:  # a grader bug must not look like a plugin pass
            passed, why = False, "grader error: %s" % exc
        out.append({"name": spec.get("name", spec["type"]), "type": spec["type"], "passed": bool(passed), "explanation": why})
    return out
