"""Self-check of the poc-start, poc-checkpoint and poc-verify cases (plan 2.3 to 2.5): each case's
graders must pass a hand-made correct result and fail one with a planted defect. No model calls.
Run from the repo root: python3 docs/evals/tools/selfcheck/stage_cases.py
"""
import json, os, re, shutil, sys, tempfile
from pathlib import Path
sys.path.insert(0, "evals")
from harness import cases, graders, runner
skill = Path("skills/poc-start/SKILL.md").read_text()
WIRING = next(l[2:] for l in skill.splitlines() if l.startswith("> Docs folder:"))
T = lambda name: skill.split("### %s" % name)[1].split("````", 1)[1].split("\n", 1)[1].split("````")[0]
def ev(*items):
    out = []
    for kind, v in items:
        c = [{"type": "text", "text": v}] if kind == "text" else [{"type": "tool_use", "name": v, "input": {}}]
        out.append(json.dumps({"type": "assistant", "message": {"content": c}}))
    return "\n".join(out)

def poc(vis):
    t = T("POC.md")
    fill = {"<short title>": "Webhook HMAC check", "<YYYY-MM-DD HH:MM>": "2026-11-27 10:00", "<N hours>": "2 hours", "<1 or 2>": "1",
            "<name or none>": "none", "<private or public>": vis,
            "<One or two sentences. What are we trying to find out or prove?>": "Can a receiver verify the HMAC over the raw body?",
            "<How we will know it worked. Observable, ideally one command. If it cannot be scripted, write the manual check in the last section.>": "Manual, see the last section.",
            "1. <assumption, why it could be wrong>": "1. Signed over the raw body, could be parsed JSON.", "- <>": "- the HMAC check",
            '<Exact steps and the expected observation, or "none".>': "Send the test event, see 'signature ok'."}
    for k, v in fill.items(): t = t.replace(k, v)
    return t
def start_files(ws, vis="private"):
    (ws / "poc-spec").mkdir(exist_ok=True)
    (ws / "poc-spec/POC.md").write_text(poc(vis))
    (ws / "poc-spec/LOG.md").write_text(T("LOG.md") + "\n## 2026-11-27 10:00 PoC started\n- Tried: nothing yet\n- Learned: nothing yet\n- Dead ends: none\n- Decision: none yet\n- Next question: none yet\n- Later: none\n")
    (ws / "verify.sh").write_text(T("verify.sh")); (ws / "verify.sh").chmod(0o755)
    (ws / "CLAUDE.md").write_text("\n" + WIRING + "\n")
WRITE_EV = ev(("text", "Writing the files."), ("tool", "Write"))
START_NEXT = "Read poc-spec/POC.md and correct it.\n\nNext: start building and run /spike-loop:poc-verify when there is something to check"

def closing(ws, docs, outcome, resume):
    log = ws / docs / "LOG.md"
    log.write_text(log.read_text() + "\n## 2026-11-27 10:00 Checkpoint: %s\n- Tried: x\n- Learned: y\n- Dead ends: none\n- Decision: %s\n- Next question: z\n- Later: none\n- State: branch: main; at: abc1234; uncommitted: none; unmerged worktrees: none; waiting on you: none; resume: %s\n" % (outcome, outcome, resume))
def summary(ws): (ws / "SUMMARY.md").write_text("# Webhook\n\nQuestion: q\n\nAnswer: yes, it verifies.\n")
CLEAR = "Summary...\n\nNext: `/clear`, then `/spike-loop:poc-help`"
def handoff(ws):
    (ws / "poc-spec/handoffs").mkdir(parents=True)
    (ws / "poc-spec/handoffs/2026-11-27-webhook-retry.md").write_text("# Hand-off\n- State: branch: main; at: abc1234; uncommitted: none\n")

def vf(text): return "VERDICT: " + text + "\nCommands run:\ncd /x && ./verify.sh"

