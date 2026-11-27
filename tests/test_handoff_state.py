"""Tests for the hand-off state rules (docs/handoff/spec.md, plan Phase 1).

The rules are prose in skill files, so a substring check passes a broken skill. These tests parse:
numbered steps by their bold label, the State template, the value table, the exclusion lines and
the git commands in backticks, and compare them with the spec and with
docs/handoff/tools/check_git_rules.py, which checks the git rules themselves.

Run: python3 -m unittest discover -s tests
"""
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "docs", "handoff", "tools"))
import check_git_rules as R  # noqa: E402  (constants and the reference rules)

SPEC = os.path.join("docs", "handoff", "spec.md")
CHECKPOINT = os.path.join("skills", "poc-checkpoint", "SKILL.md")
HELP = os.path.join("skills", "poc-help", "SKILL.md")
LOG = os.path.join("skills", "poc-log", "SKILL.md")
START = os.path.join("skills", "poc-start", "SKILL.md")

# The order of work in poc-checkpoint (spec "Order of work"): each label is a numbered step.
CHECKPOINT_ORDER = ["Outcome.", "Topic.", "State.", "Hand-off file.", "Closing entry.",
                    "Pivot, harden, stop.", "Read back.", "Next."]
GIT_PREFIX = 'git --no-optional-locks -C "<root>" '
HELP_NEEDS = ["rev-parse --is-inside-work-tree", "branch --show-current", "rev-parse --short HEAD",
              "status --porcelain -- . <exclusions>", "merge-base --is-ancestor <recorded sha> HEAD",
              "log --oneline <recorded sha>..HEAD -- . <exclusions>"]
CHECKPOINT_NEEDS = [c for c in R.COMMANDS if c not in (
    "merge-base --is-ancestor <recorded sha> HEAD", "log --oneline <recorded sha>..HEAD -- . <exclusions>")]
EXCLUSION_LINES = {
    "new": "Exclusions, `poc-spec` layout: " + " ".join("`%s`" % p for p in R.EXCLUDE["new"]),
    "old": "Exclusions, root layout: " + " ".join("`%s`" % p for p in R.EXCLUDE["old"]),
}


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


def steps(text):
    """Top-level numbered steps as (label, text). A step runs to the next numbered step or heading."""
    out, cur = [], None
    for line in text.splitlines():
        m = re.match(r"^\d+\. \*\*(.+?)\*\*", line)
        if m:
            cur = [m.group(1), line]
            out.append(cur)
        elif re.match(r"^(\d+\. |#)", line):
            cur = None
        elif cur is not None:
            cur[1] += "\n" + line
    return [(l, t) for l, t in out]


def step(text, label):
    found = [t for l, t in steps(text) if l == label]
    return found[0] if len(found) == 1 else None


def state_template(text):
    lines = [l.strip() for l in text.splitlines() if l.strip().startswith("- State: branch: <")]
    return lines


def value_table(text):
    """{field: set of backticked fixed values} from the rows `| `field` | values |`."""
    table = {}
    for line in text.splitlines():
        m = re.match(r"^\| `([a-z ]+)` \| (.+) \|$", line.strip())
        if m and m.group(1) in R.FIELDS:
            table[m.group(1)] = set(re.findall(r"`([^`]+)`", m.group(2)))
    return table


def git_spans(text):
    return [s for s in re.findall(r"`([^`\n]+)`", text) if s.startswith("git ")]


def normalise(span):
    return span[len(GIT_PREFIX):] if span.startswith(GIT_PREFIX) else span


class FormatAgreement(unittest.TestCase):
    def test_state_template_is_the_same_in_spec_and_checkpoint(self):  # plan 1.1, 1.7
        spec, skill = state_template(read(SPEC)), state_template(read(CHECKPOINT))
        self.assertEqual(len(spec), 1, "spec has one State template line")
        self.assertEqual(skill, spec, "poc-checkpoint carries the spec's State template word for word")
        fields = [p.split(": ")[0] for p in spec[0][len("- State: "):].split("; ")]
        self.assertEqual(fields, R.FIELDS)

    def test_value_table_is_the_same_in_spec_and_checkpoint(self):  # plan 1.1, 1.7
        spec, skill = value_table(read(SPEC)), value_table(read(CHECKPOINT))
        self.assertEqual(sorted(spec), sorted(R.FIELDS), "spec value table covers the six fields")
        self.assertEqual(skill, spec)
        wt = spec["unmerged worktrees"]
        self.assertEqual(wt, {"none", ", ", "detached <short sha>", " (uncommitted)", "not a git repo"},
                         "the worktree grammar holds names only, never a path")

    def test_start_template_has_no_state_line(self):  # plan 1.1
        self.assertNotIn("- State:", read(START))

    def test_worktree_paths_are_printed_not_written(self):  # plan 1.7
        st = step(read(CHECKPOINT), "State.")
        self.assertIsNotNone(st, "poc-checkpoint has one **State.** step")
        self.assertRegex(st, r"worktree path[^.]*never written")


