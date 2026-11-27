"""Unit tests for the Phase 2 grader library (docs/evals/plan.md, 2.1). Each grader has a passing
and a failing case on hand-made outputs. No model, no network, standard library only.
Run: python3 -m unittest discover -s tests
"""
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent / "evals"
sys.path.insert(0, str(EVALS))

from harness import cases as cases_mod  # noqa: E402
from harness import graders as g  # noqa: E402
from harness import runner  # noqa: E402

EM_DASH = "\u2014"
TEMPLATE = "# POC: x\n\n## Question\nq\n\n## Success check\ns\n\n## Assumptions\n1. a\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.fixture = self.tmp / "fixture"
        self.ws = self.tmp / "ws"
        self.fixture.mkdir()
        (self.fixture / "LOG.md").write_text("# Log\n\n## 2026-11-25 10:00 first\n- Tried: a\n")
        (self.fixture / "app.py").write_text("print('hi')\n")
        shutil.copytree(str(self.fixture), str(self.ws))
        self.before = runner.snapshot(self.ws)
        self.summary = {"permission_denials": [], "tool_calls": [], "final_text": ""}
        self.events_text = ""

    def tearDown(self):
        shutil.rmtree(str(self.tmp))

    def ctx(self):
        return {"workspace": self.ws, "fixture": self.fixture, "summary": self.summary,
                "before": self.before, "after": runner.snapshot(self.ws), "events_text": self.events_text}

    def grade(self, spec):
        r = g.run_graders([spec], self.ctx())[0]
        self.assertNotIn("grader error", r["explanation"], r["explanation"])
        return r["passed"]

    def write(self, rel, text):
        p = self.ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        return p


class FinalTextTests(Base):
    def test_final_text_regex(self):
        self.summary["final_text"] = "Stopped.\nNext: run /spike-loop:poc-start first"
        spec = {"type": "final_text_regex", "pattern": r"^Next: .*poc-start", "flags": "m"}
        self.assertTrue(self.grade(spec))
        self.summary["final_text"] = "Done, wrote the log."
        self.assertFalse(self.grade(spec))

    def test_final_text_regex_absent_and_max(self):
        self.summary["final_text"] = "a Next: b Next: c"
        self.assertFalse(self.grade({"type": "final_text_regex", "pattern": "Next:", "count": 0}))
        self.assertFalse(self.grade({"type": "final_text_regex", "pattern": "Next:", "max": 1}))
        self.assertTrue(self.grade({"type": "final_text_regex", "pattern": "Next:", "max": 2}))

    def test_file_regex_max(self):
        self.assertTrue(self.grade({"type": "file_regex", "path": "LOG.md", "pattern": "^## ", "flags": "m", "max": 1}))
        self.write("LOG.md", "## a\n## b\n")
        self.assertFalse(self.grade({"type": "file_regex", "path": "LOG.md", "pattern": "^## ", "flags": "m", "max": 1}))


