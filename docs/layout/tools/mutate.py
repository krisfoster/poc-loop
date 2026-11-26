#!/usr/bin/env python3
"""Mutation check for tests/test_docs_layout.py (plan Gate 1 and task 3.2).

Takes a compliant tree (the stand-in from make_standin.py at Gate 1, the real tree at task 3.2), makes a copy per
mutation, applies one deliberate wrong edit, runs the tests against the copy, and checks that exactly the expected
tests fail. Negative controls (edits that are fine) must fail nothing. Exit 0 only if every row behaves.

Targets come from the constants in tests/test_docs_layout.py (the rule texts, the warning lines, the git commands),
so they exist in any compliant tree however it is formatted. A target that is not found, or an edit that changes
nothing, is reported as its own row and counts as wrong. It never aborts the run.

Usage: python3 docs/layout/tools/mutate.py <compliant root>
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tests"))
import test_docs_layout as T  # noqa: E402  (constants only)

T_PATHS = "test_no_hard_coded_root_path"
T_VAGUE = "test_no_vague_base"
T_RULE_A = "test_rule_a_in_every_skill_and_agent"
T_RULE_B = "test_rule_b_in_every_file_that_resolves_the_docs_folder"
T_NOB = "test_poc_start_does_not_carry_rule_b"
T_ROOT = "test_root_files_stay_at_the_root"
T_NAME = "test_folder_name_is_exactly_poc_spec"
T_START = "test_write_step_names_the_new_paths_and_wiring_matches"
T_WARN = "test_packager_has_the_warning_and_its_limits"
T_DOCS = "test_readme_and_workflow_use_the_new_paths"
T_SPEC = "test_constants_equal_the_spec"
T_LIST = "test_every_skill_is_listed_for_rule_a_or_exempt"


class TargetNotFound(Exception):
    pass


def edit(rel, fn):
    def run(root):
        p = root / rel
        old = p.read_text(encoding="utf-8")
        new = fn(old)
        if new == old:
            raise TargetNotFound("edit changed nothing in %s" % rel)
        p.write_text(new, encoding="utf-8")
    return run


def append(rel, line):
    return edit(rel, lambda t: t.rstrip("\n") + "\n" + line + "\n")


def swap(rel, a, b):
    def f(t):
        if a not in t:
            raise TargetNotFound("%r not found in %s" % (a[:60], rel))
        return t.replace(a, b, 1)
    return edit(rel, f)


def in_write_step(a, b):
    """Replace a with b only on the poc-start line that starts with a number and '**Write**'."""
    def f(t):
        out, hit = [], False
        for line in t.splitlines(keepends=True):
            if re.match(r"^\d+\. \*\*Write\*\*", line):
                if a not in line:
                    raise TargetNotFound("%r not in the write step" % a)
                line, hit = line.replace(a, b), True
            out.append(line)
        if not hit:
            raise TargetNotFound("no write step found")
        return "".join(out)
    return edit(T.POC_START, f)


def new_skill(root):
    d = root / "skills" / "poc-new"
    d.mkdir()
    (d / "SKILL.md").write_text("---\nname: poc-new\n---\nA new command with no rules.\n", encoding="utf-8")


WORD = "Everything else is relative to the root."
ASK = "ask which to keep"
LS_TRACKED, LS_OTHERS = T.LS_FILES_COMMANDS[1], T.LS_FILES_COMMANDS[0]
LS_OLD_TRACKED = T.LS_FILES_COMMANDS[3]

# (label, mutation, expected failing tests). An empty set is a negative control.
# Altering Rule B, a warning line or a git command also fails test 3 (T_PATHS) on purpose: that test exempts those
# texts only when they are verbatim and only in the files that should carry them, so a changed or misplaced copy
# exposes the document names inside it.
CASES = [
    ("Rule A reworded by one word", swap("skills/poc-log/SKILL.md", T.RULE_A, T.RULE_A.replace(WORD, WORD[:-1] + " dir.")), {T_RULE_A}),
    ("Rule A missing from an agent", swap("agents/verifier.md", T.RULE_A, ""), {T_RULE_A}),
    ("Rule B reworded in the packager", swap(T.PACKAGER, T.RULE_B, T.RULE_B.replace(ASK, "ask which one to keep")), {T_RULE_B, T_PATHS}),
    ("Rule B added to poc-start", append(T.POC_START, T.RULE_B), {T_NOB, T_PATHS}),
    ("bare LOG.md in poc-verify", append("skills/poc-verify/SKILL.md", "Then append a note to LOG.md."), {T_PATHS}),
    ("bare POC.md in frontmatter of poc-research", swap("skills/poc-research/SKILL.md", "description: ", "description: Reads POC.md. "), {T_PATHS}),
    ("hard-coded poc-spec/POC.md in poc-log", append("skills/poc-log/SKILL.md", "Read poc-spec/POC.md first."), {T_PATHS}),
    ("poc-spec/LOG.md in a poc-help step", append(T.POC_HELP, "3. Read poc-spec/LOG.md for the last Decision."), {T_PATHS}),
    ("legacy note pasted into poc-log", append("skills/poc-log/SKILL.md", T.LEGACY_NOTE), {T_PATHS}),
    ("pwd in poc-debug", append("skills/poc-debug/SKILL.md", "Run pwd to see where you are."), {T_VAGUE}),
    ("Current Directory (capitalised) in poc-build", append("skills/poc-build/SKILL.md", "Work in the Current Directory."), {T_VAGUE}),
    ("current directory in frontmatter of poc-sources", swap("skills/poc-sources/SKILL.md", "description: ", "description: Works in the current directory. "), {T_VAGUE}),
    ("current project in poc-verify", append("skills/poc-verify/SKILL.md", "Verify the current project."), {T_VAGUE}),
    ("SUMMARY.md under poc-spec in README", append("README.md", "Written to poc-spec/SUMMARY.md."), {T_ROOT}),
    ("verify.sh under <docs>", append("skills/poc-harden/SKILL.md", "Run <docs>/verify.sh."), {T_ROOT}),
    ("folder drifts to specs/", append("README.md", "Files live in specs/ now."), {T_NAME}),
    ("folder drifts to spec/", append("docs/workflow.md", "Files live in spec/ now."), {T_NAME}),
    ("folder drifts to poc_spec/", append("README.md", "Files live in poc_spec/ now."), {T_NAME}),
    ("poc-start write step loses the log path", in_write_step("poc-spec/LOG.md", "LOG.md"), {T_START, T_PATHS}),
    ("poc-start loses the wiring block", swap(T.POC_START, T.WIRING, ""), {T_START}),
    ("poc-start loses the never-overwrite sentence", swap(T.POC_START, T.NO_OVERWRITE, ""), {T_START}),
    ("never-overwrite sentence pasted into poc-log", append("skills/poc-log/SKILL.md", T.NO_OVERWRITE), {T_PATHS}),
    ("packager warning line broken", swap(T.PACKAGER, T.WARNING_NEW, T.WARNING_NEW.replace("would travel with this repo (", "would travel with the repo (")), {T_WARN, T_PATHS}),
    ("packager --others command weakened", swap(T.PACKAGER, LS_OTHERS, LS_OTHERS.replace("--others --exclude-standard", "--others")), {T_WARN, T_PATHS}),
    ("packager drops the tracked-file command", swap(T.PACKAGER, LS_TRACKED, ""), {T_WARN}),
    ("packager drops the older-layout command", swap(T.PACKAGER, LS_OLD_TRACKED, ""), {T_WARN}),
    ("packager command uses cd instead of git -C", swap(T.PACKAGER, LS_TRACKED, LS_TRACKED.replace('git -C "<root>" ls-files', 'cd "<root>" && git ls-files')), {T_WARN, T_PATHS}),
    ("README bare POC.md", append("README.md", "Edit POC.md to start."), {T_DOCS}),
    ("workflow bare LOG.md", append("docs/workflow.md", "Append to LOG.md."), {T_DOCS}),
    ("spec text drifts from the constants", swap("docs/layout/spec.md", T.RULE_A, T.RULE_A.replace(WORD, WORD[:-1] + " dir.")), {T_SPEC}),
    ("new skill without Rule A", new_skill, {T_LIST}),
    # negative controls
    ("control: CHANGELOG.md mentioned in README", append("README.md", "See CHANGELOG.md for changes."), set()),
    ("control: 'the current PoC' in a description", swap("skills/poc-log/SKILL.md", "description: ", "description: In the current PoC, "), set()),
    ("control: README names poc-spec/POC.md", append("README.md", "Edit poc-spec/POC.md to start."), set()),
    ("control: older layout line in README", append("README.md", "In the older layout POC.md sits at the repo root."), set()),
    ("control: poc-spec/POC.md on a poc-help table row", append(T.POC_HELP, "| `/x` | reads poc-spec/POC.md | next |"), set()),
]


def run_tests(root):
    env = dict(os.environ, SPIKE_LAYOUT_ROOT=str(root))
    p = subprocess.run([sys.executable, "-m", "unittest", "-v", "tests.test_docs_layout"], cwd=str(REPO), env=env,
                       capture_output=True, text=True)
    failed = set()
    for line in (p.stdout + p.stderr).splitlines():
        m = re.match(r"^(\w+) \(.*\) \.\.\. (FAIL|ERROR)$", line)
        if m:
            failed.add(m.group(1))
    return failed


def main(base):
    base = Path(base)
    baseline = run_tests(base)
    if baseline:
        print("The tree under test is not compliant, these already fail: %s" % ", ".join(sorted(baseline)))
        return 2
    bad = 0
    print("%-55s %-9s %s" % ("mutation", "result", "failing tests"))
    for label, mutation, expected in CASES:
        tmp = Path(tempfile.mkdtemp(prefix="mutate-"))
        try:
            work = tmp / "tree"
            shutil.copytree(str(base), str(work))
            try:
                mutation(work)
            except TargetNotFound as exc:
                bad += 1
                print("%-55s %-9s %s" % (label, "NO TARGET", exc))
                continue
            failed = run_tests(work)
        finally:
            shutil.rmtree(str(tmp), ignore_errors=True)
        ok = failed == expected
        bad += 0 if ok else 1
        print("%-55s %-9s %s%s" % (label, "ok" if ok else "WRONG", ", ".join(sorted(failed)) or "none",
                                   "" if ok else "   (expected: %s)" % (", ".join(sorted(expected)) or "none")))
    print("\n%d mutations and controls, %d wrong" % (len(CASES), bad))
    return 1 if bad else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1]))
