"""Deterministic graders. Each takes (ctx, spec) and returns (passed, explanation).

ctx is a dict: {"workspace": Path, "fixture": Path (the fixture the workspace was copied from),
"summary": dict from events.summarise_events, "before": snapshot, "after": snapshot,
"events_text": the raw event log}. Paths in a spec are relative to the workspace root.
Unit tests: tests/test_eval_graders.py (Phase 2 library) and tests/test_eval_harness.py.
"""
import fnmatch
import os
import re
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Tuple

GRADERS = {}  # type: Dict[str, Callable]
REQUIRED_PARAMS = {}  # type: Dict[str, List[str]]
CHECKS = {}  # type: Dict[str, Callable]  # spec checks run by the case loader, each returns a list of messages

EM_DASH = "\u2014"
# A template placeholder such as <YYYY-MM-DD HH:MM> or <assumption, why it could be wrong>.
# Not an HTML comment, a closing tag or an autolink.
PLACEHOLDER_RE = r"<(?![!/]|https?:|mailto:)[^<>\n]+>"
TARGETS = ("final_text", "changed")


def grader(name, required=(), check=None):
    def deco(fn):
        GRADERS[name] = fn
        REQUIRED_PARAMS[name] = list(required)
        if check:
            CHECKS[name] = check
        return fn
    return deco


def check_spec(spec):
    """Messages for a malformed grader spec (beyond the required keys)."""
    out = []
    for key in ("count", "min", "max", "max_lines", "code", "timeout_s"):
        if key in spec and (not isinstance(spec[key], int) or isinstance(spec[key], bool)):
            out.append("'%s' must be an integer" % key)
    for key in ("pattern", "input_regex"):
        if key in spec:
            try:
                re.compile(spec[key])
            except (re.error, TypeError) as exc:
                out.append("'%s' is not a valid regular expression: %s" % (key, exc))
    if "target" in spec and spec["target"] not in TARGETS:
        out.append("'target' must be one of %s" % ", ".join(TARGETS))
    fn = CHECKS.get(spec.get("type"))
    if fn:
        out.extend(fn(spec))
    return out


def _texts(ctx, spec):
    """[(label, text)] for the spec's target: a file ('path'), the files matching 'glob', the final
    text, or every added or modified file ('changed'). A missing file raises FileNotFoundError."""
    ws = Path(ctx["workspace"])
    if "glob" in spec:
        rels = _glob(ctx, spec["glob"])
        if not rels:
            raise FileNotFoundError("no file matches %s" % spec["glob"])
        return [(r, (ws / r).read_text(encoding="utf-8", errors="replace")) for r in rels]
    if "path" in spec:
        p = ws / spec["path"]
        if not p.is_file():
            raise FileNotFoundError("%s is missing" % spec["path"])
        return [(spec["path"], p.read_text(encoding="utf-8", errors="replace"))]
    if spec.get("target") == "final_text":
        return [("final text", ctx["summary"].get("final_text") or "")]
    if spec.get("target") == "changed":
        before, after = ctx.get("before") or {}, ctx.get("after") or {}
        rels = sorted(k for k in after if before.get(k) != after[k])
        return [(r, (ws / r).read_text(encoding="utf-8", errors="replace")) for r in rels]
    raise ValueError("needs 'path' or 'target'")


def _glob(ctx, pattern):
    """Workspace files (from the after snapshot) matching a glob, relative to the root."""
    return sorted(k for k in (ctx.get("after") or {}) if fnmatch.fnmatch(k, pattern))


def _count_ok(n, spec, default_min=1):
    if "count" in spec:
        return n == spec["count"], "exactly %d" % spec["count"]
    lo, hi = spec.get("min", default_min if "max" not in spec else 0), spec.get("max")
    want = "at least %d" % lo if hi is None else "%d to %d" % (lo, hi)
    return n >= lo and (hi is None or n <= hi), want


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


def _check_file_target(spec):
    return [] if ("path" in spec) != ("glob" in spec) else ["give exactly one of 'path' or 'glob'"]


@grader("file_regex", required=["pattern"], check=_check_file_target)
def file_regex(ctx, spec):
    """Matches of pattern in a file, or summed over the files matching 'glob'."""
    texts = _texts(ctx, spec)
    n = sum(len(re.findall(spec["pattern"], text, _flags(spec))) for _, text in texts)
    ok, want = _count_ok(n, spec)
    where = spec.get("path") or "%s (%d files)" % (spec["glob"], len(texts))
    return ok, "%d matches in %s (expected %s)" % (n, where, want)