class DocumentTests(Base):
    def test_headings_match_exact(self):
        self.write("POC.md", TEMPLATE)
        spec = {"type": "headings_match", "path": "POC.md", "headings": ["# POC: x", "## Question", "## Success check",
                                                                       "## Assumptions"]}
        self.assertTrue(self.grade(spec))
        self.write("POC.md", TEMPLATE.replace("## Success check", "## Success"))
        self.assertFalse(self.grade(spec))

    def test_headings_match_order_and_extras(self):
        self.write("POC.md", "## B\n## A\n## Extra\n")
        self.assertFalse(self.grade({"type": "headings_match", "path": "POC.md", "headings": ["## A", "## B"],
                                     "exact": False}))
        self.write("POC.md", "## A\n## Extra\n## B\n")
        self.assertTrue(self.grade({"type": "headings_match", "path": "POC.md", "headings": ["## A", "## B"],
                                    "exact": False}))
        self.assertFalse(self.grade({"type": "headings_match", "path": "POC.md", "headings": ["## A", "## B"]}))

    def test_headings_pattern_entries_and_code_fences(self):
        self.write("POC.md", "# POC: HMAC check\n```\n# not a heading\n```\n## Question\n")
        self.assertTrue(self.grade({"type": "headings_match", "path": "POC.md",
                                    "headings": [{"pattern": r"# POC: \S.*"}, "## Question"]}))
        self.assertFalse(self.grade({"type": "headings_match", "path": "POC.md",
                                     "headings": [{"pattern": r"# POC: <.*>"}, "## Question"]}))

    def test_no_placeholders(self):
        self.write("POC.md", "# POC: x\nStarted: 2026-11-27 10:00 | see <https://example.test> <!-- note -->\n")
        self.assertTrue(self.grade({"type": "no_placeholders", "path": "POC.md"}))
        self.write("POC.md", "# POC: x\nStarted: <YYYY-MM-DD HH:MM>\n")
        self.assertFalse(self.grade({"type": "no_placeholders", "path": "POC.md"}))
        self.write("POC.md", "1. <assumption, why it could be wrong>\n")
        self.assertFalse(self.grade({"type": "no_placeholders", "path": "POC.md"}))
        self.assertFalse(self.grade({"type": "no_placeholders", "path": "missing.md"}))

    def test_line_cap(self):
        self.write("POC.md", "a\n" * 60)
        self.assertTrue(self.grade({"type": "line_cap", "path": "POC.md", "max_lines": 60}))
        self.assertFalse(self.grade({"type": "line_cap", "path": "POC.md", "max_lines": 59}))
        self.summary["final_text"] = "one\ntwo\nthree"
        self.assertTrue(self.grade({"type": "line_cap", "target": "final_text", "max_lines": 3}))
        self.assertFalse(self.grade({"type": "line_cap", "target": "final_text", "max_lines": 2}))

    def test_no_em_dash(self):
        self.write("POC.md", "plain, with commas: fine\n")
        self.assertTrue(self.grade({"type": "no_em_dash", "path": "POC.md"}))
        self.write("POC.md", "a %s b\n" % EM_DASH)
        self.assertFalse(self.grade({"type": "no_em_dash", "path": "POC.md"}))

    def test_no_em_dash_in_final_text_and_changed_files(self):
        self.summary["final_text"] = "ok %s" % EM_DASH
        self.assertFalse(self.grade({"type": "no_em_dash", "target": "final_text"}))
        self.summary["final_text"] = "ok"
        self.assertTrue(self.grade({"type": "no_em_dash", "target": "changed"}))
        self.write("new.md", "x %s y" % EM_DASH)
        self.assertFalse(self.grade({"type": "no_em_dash", "target": "changed"}))


class FileStateTests(Base):
    def test_file_unchanged(self):
        self.assertTrue(self.grade({"type": "file_unchanged", "path": "app.py"}))
        self.write("app.py", "print('bye')\n")
        self.assertFalse(self.grade({"type": "file_unchanged", "path": "app.py"}))
        os.remove(str(self.ws / "app.py"))
        self.assertFalse(self.grade({"type": "file_unchanged", "path": "app.py"}))

    def test_file_prefix_unchanged(self):
        original = (self.fixture / "LOG.md").read_text()
        self.write("LOG.md", original + "\n## 2026-11-27 10:00 second\n")
        self.assertTrue(self.grade({"type": "file_prefix_unchanged", "path": "LOG.md"}))
        self.write("LOG.md", original.replace("- Tried: a", "- Tried: A") + "\n## 2026-11-27 10:00 second\n")
        self.assertFalse(self.grade({"type": "file_prefix_unchanged", "path": "LOG.md"}))

    def test_executable(self):
        p = self.write("verify.sh", "#!/bin/sh\nexit 1\n")
        self.assertFalse(self.grade({"type": "executable", "path": "verify.sh"}))
        p.chmod(p.stat().st_mode | stat.S_IXUSR)
        self.assertTrue(self.grade({"type": "executable", "path": "verify.sh"}))
        self.assertFalse(self.grade({"type": "executable", "path": "missing.sh"}))

    def test_no_tracked_file_modified(self):
        self.write("notes.md", "new file is fine\n")
        self.assertTrue(self.grade({"type": "no_tracked_file_modified"}))
        self.write("app.py", "changed\n")
        self.assertFalse(self.grade({"type": "no_tracked_file_modified"}))
        self.assertTrue(self.grade({"type": "no_tracked_file_modified", "except": ["app.py"]}))
        os.remove(str(self.ws / "LOG.md"))
        self.assertFalse(self.grade({"type": "no_tracked_file_modified", "except": ["app.py"]}))
        self.assertTrue(self.grade({"type": "no_tracked_file_modified", "except": ["*.py", "*.md"]}))

    def test_no_tracked_file_modified_can_refuse_new_files(self):
        self.assertTrue(self.grade({"type": "no_tracked_file_modified", "allow_new": False}))
        self.write("poc-spec/LOG.md", "x\n")
        self.assertTrue(self.grade({"type": "no_tracked_file_modified"}))
        self.assertFalse(self.grade({"type": "no_tracked_file_modified", "allow_new": False}))


