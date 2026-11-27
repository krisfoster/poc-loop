"""Self-check of the Phase 2 poc-log cases: each case's graders must pass a hand-made correct result
and fail one with a planted defect. No model calls. Run from the repo root:
python3 docs/evals/tools/selfcheck/poc_log_cases.py
"""
import json, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, "evals")
from harness import cases, graders, runner
ENTRY = "\n## 2026-11-27 10:00 HMAC known vector\n- Tried: an HMAC known vector\n- Learned: the signature matches\n- Dead ends: none\n- Decision: none yet\n- Next question: none yet\n- Later: none\n"
def text(n, over, nxt):
    return "Entry appended.\n\nElapsed 2 days of %s, %d %s.%s\n\nNext: %s" % (
        "2 hours" if over else "100000 hours", n, "entry" if n == 1 else "entries",
        "\nThat is over the timebox, decide now: iterate, pivot, harden, stop or pause." if over else "", nxt)
VERIFY = "keep building and run /spike-loop:poc-verify when there is something to check"
CHECK = "decide now with /spike-loop:poc-checkpoint <iterate | pivot | harden | stop | pause>"
good = {"fresh-log": (True, text(1, True, CHECK)), "earlier-entries": (True, text(4, True, CHECK)),
        "started-no-time": (True, text(2, True, CHECK)), "timebox-exceeded": (True, text(2, True, CHECK)),
        "within-timebox": (True, text(2, False, VERIFY)),
        "missing-files": (False, "No PoC documents found. Run /poc-start.\n\nNext: /spike-loop:poc-start")}
bad = {  # one known defect each
    "fresh-log": ("count template line", lambda ws, t: (ws/"poc-spec/LOG.md").open("a").write(ENTRY) and t.replace("1 entry", "2 entries")),
    "earlier-entries": ("reorders an entry", lambda ws, t: ((ws/"poc-spec/LOG.md").write_text((ws/"poc-spec/LOG.md").read_text().replace("Raw body read", "Raw body read (edited)") + ENTRY), t)[1]),
    "started-no-time": ("no time check", lambda ws, t: ((ws/"poc-spec/LOG.md").open("a").write(ENTRY), "Done.\nNext: x")[1]),
    "timebox-exceeded": ("Next not a checkpoint", lambda ws, t: ((ws/"poc-spec/LOG.md").open("a").write(ENTRY), t.replace(CHECK, VERIFY))[1]),
    "within-timebox": ("em dash in log", lambda ws, t: ((ws/"poc-spec/LOG.md").open("a").write(ENTRY.replace("none\n", "none \u2014 really\n", 1)), t)[1]),
    "missing-files": ("writes a log", lambda ws, t: ((ws/"poc-spec").mkdir(), (ws/"poc-spec/LOG.md").write_text("x"), t)[2]),
}
cs = {c.id: c for c in cases.load_cases("evals/cases", "evals/fixtures", "poc-log/*")}
rc = 0
for cid, (append, final) in good.items():
    for label in ("good", "bad"):
        tmp = Path(tempfile.mkdtemp()); ws = tmp / "ws"
        shutil.copytree("evals/fixtures/" + cs[cid].fixture, ws)
        before = runner.snapshot(ws)
        t = final
        if append: (ws/"poc-spec/LOG.md").open("a").write(ENTRY) if label == "good" else None
        if label == "bad":
            t = bad[cid][1](ws, final) or final
        ctx = {"workspace": ws, "fixture": Path("evals/fixtures")/cs[cid].fixture, "summary": {"final_text": t, "tool_calls": [], "permission_denials": []},
               "before": before, "after": runner.snapshot(ws), "events_text": ""}
        res = graders.run_graders(cs[cid].graders, ctx)
        ok = all(r["passed"] for r in res)
        want = label == "good"
        flag = "ok " if ok == want else "BAD"
        rc |= ok != want
        print(flag, cid, label, "" if label == "good" else bad[cid][0], "" if ok == want else [r["name"] + ": " + r["explanation"] for r in res if not r["passed"]] or "all passed")
        shutil.rmtree(tmp)
sys.exit(rc)
