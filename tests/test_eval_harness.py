"""Tests for evals/harness. No model, no network, standard library only.
Run: python3 -m unittest discover -s tests
"""
import contextlib
import copy
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EVALS = ROOT / "evals"
FAKE = HERE / "fake_claude.py"
sys.path.insert(0, str(EVALS))

from harness import cases as cases_mod  # noqa: E402
from harness import events as ev  # noqa: E402
from harness import graders as graders_mod  # noqa: E402
from harness import report as report_mod  # noqa: E402
from harness import runner  # noqa: E402
import run_eval  # noqa: E402

HAVE_GIT = shutil.which("git") is not None

GOOD = {
    "id": "basic", "stage": "poc-log", "set": "tune", "prompt": "hello", "fixture": "poc-log-basic",
    "allowed_tools": ["Read"], "graders": [{"type": "file_exists", "path": "LOG.md"}],
}


def case_from(prompt="MODE:ok", **over):
    raw = dict(GOOD, prompt=prompt, **over)
    case, errs = cases_mod.validate(raw, str(EVALS / "cases" / "poc-log" / "basic.json"), EVALS / "fixtures")
    assert case, errs
    return case


class CaseTests(unittest.TestCase):
    def check(self, mutate, expect):
        raw = copy.deepcopy(GOOD)
        mutate(raw)
        case, errs = cases_mod.validate(raw, "cases/poc-log/basic.json", EVALS / "fixtures")
        self.assertIsNone(case)
        joined = "\n".join(errs)
        self.assertIn("cases/poc-log/basic.json", joined)  # names the file
        self.assertIn(expect, joined)  # names the field

    def test_good_case_loads(self):
        case, errs = cases_mod.validate(copy.deepcopy(GOOD), "cases/poc-log/basic.json", EVALS / "fixtures")
        self.assertEqual(errs, [])
        self.assertEqual(case.name, "poc-log/basic")

    def test_bad_fields_name_the_field(self):
        self.check(lambda r: r.pop("prompt"), "field 'prompt'")
        self.check(lambda r: r.update(n_runs=0), "field 'n_runs'")
        self.check(lambda r: r.update(n_runs=True), "field 'n_runs'")
        self.check(lambda r: r.update(set="other"), "field 'set'")
        self.check(lambda r: r.update(max_cost_usd=0.05), "field 'max_cost_usd'")
        self.check(lambda r: r.update(fixture="nope"), "field 'fixture'")
        self.check(lambda r: r.update(stage="wrong"), "field 'stage'")
        self.check(lambda r: r.update(bogus=1), "field 'bogus'")
        self.check(lambda r: r.update(graders=[{"type": "nope"}]), "graders[0].type")
        self.check(lambda r: r.update(graders=[{"type": "file_regex", "path": "x"}]), "graders[0].pattern")

    def test_cwd_and_add_root_dir_are_validated(self):
        self.check(lambda r: r.update(cwd="/etc"), "field 'cwd'")
        self.check(lambda r: r.update(cwd="../x"), "field 'cwd'")
        self.check(lambda r: r.update(cwd="sub/../.."), "field 'cwd'")
        self.check(lambda r: r.update(cwd=""), "field 'cwd'")
        self.check(lambda r: r.update(cwd="no/such/dir"), "field 'cwd'")  # must exist in the fixture
        self.check(lambda r: r.update(add_root_dir="yes"), "field 'add_root_dir'")
        good = dict(copy.deepcopy(GOOD), fixture="poc-log-specs", cwd="sub/deep", add_root_dir=True)
        case, errs = cases_mod.validate(good, "cases/poc-log/basic.json", EVALS / "fixtures")
        self.assertEqual(errs, [])
        self.assertEqual((case.cwd, case.add_root_dir), ("sub/deep", True))
        default, _ = cases_mod.validate(copy.deepcopy(GOOD), "cases/poc-log/basic.json", EVALS / "fixtures")
        self.assertEqual((default.cwd, default.add_root_dir), (".", False))

    def test_loader_rejects_before_any_run_and_real_cases_load(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "poc-log").mkdir()
            (Path(d) / "poc-log" / "basic.json").write_text('{"id": "basic"}')
            with self.assertRaises(cases_mod.CaseError) as cm:
                cases_mod.load_cases(d, EVALS / "fixtures")
            self.assertIn("basic.json", str(cm.exception))
        self.assertTrue(cases_mod.load_cases(EVALS / "cases", EVALS / "fixtures", set_filter="all"))