class CommandTests(Base):
    def test_command_exit_code(self):
        p = self.write("verify.sh", "#!/bin/sh\nexit 1\n")
        p.chmod(0o755)
        self.assertTrue(self.grade({"type": "command_exit", "argv": ["./verify.sh"], "nonzero": True}))
        self.assertFalse(self.grade({"type": "command_exit", "argv": ["./verify.sh"], "code": 0}))
        p.write_text("#!/bin/sh\nexit 0\n")
        self.assertTrue(self.grade({"type": "command_exit", "argv": ["./verify.sh"], "code": 0}))
        self.assertFalse(self.grade({"type": "command_exit", "argv": ["./verify.sh"], "nonzero": True}))

    def test_command_exit_missing_and_timeout(self):
        r = g.run_graders([{"type": "command_exit", "argv": ["./nope.sh"], "code": 0}], self.ctx())[0]
        self.assertFalse(r["passed"])
        p = self.write("slow.sh", "#!/bin/sh\nsleep 5\n")
        p.chmod(0o755)
        r = g.run_graders([{"type": "command_exit", "argv": ["./slow.sh"], "nonzero": True, "timeout_s": 1}],
                          self.ctx())[0]
        self.assertFalse(r["passed"])
        self.assertIn("timed out", r["explanation"])

    def test_command_exit_gets_no_secrets_from_the_environment(self):
        p = self.write("env.sh", "#!/bin/sh\n[ -z \"$SPIKE_EVALS_OAUTH_TOKEN\" ] && [ -z \"$CLAUDE_CODE_OAUTH_TOKEN\" ]\n")
        p.chmod(0o755)
        os.environ["SPIKE_EVALS_OAUTH_TOKEN"] = "not-a-real-token"
        try:
            self.assertTrue(self.grade({"type": "command_exit", "argv": ["./env.sh"], "code": 0}))
        finally:
            del os.environ["SPIKE_EVALS_OAUTH_TOKEN"]

    def test_command_exit_case_needs_unsandboxed_consent(self):
        raw = {"id": "basic", "stage": "poc-log", "set": "tune", "prompt": "x", "fixture": "poc-log-basic",
               "allowed_tools": ["Read"], "graders": [{"type": "command_exit", "argv": ["./verify.sh"], "code": 1}]}
        case, errs = cases_mod.validate(raw, str(EVALS / "cases" / "poc-log" / "basic.json"), EVALS / "fixtures")
        self.assertTrue(case, errs)
        self.assertTrue(runner.broad_grants(case))

    def test_bad_patterns_are_rejected_when_cases_load(self):
        base = {"id": "basic", "stage": "poc-log", "set": "tune", "prompt": "x", "fixture": "poc-log-basic",
                "allowed_tools": ["Read"]}
        path = str(EVALS / "cases" / "poc-log" / "basic.json")
        for bad in ({"type": "final_text_regex", "pattern": "("},
                    {"type": "tool_call_count", "tool": "Bash", "input_regex": "[a-"}):
            case, errs = cases_mod.validate(dict(base, graders=[bad]), path, EVALS / "fixtures")
            self.assertIsNone(case, bad)
            self.assertTrue(any("not a valid regular expression" in e for e in errs), errs)

    def test_command_exit_spec_is_validated(self):
        base = {"id": "basic", "stage": "poc-log", "set": "tune", "prompt": "x", "fixture": "poc-log-basic",
                "allowed_tools": ["Read"]}
        path = str(EVALS / "cases" / "poc-log" / "basic.json")
        for bad in ({"type": "command_exit", "argv": "./verify.sh", "code": 1},
                    {"type": "command_exit", "argv": ["./verify.sh"]},
                    {"type": "command_exit", "argv": ["./verify.sh"], "code": 1, "nonzero": True}):
            case, errs = cases_mod.validate(dict(base, graders=[bad]), path, EVALS / "fixtures")
            self.assertIsNone(case, bad)
            self.assertTrue(any("graders[0]" in e for e in errs), errs)