class Exclusions(unittest.TestCase):
    def test_exclusion_lines_agree(self):  # plan 1.1b
        for rel in (SPEC, CHECKPOINT, HELP):
            text = read(rel)
            for layout, line in EXCLUSION_LINES.items():
                self.assertIn(line, text, "%s lacks the %s exclusion line" % (rel, layout))
        for layout in ("new", "old"):
            self.assertNotIn(".", R.EXCLUDE[layout], "never exclude `.`")

    def test_no_exclusion_line_excludes_the_whole_repo(self):  # plan 1.1b
        for rel in (SPEC, CHECKPOINT, HELP):
            for line in read(rel).splitlines():
                if line.strip().startswith("Exclusions,"):
                    self.assertNotIn("`.`", line, rel)


class CheckpointOrder(unittest.TestCase):
    def setUp(self):
        self.text = read(CHECKPOINT)
        self.steps = steps(self.text)
        self.labels = [l for l, _ in self.steps]

    def test_steps_in_the_spec_order_and_next_is_last(self):  # plan 1.3
        for label in CHECKPOINT_ORDER:
            self.assertEqual(self.labels.count(label), 1, "one **%s** step" % label)
        pos = [self.labels.index(l) for l in CHECKPOINT_ORDER]
        self.assertEqual(pos, sorted(pos), "steps out of order: %s" % self.labels)
        self.assertEqual(self.labels[-1], "Next.", "the Next: line is the last step")

    def test_no_clear_before_the_read_back(self):  # plan 1.2
        self.assertIn("Read back.", self.labels)
        self.assertIsNotNone(step(self.text, "Next."))
        rb = self.labels.index("Read back.")
        for label, text in self.steps[:rb]:
            self.assertNotIn("/clear", text, "step %s mentions /clear before the read-back" % label)
        self.assertRegex(step(self.text, "Read back."), r"print no `/clear`")
        self.assertRegex(step(self.text, "Next."), r"(?i)only after a read-back that passed")

    def test_one_closing_entry_for_every_outcome(self):  # plan 1.3
        appending = [l for l, t in self.steps if re.search(r"(?i)\bappend\b[^.]*\bentry\b", t)]
        self.assertEqual(appending, ["Closing entry."])
        ce = step(self.text, "Closing entry.")
        self.assertIn("`State:`", ce)
        self.assertRegex(ce, r"(?i)every outcome")
        self.assertNotRegex(ce, r"(?i)\b(only )?if\b[^.]*\b(older|stale|missing)\b")

    def test_outcomes_include_pause(self):  # plan 1.4, 1.8
        front = self.text.split("---")[1]
        hint = re.search(r'(?m)^argument-hint: "(.+)"', front).group(1)
        for o in ("iterate", "pivot", "harden", "stop", "pause [topic]"):
            self.assertIn(o, hint)
        outcome = step(self.text, "Outcome.")
        self.assertIsNotNone(outcome)
        self.assertRegex(outcome, r"recommend one of iterate, pivot, harden, stop or pause")

    def test_topic_rule(self):  # plan 1.4
        t = step(self.text, "Topic.")
        self.assertIsNotNone(t)
        self.assertIn("`[a-z0-9-]+`", t)
        self.assertRegex(t, r"(?i)refuse")
        self.assertIn("`.`", t)
        self.assertIn("`/`", t)
        self.assertRegex(t, r"(?i)customer or deal name")
        self.assertRegex(t, r"(?i)no topic[^.]*no hand-off file")

    def test_hand_off_file_rule(self):  # plan 1.4
        h = step(self.text, "Hand-off file.")
        self.assertIsNotNone(h)
        self.assertIn("poc-spec/handoffs/<YYYY-MM-DD>-<topic>.md", h)
        self.assertRegex(h, r"try to Read")
        self.assertIn("`-2`", h)
        self.assertIn("`-3`", h)
        self.assertRegex(h, r"Write tool")
        self.assertRegex(h, r"(?i)never overwritten")
        self.assertRegex(h, r"(?i)root layout[^.]*no hand-off file")
        self.assertRegex(h, r"(?i)at most 40 lines")

    def test_resume_value_defined_for_every_outcome(self):  # plan 1.4
        row = [l for l in read(CHECKPOINT).splitlines() if l.startswith("| `resume` |")]
        self.assertEqual(len(row), 1)
        for o in ("iterate", "pivot", "`pause <topic>`", "`pause` with no topic", "harden", "stop"):
            self.assertIn(o, row[0])

    def test_next_after_clear_names_poc_help(self):  # plan 1.2
        n = step(self.text, "Next.")
        self.assertIsNotNone(n)
        self.assertRegex(n, r"`/clear`, then `/spike-loop:poc-help`")
        self.assertEqual(n.count("/clear"), 1, "the Next step names /clear once, for iterate, pivot and pause")