class EventTests(unittest.TestCase):
    def test_last_result_index_wins_and_garbage_is_counted(self):
        lines = [
            "not json",
            json.dumps({"type": "system", "subtype": "init", "claude_code_version": "1", "apiKeySource": "none"}),
            json.dumps({"type": "result", "result_index": 0, "result": "stale", "total_cost_usd": 0.5}),
            json.dumps({"type": "result", "result_index": 1, "result": "final", "total_cost_usd": 0.5}),
        ]
        events, bad = ev.parse_lines(lines)
        summary, init = ev.summarise_events(events)
        self.assertEqual(bad, 1)
        self.assertEqual(summary["final_text"], "final")
        self.assertEqual(summary["n_result_events"], 2)

    def test_tool_calls_and_denials(self):
        events = [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Agent", "input": {}}]}},
            {"type": "assistant", "parent_tool_use_id": "t", "message": {"content": [{"type": "tool_use", "name": "Read", "input": {}}]}},
            {"type": "result", "permission_denials": [{"tool_name": "Bash", "tool_input": {"command": "x"}}]},
        ]
        s, _ = ev.summarise_events(events)
        self.assertEqual([(c["name"], c["child"]) for c in s["tool_calls"]], [("Agent", False), ("Read", True)])
        self.assertEqual(len(s["permission_denials"]), 1)

    def test_isolation_check(self):
        ok = {"mcp_servers": [], "tools": ["Bash"], "plugins": [{"name": "spike-loop"}], "agents": ["claude", "spike-loop:x"], "apiKeySource": "none"}
        self.assertEqual(ev.check_isolation(ok), [])
        self.assertTrue(ev.check_isolation(None))
        self.assertTrue(ev.check_isolation(dict(ok, mcp_servers=[{"name": "c"}])))
        self.assertTrue(ev.check_isolation(dict(ok, tools=["mcp__x__y"])))
        self.assertTrue(ev.check_isolation(dict(ok, plugins=[{"name": "my-own-plugin"}])))
        self.assertTrue(ev.check_isolation(dict(ok, agents=["claude", "researcher-internal"])))
        self.assertTrue(ev.check_isolation(dict(ok, apiKeySource="ANTHROPIC_API_KEY")))
        self.assertEqual(ev.check_isolation(dict(ok, skills=["spike-loop:poc-log", "debug"])), [])
        self.assertTrue(ev.check_isolation(dict(ok, skills=["spike-loop:poc-log", "my-own-user-skill"])))

    def test_isolation_confirms_config_dir_and_cwd_from_init(self):
        with tempfile.TemporaryDirectory() as d:
            cfg, ws = os.path.join(d, "cc"), os.path.join(d, "ws")
            os.makedirs(cfg), os.makedirs(ws)
            ok = {"mcp_servers": [], "tools": [], "plugins": [], "agents": [], "apiKeySource": "none",
                  "memory_paths": {"auto": os.path.join(cfg, "projects", "x", "memory") + "/"}, "cwd": ws}
            self.assertEqual(ev.check_isolation(ok, config_dir=cfg, cwd=ws), [])
            self.assertTrue(ev.check_isolation(dict(ok, memory_paths={"auto": "/Users/someone/.claude/projects/x/"}), config_dir=cfg, cwd=ws))
            self.assertTrue(ev.check_isolation(dict(ok, memory_paths=None), config_dir=cfg, cwd=ws))
            self.assertTrue(ev.check_isolation(dict(ok, cwd="/elsewhere"), config_dir=cfg, cwd=ws))

    def test_redaction(self):
        text = "key sk-ant-abc123_DEF-xyz and my-secret-value here"
        out = ev.redact(text, ("my-secret-value",))
        self.assertNotIn("sk-ant", out)
        self.assertNotIn("my-secret-value", out)