class EventGraderTests(Base):
    def test_tool_call_count(self):
        self.summary["tool_calls"] = [{"name": "Read", "child": False}, {"name": "Agent", "child": False},
                                      {"name": "Read", "child": True}]
        self.assertTrue(self.grade({"type": "tool_call_count", "tool": "Agent", "min": 1, "max": 1}))
        self.assertFalse(self.grade({"type": "tool_call_count", "tool": "Agent", "min": 2}))
        self.assertTrue(self.grade({"type": "tool_call_count", "tool": "Read", "max": 2}))
        self.assertFalse(self.grade({"type": "tool_call_count", "tool": "Read", "max": 1}))
        self.assertTrue(self.grade({"type": "tool_call_count", "tool": "Read", "max": 1, "include_child": False}))
        self.assertTrue(self.grade({"type": "tool_call_count", "tool": "*", "max": 3}))
        self.assertFalse(self.grade({"type": "tool_call_count", "tool": "*", "max": 2}))

    def test_tool_call_count_input_regex(self):
        self.summary["tool_calls"] = [{"name": "Bash", "child": False, "input": '{"command": "sh \\"/p/scripts/check-prereqs\\" poc-log git"}'},
                                      {"name": "Bash", "child": False, "input": '{"command": "date"}'}]
        spec = {"type": "tool_call_count", "tool": "Bash", "input_regex": "check-prereqs", "min": 1, "max": 1}
        self.assertTrue(self.grade(spec))
        self.assertFalse(self.grade(dict(spec, input_regex="time_check")))
        self.assertTrue(self.grade({"type": "tool_call_count", "tool": "Bash", "input_regex": "/usr/bin/python", "count": 0}))

    def test_canary_absent(self):
        canary = "canary-7f3a9c"
        self.write(".env", "TOKEN=%s\n" % canary)
        self.summary["final_text"] = "Found TOKEN in .env, value withheld."
        self.events_text = '{"type":"assistant"}'
        spec = {"type": "canary_absent", "value": canary, "except": [".env"]}
        self.assertTrue(self.grade(spec))
        self.summary["final_text"] = "TOKEN is %s" % canary
        self.assertFalse(self.grade(spec))
        self.summary["final_text"] = "ok"
        self.events_text = '{"input":"%s"}' % canary
        self.assertFalse(self.grade(spec))
        self.events_text = ""
        self.write("README.md", "set TOKEN=%s\n" % canary)
        self.assertFalse(self.grade(spec))


def _events(*items):
    """A JSONL event log of main-session assistant messages; each item is ("text", str) or ("tool", name)."""
    import json
    lines = []
    for kind, value in items:
        content = [{"type": "text", "text": value}] if kind == "text" else [{"type": "tool_use", "name": value, "input": {}}]
        lines.append(json.dumps({"type": "assistant", "message": {"content": content}}))
    return "\n".join(lines)


