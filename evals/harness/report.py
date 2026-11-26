"""Summaries, the markdown table, counts-only baselines, and the regression comparison."""
import json
from pathlib import Path
from typing import Any, Dict, List, Optional


def load_results(result_dir):
    out = []
    for p in sorted(Path(result_dir).glob("*/*/run*.json")):
        out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def _empty_case(stage, set_):
    return {"stage": stage, "set": set_, "runs": 0, "valid": 0, "passes": 0, "invalid": 0,
            "harness_failures": 0, "denial_runs": 0, "cost_usd": 0.0}


def summarise(results):
    cases = {}  # type: Dict[str, Dict[str, Any]]
    stages = {}  # type: Dict[str, Dict[str, int]]
    versions, models, plugin_versions = set(), set(), set()
    for r in results:
        c = cases.setdefault(r["case"], _empty_case(r["stage"], r["set"]))
        c["runs"] += 1
        if r["status"] == "invalid":
            c["invalid"] += 1
        elif r["status"] == "harness_failure":
            c["harness_failures"] += 1
        else:
            c["valid"] += 1
            c["passes"] += 1 if r.get("passed") else 0
        if r.get("permission_denials"):
            c["denial_runs"] += 1
        c["cost_usd"] = round(c["cost_usd"] + (r.get("cost_usd") or 0.0), 4)
        if r.get("claude_version"):
            versions.add(r["claude_version"])
        if r.get("plugin_version"):
            plugin_versions.add(r["plugin_version"])
        models.update(r.get("models") or [])
    for name, c in cases.items():
        s = stages.setdefault(c["stage"], {"runs": 0, "valid": 0, "passes": 0})
        s["runs"] += c["runs"]
        s["valid"] += c["valid"]
        s["passes"] += c["passes"]
    totals = {
        "runs": sum(c["runs"] for c in cases.values()),
        "valid": sum(c["valid"] for c in cases.values()),
        "passes": sum(c["passes"] for c in cases.values()),
        "cost_usd": round(sum(c["cost_usd"] for c in cases.values()), 4),
    }
    return {
        "schema": 1,
        "meta": {"plugin_versions": sorted(plugin_versions), "claude_versions": sorted(versions), "models": sorted(models)},
        "cases": cases, "stages": stages, "totals": totals,
    }


def to_markdown(summary, skipped=()):
    m = summary["meta"]
    lines = ["Plugin %s | Claude Code %s | models: %s" % (
        ", ".join(m["plugin_versions"]) or "?", ", ".join(m["claude_versions"]) or "?", ", ".join(m["models"]) or "?"), ""]
    lines += ["| Case | Set | Passes | Valid runs | Invalid | Harness failures | Runs with denials | Est. cost USD |",
              "|---|---|---|---|---|---|---|---|"]
    for name in sorted(summary["cases"]):
        c = summary["cases"][name]
        lines.append("| %s | %s | %d/%d | %d | %d | %d | %d | %.4f |" % (
            name, c["set"], c["passes"], c["valid"], c["valid"], c["invalid"], c["harness_failures"], c["denial_runs"], c["cost_usd"]))
    lines += ["", "| Stage | Passes | Valid runs |", "|---|---|---|"]
    for name in sorted(summary["stages"]):
        s = summary["stages"][name]
        lines.append("| %s | %d/%d | %d |" % (name, s["passes"], s["valid"], s["valid"]))
    t = summary["totals"]
    lines += ["", "Total: %d runs, %d valid, %d passes, estimated cost USD %.4f (a subscription estimate, not a bill)." % (
        t["runs"], t["valid"], t["passes"], t["cost_usd"])]
    if skipped:
        lines += ["", "Not run because a budget cap was reached: %s" % ", ".join(skipped)]
    return "\n".join(lines) + "\n"


def baseline_counts(summary):
    """Counts only, built from a whitelist of fields. Never includes model output, prompts or paths."""
    out = {
        "schema": 1,
        "plugin_versions": list(summary["meta"]["plugin_versions"]),
        "claude_versions": list(summary["meta"]["claude_versions"]),
        "models": list(summary["meta"]["models"]),
        "cases": {}, "stages": {},
    }
    for name, c in summary["cases"].items():
        out["cases"][name] = {k: c[k] for k in ("stage", "set", "runs", "valid", "passes", "invalid", "harness_failures")}
    for name, s in summary["stages"].items():
        out["stages"][name] = {k: s[k] for k in ("runs", "valid", "passes")}
    return out


