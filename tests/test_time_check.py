"""Tests for skills/poc-log/scripts/time_check.py (docs/prereqs/spec.md, Tests 2). No model, no network.
Run: python3 -m unittest discover -s tests
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "skills" / "poc-log" / "scripts" / "time_check.py"

HEADER = "Started: %s | Timebox (first pass): %s | Tier: 1 | Deal: none | Repo visibility: private"
LOG_HEAD = ("# Log\n\nAppend only. Newest entry last. Format per entry:\n\n## <YYYY-MM-DD HH:MM> <one-line title>\n"
            "- Tried: <>\n- Decision: <iterate | pivot | harden | stop | pause | none yet>\n")


def entry(ts, title="work"):
    return "\n## %s %s\n- Tried: x\n- Decision: none yet\n" % (ts, title)


class TimeCheckTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        (self.root / "poc-spec").mkdir()

    def tearDown(self):
        shutil.rmtree(str(self.root))

    def write(self, started="2026-11-25 18:30", timebox="2 hours", entries=("2026-11-25 18:30",), docs="poc-spec",
              log_extra=""):
        d = self.root / docs
        d.mkdir(exist_ok=True)
        (d / "POC.md").write_text("# POC: x\n\n%s\n\n## Question\nq\n" % (HEADER % (started, timebox)))
        (d / "LOG.md").write_text(LOG_HEAD + "".join(entry(e) for e in entries) + log_extra)

    def run_it(self, now="2026-11-27 18:00", docs="poc-spec"):
        args = [sys.executable, str(SCRIPT), "--root", str(self.root), "--docs", docs]
        if now:
            args += ["--now", now]
        r = subprocess.run(args, capture_output=True, text=True)
        return r.returncode, r.stdout.splitlines(), r.stderr

    def assertLines(self, line1, state, **kw):
        now = kw.pop("now", "2026-11-27 18:00")
        code, out, err = self.run_it(now=now, **kw)
        self.assertEqual(code, 0, (out, err))
        self.assertEqual(out, [line1, "timebox: %s" % state])

    def test_over_with_started_time(self):
        self.write(entries=("2026-11-25 18:30", "2026-11-26 09:00"))
        self.assertLines("Elapsed 47h 30m of 2 hours, 2 entries.", "over")

    def test_within(self):
        self.write(timebox="100000 hours")
        self.assertLines("Elapsed 47h 30m of 100000 hours, 1 entry.", "within")

    def test_exactly_at_the_timebox_is_within(self):
        self.write(started="2026-11-27 16:00")
        self.assertLines("Elapsed 2h 0m of 2 hours, 1 entry.", "within")

    def test_under_an_hour(self):
        self.write(started="2026-11-27 17:15", entries=("2026-11-27 17:15",))
        self.assertLines("Elapsed 45m of 2 hours, 1 entry.", "within")

    def test_started_without_time_uses_first_entry(self):
        self.write(started="2026-11-25", entries=("2026-11-25 18:30", "2026-11-26 09:00"))
        self.assertLines("Elapsed 47h 30m of 2 hours, 2 entries.", "over")

    def test_started_without_time_and_no_entries_uses_midnight(self):
        self.write(started="2026-11-27", entries=())
        self.assertLines("Elapsed 18h 0m of 2 hours, 0 entries.", "over")

    def test_timebox_forms(self):
        for box, state in (("90 min", "over"), ("1.5h", "over"), ("1h 30m", "over"), ("45 minutes", "over"),
                           ("3 hrs", "within"), ("1 day", "within"), ("2d", "within"), ("2 Hours", "within"),
                           ("120m", "within")):
            self.write(started="2026-11-27 16:00", timebox=box)
            self.assertLines("Elapsed 2h 0m of %s, 1 entry." % box, state)

    def test_unparsed_timebox_is_unknown_and_shown_as_written(self):
        self.write(timebox="until the demo")
        self.assertLines("Elapsed 47h 30m of until the demo, 1 entry.", "unknown")

    def test_template_line_is_not_counted_and_a_bare_heading_is(self):
        self.write(entries=("2026-11-25 18:30",), log_extra="\n## 2026-11-26 10:00\n- Tried: y\n")
        self.assertLines("Elapsed 47h 30m of 2 hours, 2 entries.", "over")

    def test_future_started(self):
        self.write(started="2026-11-28 09:00")
        self.assertLines("Elapsed 0m of 2 hours, 1 entry.", "unknown")

    def test_root_layout(self):
        self.write(docs=".")
        self.assertLines("Elapsed 47h 30m of 2 hours, 1 entry.", "over", docs=".")

    def test_missing_files_and_fields(self):
        code, out, _ = self.run_it()
        self.assertEqual((code, out), (3, ["time check: poc-spec/POC.md is missing"]))
        self.write()
        os.remove(str(self.root / "poc-spec" / "LOG.md"))
        code, out, _ = self.run_it()
        self.assertEqual((code, out), (3, ["time check: poc-spec/LOG.md is missing"]))
        self.write()
        (self.root / "poc-spec" / "POC.md").write_text("# POC: x\nno header\n")
        code, out, _ = self.run_it()
        self.assertEqual((code, out), (3, ["time check: no Started: date in poc-spec/POC.md"]))
        code, out, _ = self.run_it(docs=".")
        self.assertEqual((code, out), (3, ["time check: POC.md is missing"]))

    def test_invalid_dates_and_times_stop_cleanly(self):
        for started in ("2026-02-30 10:00", "2026-11-27 25:00"):
            self.write(started=started)
            code, out, err = self.run_it()
            self.assertEqual((code, out), (3, ["time check: the Started: date in poc-spec/POC.md is not a valid date and time"]), err)
            self.assertEqual(err, "")
        self.write(started="2026-11-25", entries=("2026-11-25 25:00",))
        code, out, err = self.run_it()
        self.assertEqual((code, err), (0, ""), out)  # an invalid log time is skipped, midnight is used
        self.assertEqual(out[0], "Elapsed 66h 0m of 2 hours, 1 entry.")

    def test_a_timebox_with_no_number_is_unknown(self):
        for box in ("nd", "and", "hours", "a few hours", "2 hours and some"):
            self.write(started="2026-11-27 16:00", timebox=box)
            self.assertLines("Elapsed 2h 0m of %s, 1 entry." % box, "unknown")
        self.write(started="2026-11-27 16:00", timebox="1h and 30m")
        self.assertLines("Elapsed 2h 0m of 1h and 30m, 1 entry.", "over")

    def test_only_the_header_line_is_read(self):
        d = self.root / "poc-spec"
        self.write()
        (d / "POC.md").write_text("# POC: Timebox demo\n\nStarted: 2026-11-27 16:00 | Timebox (first pass): 2 hours | Tier: 1\n\n"
                                  "## Question\nStarted: 2020-01-01 00:00 is not the header\n")
        self.assertLines("Elapsed 2h 0m of 2 hours, 1 entry.", "within")

    def test_an_unpadded_hour_is_read(self):
        self.write(started="2026-11-27 9:05")
        self.assertLines("Elapsed 8h 55m of 2 hours, 1 entry.", "over")

    def test_headings_inside_a_code_fence_are_not_entries(self):
        self.write(log_extra="\n```\n## 2026-11-26 10:00 an example in a fence\n```\n")
        self.assertLines("Elapsed 47h 30m of 2 hours, 1 entry.", "over")

    def test_messages_never_hold_an_absolute_path(self):
        code, out, err = self.run_it()
        self.assertNotIn(str(self.root), "\n".join(out) + err)

    def test_runs_against_the_real_clock(self):
        self.write(started="2000-01-01 00:00", timebox="1 hour")
        code, out, _ = self.run_it(now=None)
        self.assertEqual(code, 0)
        self.assertRegex(out[0], r"^Elapsed \d+h \d+m of 1 hour, 1 entry\.$")
        self.assertEqual(out[1], "timebox: over")

    def test_writes_nothing(self):
        self.write()
        before = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.run_it()
        after = {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_standard_library_only(self):
        import ast
        tree = ast.parse(SCRIPT.read_text())
        mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
        self.assertLessEqual(mods, {"argparse", "datetime", "re", "sys", "pathlib", "os"})


if __name__ == "__main__":
    unittest.main()