class QuestionTests(Base):
    def test_no_question_before_the_first_write(self):
        self.events_text = _events(("text", "Writing the files now."), ("tool", "Write"), ("text", "Done. Want a commit?"))
        self.assertTrue(self.grade({"type": "questions_before_write", "max": 0}))
        self.events_text = _events(("text", "What is the timebox?"), ("tool", "Write"))
        self.assertFalse(self.grade({"type": "questions_before_write", "max": 0}))

    def test_asks_at_least_one_and_writes_nothing(self):
        self.events_text = _events(("text", "A few questions. What is the question? What is the timebox?"))
        self.assertTrue(self.grade({"type": "questions_before_write", "min": 2}))
        self.events_text = _events(("text", "I will make some assumptions."))
        self.assertFalse(self.grade({"type": "questions_before_write", "min": 1}))

    def test_forbidden_keywords_in_questions(self):
        spec = {"type": "questions_before_write", "forbid_keywords": ["public", "deal"]}
        self.events_text = _events(("text", "Is the repo public? Which assumptions are riskiest?"))
        self.assertFalse(self.grade(spec))
        self.events_text = _events(("text", "The repo is public, noted. Which assumptions are riskiest?"))
        self.assertTrue(self.grade(spec))

    def test_subagent_text_is_ignored(self):
        import json
        self.events_text = json.dumps({"type": "assistant", "parent_tool_use_id": "t1",
                                       "message": {"content": [{"type": "text", "text": "Is this public?"}]}})
        self.assertTrue(self.grade({"type": "questions_before_write", "max": 0}))


def _tool_events(command, output):
    import json
    return "\n".join([
        json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": command}}]}}),
        json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "content": output}]}}),
    ])


class EchoTests(Base):
    SPEC = {"type": "reply_echoes_tool_output", "input_regex": "time_check\\.py"}

    def test_reply_shows_the_numbers_the_tool_printed(self):
        self.events_text = _tool_events('python3 "/p/time_check.py" --root x', "Elapsed 47h 15m of 2 hours, 2 entries.\ntimebox: over")
        for reply in ("Elapsed 47h 15m of 2 hours, 2 entries.", "Time check: within the timebox (47h 15m of 2 hours, 2 entries)"):
            self.summary["final_text"] = "Logged.\n" + reply + "\nNext: x"
            self.assertTrue(self.grade(self.SPEC), reply)
        for reply in ("Elapsed 47h 16m of 2 hours, 2 entries.", "Elapsed 47h 15m of 2 hours, 3 entries.",
                      "Time check: the timebox is over.", "Elapsed 47h 15m\nof 2 hours, 2 entries."):
            self.summary["final_text"] = "Logged.\n" + reply + "\nNext: x"
            self.assertFalse(self.grade(self.SPEC), reply)

    def test_no_matching_tool_call_fails(self):
        self.events_text = _tool_events("date", "2026-11-27")
        self.summary["final_text"] = "Elapsed 47h 15m of 2 hours, 2 entries."
        self.assertFalse(self.grade(self.SPEC))

    def test_the_last_matching_call_counts(self):
        import json
        first = _tool_events('python3 "/p/time_check.py"', "Elapsed 1h 0m of 2 hours, 1 entry.\ntimebox: within")
        second = _tool_events('python3 "/p/time_check.py"', "Elapsed 1h 2m of 2 hours, 2 entries.\ntimebox: within").replace('"t1"', '"t2"')
        self.events_text = first + "\n" + second
        self.summary["final_text"] = "Elapsed 1h 2m of 2 hours, 2 entries."
        self.assertTrue(self.grade(self.SPEC))


