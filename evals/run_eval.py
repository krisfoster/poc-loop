#!/usr/bin/env python3
"""Stage evals for the Spike Loop. See docs/evals/spec.md and docs/evals/plan.md.

  run_eval.py list      [--case GLOB] [--set tune|holdout|all]
  run_eval.py dry-run   [--case GLOB] [--set ...] [--runs N]       no model is called
  run_eval.py run       [--case GLOB] [--set ...] [--runs N] [--suite-cap USD] [--out DIR] [--keep]
  run_eval.py report    RESULT_DIR
  run_eval.py baseline  RESULT_DIR --out FILE                       counts only
  run_eval.py compare   BASELINE NEW [--rerun DIR] [--allow-missing]  exit 1 on a regression, 3 if a case could not be judged

Standard library only. The token comes from SPIKE_EVALS_OAUTH_TOKEN (environment or .env), never printed.
"""
import argparse
import datetime
import json
import shutil
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(HERE))

from harness import cases as cases_mod  # noqa: E402
from harness import report as report_mod  # noqa: E402
from harness import runner  # noqa: E402

CASES_DIR = HERE / "cases"
FIXTURES_DIR = HERE / "fixtures"
BASELINES_DIR = HERE / "baselines"
THRESHOLDS = HERE / "thresholds.json"
COSTS_FILE = BASELINES_DIR / "costs.json"
HEADROOM = 1.5  # stop launching a run if spent + HEADROOM * its cap would exceed the suite cap (caps are soft, see findings 0.5)


def _load(args):
    return cases_mod.load_cases(CASES_DIR, FIXTURES_DIR, getattr(args, "case", None), getattr(args, "set", "tune"))