class GitCommands(unittest.TestCase):
    def check_section(self, text, needs):
        spans = git_spans(text)
        self.assertTrue(spans, "no git commands found")
        for s in spans:
            self.assertTrue(s.startswith("git --no-optional-locks -C \""), "without --no-optional-locks: %s" % s)
            self.assertIn(normalise(s), R.COMMANDS, "not one of the spec's commands: %s" % s)
        got = {normalise(s) for s in spans}
        for c in needs:
            self.assertIn(c, got, "missing: %s" % c)

    def test_checkpoint_state_step_commands(self):  # plan 1.6
        st = step(read(CHECKPOINT), "State.")
        self.assertIsNotNone(st)
        self.check_section(st, CHECKPOINT_NEEDS)

    def test_help_staleness_step_commands(self):  # plan 1.6
        st = step(read(HELP), "Staleness.")
        self.assertIsNotNone(st, "poc-help has one **Staleness.** step")
        self.check_section(st, HELP_NEEDS)
        self.assertRegex(st, r"(?i)count")
        self.assertRegex(st, r"(?i)listed path")

    def test_spec_writes_every_command(self):  # plan 1.6, also run by the script
        spec = read(SPEC)
        for c in R.COMMANDS:
            self.assertIn(c, spec)


class HelpRules(unittest.TestCase):
    def setUp(self):
        self.text = read(HELP)

    def rows(self):
        out = {}
        for line in self.text.splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) == 3 and cells[0] in ("State, fresh", "State, stale",
                                                "No State, or a State line with any entry after it"):
                out[cells[0]] = cells
        return out

    def test_three_rows_and_no_clear_in_any_next(self):  # plan 1.2, 1.5, 1.6
        rows = self.rows()
        self.assertEqual(len(rows), 3, "the fresh, stale and no-State rows")
        for name, cells in rows.items():
            self.assertNotIn("/clear", cells[2], name)
        for line in self.text.splitlines():
            if "Next" in line:
                self.assertNotIn("/clear", line, "a Next rule in poc-help names /clear: %s" % line.strip())
        nxt = step(self.text, "Next.")
        self.assertIsNotNone(nxt, "poc-help has one **Next.** step")
        self.assertNotIn("/clear", nxt, "the Next step, its table and its Decision list never name /clear")

    def test_stale_pause_takes_the_topic_from_the_file_name(self):  # plan 1.4
        stale = self.rows().get("State, stale")
        self.assertIsNotNone(stale)
        self.assertIn("`/spike-loop:poc-checkpoint pause <topic>`", stale[2])
        self.assertRegex(stale[2], r"(?i)file name")

    def test_last_entry_only_and_no_fallback(self):  # plan 1.5
        st = step(self.text, "State.")
        self.assertIsNotNone(st, "poc-help has one **State.** step")
        self.assertRegex(st, r"(?i)only a `State:` line in the last dated entry")
        self.assertRegex(st, r'(?i)with any entry after it means "State unknown"')
        self.assertRegex(self.text, r"(?i)State unknown")
        self.assertNotRegex(self.text, r"(?i)newest[^.]*handoffs")
        rows = self.rows()
        self.assertNotIn("stale", rows.get("No State, or a State line with any entry after it", ["", "", ""])[1].lower())

    def test_help_stays_read_only(self):
        self.assertIn("Write nothing", self.text)


class LogAndStart(unittest.TestCase):
    def test_poc_log_writes_no_state_and_no_clear(self):  # plan 1.2, 2.3
        text = read(LOG)
        self.assertNotIn("- State:", text)
        for line in text.splitlines():
            if "Next:" in line:
                self.assertNotIn("/clear", line)
        rule = [l for l in text.splitlines() if "Next:" in l and "`iterate`:" in l]
        self.assertEqual(len(rule), 1, "one Decision-based Next rule")
        for o in ("iterate", "pivot", "pause"):
            self.assertIn("`%s`: `/spike-loop:poc-checkpoint %s`" % (o, o), rule[0])

    def test_decision_lists_include_pause(self):  # plan 1.8
        start = [l for l in read(START).splitlines() if l.startswith("- Decision: <")]
        self.assertEqual(start, ["- Decision: <iterate | pivot | harden | stop | pause | none yet>"])
        self.assertIn("pause", [l for l in read(LOG).splitlines() if "Decision" in l][0])