def load_thresholds(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _rate(c):
    return (c["passes"] / c["valid"]) if c.get("valid") else None


def _pool(summary, case_names, set_by_case):
    """Pooled stage counts over the named cases only."""
    stages = {}
    for name in case_names:
        c = summary["cases"][name]
        s = stages.setdefault(c["stage"], {"valid": 0, "passes": 0})
        s["valid"] += c["valid"]
        s["passes"] += c["passes"]
    return stages


def compare(base, new, thresholds, rerun=None, allow_missing=False):
    """Apply the regression rules from docs/evals/spec.md. base and new are summaries or baselines.

    regressions: cases or stages that fell. incomplete: cases that could not be judged (no valid runs, absent from
    the new results, or needing a rerun). The CLI exits 1 for a regression and 3 for incomplete, so neither passes.
    """
    cases, regressions, reruns, incomplete = {}, [], [], []
    for name in sorted(set(base["cases"]) | set(new["cases"])):
        b, n = base["cases"].get(name), new["cases"].get(name)
        if b is None:
            cases[name] = {"status": "new"}
            continue
        if n is None:
            cases[name] = {"status": "missing"}
            if not allow_missing:
                incomplete.append(name)
            continue
        br, nr = _rate(b), _rate(n)
        if br is None or nr is None:
            cases[name] = {"status": "unscored", "note": "no valid runs on one side"}
            incomplete.append(name)
            continue
        drop_runs = round((br - nr) * n["valid"], 3)
        entry = {"base": "%d/%d" % (b["passes"], b["valid"]), "new": "%d/%d" % (n["passes"], n["valid"]), "drop_runs": drop_runs}
        if drop_runs >= thresholds["case_drop_runs"]:
            entry["status"] = "regression"
            regressions.append(name)
        elif drop_runs >= thresholds["case_rerun_drop_runs"]:
            rr = (rerun or {}).get("cases", {}).get(name)
            if rr and rr.get("valid"):
                rr_rate = rr["passes"] / rr["valid"]
                if rr_rate < br - 1.0 / rr["valid"]:
                    entry["status"] = "regression"
                    entry["note"] = "confirmed on rerun %d/%d" % (rr["passes"], rr["valid"])
                    regressions.append(name)
                else:
                    entry["status"] = "cleared_on_rerun"
                    entry["note"] = "rerun %d/%d" % (rr["passes"], rr["valid"])
            else:
                entry["status"] = "rerun"
                entry["note"] = "rerun at N=%d to confirm" % thresholds["rerun_n"]
                reruns.append(name)
                incomplete.append(name)
        else:
            entry["status"] = "improved" if nr > br else "same"
        cases[name] = entry

    # Stage pools use only cases present on both sides, in the same set, so subsets and mixed sets compare like with like.
    common = [k for k in base["cases"] if k in new["cases"] and base["cases"][k]["set"] == new["cases"][k]["set"]]
    bpool, npool = _pool(base, common, None), _pool(new, common, None)
    stages = {}
    for name in sorted(set(bpool) & set(npool)):
        b, n = bpool[name], npool[name]
        if n["valid"] < thresholds["stage_min_runs"] or not b["valid"]:
            stages[name] = {"status": "too_few_runs", "valid": n["valid"]}
            continue
        drop_pp = round((b["passes"] / b["valid"] - n["passes"] / n["valid"]) * 100, 1)
        status = "regression" if drop_pp >= thresholds["stage_drop_pp"] else "ok"
        stages[name] = {"status": status, "drop_pp": drop_pp}
        if status == "regression":
            regressions.append("stage:" + name)
    return {"cases": cases, "stages": stages, "regressions": regressions, "reruns_needed": reruns, "incomplete": incomplete}


def compare_markdown(report):
    lines = ["| Case | Baseline | New | Drop (runs) | Status |", "|---|---|---|---|---|"]
    for name, e in report["cases"].items():
        lines.append("| %s | %s | %s | %s | %s %s |" % (
            name, e.get("base", "-"), e.get("new", "-"), e.get("drop_runs", "-"), e["status"], e.get("note", "")))
    lines += ["", "| Stage | Status |", "|---|---|"]
    for name, e in report["stages"].items():
        lines.append("| %s | %s %s |" % (name, e["status"], ("(drop %s pp)" % e["drop_pp"]) if "drop_pp" in e else ""))
    lines += ["", "Regressions: %s" % (", ".join(report["regressions"]) or "none")]
    if report["incomplete"]:
        lines.append("Incomplete (could not be judged, exit 3): %s" % ", ".join(report["incomplete"]))
    if report["reruns_needed"]:
        lines.append("Rerun needed: %s" % ", ".join(report["reruns_needed"]))
    return "\n".join(lines) + "\n"