G = {  # case: (good builder -> (final, events), bad builder -> (final, events), bad label)
 "poc-start/all-answers": (lambda ws: (start_files(ws), (START_NEXT, WRITE_EV))[1],
                           lambda ws: (start_files(ws), (ws / "verify.sh").write_text("#!/usr/bin/env bash\nexit 0\n"), (START_NEXT, WRITE_EV))[2], "stub exits 0"),
 "poc-start/public-repo": (lambda ws: (start_files(ws, "public"), ("Keep customer names and deal details out of poc-spec/. " + START_NEXT, WRITE_EV))[1],
                           lambda ws: (start_files(ws, "public"), ("Is the repo public? " + START_NEXT, ev(("text", "Is the repo public?"), ("tool", "Write"))))[1], "re-asks visibility"),
 "poc-start/partial-answers": (lambda ws: ("What is the question? What are the riskiest assumptions?", ev(("text", "What is the question? What are the riskiest assumptions?"))),
                               lambda ws: ("What tier is this?", ev(("text", "What tier is this?"))), "re-asks tier"),
 "poc-start/no-arguments": (lambda ws: ("What is the question?", ev(("text", "What is the question?"))),
                            lambda ws: (start_files(ws), ("Wrote files.", WRITE_EV))[1], "writes files"),
 "poc-start/tier-0": (lambda ws: ("That is a one-line change.\nNext: no PoC files are needed, just ask for the change", ""),
                      lambda ws: ((ws / "app.py").write_text("bar = 1\n"), ("Done.\nNext: no PoC files are needed, just ask for the change", ""))[1], "makes the change"),
 "poc-start/existing-poc": (lambda ws: ("poc-spec/POC.md already exists. Stopping.\nNext: decide", ""),
                            lambda ws: ((ws / "poc-spec/POC.md").write_text("new"), ("Overwrote it.", ""))[1], "overwrites"),
 "poc-start/no-git-repo": (lambda ws: ("No git repo. I can run git init but cannot ask.\nNext: run git init or answer", ""),
                           lambda ws: ((ws / ".git").mkdir(), ("Ran git init.\nNext: x", ""))[1], "runs git init"),
 "poc-checkpoint/iterate": (lambda ws: (closing(ws, "poc-spec", "iterate", "check whether the header is hex or base64 with /spike-loop:poc-research"), (CLEAR, ""))[1],
                            lambda ws: (closing(ws, "poc-spec", "iterate", "/clear"), (CLEAR, ""))[1], "resume is /clear"),
 "poc-checkpoint/pivot": (lambda ws: (closing(ws, "poc-spec", "pivot", "edit the assumptions then build"), (CLEAR, ""))[1],
                          lambda ws: (closing(ws, "poc-spec", "pivot", "x"), summary(ws), (CLEAR, ""))[2], "writes SUMMARY.md"),
 "poc-checkpoint/harden": (lambda ws: (closing(ws, "poc-spec", "harden", "/spike-loop:poc-harden"), summary(ws), ("Next: /spike-loop:poc-harden", ""))[2],
                           lambda ws: (closing(ws, "poc-spec", "harden", "/spike-loop:poc-harden"), ("Next: /spike-loop:poc-harden", ""))[1], "no SUMMARY.md"),
 "poc-checkpoint/stop": (lambda ws: (closing(ws, "poc-spec", "stop", "none, the PoC is closed"), summary(ws), ("Next: nothing further, the PoC is closed", ""))[2],
                         lambda ws: (closing(ws, "poc-spec", "stop", "none, the PoC is closed"), summary(ws), (CLEAR, ""))[2], "Next has /clear"),
 "poc-checkpoint/stop-existing-summary": (lambda ws: (closing(ws, "poc-spec", "stop", "none, the PoC is closed"), summary(ws), ("Updated SUMMARY.md in place.\nNext: nothing further", ""))[2],
                         lambda ws: (closing(ws, "poc-spec", "stop", "none, the PoC is closed"), ("Updated SUMMARY.md.\nNext: nothing further", ""))[1], "summary not rewritten"),
 "poc-checkpoint/pause-topic": (lambda ws: (handoff(ws), closing(ws, "poc-spec", "pause", "read poc-spec/handoffs/2026-11-27-webhook-retry.md, then try base64 headers"), (CLEAR, ""))[2],
                                lambda ws: (closing(ws, "poc-spec", "pause", "read poc-spec/handoffs/2026-11-27-webhook-retry.md, then go"), (CLEAR, ""))[1], "no hand-off file"),
 "poc-checkpoint/pause-bad-topic": (lambda ws: ("That topic is not allowed. Give another topic.", ""),
                                    lambda ws: ((ws / "poc-spec/handoffs").mkdir(), (ws / "poc-spec/handoffs/2026-11-27-etc.md").write_text("x"), ("topic ok", ""))[2], "writes a hand-off"),
 "poc-checkpoint/empty-argument": (lambda ws: ("I recommend iterate. Confirm?\nNext: /spike-loop:poc-checkpoint iterate to confirm it", ev(("text", "I recommend iterate. Confirm?"))),
                                   lambda ws: ("I recommend iterate or pivot. Confirm?\nNext: /spike-loop:poc-checkpoint iterate or pivot", ev(("text", "Confirm?"))), "names two outcomes"),
 "poc-checkpoint/root-layout": (lambda ws: (closing(ws, ".", "iterate", "keep building"), (CLEAR, ""))[1],
                                lambda ws: (closing(ws, ".", "iterate", "keep building"), (ws / "poc-spec").mkdir(), (ws / "poc-spec/x").write_text("x"), (CLEAR, ""))[3], "creates poc-spec/"),
 "poc-checkpoint/missing-files": (lambda ws: ("No PoC.\nNext: /spike-loop:poc-start", ""),
                                  lambda ws: ((ws / "LOG.md").write_text("x"), ("Next: /spike-loop:poc-start", ""))[1], "writes a log"),
 "poc-verify/pass": (lambda ws: (vf("PASS\nNext: /spike-loop:poc-log to record it"), ""), lambda ws: (vf("FAIL\nNext: /spike-loop:poc-log"), ""), "wrong verdict"),
 "poc-verify/fail": (lambda ws: (vf("FAIL\ncheck failed: expected greeting hello, got goodbye\nNext: fix it and run /spike-loop:poc-verify again"), ""),
                     lambda ws: (vf("FAIL\nsomething failed\nNext: fix it and run /spike-loop:poc-verify again"), ""), "no relevant error"),
 "poc-verify/makefile-only": (lambda ws: (vf("PASS\nmake test\nNext: /spike-loop:poc-log"), ""), lambda ws: (vf("PASS\nNext: /spike-loop:poc-log"), ""), "make test not run"),
 "poc-verify/stub": (lambda ws: (vf("FAIL\nverify.sh is still a stub"), ""), lambda ws: (vf("PASS"), ""), "stub passes"),
 "poc-verify/manual": (lambda ws: ("VERDICT: PARTIAL\nNEEDS HUMAN: Open http://localhost:8080/health in a browser and confirm it says ok", ""),
                       lambda ws: ("VERDICT: PARTIAL\nNEEDS HUMAN: check the health page", ""), "step not exact"),
 "poc-verify/many-service": (lambda ws: ("VERDICT: PARTIAL\nSix services, beyond a quick check.", ""),
                             lambda ws: ((ws / "greeting.txt").write_text("x"), ("VERDICT: PARTIAL", ""))[1], "writes a file"),
}
# a correct Bash call for makefile-only's tool_call_count
TOOLS = {"poc-verify/makefile-only": [{"name": "Bash", "child": True}]}
cs = {c.name: c for c in cases.load_cases("evals/cases", "evals/fixtures")}
rc = 0
for name, (good, bad, label) in G.items():
    c = cs[name]
    for kind, fn in (("good", good), ("bad", bad)):
        tmp = Path(tempfile.mkdtemp()); ws = tmp / "ws"; home = tmp / "home"; home.mkdir()
        runner.make_workspace(Path("evals/fixtures") / c.fixture, ws, c.git, home)
        before = runner.snapshot(ws)
        final, events = fn(ws)
        ctx = {"workspace": ws, "fixture": Path("evals/fixtures") / c.fixture, "before": before, "after": runner.snapshot(ws),
               "summary": {"final_text": final, "tool_calls": TOOLS.get(name, []), "permission_denials": []}, "events_text": events}
        res = graders.run_graders(c.graders, ctx)
        ok = all(r["passed"] for r in res)
        right = ok == (kind == "good")
        rc |= not right
        print("ok " if right else "BAD", name, kind, label if kind == "bad" else "",
              "" if right else [r["name"] + ": " + r["explanation"] for r in res if not r["passed"]] or "all passed")
        shutil.rmtree(tmp)
sys.exit(rc)
