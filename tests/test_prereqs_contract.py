"""Contract tests for the prerequisite guard in skills and agents (docs/prereqs/spec.md, Tests 3).
Run: python3 -m unittest discover -s tests
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHECK = 'sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs"'
RULES = ["Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs *)", 'Bash(sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" *)']
TOOLS = ("git", "python3", "rsync", "gitleaks", "typos")

# The one list of what each command and agent checks. A change here is a design change: update the spec.
SKILLS = {
    "poc-build": "git", "poc-checkpoint": "git", "poc-debug": "git",
    "poc-harden": "git rsync gitleaks:optional typos:optional", "poc-help": "git",
    "poc-log": "git python3:optional", "poc-package": "git rsync gitleaks:optional",
    "poc-research": "git python3:optional", "poc-review": "git", "poc-sources": "python3", "poc-start": "git",
    "poc-verify": "git",
}
AGENTS = {
    "debugger": "git", "implementer": "git", "packager": "git rsync gitleaks:optional", "researcher": "git",
    "reviewer": "git", "reviewer-lite": "git", "verifier": "git",
}
NOT_CHECKED = {"research-protocol": "preloaded into agents, never a command; the researcher agent checks git"}

SKILL_PARA = ('**Prerequisites.** Before anything else, run `%s {cmd} {tools}` as a command on its own, never joined to '
              'another with `;` or `&&`, and read its output. If the last line '
              'is `prereqs: missing ...`, print each `MISSING:` line as it is, change nothing, and end with '
              '`Next: install what is missing, then run /spike-loop:{cmd} again`. Print any `skipped:` line and leave '
              'out the step that needs that tool. If the check cannot run (refused, not found, or no POSIX shell), say '
              'so in one line and continue: a command that needs a missing tool will fail with its own error. This '
              'check covers any agent this command starts: when you brief an agent, say "prerequisites checked".') % CHECK
AGENT_PARA = ('**Prerequisites.** Skip this if the command that started you, or your brief, says prerequisites were '
              'checked. Otherwise, before anything else, run `%s {cmd} {tools}` as a command on its own, never joined to '
              'another with `;` or `&&`, and read its output. If the last line '
              'is `prereqs: missing ...`, print each `MISSING:` line as it is, change nothing, and stop, reporting '
              'what is missing. Print any `skipped:` line and leave out the step that needs that tool. If the check '
              'cannot run (refused, not found, or no POSIX shell), say so in one line and continue.') % CHECK

USES = {  # how a body shows it runs the tool
    "git": re.compile(r"`git |git -C|git --no-optional-locks"),
    "python3": re.compile(r"`python3 "),
    "rsync": re.compile(r"\brsync\b"),
    "gitleaks": re.compile(r"\bgitleaks\b"),
    "typos": re.compile(r"`typos`"),
}


def fill(template, cmd, tools):
    return template.replace("{cmd}", cmd).replace("{tools}", tools)


def path_of(name):
    p = ROOT / "skills" / name / "SKILL.md"
    return p if p.is_file() else ROOT / "agents" / ("%s.md" % name)


def split(text):
    """(frontmatter lines, body)"""
    lines = text.splitlines()
    end = lines.index("---", 1)
    return lines[1:end], "\n".join(lines[end + 1:])


def prereq_lines(body):
    return [l for l in body.splitlines() if l.startswith("**Prerequisites.**")]


class GuardTests(unittest.TestCase):
    def test_every_skill_and_agent_is_classified(self):
        skills = {d.name for d in (ROOT / "skills").iterdir() if (d / "SKILL.md").is_file()}
        agents = {p.stem for p in (ROOT / "agents").glob("*.md")}
        self.assertEqual(skills, set(SKILLS) | set(NOT_CHECKED))
        self.assertEqual(agents, set(AGENTS))

    def test_skill_paragraph_is_exact(self):
        for name, tools in SKILLS.items():
            _, body = split(path_of(name).read_text())
            got = prereq_lines(body)
            self.assertEqual(got, [fill(SKILL_PARA, name, tools)], name)

    def test_agent_paragraph_is_exact(self):
        for name, tools in AGENTS.items():
            _, body = split(path_of(name).read_text())
            self.assertEqual(prereq_lines(body), [fill(AGENT_PARA, name, tools)], name)

    def test_paragraph_comes_before_the_work(self):
        for name in list(SKILLS) + list(AGENTS):
            _, body = split(path_of(name).read_text())
            lines = body.splitlines()
            at = next(i for i, l in enumerate(lines) if l.startswith("**Prerequisites.**"))
            first_step = next((i for i, l in enumerate(lines) if re.match(r"(1\. |## Rules|\*\*Paths\.\*\*)", l)), len(lines))
            self.assertLess(at, first_step, name)

    def test_skills_pre_approve_the_checker(self):
        for name in SKILLS:
            fm, _ = split(path_of(name).read_text())
            self.assertIn("allowed-tools:", fm, name)
            i = fm.index("allowed-tools:")
            listed = []
            for l in fm[i + 1:]:
                if not l.startswith("  - "):
                    break
                listed.append(l[4:])
            for rule in RULES:
                self.assertIn(rule, listed, name)

    def test_research_protocol_is_only_preloaded_into_agents_that_check_git(self):
        users = [n for n in AGENTS if "research-protocol" in path_of(n).read_text()]
        self.assertTrue(users)
        for n in users:
            self.assertIn("git", AGENTS[n].split(), n)

    def test_every_tool_a_file_runs_is_listed(self):
        for name, tools in list(SKILLS.items()) + list(AGENTS.items()):
            _, body = split(path_of(name).read_text())
            body = "\n".join(l for l in body.splitlines() if not l.startswith("**Prerequisites.**"))
            listed = {t.split(":")[0] for t in tools.split()}
            for tool, rx in USES.items():
                if rx.search(body):
                    self.assertIn(tool, listed, "%s runs %s but does not check it" % (name, tool))

    def test_listed_tools_are_registry_tools(self):
        for tools in list(SKILLS.values()) + list(AGENTS.values()):
            for t in tools.split():
                self.assertIn(t.split(":")[0], TOOLS)

    def test_registry_doc_names_the_users_of_each_tool(self):
        doc = (ROOT / "docs" / "prerequisites.md").read_text()
        for tool in ("rsync", "gitleaks", "typos", "python3"):
            row = next(l for l in doc.splitlines() if l.startswith("| `%s` |" % tool))
            users = [n for n, t in list(SKILLS.items()) + list(AGENTS.items()) if tool in [x.split(":")[0] for x in t.split()]]
            for u in users:
                self.assertIn("`%s`" % u, row, "%s row does not name %s" % (tool, u))


class PocLogTests(unittest.TestCase):
    def setUp(self):
        self.fm, self.body = split(path_of("poc-log").read_text())

    def step(self, n):
        return next(l for l in self.body.splitlines() if l.startswith("%d. " % n))

    def test_time_check_runs_the_script(self):
        s = self.step(4)
        self.assertIn('run exactly `python3 "${CLAUDE_SKILL_DIR}/scripts/time_check.py" --root "<root>" --docs <docs>`', s)
        self.assertIn("Print its first line exactly as the script printed it, on a line of its own, and put any "
                      "comment on the next line, never inside it.", s)
        self.assertIn("If its second line is `timebox: over`, say so plainly", s)
        self.assertIn("print `Time check: not run (<reason>)` and nothing else about time: never work out elapsed "
                      "time or count entries yourself.", s)
        self.assertIn("Never write the time line or the reason into `<docs>/LOG.md`.", s)
        self.assertNotIn("compute elapsed", s)

    def test_append_with_edit_then_run_the_script_as_written(self):
        self.assertIn("append it to the end of `<docs>/LOG.md` with the Edit tool", self.step(3))
        s = self.step(4)
        self.assertIn("Otherwise, after the entry is in the file, run exactly", s)
        self.assertIn("as a command on its own: no `cd` in front, no extra flags, nothing joined to it (it takes the "
                      "root as an argument).", s)
        self.assertIn("if the prerequisites check skipped `python3`, do not run the script: print the checker's "
                      "`skipped:` line as it is, then `Time check: not run (python3 skipped)`.", s)

    def test_next_rule_keys_on_the_script(self):
        s = self.step(5)
        self.assertIn("First, if the time check printed `timebox: over` and the Decision is `none yet`, the line is "
                      "`Next: /spike-loop:poc-checkpoint <iterate | pivot | harden | stop | pause>` to decide now, "
                      "never `/spike-loop:poc-verify`.", s)

    def test_script_is_pre_approved(self):
        for rule in ['Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/time_check.py *)',
                     'Bash(python3 "${CLAUDE_SKILL_DIR}/scripts/time_check.py" *)']:
            self.assertIn("  - " + rule, self.fm)


class PocResearchTests(unittest.TestCase):
    def test_without_python_it_researches_public_sources(self):
        _, body = split(path_of("poc-research").read_text())
        step = next(l for l in body.splitlines() if l.startswith("1. "))
        self.assertIn("If the prerequisites check skipped `python3`, do not run it: treat the setup as not done and "
                      "research public sources only, saying so in one line.", step)


if __name__ == "__main__":
    unittest.main()