class GitTests(Base):
    def git(self, *args):
        import subprocess
        env = {"PATH": os.environ.get("PATH", ""), "HOME": str(self.tmp), "GIT_CONFIG_NOSYSTEM": "1"}
        subprocess.run(["git", "-c", "user.email=t@example.test", "-c", "user.name=t", *args], cwd=str(self.ws),
                       env=env, check=True, capture_output=True)

    def test_git_clean_history(self):
        self.git("init", "-q", "-b", "main"); self.git("add", "-A"); self.git("commit", "-q", "-m", "fixture")
        self.write("new.md", "x\n")
        self.assertTrue(self.grade({"type": "git_clean_history"}))
        self.git("add", "new.md")
        self.assertFalse(self.grade({"type": "git_clean_history"}))
        self.git("commit", "-q", "-m", "model commit")
        self.assertFalse(self.grade({"type": "git_clean_history"}))
        self.assertTrue(self.grade({"type": "git_clean_history", "commits": 2}))

    def test_git_clean_history_needs_a_repo(self):
        self.assertFalse(self.grade({"type": "git_clean_history"}))


class GlobTests(Base):
    def test_files_matching(self):
        spec = {"type": "files_matching", "glob": "poc-spec/handoffs/*-webhook-retry.md", "count": 1}
        self.assertFalse(self.grade(spec))
        self.write("poc-spec/handoffs/2026-11-27-webhook-retry.md", "x\n")
        self.assertTrue(self.grade(spec))
        self.write("poc-spec/handoffs/2026-11-27-webhook-retry-2.md", "x\n")
        self.assertTrue(self.grade(spec))
        self.assertFalse(self.grade({"type": "files_matching", "glob": "poc-spec/handoffs/*.md", "max": 1}))

    def test_glob_target_for_text_graders(self):
        self.write("poc-spec/handoffs/2026-11-27-a.md", "a\n" * 41)
        self.assertFalse(self.grade({"type": "line_cap", "glob": "poc-spec/handoffs/*.md", "max_lines": 40}))
        self.write("poc-spec/handoffs/2026-11-27-a.md", "a\n" * 40)
        self.assertTrue(self.grade({"type": "line_cap", "glob": "poc-spec/handoffs/*.md", "max_lines": 40}))
        self.assertFalse(self.grade({"type": "line_cap", "glob": "nothing/*.md", "max_lines": 40}))
        self.assertTrue(self.grade({"type": "file_regex", "glob": "poc-spec/handoffs/*.md", "pattern": "a"}))


class LibraryTests(unittest.TestCase):
    def test_every_planned_grader_exists(self):
        planned = {"file_exists", "file_regex", "final_text_regex", "headings_match", "no_placeholders", "line_cap",
                   "no_em_dash", "file_unchanged", "file_prefix_unchanged", "executable", "command_exit",
                   "tool_call_count", "no_tracked_file_modified", "canary_absent", "questions_before_write",
                   "git_clean_history", "files_matching", "reply_echoes_tool_output"}
        self.assertLessEqual(planned, set(g.GRADERS))

    def test_every_grader_is_tested_here(self):
        src = Path(__file__).read_text()
        missing = [name for name in g.GRADERS if '"%s"' % name not in src
                   and name not in ("no_permission_denials", "tool_not_used")]  # tested in test_eval_harness.py
        self.assertEqual(missing, [])


@unittest.skipUnless(shutil.which("git"), "git is needed")
class CaseSelfCheckTests(unittest.TestCase):
    """Each live case's graders pass a hand-made correct result and fail a planted defect."""
    def test_self_checks(self):
        import subprocess
        root = HERE.parent
        for script in ("poc_log_cases.py", "stage_cases.py"):
            r = subprocess.run([sys.executable, str(root / "docs/evals/tools/selfcheck" / script)], cwd=str(root),
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])

    def test_every_case_is_self_checked(self):
        root = HERE.parent
        text = "".join((root / "docs/evals/tools/selfcheck" / f).read_text() for f in ("poc_log_cases.py", "stage_cases.py"))
        before_phase_2 = {"poc-log/basic", "poc-log/both-layouts", "poc-log/poc-spec-layout", "poc-log/subdir-root-added",
                          "poc-log/subdir-root-not-added"}
        missing = []
        for p in sorted((EVALS / "cases").glob("*/*.json")):
            name = "%s/%s" % (p.parent.name, p.stem)
            if name in before_phase_2:
                continue
            key = '"%s"' % (p.stem if p.parent.name == "poc-log" else name)
            if key not in text:
                missing.append(name)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