def _measured_costs():
    try:
        return json.loads(COSTS_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def cmd_list(args):
    for c in _load(args):
        print("%-28s set=%-7s runs=%d  %s" % (c.name, c.set, c.n_runs, c.description))
    return 0


def cmd_dry_run(args):
    cases = _load(args)
    costs = _measured_costs()
    total, unknown = 0.0, 0
    print("%-28s %5s %9s %14s" % ("case", "runs", "run cap", "est. per run"))
    for c in cases:
        n = args.runs or c.n_runs
        est = costs.get(c.name)
        if est is None:
            unknown += n
            est_s = "unmeasured"
        else:
            total += est * n
            est_s = "$%.4f" % est
        print("%-28s %5d %9s %14s" % (c.name, n, "$%.2f" % c.max_cost_usd, est_s))
    print("\n%d cases. Estimated total $%.4f%s. Dry run only: no model was called." % (
        len(cases), total, (" plus %d runs with no measured cost" % unknown) if unknown else ""))
    return 0


def cmd_run(args):
    cases = _load(args)
    if not cases:
        print("no cases selected", file=sys.stderr)
        return 2
    broad = {c.name: runner.broad_grants(c) for c in cases if runner.broad_grants(c)}
    if broad and not args.unsandboxed_ok:
        print("These cases grant tools that run on this machine without an OS sandbox:", file=sys.stderr)
        for name, tools in broad.items():
            print("  %s: %s" % (name, ", ".join(tools)), file=sys.stderr)
        print("Run in a sandbox, or pass --unsandboxed-ok to accept the risk.", file=sys.stderr)
        return 2
    try:
        token, plaintext = runner.load_token(REPO)
    except runner.RunnerError as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 2
    if plaintext:
        print("warning: the token is a plaintext value in .env. The repo rule is an op:// reference "
              "(SPIKE_EVALS_OAUTH_TOKEN=op://vault/item/field). Treat this as temporary.", file=sys.stderr)

    out = Path(args.out) if args.out else HERE / "results" / datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out.mkdir(parents=True, exist_ok=True)
    plugin_tmp = Path(tempfile.mkdtemp(prefix="spike-plugin-"))
    claude_cmd = tuple(args.claude_cmd.split()) if args.claude_cmd else ("claude",)
    spent, skipped, results = 0.0, [], []
    try:
        plugin_dir = runner.build_plugin_copy(REPO, plugin_tmp / "plugin")
        stopped = False
        for c in cases:
            n = args.runs or c.n_runs
            if stopped:
                skipped.append("%s (not started)" % c.name)
                continue
            for i in range(1, n + 1):
                if spent + HEADROOM * c.max_cost_usd > args.suite_cap:
                    skipped.append("%s (from run %d)" % (c.name, i))
                    stopped = True  # the suite stops when the cap is reached, later cases do not sneak in
                    break
                r = runner.run_once(c, i, REPO, plugin_dir, token, out, FIXTURES_DIR, claude_cmd, args.keep)
                results.append(r)
                # Caps are soft and a run with no result may still have spent money, so an unknown cost counts as the cap.
                spent += r["cost_usd"] if r.get("cost_usd") is not None else c.max_cost_usd
                print("%s run %d: %s%s  est. cost %s" % (
                    c.name, i, "PASS" if r["passed"] else r["status"] if r["status"] != "ok" else "FAIL",
                    (" (%s)" % r["reason"]) if r.get("reason") else "",
                    ("$%.4f" % r["cost_usd"]) if r.get("cost_usd") is not None else "unknown, counted as the cap"), flush=True)
    finally:
        shutil.rmtree(str(plugin_tmp), ignore_errors=True)
        # Always write what was paid for, even after an interrupt or an unexpected error.
        summary = report_mod.summarise(results)
        (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
        md = report_mod.to_markdown(summary, skipped)
        (out / "summary.md").write_text(md, encoding="utf-8")
    print("\n" + md)
    print("Results in %s" % out)
    return 2 if skipped else 0


def _as_summary(path):
    p = Path(path)
    if p.is_dir():
        return report_mod.summarise(report_mod.load_results(p))
    return json.loads(p.read_text(encoding="utf-8"))


def cmd_report(args):
    print(report_mod.to_markdown(_as_summary(args.result_dir)))
    return 0


def cmd_baseline(args):
    counts = report_mod.baseline_counts(_as_summary(args.result_dir))
    Path(args.out).write_text(json.dumps(counts, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("wrote %s (counts only)" % args.out)
    return 0


def cmd_compare(args):
    rep = report_mod.compare(_as_summary(args.baseline), _as_summary(args.new),
                             report_mod.load_thresholds(THRESHOLDS), _as_summary(args.rerun) if args.rerun else None,
                             allow_missing=args.allow_missing)
    print(report_mod.compare_markdown(rep))
    if rep["regressions"]:
        return 1
    return 3 if rep["incomplete"] else 0


def _runs(value):
    try:
        n = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be an integer from 1 to 20")
    if not 1 <= n <= 20:
        raise argparse.ArgumentTypeError("must be an integer from 1 to 20")
    return n


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    def selectors(p, with_runs=False):
        p.add_argument("--case", help="glob on stage/id")
        p.add_argument("--set", default="tune", choices=["tune", "holdout", "all"],
                       help="default tune; holdout is only for release runs")
        if with_runs:
            p.add_argument("--runs", type=_runs, help="override n_runs for every case (1 to 20)")

    selectors(sub.add_parser("list"))
    selectors(sub.add_parser("dry-run"), True)
    r = sub.add_parser("run")
    selectors(r, True)
    r.add_argument("--suite-cap", type=float, default=1.0, help="stop launching runs near this estimated USD total (default 1.00)")
    r.add_argument("--out")
    r.add_argument("--keep", action="store_true", help="keep each run's temporary workspace and print nothing secret")
    r.add_argument("--unsandboxed-ok", action="store_true", help="allow cases that grant Bash, WebFetch or WebSearch without a sandbox")
    r.add_argument("--claude-cmd", help="command to run instead of `claude` (used by the tests)")
    sub.add_parser("report").add_argument("result_dir")
    b = sub.add_parser("baseline")
    b.add_argument("result_dir")
    b.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("baseline")
    c.add_argument("new")
    c.add_argument("--rerun")
    c.add_argument("--allow-missing", action="store_true", help="do not treat baseline cases absent from NEW as incomplete (a deliberate subset run)")
    args = ap.parse_args(argv)
    try:
        return {"list": cmd_list, "dry-run": cmd_dry_run, "run": cmd_run, "report": cmd_report,
                "baseline": cmd_baseline, "compare": cmd_compare}[args.cmd](args)
    except cases_mod.CaseError as exc:
        print("case error:\n%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