class GraderTests(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        (Path(self.d) / "LOG.md").write_text("## 2026-11-25 10:00 a\n## 2026-11-25 11:00 b\n")
        self.ctx = {"workspace": self.d, "summary": {"permission_denials": [], "tool_calls": [{"name": "Bash"}]}}

    def tearDown(self):
        shutil.rmtree(self.d)

    def run_one(self, spec):
        return graders_mod.run_graders([spec], self.ctx)[0]["passed"]

    def test_file_graders(self):
        self.assertTrue(self.run_one({"type": "file_exists", "path": "LOG.md"}))
        self.assertFalse(self.run_one({"type": "file_exists", "path": "nope"}))
        self.assertTrue(self.run_one({"type": "file_exists", "path": "nope", "exists": False}))
        rx = {"type": "file_regex", "path": "LOG.md", "pattern": r"^## \d{4}-\d{2}-\d{2} \d{2}:\d{2} ", "flags": "m"}
        self.assertTrue(self.run_one(dict(rx, count=2)))
        self.assertFalse(self.run_one(dict(rx, count=3)))
        self.assertFalse(self.run_one({"type": "file_regex", "path": "missing", "pattern": "x"}))

    def test_summary_graders_and_error_safety(self):
        self.assertTrue(self.run_one({"type": "no_permission_denials"}))
        self.assertFalse(self.run_one({"type": "tool_not_used", "tool": "Bash"}))
        r = graders_mod.run_graders([{"type": "file_regex", "path": "LOG.md", "pattern": "("}], self.ctx)[0]
        self.assertFalse(r["passed"])
        self.assertIn("grader error", r["explanation"])


@unittest.skipUnless(HAVE_GIT, "git is needed")
class RunnerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.plugin = runner.build_plugin_copy(ROOT, cls.tmp / "plugin")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(str(cls.tmp), ignore_errors=True)

    def run_case(self, prompt, timeout=None, **env):
        case = case_from(prompt)
        if timeout:
            case.timeout_s = timeout
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(out), True)
        with mock.patch.dict(os.environ, env):
            return runner.run_once(case, 1, ROOT, self.plugin, "dummy-token", out, EVALS / "fixtures",
                                   claude_cmd=(sys.executable, str(FAKE)), keep=True), out

    def settings_in(self, seen):
        argv = seen["argv"]
        return json.loads(argv[argv.index("--settings") + 1])

    def test_default_case_starts_in_the_workspace_root_without_extra_directories(self):
        r, out = self.run_case("MODE:ok")
        seen = json.loads((Path(r["workspace_kept"]) / "ws" / "seen.json").read_text())
        settings = self.settings_in(seen)
        self.assertTrue(settings["permissions"]["blockReadsOutsideWorkingDirectories"])
        # Only the plugin copy is added, so its bundled scripts can run; it holds no .env (see the copy test).
        self.assertEqual(settings["permissions"]["additionalDirectories"], [str(Path(r["workspace_kept"]) / "plugin")])
        shutil.rmtree(r["workspace_kept"], ignore_errors=True)

    def test_case_can_start_in_a_subdirectory_with_the_root_added(self):
        case = case_from("MODE:ok", fixture="poc-log-specs", cwd="sub/deep", add_root_dir=True,
                         graders=[{"type": "file_exists", "path": "poc-spec/LOG.md"}])
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(out), True)
        r = runner.run_once(case, 1, ROOT, self.plugin, "dummy-token", out, EVALS / "fixtures",
                            claude_cmd=(sys.executable, str(FAKE)), keep=True)
        self.addCleanup(shutil.rmtree, r["workspace_kept"], True)
        self.assertEqual(r["status"], "ok", r.get("reason"))  # the isolation check accepts a subdirectory start
        ws = Path(r["workspace_kept"]) / "ws"
        seen_path = ws / "sub" / "deep" / "seen.json"
        self.assertTrue(seen_path.is_file(), "the process did not start in sub/deep")
        self.assertFalse((ws / "seen.json").exists())
        settings = self.settings_in(json.loads(seen_path.read_text()))
        self.assertEqual(settings["permissions"]["additionalDirectories"], [str(Path(r["workspace_kept"]) / "plugin"), str(ws)])
        self.assertTrue(settings["permissions"]["blockReadsOutsideWorkingDirectories"])
        self.assertTrue(r["passed"])  # graders still look at the whole workspace

    def test_subdirectory_start_without_the_root_added_has_no_extra_directories(self):
        case = case_from("MODE:ok", fixture="poc-log-specs", cwd="sub/deep",
                         graders=[{"type": "file_exists", "path": "poc-spec/LOG.md"}])
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(out), True)
        r = runner.run_once(case, 1, ROOT, self.plugin, "dummy-token", out, EVALS / "fixtures",
                            claude_cmd=(sys.executable, str(FAKE)), keep=True)
        self.addCleanup(shutil.rmtree, r["workspace_kept"], True)
        settings = self.settings_in(json.loads((Path(r["workspace_kept"]) / "ws" / "sub" / "deep" / "seen.json").read_text()))
        self.assertEqual(settings["permissions"]["additionalDirectories"], [str(Path(r["workspace_kept"]) / "plugin")])

    def test_each_run_gets_its_own_plugin_copy_and_an_edit_makes_it_invalid(self):
        before = (self.plugin / "scripts" / "check-prereqs").read_bytes()
        r, out = self.run_case("MODE:editplugin")
        self.addCleanup(shutil.rmtree, r["workspace_kept"], True)
        self.assertEqual(r["status"], "invalid", r.get("reason"))
        self.assertIn("plugin", r["reason"])
        self.assertEqual((self.plugin / "scripts" / "check-prereqs").read_bytes(), before)
        r2, _ = self.run_case("MODE:ok")
        self.addCleanup(shutil.rmtree, r2["workspace_kept"], True)
        self.assertEqual(r2["status"], "ok", r2.get("reason"))

    def test_plugin_copy_holds_no_secrets_file(self):
        self.assertEqual([p for p in self.plugin.rglob(".env*")], [])

    def test_plugin_copy_has_the_bundled_scripts(self):
        self.assertTrue((self.plugin / "scripts" / "check-prereqs").is_file())
        self.assertTrue((self.plugin / "skills" / "poc-log" / "scripts" / "time_check.py").is_file())

    def run_seen(self, **over):
        case = case_from("MODE:ok", **over)
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(out), True)
        r = runner.run_once(case, 1, ROOT, self.plugin, "dummy-token", out, EVALS / "fixtures",
                            claude_cmd=(sys.executable, str(FAKE)), keep=True)
        self.addCleanup(shutil.rmtree, r["workspace_kept"], True)
        return r, json.loads((Path(r["workspace_kept"]) / "ws" / "seen.json").read_text())

    @unittest.skipUnless(shutil.which("python3"), "python3 needed")
    def test_hide_tools_takes_the_tool_off_path(self):
        r, seen = self.run_seen()
        self.assertTrue(seen["python3_found"])
        r, seen = self.run_seen(hide_tools=["python3"])
        self.assertEqual(r["status"], "ok", r.get("reason"))
        self.assertFalse(seen["python3_found"])
        self.assertFalse(seen["python_found"])
        self.assertTrue(seen["git_found"])
        self.assertEqual(r["hidden_tools"], ["python3"])

    def test_hide_tools_is_validated(self):
        for bad in ("python3", [""], ["a/b"], [3]):
            raw = dict(GOOD, hide_tools=bad)
            case, errs = cases_mod.validate(raw, str(EVALS / "cases" / "poc-log" / "basic.json"), EVALS / "fixtures")
            self.assertIsNone(case, bad)
            self.assertTrue(any("hide_tools" in e for e in errs), errs)

    def test_plugin_copy_has_only_plugin_dirs(self):
        top = {p.name for p in self.plugin.iterdir()}
        self.assertIn("skills", top)
        for banned in ("evals", "docs", "tests", ".env", ".git", "CLAUDE.md"):
            self.assertNotIn(banned, top)

    def test_ok_run_isolation_diff_and_grading(self):
        r, out = self.run_case("MODE:ok", SPIKE_TEST_SENTINEL="leak", SPIKE_EVALS_OAUTH_TOKEN="should-not-pass")
        self.assertEqual(r["status"], "ok", r.get("reason"))
        self.assertEqual(r["final_text"], "FINAL ANSWER")
        self.assertEqual(r["claude_version"], "9.9.9-fake")
        self.assertEqual(r["models"], ["fake-model"])
        self.assertIn("LOG.md", r["workspace_changes"]["modified"])
        self.assertIn("seen.json", r["workspace_changes"]["added"])
        self.assertEqual([(c["name"], c["child"]) for c in r["tool_calls"]], [("Bash", False), ("Read", True)])
        seen = json.loads((Path(r["workspace_kept"]) / "ws" / "seen.json").read_text())
        self.assertNotIn("SPIKE_TEST_SENTINEL", seen["env_names"])
        self.assertNotIn("SPIKE_EVALS_OAUTH_TOKEN", seen["env_names"])
        self.assertTrue(seen["has_oauth_token"])
        self.assertTrue(seen["home"].startswith(r["workspace_kept"]))
        self.assertNotIn("evals", seen["plugin_top_level"])
        for flag in ("--allowedTools", "--max-budget-usd", "--output-format", "--plugin-dir"):
            self.assertIn(flag, seen["argv"])
        shutil.rmtree(r["workspace_kept"], ignore_errors=True)
        self.assertTrue((out / "poc-log" / "basic" / "run1.json").is_file())
        self.assertNotIn("dummy-token", (out / "poc-log" / "basic" / "run1.events.jsonl").read_text())

    def test_failure_classification(self):
        for prompt, status, reason in (
            ("MODE:budget", "harness_failure", "budget_exhausted"),
            ("MODE:mcp", "invalid", "MCP servers"),
            ("MODE:badskill", "invalid", "unexpected skills"),
            ("MODE:outside", "invalid", "memory path outside"),
            ("MODE:crash", "harness_failure", "no init or result event"),  # not an isolation problem
        ):
            r, _ = self.run_case(prompt)
            self.assertEqual((r["status"], r["passed"]), (status, False), prompt)
            self.assertIn(reason, r["reason"])
            self.assertEqual(r["grader_results"], [])
            shutil.rmtree(r["workspace_kept"], ignore_errors=True)

    def test_timeout_and_stale_result_and_garbage(self):
        r, _ = self.run_case("MODE:sleep", timeout=1)
        self.assertEqual((r["status"], r["passed"]), ("harness_failure", False))
        self.assertIn("timeout", r["reason"])
        shutil.rmtree(r["workspace_kept"], ignore_errors=True)
        r, _ = self.run_case("MODE:twores")
        self.assertEqual(r["final_text"], "FINAL ANSWER")
        self.assertEqual(r["n_result_events"], 2)
        shutil.rmtree(r["workspace_kept"], ignore_errors=True)
        r, _ = self.run_case("MODE:garbage")
        self.assertEqual(r["non_json_lines"], 1)
        shutil.rmtree(r["workspace_kept"], ignore_errors=True)

    def test_token_never_reaches_any_written_file(self):
        token = "dummy-token-ABCDEFGH"
        case = case_from("MODE:leak")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(out), True)
        r = runner.run_once(case, 1, ROOT, self.plugin, token, out, EVALS / "fixtures",
                            claude_cmd=(sys.executable, str(FAKE)), keep=False)
        for p in out.rglob("*"):
            if p.is_file():
                self.assertNotIn(token, p.read_text(), str(p))
        self.assertNotIn(token, json.dumps(r))
        self.assertIn("[REDACTED]", (out / "poc-log" / "basic" / "run1.json").read_text())  # it was there, then redacted

    def test_stderr_tail_is_redacted_before_it_is_cut(self):
        token = "dummy-token-ABCDEFGH"
        case = case_from("MODE:stderrleak")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(out), True)
        r = runner.run_once(case, 1, ROOT, self.plugin, token, out, EVALS / "fixtures",
                            claude_cmd=(sys.executable, str(FAKE)), keep=False)
        self.assertNotIn(token[-5:], r["stderr_tail"])
        self.assertLessEqual(len(r["stderr_tail"]), 500)

    def test_missing_binary_is_a_harness_failure_not_an_exception(self):
        case = case_from("MODE:ok")
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(out), True)
        r = runner.run_once(case, 1, ROOT, self.plugin, "dummy-token", out, EVALS / "fixtures",
                            claude_cmd=("/nonexistent/claude",), keep=False)
        self.assertEqual((r["status"], r["passed"]), ("harness_failure", False))
        self.assertIn("FileNotFoundError", r["reason"])
        self.assertTrue((out / "poc-log" / "basic" / "run1.json").is_file())

    def test_settings_flag_blocks_reads_outside_the_workspace(self):
        r, _ = self.run_case("MODE:ok")
        seen = json.loads((Path(r["workspace_kept"]) / "ws" / "seen.json").read_text())
        argv = seen["argv"]
        settings = json.loads(argv[argv.index("--settings") + 1])
        self.assertTrue(settings["permissions"]["blockReadsOutsideWorkingDirectories"])
        shutil.rmtree(r["workspace_kept"], ignore_errors=True)

    def test_denials_are_recorded_but_do_not_fail_the_run(self):
        r, _ = self.run_case("MODE:denial")
        self.assertEqual(r["status"], "ok")
        self.assertEqual(len(r["permission_denials"]), 1)
        summary = report_mod.summarise([r])
        self.assertEqual(summary["cases"]["poc-log/basic"]["denial_runs"], 1)
        shutil.rmtree(r["workspace_kept"], ignore_errors=True)

    def test_instruction_files_above_the_workspace_are_detected(self):
        with tempfile.TemporaryDirectory() as d:
            ws = Path(d) / "a" / "b" / "ws"
            ws.mkdir(parents=True)
            self.assertEqual(runner.check_parent_instructions(ws), [])
            (Path(d) / "a" / "CLAUDE.md").write_text("x")
            self.assertEqual(len(runner.check_parent_instructions(ws)), 1)

    def test_failing_grader_is_a_fail_not_a_harness_failure(self):
        case = case_from("MODE:nowrite", graders=[
            {"type": "file_regex", "path": "LOG.md", "pattern": r"^## \d{4}-\d{2}-\d{2} \d{2}:\d{2} ", "flags": "m", "count": 2}])
        out = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(out), True)
        r = runner.run_once(case, 1, ROOT, self.plugin, "dummy-token", out, EVALS / "fixtures",
                            claude_cmd=(sys.executable, str(FAKE)), keep=True)
        self.addCleanup(shutil.rmtree, r["workspace_kept"], True)
        self.assertEqual(r["status"], "ok")  # the run was valid
        self.assertFalse(r["passed"])  # the plugin output was wrong: no entry was written
        self.assertFalse(r["grader_results"][0]["passed"])


