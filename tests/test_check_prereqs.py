"""Tests for scripts/check-prereqs (docs/prereqs/spec.md, Tests 1). No model, no network.
Run: python3 -m unittest discover -s tests
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
CHECKER = ROOT / "scripts" / "check-prereqs"
sys.path.insert(0, str(ROOT / "evals"))
from harness import hidepath  # noqa: E402

TOOLS = ("git", "python3", "rsync", "gitleaks", "typos")
INSTALL_WORDS = ("macOS", "Debian or Ubuntu", "Windows")


def commands():
    skills = [d.name for d in (ROOT / "skills").iterdir() if (d / "SKILL.md").is_file() and d.name != "research-protocol"]
    agents = [p.stem for p in (ROOT / "agents").glob("*.md")]
    return sorted(skills + agents)


class CheckerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.before = set(os.listdir(str(self.tmp)))

    def tearDown(self):
        shutil.rmtree(str(self.tmp))

    def run_checker(self, *args, hide=(), extra_bin=None):
        path = hidepath.hidden_path(str(self.tmp / ("bin%d" % len(os.listdir(str(self.tmp))))), list(hide))
        if extra_bin:
            path = extra_bin + os.pathsep + path
        env = {"PATH": path, "HOME": str(self.tmp), "SECRET_PROBE_VALUE": "do-not-print-me"}
        r = subprocess.run(["sh", str(CHECKER)] + list(args), cwd=str(self.tmp), env=env,
                           capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout, r.stderr

    def fake(self, name, script):
        d = self.tmp / "fakebin"
        d.mkdir(exist_ok=True)
        p = d / name
        p.write_text("#!/bin/sh\n" + script)
        p.chmod(0o755)
        return str(d)

    @unittest.skipUnless(shutil.which("git") and shutil.which("python3"), "git and python3 needed")
    def test_all_present(self):
        code, out, _ = self.run_checker("poc-log", "git", "python3:optional")
        self.assertEqual(code, 0, out)
        lines = out.strip().splitlines()
        self.assertRegex(lines[0], r"^ok: git \d")
        self.assertRegex(lines[1], r"^ok: python3 3\.\d+")
        self.assertEqual(lines[-1], "prereqs: ok")

    def test_required_missing(self):
        code, out, _ = self.run_checker("poc-research", "git", "python3", hide=["python3"])
        self.assertEqual(code, 1, out)
        miss = [l for l in out.splitlines() if l.startswith("MISSING: ")]
        self.assertEqual(len(miss), 1, out)
        self.assertIn("python3 3.9 or later is needed by /spike-loop:poc-research", miss[0])
        for w in INSTALL_WORDS:
            self.assertIn(w, miss[0])
        self.assertTrue(miss[0].endswith("then run the command again."), miss[0])
        self.assertEqual(out.strip().splitlines()[-1], "prereqs: missing python3")

    def test_optional_missing_is_skipped(self):
        code, out, _ = self.run_checker("poc-log", "python3:optional", hide=["python3"])
        self.assertEqual(code, 0, out)
        skip = [l for l in out.splitlines() if l.startswith("skipped: ")]
        self.assertEqual(len(skip), 1, out)
        self.assertIn("/spike-loop:poc-log leaves out the time check", skip[0])
        self.assertEqual(out.strip().splitlines()[-1], "prereqs: ok")

    def python_as(self, version):
        """A python3 shim that runs the checker's real check with sys.version_info set to version."""
        real = shutil.which("python3")
        v = tuple(int(x) for x in version.split("."))
        return self.fake("python3", 'exec "%s" -c "import sys; sys.version_info = %r + (\'final\', 0); '
                         'exec(sys.argv[1])" "$2"\n' % (real, v))

    @unittest.skipUnless(shutil.which("python3"), "python3 needed")
    def test_old_python_counts_as_missing(self):
        code, out, _ = self.run_checker("poc-research", "python3", hide=["python3"], extra_bin=self.python_as("3.8.10"))
        self.assertEqual(code, 1, out)
        self.assertIn("found 3.8.10", out)

    @unittest.skipUnless(shutil.which("python3"), "python3 needed")
    def test_python_3_9_is_enough(self):
        code, out, _ = self.run_checker("poc-research", "python3", hide=["python3"], extra_bin=self.python_as("3.9.0"))
        self.assertEqual(code, 0, out)
        self.assertIn("ok: python3 3.9.0", out)

    def test_agent_names_read_as_agents(self):
        code, out, _ = self.run_checker("packager", "rsync", hide=["rsync"])
        self.assertEqual(code, 1, out)
        self.assertIn("needed by the packager agent for the clean-clone test", out)

    def test_several_missing_are_all_listed(self):
        code, out, _ = self.run_checker("poc-harden", "git", "rsync", "gitleaks:optional", "typos:optional",
                                        hide=["git", "rsync", "gitleaks", "typos"])
        self.assertEqual(code, 1, out)
        self.assertEqual(out.strip().splitlines()[-1], "prereqs: missing git rsync")
        self.assertEqual(len([l for l in out.splitlines() if l.startswith("skipped: ")]), 2, out)

    def test_usage_errors(self):
        for args in ((), ("poc-log",), ("poc-nope", "git"), ("poc-log", "perl"), ("poc-log", "git:sometimes")):
            code, out, _ = self.run_checker(*args)
            self.assertEqual(code, 2, (args, out))
            self.assertTrue(out.strip().splitlines()[-1].startswith("prereqs: usage error"), out)

    def test_every_command_and_tool_is_known(self):
        for cmd in commands():
            code, out, _ = self.run_checker(cmd, *["%s:optional" % t for t in TOOLS], hide=list(TOOLS))
            self.assertEqual(code, 0, (cmd, out))
            self.assertEqual(len([l for l in out.splitlines() if l.startswith("skipped: ")]), len(TOOLS), out)

    def test_every_missing_message_has_install_steps(self):
        for tool in TOOLS:
            code, out, _ = self.run_checker("poc-harden", tool, hide=list(TOOLS))
            line = next(l for l in out.splitlines() if l.startswith("MISSING: "))
            for w in INSTALL_WORDS:
                self.assertIn(w, line, (tool, line))

    def test_output_holds_no_path_or_environment_value(self):
        code, out, err = self.run_checker("poc-harden", *["%s:optional" % t for t in TOOLS])
        for text in (out, err):
            self.assertNotIn(str(self.tmp), text)
            self.assertNotIn("do-not-print-me", text)
            self.assertNotIn(os.path.expanduser("~"), text)

    def test_writes_nothing(self):
        self.run_checker("poc-harden", "git", "rsync", hide=["rsync"])
        left = set(os.listdir(str(self.tmp))) - self.before
        self.assertTrue(all(n.startswith("bin") or n == "fakebin" for n in left), left)

    def test_posix_syntax(self):
        r = subprocess.run(["sh", "-n", str(CHECKER)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        if shutil.which("shellcheck"):
            r = subprocess.run(["shellcheck", "-s", "sh", str(CHECKER)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout)

    def test_known_commands_match_the_repo(self):
        text = CHECKER.read_text()
        listed = re.search(r'^COMMANDS="([^"]*)"', text, re.M)
        self.assertTrue(listed, "COMMANDS line")
        self.assertEqual(sorted(listed.group(1).split()), commands())


class RegistryDocTests(unittest.TestCase):
    def test_doc_matches_the_registry(self):
        script = CHECKER.read_text()
        doc = (ROOT / "docs" / "prerequisites.md").read_text()
        install = dict(re.findall(r"^    (\w+)\) echo '([^']*)' ;;$", script, re.M))
        self.assertEqual(sorted(install), sorted(TOOLS))
        for tool, text in install.items():
            row = [l for l in doc.splitlines() if l.startswith("| `%s` |" % tool)]
            self.assertEqual(len(row), 1, tool)
            self.assertIn(text, row[0], tool)

    def test_readme_points_at_the_doc(self):
        self.assertIn("docs/prerequisites.md", (ROOT / "README.md").read_text())


if __name__ == "__main__":
    unittest.main()