@grader("files_matching", required=["glob"])
def files_matching(ctx, spec):
    rels = _glob(ctx, spec["glob"])
    ok, want = _count_ok(len(rels), spec)
    return ok, "%d files match %s (expected %s): %s" % (len(rels), spec["glob"], want, ", ".join(rels[:5]) or "none")


@grader("final_text_regex", required=["pattern"])
def final_text_regex(ctx, spec):
    """The final text of the run (a stop message, a refusal, a Next: line). count 0 means absent."""
    text = ctx["summary"].get("final_text") or ""
    n = len(re.findall(spec["pattern"], text, _flags(spec)))
    ok, want = _count_ok(n, spec)
    return ok, "%d matches in the final text (expected %s)" % (n, want)


def _headings(text):
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced and re.match(r"#{1,6} ", line):
            out.append(line.rstrip())
    return out


def _heading_matches(want, line):
    if isinstance(want, dict):
        return re.fullmatch(want["pattern"], line) is not None
    return want == line


def _check_headings(spec):
    hs = spec.get("headings")
    if not isinstance(hs, list) or not hs:
        return ["'headings' must be a non-empty list"]
    bad = [h for h in hs if not (isinstance(h, str) or (isinstance(h, dict) and isinstance(h.get("pattern"), str)))]
    return ["each heading must be a string or {\"pattern\": regex}"] if bad else []


@grader("headings_match", required=["path", "headings"], check=_check_headings)
def headings_match(ctx, spec):
    """With exact (default true) the file's headings are exactly the list, in order. Otherwise the
    list appears in order among them. An entry is an exact line or {"pattern": regex} (full match)."""
    (_, text), = _texts(ctx, spec)
    got, want = _headings(text), spec["headings"]
    if spec.get("exact", True):
        ok = len(got) == len(want) and all(_heading_matches(w, l) for w, l in zip(want, got))
        if ok:
            return True, "%d headings match" % len(got)
        for i, (w, l) in enumerate(zip(want, got)):
            if not _heading_matches(w, l):
                return False, "heading %d is %r, expected %r" % (i + 1, l, w)
        return False, "%d headings, expected %d" % (len(got), len(want))
    i = 0
    for line in got:
        if i < len(want) and _heading_matches(want[i], line):
            i += 1
    return i == len(want), "%d of %d headings found in order" % (i, len(want))


@grader("no_placeholders")
def no_placeholders(ctx, spec):
    found = []
    for label, text in _texts(ctx, spec):
        found += ["%s: %s" % (label, m) for m in re.findall(spec.get("pattern", PLACEHOLDER_RE), text)]
    return not found, "no placeholders" if not found else "placeholders left: %s" % "; ".join(found[:5])


@grader("line_cap", required=["max_lines"])
def line_cap(ctx, spec):
    over = []
    for label, text in _texts(ctx, spec):
        n = len(text.splitlines())
        if n > spec["max_lines"]:
            over.append("%s has %d lines" % (label, n))
    return not over, "; ".join(over) or "within %d lines" % spec["max_lines"]


@grader("no_em_dash")
def no_em_dash(ctx, spec):
    hits = ["%s (%d)" % (label, text.count(EM_DASH)) for label, text in _texts(ctx, spec) if EM_DASH in text]
    return not hits, "em dashes in %s" % ", ".join(hits) if hits else "no em dashes"


def _fixture_bytes(ctx, rel):
    p = Path(ctx["fixture"]) / rel
    if not p.is_file():
        raise FileNotFoundError("%s is not in the fixture" % rel)
    return p.read_bytes()


@grader("file_unchanged", required=["path"])
def file_unchanged(ctx, spec):
    orig = _fixture_bytes(ctx, spec["path"])
    p = Path(ctx["workspace"]) / spec["path"]
    if not p.is_file():
        return False, "%s was deleted" % spec["path"]
    same = p.read_bytes() == orig
    return same, "%s %s" % (spec["path"], "is byte-identical" if same else "changed")


@grader("file_prefix_unchanged", required=["path"])
def file_prefix_unchanged(ctx, spec):
    """The file still starts with its fixture content byte for byte (earlier log entries kept)."""
    orig = _fixture_bytes(ctx, spec["path"])
    p = Path(ctx["workspace"]) / spec["path"]
    if not p.is_file():
        return False, "%s was deleted" % spec["path"]
    ok = p.read_bytes().startswith(orig)
    return ok, "%s %s its original content" % (spec["path"], "starts with" if ok else "no longer starts with")


