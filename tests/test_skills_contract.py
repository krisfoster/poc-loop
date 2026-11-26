"""Contract tests for the user-facing skills: help, Next lines and the README table.
Run: python3 -m unittest discover -s tests
"""
import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKILLS = os.path.join(ROOT, "skills")
NOT_COMMANDS = {"research-protocol"}  # preloaded into agents, never typed by the user


def commands():
    return sorted(d for d in os.listdir(SKILLS)
                  if d not in NOT_COMMANDS and os.path.isfile(os.path.join(SKILLS, d, "SKILL.md")))


def read(*parts):
    with open(os.path.join(ROOT, *parts), encoding="utf-8") as fh:
        return fh.read()


class SkillsContractTest(unittest.TestCase):
    def test_poc_help_exists(self):
        self.assertIn("poc-help", commands())

    def test_every_command_has_a_next_rule(self):
        for name in commands():
            text = read("skills", name, "SKILL.md")
            self.assertRegex(text, r"`Next:", "%s has no Next: rule" % name)

    def test_next_rules_only_name_real_commands(self):
        real = set(commands())
        for name in commands():
            for line in read("skills", name, "SKILL.md").splitlines():
                if "`Next:" not in line and "Next:" not in line:
                    continue
                for cmd in re.findall(r"/spike-loop:(poc-[a-z]+)", line):
                    self.assertIn(cmd, real, "%s points at /spike-loop:%s" % (name, cmd))

    def test_help_lists_every_command(self):
        text = read("skills", "poc-help", "SKILL.md")
        for name in commands():
            self.assertIn("/spike-loop:%s" % name, text, "poc-help does not list %s" % name)

    def test_readme_lists_every_command(self):
        text = read("README.md")
        for name in commands():
            self.assertIn("`/spike-loop:%s`" % name, text, "README does not list %s" % name)

    def test_help_is_read_only_and_has_a_hint(self):
        text = read("skills", "poc-help", "SKILL.md")
        self.assertIn("disable-model-invocation: true", text)
        self.assertRegex(text, r"(?m)^argument-hint: ")
        self.assertIn("Write nothing", text)

    def test_help_answers_from_its_table_and_reads_no_other_skill(self):
        # A live smoke run showed the read of another skill's file is blocked when reads outside
        # the working directory are blocked. The table already holds everything the answer needs.
        text = read("skills", "poc-help", "SKILL.md")
        self.assertNotIn("${CLAUDE_SKILL_DIR}/../", text)  # the paths rule may name ${CLAUDE_SKILL_DIR}, a read of a sibling skill may not
        self.assertNotIn("../poc-", text)
        self.assertIn("Do not read any other file", text)

    def test_forked_skills_keep_agent_contracts_untouched(self):
        # The Next line is added in the skill, not the agent, so poc-harden's use of the agents is unchanged.
        for agent in ("verifier", "reviewer", "reviewer-lite", "debugger", "packager", "implementer", "researcher"):
            self.assertNotIn("Next:", read("agents", agent + ".md"), agent)


if __name__ == "__main__":
    unittest.main()