class OutcomeLists(unittest.TestCase):
    def test_every_list_of_outcomes_has_pause(self):  # plan 1.8, explicit list
        places = [
            (HELP, lambda l: "/spike-loop:poc-checkpoint [" in l),
            ("README.md", lambda l: "`/spike-loop:poc-checkpoint`" in l and l.startswith("|")),
            (os.path.join("docs", "workflow.md"), lambda l: "**Iterate**" in l or "Decide" in l),
        ]
        for rel, pick in places:
            lines = [l for l in read(rel).splitlines() if pick(l)]
            self.assertTrue(lines, "no outcome list found in %s" % rel)
            self.assertTrue(any("pause" in l.lower() for l in lines), "%s lists outcomes without pause" % rel)


class Workflow(unittest.TestCase):
    def test_every_clear_goes_through_the_checkpoint(self):  # plan 1.2, 2.5
        text = read(os.path.join("docs", "workflow.md"))
        for sentence in re.split(r"(?<=[.!?])\s+|\n", text):
            if "/clear" in sentence:
                self.assertIn("/spike-loop:poc-checkpoint", sentence.split("/clear")[0],
                              "a /clear not preceded by the checkpoint: %s" % sentence.strip())


# Key clauses pinned word for word, as the layout tests pin Rule A and Rule B: a rewording that flips
# a rule (fails to succeeds, never to always) must fail a test. (file, step label or None, phrase)
PINNED = [
    (HELP, "Staleness.", "merge-base --is-ancestor <recorded sha> HEAD` fails"),
    (HELP, "Staleness.", "<recorded sha>..HEAD -- . <exclusions>` prints anything"),
    (HELP, "Staleness.", "Otherwise, when both are shas:"),
    (HELP, "Staleness.", "stale when the count of uncommitted paths differs from the recorded count"),
    (HELP, "Staleness.", "or when a listed path is no longer uncommitted"),
    (HELP, "Staleness.", '`":(exclude)<name>"`'),
    (HELP, "State.", "(the last `## ` heading)"),
    (HELP, "Hand-off.", "Read no other hand-off file: only the one `resume:` names."),
    (CHECKPOINT, "Closing entry.", "to `<docs>/LOG.md` for every outcome:"),
    (CHECKPOINT, None, "The command is the next piece of work, never `/clear` or `/spike-loop:poc-help`: those belong in the `Next:` line"),
    (CHECKPOINT, "Closing entry.", "with the `State:` line from the State step as its last line."),
    (CHECKPOINT, "Topic.", "Refuse anything else (a `.`, a `/`, an empty result)"),
    (CHECKPOINT, "Hand-off file.", "use the first whose Read fails as not found"),
    (CHECKPOINT, "Hand-off file.", "at most 40 lines: what was done, the State line, decisions waiting, "
                                   "gotchas learned, files to read first, the next step."),
    (CHECKPOINT, "State.", "Take only entries under `<main checkout>/.claude/worktrees/`, not the root's own worktree."),
    (CHECKPOINT, None, '`":(exclude)<name>"`'),
    (LOG, None, "Never write a `State:` line: only `/spike-loop:poc-checkpoint` records the state."),
]
EXACT_LINES = [
    (HELP, 'Arguments: "$ARGUMENTS". Never use em dashes. This command only reads and prints. '
           'Write nothing and run nothing that changes a file.'),
    (CHECKPOINT, 'Outcome from the user: "$ARGUMENTS". Never use em dashes. Do not commit.'),
]


class PinnedClauses(unittest.TestCase):
    def test_key_clauses_are_word_for_word(self):
        for rel, label, phrase in PINNED:
            text = read(rel) if label is None else step(read(rel), label)
            self.assertIsNotNone(text, "%s has no **%s** step" % (rel, label))
            self.assertIn(phrase, text, "%s %s" % (rel, label or ""))

    def test_exact_lines(self):
        for rel, line in EXACT_LINES:
            self.assertIn(line, read(rel).splitlines(), rel)

    def test_help_status_mode_never_writes(self):
        status = read(HELP).split("## With no arguments", 1)[1]
        self.assertNotRegex(status, r"(?i)\bappend|\b(edit|write) tool\b|with the (edit|write)\b|\brecord it again\b")

    def test_fresh_row_next_is_the_resume_command(self):
        for line in read(HELP).splitlines():
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if cells and cells[0] == "State, fresh":
                self.assertEqual(cells[2], "The `resume:` command")
                return
        self.fail("no State, fresh row")


class GitRulesScript(unittest.TestCase):
    def test_check_git_rules_passes(self):  # plan 1.8b
        r = subprocess.run([sys.executable, os.path.join(ROOT, "docs", "handoff", "tools", "check_git_rules.py")],
                           capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:])


if __name__ == "__main__":
    unittest.main()