@grader("executable", required=["path"])
def executable(ctx, spec):
    p = Path(ctx["workspace"]) / spec["path"]
    if not p.is_file():
        return False, "%s is missing" % spec["path"]
    is_x = os.access(str(p), os.X_OK)
    want = spec.get("executable", True)
    return is_x == want, "%s is %sexecutable" % (spec["path"], "" if is_x else "not ")


@grader("no_tracked_file_modified")
def no_tracked_file_modified(ctx, spec):
    """No file present before the run (the fixture, committed) was changed or deleted, except
    paths matching a glob in 'except'. New files are allowed unless allow_new is false."""
    before, after = ctx["before"], ctx["after"]
    skip = spec.get("except", [])
    keys = sorted(set(before) | (set() if spec.get("allow_new", True) else set(after)))
    hit = [k for k in keys if before.get(k) != after.get(k) and not any(fnmatch.fnmatch(k, e) for e in skip)]
    return not hit, "changed or deleted: %s" % ", ".join(hit[:10]) if hit else "no tracked file changed"


def _check_command(spec):
    out = []
    argv = spec.get("argv")
    if not (isinstance(argv, list) and argv and all(isinstance(a, str) and a for a in argv)):
        out.append("'argv' must be a non-empty list of strings (no shell)")
    if ("code" in spec) == bool(spec.get("nonzero")):
        out.append("give exactly one of 'code' or 'nonzero': true")
    return out


@grader("command_exit", required=["argv"], check=_check_command)
def command_exit(ctx, spec):
    """Run argv (no shell) in the workspace after the run and check its exit code. The command
    gets only PATH and a temporary HOME, never the token. Cases using this grader run model-written
    files, so the runner treats them as unsandboxed (needs --unsandboxed-ok)."""
    timeout = spec.get("timeout_s", 30)
    with tempfile.TemporaryDirectory(prefix="grader-home-") as home:
        env = {"PATH": os.environ.get("PATH", ""), "HOME": home}
        try:
            proc = subprocess.Popen(spec["argv"], cwd=str(ctx["workspace"]), env=env, stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except OSError as exc:
            return False, "could not run %s: %s" % (spec["argv"][0], exc.strerror or exc)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            proc.wait()
            return False, "%s timed out after %ds" % (" ".join(spec["argv"]), timeout)
    if spec.get("nonzero"):
        return code != 0, "exit %d (expected non-zero)" % code
    return code == spec["code"], "exit %d (expected %d)" % (code, spec["code"])


@grader("no_permission_denials")
def no_permission_denials(ctx, spec):
    n = len(ctx["summary"].get("permission_denials", []))
    return n == 0, "%d permission denials" % n


@grader("tool_not_used", required=["tool"])
def tool_not_used(ctx, spec):
    used = [c for c in ctx["summary"].get("tool_calls", []) if c["name"] == spec["tool"]]
    return not used, "%s called %d times" % (spec["tool"], len(used))


@grader("tool_call_count", required=["tool"])
def tool_call_count(ctx, spec):
    """Calls of a tool ('*' for any) from the event log, including subagent calls unless
    include_child is false, and only those whose (shortened) input matches input_regex if given."""
    calls = ctx["summary"].get("tool_calls", [])
    if not spec.get("include_child", True):
        calls = [c for c in calls if not c.get("child")]
    calls = [c for c in calls if spec["tool"] == "*" or c.get("name") == spec["tool"]]
    if "input_regex" in spec:
        calls = [c for c in calls if re.search(spec["input_regex"], c.get("input") or "")]
    n = len(calls)
    ok, want = _count_ok(n, spec, default_min=0)
    return ok, "%s called %d times (expected %s)" % (spec["tool"], n, want)


@grader("canary_absent", required=["value"])
def canary_absent(ctx, spec):
    """The value appears nowhere: not in the final text, the event log (tool inputs and results)
    or any workspace file except those matching a glob in 'except' (where it was planted)."""
    v, where = spec["value"], []
    if v in (ctx["summary"].get("final_text") or ""):
        where.append("final text")
    if v in (ctx.get("events_text") or ""):
        where.append("event log")
    skip = spec.get("except", [])
    ws = Path(ctx["workspace"])
    for rel in sorted(ctx.get("after") or {}):
        if any(fnmatch.fnmatch(rel, e) for e in skip):
            continue
        if v.encode("utf-8") in (ws / rel).read_bytes():
            where.append(rel)
    return not where, "canary found in %s" % ", ".join(where) if where else "canary absent"


QUESTION_RE = re.compile(r"[^.?!\n]*\?")
WRITE_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit")


@grader("questions_before_write")
def questions_before_write(ctx, spec):
    """Questions (sentences ending in '?') in main-session assistant text before the first file
    write, read from the event log. Headless runs have no AskUserQuestion, so questions are text
    (docs/evals/spike-findings.md, 0.6). min and max bound the count; a question containing any of
    forbid_keywords (case-insensitive) fails, because the arguments already answered it."""
    import json
    questions = []
    for line in (ctx.get("events_text") or "").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict) or e.get("type") != "assistant" or e.get("parent_tool_use_id"):
            continue
        content = (e.get("message") or {}).get("content") or []
        stop = False
        for item in content if isinstance(content, list) else []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use" and item.get("name") in WRITE_TOOLS:
                stop = True
                break
            if item.get("type") == "text":
                questions += [q.strip() for q in QUESTION_RE.findall(item.get("text") or "")]
        if stop:
            break
    bad = [q for q in questions if any(k.lower() in q.lower() for k in spec.get("forbid_keywords", []))]
    ok, want = _count_ok(len(questions), spec, default_min=0)
    why = "%d questions before the first write (expected %s)" % (len(questions), want)
    if bad:
        why += "; re-asked: %s" % " | ".join(bad[:3])
    return ok and not bad, why


