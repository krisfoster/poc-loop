"""Case schema and loader. Errors name the file and the field."""
import fnmatch
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import graders as graders_mod

MIN_RUN_CAP_USD = 0.10  # a first turn alone costs about $0.03, see docs/evals/spike-findings.md (0.5)
ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")
ALLOWED_KEYS = {
    "id", "stage", "set", "n_runs", "prompt", "fixture", "allowed_tools", "timeout_s",
    "max_cost_usd", "graders", "git", "description", "cwd", "add_root_dir",
}
REQUIRED_KEYS = ["id", "stage", "set", "prompt", "fixture", "allowed_tools", "graders"]


class CaseError(ValueError):
    pass


@dataclass
class Case:
    id: str
    stage: str
    set: str
    prompt: str
    fixture: str
    allowed_tools: List[str]
    graders: List[Dict[str, Any]]
    n_runs: int = 3
    timeout_s: int = 300
    max_cost_usd: float = 0.25
    git: bool = True
    cwd: str = "."  # where the session starts, relative to the workspace root (a subdirectory of the fixture)
    add_root_dir: bool = False  # add the workspace root as an additional directory, like /add-dir in a session
    description: str = ""
    source: str = field(default="", compare=False)

    @property
    def name(self):
        return "%s/%s" % (self.stage, self.id)


def _check(path, name, cond, msg, errors):
    if not cond:
        errors.append("%s: field '%s': %s" % (path, name, msg))
    return cond


def validate(raw, path, fixtures_dir=None):
    """Return (Case or None, [error strings])."""
    errors = []  # type: List[str]
    p = Path(path)
    if not isinstance(raw, dict):
        return None, ["%s: top level must be a JSON object" % path]
    for k in raw:
        _check(path, k, k in ALLOWED_KEYS, "unknown field", errors)
    for k in REQUIRED_KEYS:
        _check(path, k, k in raw, "required", errors)
    if errors:
        return None, errors

    _check(path, "id", isinstance(raw["id"], str) and ID_RE.match(raw["id"] or ""), "must match %s" % ID_RE.pattern, errors)
    _check(path, "id", raw["id"] == p.stem, "must equal the file name without .json (%s)" % p.stem, errors)
    _check(path, "stage", isinstance(raw["stage"], str) and raw["stage"] == p.parent.name,
           "must equal the parent directory name (%s)" % p.parent.name, errors)
    _check(path, "set", raw["set"] in ("tune", "holdout"), "must be 'tune' or 'holdout'", errors)
    _check(path, "prompt", isinstance(raw["prompt"], str) and raw["prompt"].strip() != "", "must be a non-empty string", errors)
    _check(path, "fixture", isinstance(raw["fixture"], str) and ID_RE.match(raw["fixture"] or ""), "must be a fixture directory name", errors)
    if fixtures_dir is not None and isinstance(raw["fixture"], str):
        _check(path, "fixture", (Path(fixtures_dir) / raw["fixture"]).is_dir(), "no such fixture directory under evals/fixtures", errors)
    tools = raw["allowed_tools"]
    _check(path, "allowed_tools", isinstance(tools, list) and all(isinstance(t, str) and t for t in tools),
           "must be a list of tool names or patterns", errors)
    n_runs = raw.get("n_runs", 3)
    _check(path, "n_runs", isinstance(n_runs, int) and not isinstance(n_runs, bool) and 1 <= n_runs <= 20,
           "must be an integer between 1 and 20", errors)
    timeout = raw.get("timeout_s", 300)
    _check(path, "timeout_s", isinstance(timeout, int) and not isinstance(timeout, bool) and 10 <= timeout <= 3600,
           "must be an integer between 10 and 3600", errors)
    cap = raw.get("max_cost_usd", 0.25)
    _check(path, "max_cost_usd", isinstance(cap, (int, float)) and not isinstance(cap, bool) and cap >= MIN_RUN_CAP_USD,
           "must be a number of at least %.2f (smaller caps stop a run on its first turn)" % MIN_RUN_CAP_USD, errors)
    _check(path, "git", isinstance(raw.get("git", True), bool), "must be true or false", errors)
    _check(path, "add_root_dir", isinstance(raw.get("add_root_dir", False), bool), "must be true or false", errors)
    cwd = raw.get("cwd", ".")
    if _check(path, "cwd", isinstance(cwd, str) and cwd.strip() != "", "must be a relative directory name", errors):
        parts = Path(cwd).parts
        _check(path, "cwd", not Path(cwd).is_absolute() and ".." not in parts,
               "must be inside the workspace (no absolute path, no '..')", errors)
        if fixtures_dir is not None and isinstance(raw.get("fixture"), str) and not Path(cwd).is_absolute() and ".." not in parts:
            _check(path, "cwd", (Path(fixtures_dir) / raw["fixture"] / cwd).is_dir(),
                   "no such directory in the fixture (it must exist before the run)", errors)

    specs = raw["graders"]
    if _check(path, "graders", isinstance(specs, list) and len(specs) > 0, "must be a non-empty list", errors):
        for i, spec in enumerate(specs):
            where = "graders[%d]" % i
            if not _check(path, where, isinstance(spec, dict) and "type" in spec, "must be an object with a 'type'", errors):
                continue
            if not _check(path, where + ".type", spec["type"] in graders_mod.GRADERS,
                          "unknown grader (known: %s)" % ", ".join(sorted(graders_mod.GRADERS)), errors):
                continue
            for req in graders_mod.REQUIRED_PARAMS[spec["type"]]:
                _check(path, "%s.%s" % (where, req), req in spec, "required for grader '%s'" % spec["type"], errors)
    if errors:
        return None, errors
    return Case(
        id=raw["id"], stage=raw["stage"], set=raw["set"], prompt=raw["prompt"], fixture=raw["fixture"],
        allowed_tools=list(tools), graders=list(specs), n_runs=n_runs, timeout_s=timeout,
        max_cost_usd=float(cap), git=raw.get("git", True), cwd=str(Path(cwd)) if cwd != "." else ".",
        add_root_dir=raw.get("add_root_dir", False), description=raw.get("description", ""), source=str(path),
    ), []


def load_cases(cases_dir, fixtures_dir=None, name_glob=None, set_filter=None):
    cases = []  # type: List[Case]
    errors = []  # type: List[str]
    for path in sorted(Path(cases_dir).glob("*/*.json")):
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            errors.append("%s: not valid JSON: %s" % (path, exc))
            continue
        case, errs = validate(raw, str(path), fixtures_dir)
        errors.extend(errs)
        if case:
            cases.append(case)
    seen = {}  # type: Dict[str, str]
    for c in cases:
        if c.name in seen:
            errors.append("%s: field 'id': duplicate of %s" % (c.source, seen[c.name]))
        seen[c.name] = c.source
    if errors:
        raise CaseError("\n".join(errors))
    if name_glob:
        cases = [c for c in cases if fnmatch.fnmatch(c.name, name_glob)]
    if set_filter and set_filter != "all":
        cases = [c for c in cases if c.set == set_filter]
    return cases