@unittest.skipUnless(HAVE_GIT, "git is needed")
class CliTests(unittest.TestCase):
    def test_dry_run_calls_nothing(self):
        boom = mock.Mock(side_effect=AssertionError("dry-run must not touch the network or start processes"))
        buf = io.StringIO()
        with mock.patch.object(socket, "socket", boom), mock.patch.object(subprocess, "Popen", boom), \
                mock.patch.object(subprocess, "run", boom), contextlib.redirect_stdout(buf):
            code = run_eval.main(["dry-run"])
        self.assertEqual(code, 0)
        self.assertIn("poc-log/basic", buf.getvalue())
        self.assertIn("no model was called", buf.getvalue())

    def test_suite_cap_stops_part_way_and_lists_skipped(self):
        out = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, out, True)
        buf = io.StringIO()
        argv = ["run", "--case", "poc-log/basic", "--runs", "3", "--suite-cap", "0.5", "--out", out,
                "--claude-cmd", "%s %s" % (sys.executable, FAKE)]
        with mock.patch.dict(os.environ, {"SPIKE_EVALS_OAUTH_TOKEN": "dummy-token"}), contextlib.redirect_stdout(buf):
            code = run_eval.main(argv)
        self.assertEqual(code, 2)  # stopped by the cap
        summary = json.loads((Path(out) / "summary.json").read_text())
        self.assertEqual(summary["cases"]["poc-log/basic"]["runs"], 2)  # 0.1 each, 1.5 x 0.25 headroom
        self.assertIn("Not run because a budget cap was reached", buf.getvalue())

    def test_exact_interpreter_grant_is_narrow(self):
        self.assertEqual(runner.broad_grants(case_from("x", allowed_tools=["Bash(bash verify.sh)"])), [])
        self.assertTrue(runner.broad_grants(case_from("x", allowed_tools=["Bash(bash *)"])))
        self.assertTrue(runner.broad_grants(case_from("x", allowed_tools=["Bash(bash verify.sh *)"])))

    def test_long_tool_inputs_keep_the_script_name(self):
        cmd = 'cd "/private/var/folders/xx/' + "y" * 80 + '/ws" && python3 "/var/folders/xx/' + "z" * 60 + '/plugin/skills/poc-log/scripts/time_check.py" --root x'
        ev_line = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": cmd}}]}}
        summary, _ = ev.summarise_events([ev_line])
        self.assertIn("time_check.py", summary["tool_calls"][0]["input"])

    def test_unsandboxed_grants_need_consent(self):
        for tool, broad in (("Bash", True), ("Bash(*)", True), ("Bash(python3 *)", True), ("Bash(sh -c *)", True),
                            ("Bash(curl *)", True), ("WebFetch", True), ("Bash(date *)", False), ("Bash(git status)", False),
                            ("Read", False)):
            got = bool(runner.broad_grants(case_from(allowed_tools=[tool])))
            self.assertEqual(got, broad, tool)

    def test_run_refuses_broad_grants_without_consent_and_starts_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "poc-log").mkdir()
            raw = dict(GOOD, allowed_tools=["Bash"])
            (Path(d) / "poc-log" / "basic.json").write_text(json.dumps(raw))
            boom = mock.Mock(side_effect=AssertionError("must not start a run"))
            err = io.StringIO()
            with mock.patch.object(run_eval, "CASES_DIR", Path(d)), mock.patch.object(runner, "run_once", boom), \
                    contextlib.redirect_stderr(err):
                self.assertEqual(run_eval.main(["run"]), 2)
            self.assertIn("--unsandboxed-ok", err.getvalue())

    def test_runs_flag_is_validated(self):
        for bad in ("0", "-1", "21", "x"):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                run_eval.main(["dry-run", "--runs", bad])

    def test_unknown_cost_counts_as_the_cap_and_the_suite_stops(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "poc-log").mkdir()
            for cid in ("a", "b"):
                raw = dict(GOOD, id=cid, prompt="MODE:crash", n_runs=5)
                (Path(d) / "poc-log" / (cid + ".json")).write_text(json.dumps(raw))
            out = tempfile.mkdtemp()
            self.addCleanup(shutil.rmtree, out, True)
            argv = ["run", "--suite-cap", "0.7", "--out", out, "--claude-cmd", "%s %s" % (sys.executable, FAKE)]
            buf = io.StringIO()
            with mock.patch.dict(os.environ, {"SPIKE_EVALS_OAUTH_TOKEN": "dummy-token"}), \
                    mock.patch.object(run_eval, "CASES_DIR", Path(d)), contextlib.redirect_stdout(buf):
                code = run_eval.main(argv)
            summary = json.loads((Path(out) / "summary.json").read_text())
            self.assertEqual(code, 2)
            self.assertEqual(summary["cases"]["poc-log/a"]["runs"], 2)  # no cost reported: 0.25 each, 0.375 headroom
            self.assertNotIn("poc-log/b", summary["cases"])  # the stop applies to later cases too
            self.assertIn("poc-log/b (not started)", buf.getvalue())