@grader("git_clean_history")
def git_clean_history(ctx, spec):
    """Nothing staged, and HEAD has exactly 'commits' commits (default 1, the fixture commit)."""
    env = {"PATH": os.environ.get("PATH", ""), "HOME": str(ctx["workspace"]), "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": os.devnull}
    def git(*args):
        return subprocess.run(["git", "--no-optional-locks", *args], cwd=str(ctx["workspace"]), env=env,
                              capture_output=True, text=True)
    r = git("rev-list", "--count", "HEAD")
    if r.returncode != 0:
        return False, "not a git repository with commits: %s" % r.stderr.strip()[:120]
    n, want = int(r.stdout.strip()), spec.get("commits", 1)
    staged = git("diff", "--cached", "--name-only").stdout.split()
    ok = n == want and not staged
    return ok, "%d commits (expected %d), staged: %s" % (n, want, ", ".join(staged[:5]) or "none")


def _tool_outputs(events_text, input_regex):
    """Output text of each tool call whose JSON input matches input_regex, in order."""
    import json
    calls, outputs = {}, []
    for line in (events_text or "").splitlines():
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if not isinstance(e, dict):
            continue
        for item in ((e.get("message") or {}).get("content") or []) if isinstance((e.get("message") or {}).get("content"), list) else []:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "tool_use" and re.search(input_regex, json.dumps(item.get("input", {}))):
                calls[item.get("id")] = True
            elif item.get("type") == "tool_result" and item.get("tool_use_id") in calls:
                c = item.get("content")
                if isinstance(c, list):
                    c = "\n".join(b.get("text", "") for b in c if isinstance(b, dict))
                outputs.append(c or "")
    return outputs


def _subsequence(want, have):
    it = iter(have)
    return all(any(x == y for y in it) for x in want)


@grader("reply_echoes_tool_output", required=["input_regex"])
def reply_echoes_tool_output(ctx, spec):
    """One line of the final text holds every number from the first line of the last output of a tool
    call matching input_regex, in the same order (wording may differ). Fails when no such call exists
    or its output line has no numbers."""
    outs = _tool_outputs(ctx.get("events_text"), spec["input_regex"])
    if not outs:
        return False, "no tool call matching %s with an output" % spec["input_regex"]
    first = (outs[-1].strip().splitlines() or [""])[0]
    want = re.findall(r"\d+", first)
    if not want:
        return False, "the tool output line has no numbers: %r" % first[:80]
    for line in (ctx["summary"].get("final_text") or "").splitlines():
        if _subsequence(want, re.findall(r"\d+", line)):
            return True, "the reply shows %s from %r" % (" ".join(want), first[:80])
    return False, "no line of the reply shows %s from %r" % (" ".join(want), first[:80])


def run_graders(specs, ctx):
    out = []
    for spec in specs:
        fn = GRADERS[spec["type"]]
        try:
            passed, why = fn(ctx, spec)
        except FileNotFoundError as exc:  # a file the stage should have written: an ordinary fail
            passed, why = False, str(exc.args[0] if exc.args else exc)
        except Exception as exc:  # a grader bug must not look like a plugin pass
            passed, why = False, "grader error: %s" % exc
        out.append({"name": spec.get("name", spec["type"]), "type": spec["type"], "passed": bool(passed), "explanation": why})
    return out
