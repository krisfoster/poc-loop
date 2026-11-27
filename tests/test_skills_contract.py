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

    def test_poc_build_calls_the_implementer_through_the_agent_tool(self):
        # F1: a `context: fork` skill ran the implementer in the main tree even though the agent sets
        # `isolation: worktree`. Calling the agent through the Agent tool does create the worktree
        # (Claude Code 2.1.325), so poc-build must not be a fork and must say how it calls the agent.
        text = read("skills", "poc-build", "SKILL.md")
        front = text.split("---")[1]
        self.assertNotRegex(front, r"(?m)^context:", "poc-build must not fork")
        self.assertNotRegex(front, r"(?m)^agent:", "poc-build must not name an agent in its frontmatter")
        step2 = [l for l in text.splitlines() if l.startswith("2. **Call the agent.**")]
        self.assertEqual(len(step2), 1)
        self.assertIn("through the Agent tool", step2[0])
        self.assertIn("`spike-loop:implementer`", step2[0])
        self.assertNotRegex(step2[0], r"(?i)\b(never|do not) call\b|ignore `spike-loop")
        self.assertIn("isolation: worktree", read("agents", "implementer.md"))

    def test_poc_build_brief_does_not_name_the_main_checkout(self):
        # The implementer's paths rule uses the repo root named in its brief. Naming the main checkout would
        # send its edits to the user's own tree, which is the F1 symptom, so the brief names the worktree.
        text = read("skills", "poc-build", "SKILL.md")
        step2 = [l for l in text.splitlines() if l.startswith("2. **Call the agent.**")][0]
        self.assertIn("Do not put the main checkout's path in the brief", step2)
        self.assertIn("root of the git worktree it starts in", step2)
        self.assertIn("must not read or edit the main checkout", step2)
        self.assertIn("commit its change in the worktree", step2)
        self.assertNotIn("as an absolute path", step2)

    def test_poc_build_tells_the_user_where_the_change_is(self):
        text = read("skills", "poc-build", "SKILL.md")
        step3 = [l for l in text.splitlines() if l.startswith("3. **Report.**")]
        self.assertEqual(len(step3), 1)
        step3 = step3[0]
        self.assertIn("worktree path and branch", step3)
        self.assertIn("status --porcelain", step3)   # is the change committed?
        self.assertIn("origin/<default>", step3)     # the base, per the docs
        self.assertIn("worktree.baseRef", step3)
        self.assertIn("Do not merge, cherry-pick or copy it", step3)
        # F1 follow-up (2026-11-27, headless): with no remote, or with worktree.baseRef "head", the worktree
        # started from the local HEAD, so the base must be checked, not stated as fixed.
        self.assertIn('`git -C "<main root>" log --oneline HEAD --not <branch>`', step3)
        self.assertIn("with no remote it starts from your current commit", step3)
        self.assertNotIn("so unpushed commits and uncommitted work are not in it", step3)
        nxt = [l for l in text.splitlines() if l.startswith("End with one line starting `Next:`")]
        self.assertEqual(len(nxt), 1)
        self.assertIn("`git merge <branch>`", nxt[0])
        self.assertIn("/spike-loop:poc-verify", nxt[0])
        self.assertIn("commit -m", nxt[0])            # the uncommitted case

    def test_no_forked_skill_names_an_agent_that_sets_isolation(self):
        # A fork does not apply the agent's isolation, so a forked skill must not rely on it or promise it.
        for name in commands():
            text = read("skills", name, "SKILL.md")
            if re.search(r"""(?m)^context:\s*["']?fork""", text):
                agent = re.search(r"""(?m)^agent:\s*["']?spike-loop:([\w-]+)""", text).group(1)
                self.assertNotIn("worktree", text.split("---")[1], name)
                self.assertNotIn("isolation: worktree", read("agents", agent + ".md"),
                                 "%s forks %s, which sets isolation that a fork does not apply" % (name, agent))

    def test_implementer_commits_in_its_worktree(self):
        # F1 follow-up: the commit rule lives in the agent too, not only in poc-build's brief, so a direct
        # Agent-tool call (or a brief that forgets it) still leaves the change committed on the worktree branch.
        rules = read("agents", "implementer.md").split("## Rules", 1)[1].split("\n\n", 1)[0]
        line = [l for l in rules.splitlines() if re.search(r"(?i)\bcommit\b", l)]
        self.assertEqual(len(line), 1, "one commit rule under ## Rules")
        self.assertIn("in the worktree you start in", line[0])
        self.assertIn("when the done condition is met", line[0])
        self.assertIn("unless the brief says not to", line[0])
        self.assertIn("Never commit in the main checkout", line[0])

    def test_poc_log_time_check_line_is_printed_exactly(self):  # docs/evals/findings.md, F2
        step = next(l for l in read("skills", "poc-log", "SKILL.md").splitlines() if l.startswith("4. Time check"))
        self.assertIn("Print this line exactly, with only the three values filled in: "
                      "`Elapsed <x> of <timebox>, <n> entries.`", step)
        self.assertIn("Put any comment on the next line, never inside it.", step)
        self.assertNotIn("Print one line:", step)

    def test_poc_log_over_timebox_next_is_its_own_rule(self):  # docs/evals/findings.md, F3
        step = next(l for l in read("skills", "poc-log", "SKILL.md").splitlines() if l.startswith("5. "))
        rule = ("First, if the time check found the timebox exceeded and the Decision is `none yet`, the line is "
                "`Next: /spike-loop:poc-checkpoint <iterate | pivot | harden | stop | pause>` to decide now, "
                "never `/spike-loop:poc-verify`.")
        self.assertIn(rule, step)
        self.assertLess(step.index(rule), step.index("`none yet`: keep building"))
        self.assertNotIn("(if over the timebox", step)

    def test_poc_help_row_for_build_mentions_the_merge(self):
        row = [l for l in read("skills", "poc-help", "SKILL.md").splitlines() if "/spike-loop:poc-build" in l][0]
        self.assertIn("merge its branch", row)


if __name__ == "__main__":
    unittest.main()