def result(case, passed, status="ok", stage="poc-log", denials=False):
    return {"case": case, "stage": stage, "set": "tune", "status": status, "passed": passed,
            "cost_usd": 0.01, "plugin_version": "0.1.1", "claude_version": "2.1.325", "models": ["m"],
            "permission_denials": [{"x": 1}] if denials else [], "final_text": "SECRET MODEL OUTPUT",
            "prompt": "SECRET PROMPT"}


class ReportTests(unittest.TestCase):
    def thresholds(self):
        return report_mod.load_thresholds(EVALS / "thresholds.json")

    def summary(self, spec):
        results = []
        for name, (p, f, inv, hf) in spec.items():
            results += [result(name, True)] * p + [result(name, False)] * f
            results += [result(name, False, "invalid")] * inv + [result(name, False, "harness_failure")] * hf
        return report_mod.summarise(results)

    def test_counts_exclude_invalid_and_harness_failures(self):
        s = self.summary({"poc-log/a": (2, 1, 1, 1)})
        c = s["cases"]["poc-log/a"]
        self.assertEqual((c["runs"], c["valid"], c["passes"], c["invalid"], c["harness_failures"]), (5, 3, 2, 1, 1))
        md = report_mod.to_markdown(s)
        self.assertIn("2/3", md)

    def test_baseline_is_counts_only(self):
        text = json.dumps(report_mod.baseline_counts(self.summary({"poc-log/a": (3, 0, 0, 0)})))
        self.assertNotIn("SECRET", text)
        self.assertNotIn("final_text", text)
        self.assertNotIn("prompt", text)

    def test_compare_rules(self):
        base = self.summary({"poc-log/same": (3, 0, 0, 0), "poc-log/small": (3, 0, 0, 0), "poc-log/big": (3, 0, 0, 0),
                             "poc-log/up": (1, 2, 0, 0)})
        new = self.summary({"poc-log/same": (3, 0, 0, 0), "poc-log/small": (2, 1, 0, 0), "poc-log/big": (1, 2, 0, 0),
                            "poc-log/up": (3, 0, 0, 0)})
        rep = report_mod.compare(base, new, self.thresholds())
        st = {k: v["status"] for k, v in rep["cases"].items()}
        self.assertEqual(st, {"poc-log/same": "same", "poc-log/small": "rerun", "poc-log/big": "regression", "poc-log/up": "improved"})
        self.assertEqual(rep["regressions"], ["poc-log/big"])
        self.assertEqual(rep["reruns_needed"], ["poc-log/small"])

    def test_rerun_confirms_or_clears(self):
        base = self.summary({"poc-log/small": (3, 0, 0, 0)})
        new = self.summary({"poc-log/small": (2, 1, 0, 0)})
        bad = self.summary({"poc-log/small": (3, 2, 0, 0)})
        good = self.summary({"poc-log/small": (5, 0, 0, 0)})
        self.assertEqual(report_mod.compare(base, new, self.thresholds(), bad)["cases"]["poc-log/small"]["status"], "regression")
        self.assertEqual(report_mod.compare(base, new, self.thresholds(), good)["cases"]["poc-log/small"]["status"], "cleared_on_rerun")

    def test_stage_rule_needs_enough_runs(self):
        base = self.summary({"poc-log/a": (12, 0, 0, 0)})
        few = self.summary({"poc-log/a": (3, 3, 0, 0)})
        many = self.summary({"poc-log/a": (6, 6, 0, 0)})
        self.assertEqual(report_mod.compare(base, few, self.thresholds())["stages"]["poc-log"]["status"], "too_few_runs")
        rep = report_mod.compare(base, many, self.thresholds())
        self.assertEqual(rep["stages"]["poc-log"]["status"], "regression")
        self.assertIn("stage:poc-log", rep["regressions"])


    def test_incomplete_cases_do_not_pass_the_gate(self):
        base = self.summary({"poc-log/a": (3, 0, 0, 0), "poc-log/b": (3, 0, 0, 0), "poc-log/c": (3, 0, 0, 0)})
        new = self.summary({"poc-log/a": (0, 0, 0, 3), "poc-log/b": (0, 1, 0, 0)})  # a: every run a harness failure
        rep = report_mod.compare(base, new, self.thresholds())
        self.assertEqual(rep["cases"]["poc-log/a"]["status"], "unscored")
        self.assertEqual(rep["cases"]["poc-log/c"]["status"], "missing")
        self.assertEqual(rep["cases"]["poc-log/b"]["status"], "rerun")  # one failing run of one: needs a rerun, not a pass
        self.assertEqual(sorted(rep["incomplete"]), ["poc-log/a", "poc-log/b", "poc-log/c"])
        rep2 = report_mod.compare(base, new, self.thresholds(), allow_missing=True)
        self.assertEqual(sorted(rep2["incomplete"]), ["poc-log/a", "poc-log/b"])

    def test_compare_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            def write(name, spec):
                path = Path(d) / name
                path.write_text(json.dumps(report_mod.baseline_counts(self.summary(spec))))
                return str(path)
            base = write("base.json", {"poc-log/a": (3, 0, 0, 0)})
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(run_eval.main(["compare", base, write("same.json", {"poc-log/a": (3, 0, 0, 0)})]), 0)
                self.assertEqual(run_eval.main(["compare", base, write("bad.json", {"poc-log/a": (0, 3, 0, 0)})]), 1)
                self.assertEqual(run_eval.main(["compare", base, write("none.json", {"poc-log/a": (0, 0, 0, 3)})]), 3)
                self.assertEqual(run_eval.main(["compare", base, write("gone.json", {"poc-log/z": (3, 0, 0, 0)})]), 3)
                self.assertEqual(run_eval.main(["compare", base, write("gone.json", {"poc-log/z": (3, 0, 0, 0)}), "--allow-missing"]), 0)

    def test_stage_pool_uses_only_cases_on_both_sides(self):
        base = self.summary({"poc-log/a": (12, 0, 0, 0), "poc-log/b": (0, 12, 0, 0)})
        new = self.summary({"poc-log/a": (12, 0, 0, 0)})  # a subset run: b was not run
        rep = report_mod.compare(base, new, self.thresholds(), allow_missing=True)
        self.assertEqual(rep["stages"]["poc-log"]["status"], "ok")  # pooling over everything would have shown a rise


class CommittedTreeSafetyTests(unittest.TestCase):
    PATTERNS = [r"sk-ant-[A-Za-z0-9_-]{10,}", r"gh[pousr]_[A-Za-z0-9]{20,}", r"AKIA[0-9A-Z]{16}",
                r"-----BEGIN [A-Z ]*PRIVATE KEY-----", r"xox[baprs]-[A-Za-z0-9-]{10,}"]

    def test_no_secret_shaped_literals_in_evals_or_tests(self):
        hits = []
        for base in (EVALS, HERE):
            for p in base.rglob("*"):
                if not p.is_file() or "__pycache__" in p.parts or "results" in p.parts or p.suffix == ".pyc":
                    continue
                text = p.read_text(encoding="utf-8", errors="ignore")
                for pat in self.PATTERNS:
                    if p.name != "test_eval_harness.py" and re.search(pat, text):
                        hits.append("%s matches %s" % (p, pat))
        self.assertEqual(hits, [])

    @unittest.skipUnless(shutil.which("gitleaks"), "gitleaks is not installed")
    def test_gitleaks_clean_on_evals(self):
        r = subprocess.run(["gitleaks", "dir", str(EVALS), "--no-banner", "--redact"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
