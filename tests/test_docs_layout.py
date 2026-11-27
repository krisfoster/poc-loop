"""Tests for the poc-spec layout and repo-root paths.

Spec: docs/layout/spec.md. Plan: docs/layout/plan.md. Text checks only: they show the skills and agents say
the right thing, not that a model follows them. Run: python3 -m unittest discover -s tests

SPIKE_LAYOUT_ROOT points the tests at another copy of the tree (the Gate 1 and Phase 3 mutation checks).
"""
import os
import re
import unittest
from pathlib import Path

ROOT = Path(os.environ.get("SPIKE_LAYOUT_ROOT") or Path(__file__).resolve().parents[1])
SPEC_PATH = ROOT / "docs" / "layout" / "spec.md"

# Rule texts, generated from docs/layout/spec.md. test_constants_equal_the_spec keeps them in step.
RULE_A = '**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that needs the working directory (it uses a relative path or runs a script there) as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run any other command as it is (such as `date`, a script by its absolute path, or `chmod` or `tail` given a `<root>/<path>`), unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full, and use them to check, read and list files. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.'
RULE_B = "**Docs folder.** Check these four paths, relative to the repo root, by reading each with the Read tool (it needs no `cd`, a missing file is just an error, and Glob can skip gitignored files, which `poc-spec/` often is): `poc-spec/POC.md`, `poc-spec/LOG.md`, `POC.md`, `LOG.md`. If files exist only under `poc-spec/`, the docs folder `<docs>` is `poc-spec`. If they exist only at the root, `<docs>` is `.` (an older PoC, use it as is). If files exist in both places, stop, say the PoC is half-migrated, name the files, and ask which to keep (an agent reports this and stops). If none exist, follow the command's own step. `<docs>/POC.md` means `poc-spec/POC.md` or `POC.md`, and likewise `<docs>/LOG.md`."
WIRING = 'Docs folder: `poc-spec/`. All paths are relative to the repo root. At session start read `poc-spec/POC.md` and the last 40 lines of `poc-spec/LOG.md`. Stay within `poc-spec/POC.md`. Park new ideas in `poc-spec/LOG.md` under Later. Never claim done without the output of `./verify.sh` or the manual check. Hand-offs, specs and plans for this PoC go under `poc-spec/`.'
LEGACY_NOTE = 'Older layout: POC.md and LOG.md are at the repo root. It works as is. To move them: mkdir poc-spec && git mv POC.md LOG.md poc-spec/ (use mv if they are untracked), then update CLAUDE.md.'
WARNING_NEW = 'poc-spec/ would travel with this repo (<n> files tracked or not ignored) and this PoC is public or tied to a deal. LOG.md can hold customer names. Add poc-spec/ to .gitignore and run git rm -r --cached poc-spec before sharing. Anything already pushed stays in history.'
WARNING_OLD = 'POC.md and LOG.md would travel with this repo and this PoC is public or tied to a deal. LOG.md can hold customer names. Add both to .gitignore and run git rm --cached POC.md LOG.md before sharing. Anything already pushed stays in history.'
NO_OVERWRITE = 'If `poc-spec/POC.md`, `poc-spec/LOG.md` or `verify.sh` already exists, or a `POC.md` or `LOG.md` sits at the repo root (an older PoC), stop and ask.'

# The packager's four git ls-files commands name the document files on purpose, in both layouts.
LS_FILES_COMMANDS = (
    'git -C "<root>" ls-files --others --exclude-standard poc-spec/POC.md poc-spec/LOG.md',
    'git -C "<root>" ls-files poc-spec/POC.md poc-spec/LOG.md',
    'git -C "<root>" ls-files --others --exclude-standard POC.md LOG.md',
    'git -C "<root>" ls-files POC.md LOG.md',
)

# Skills without Rule A: poc-sources touches only user-level paths, research-protocol is read inside agents.
RULE_A_EXEMPT = {"poc-sources", "research-protocol"}
RULE_A_SKILLS = ["poc-build", "poc-checkpoint", "poc-debug", "poc-harden", "poc-help", "poc-log",
                 "poc-package", "poc-research", "poc-review", "poc-start", "poc-verify"]
RULE_B_SKILLS = ["poc-checkpoint", "poc-harden", "poc-help", "poc-log", "poc-package", "poc-research", "poc-review"]
RULE_B_AGENTS = ["packager"]
POC_START = "skills/poc-start/SKILL.md"
POC_HELP = "skills/poc-help/SKILL.md"
POC_CHECKPOINT = "skills/poc-checkpoint/SKILL.md"
# The hand-off state rules (docs/handoff/spec.md) name the root-layout files in one exact line.
ROOT_EXCLUSIONS = "Exclusions, root layout: `POC.md` `LOG.md` `SUMMARY.md` `.claude`"
PACKAGER = "agents/packager.md"
RULE_B_FILES = {"skills/%s/SKILL.md" % n for n in RULE_B_SKILLS} | {"agents/%s.md" % n for n in RULE_B_AGENTS}


def exempt_snippets(name):
    """Texts that may name the document files, each only in the files that should carry it and only verbatim."""
    snippets = ()
    if name in RULE_B_FILES:
        snippets += (RULE_B,)
    if name == POC_HELP:
        snippets += (LEGACY_NOTE,)
    if name in (POC_HELP, POC_CHECKPOINT):
        snippets += (ROOT_EXCLUSIONS,)
    if name == POC_START:
        snippets += (NO_OVERWRITE,)
    if name == PACKAGER:
        snippets += (WARNING_NEW, WARNING_OLD) + LS_FILES_COMMANDS
    return snippets


def new_path_allowed(name, line):
    """poc-spec/POC.md and poc-spec/LOG.md may be named in poc-start, and on table rows of poc-help."""
    return name == POC_START or (name == POC_HELP and line.lstrip().startswith("|"))
BANNED = [r"current director(?:y|ies)", r"current working director(?:y|ies)", r"current repo\b", r"current git repo\b",
          r"current project\b", r"this directory", r"\bcwd\b", r"\bpwd\b", r"\$PWD"]
DOC_NAME = re.compile(r"(?<![\w])(POC|LOG)\.md")


def rel(path):
    return path.relative_to(ROOT).as_posix()


def skill_path(name):
    return ROOT / "skills" / name / "SKILL.md"


def agent_path(name):
    return ROOT / "agents" / (name + ".md")


def all_skills():
    return sorted(p for p in (ROOT / "skills").glob("*/SKILL.md"))


def all_agents():
    return sorted((ROOT / "agents").glob("*.md"))


def read(path):
    return Path(path).read_text(encoding="utf-8")


def fail_with(problems):
    if problems:
        raise AssertionError("\n" + "\n".join(problems))


def spec_blocks():
    """Pull the rule texts out of the spec the same way the constants were generated."""
    text = read(SPEC_PATH)

    def quote(start):
        for line in text.splitlines():
            if line.startswith("> " + start):
                return line[2:]
        return None

    def tick(pattern):
        m = re.search(pattern, text, re.M)
        return m.group(1) if m else None

    return {
        "RULE_A": quote("**Paths.** "),
        "RULE_B": quote("**Docs folder.** "),
        "WIRING": quote("Docs folder: `poc-spec/`."),
        "LEGACY_NOTE": tick(r"`poc-help` prints one line when it finds the root layout: `([^`]+)`"),
        "WARNING_NEW": tick(r"^New layout: `([^`]+)`$"),
        "WARNING_OLD": tick(r"^Older layout: `([^`]+)`$"),
        "NO_OVERWRITE": quote("If `poc-spec/POC.md`, `poc-spec/LOG.md` or `verify.sh` already exists"),
    }


class SpecAndConstantsTest(unittest.TestCase):
    def test_constants_equal_the_spec(self):  # test 10
        got = spec_blocks()
        problems = []
        for name, value in (("RULE_A", RULE_A), ("RULE_B", RULE_B), ("WIRING", WIRING),
                            ("LEGACY_NOTE", LEGACY_NOTE), ("WARNING_NEW", WARNING_NEW), ("WARNING_OLD", WARNING_OLD),
                            ("NO_OVERWRITE", NO_OVERWRITE)):
            if got[name] != value:
                problems.append("%s differs from %s (spec has %r)" % (name, rel(SPEC_PATH), got[name]))
        fail_with(problems)

    def test_every_skill_is_listed_for_rule_a_or_exempt(self):
        listed = set(RULE_A_SKILLS) | RULE_A_EXEMPT
        problems = ["skills/%s has no entry in RULE_A_SKILLS or RULE_A_EXEMPT" % p.parent.name
                    for p in all_skills() if p.parent.name not in listed]
        problems += ["skills/%s is listed but does not exist" % n for n in listed if not skill_path(n).is_file()]
        fail_with(problems)


class RulesPresentTest(unittest.TestCase):
    def rule_a_files(self):
        return [skill_path(n) for n in RULE_A_SKILLS] + all_agents()

    def rule_b_files(self):
        return [skill_path(n) for n in RULE_B_SKILLS] + [agent_path(n) for n in RULE_B_AGENTS]

    def test_rule_a_in_every_skill_and_agent(self):  # test 1
        problems = ["%s lacks Rule A verbatim" % rel(p) for p in self.rule_a_files() if RULE_A not in read(p)]
        fail_with(problems)

    def test_rule_b_in_every_file_that_resolves_the_docs_folder(self):  # test 2
        problems = ["%s lacks Rule B verbatim" % rel(p) for p in self.rule_b_files() if RULE_B not in read(p)]
        fail_with(problems)

    def test_poc_start_does_not_carry_rule_b(self):  # it creates the files and has its own check
        self.assertNotIn(RULE_B, read(skill_path("poc-start")))


class PathsTest(unittest.TestCase):
    def test_no_hard_coded_root_path(self):  # test 3
        problems = []
        for path in all_skills() + all_agents():
            name = rel(path)
            text = read(path)
            for snippet in exempt_snippets(name):
                text = text.replace(snippet, "")
            if name == POC_START:
                text = re.sub(r"(?m)^### (?:POC|LOG)\.md$", "", text)  # template headings name template blocks
            for lineno, line in enumerate(text.splitlines(), 1):
                for m in DOC_NAME.finditer(line):
                    before = line[:m.start()]
                    if before.endswith("<docs>/"):
                        continue
                    if before.endswith("poc-spec/"):
                        if not new_path_allowed(name, line):
                            problems.append("%s:%d names poc-spec/%s.md directly: use <docs>/" % (name, lineno, m.group(1)))
                        continue
                    problems.append("%s:%d bare %s.md: %s" % (name, lineno, m.group(1), line.strip()[:90]))
        fail_with(problems)

    def test_no_vague_base(self):  # test 4
        problems = []
        for path in all_skills() + all_agents():
            text = read(path).replace(RULE_A, "")
            for lineno, line in enumerate(text.splitlines(), 1):
                for pat in BANNED:
                    if re.search(pat, line, re.I):
                        problems.append("%s:%d vague base %r: %s" % (rel(path), lineno, pat, line.strip()[:90]))
        fail_with(problems)

    def test_root_files_stay_at_the_root(self):  # test 5
        problems = []
        pats = re.compile(r"(?:poc-spec/|<docs>/)(SUMMARY\.md|verify\.sh)")
        for path in all_skills() + all_agents() + [ROOT / "README.md", ROOT / "docs" / "workflow.md"]:
            for lineno, line in enumerate(read(path).splitlines(), 1):
                for m in pats.finditer(line):
                    problems.append("%s:%d puts %s under the docs folder" % (rel(path), lineno, m.group(1)))
        fail_with(problems)

    def test_folder_name_is_exactly_poc_spec(self):  # test 6
        problems = []
        tok = re.compile(r"[\w.-]*specs?/")
        for path in all_skills() + all_agents() + [ROOT / "README.md", ROOT / "docs" / "workflow.md"]:
            for lineno, line in enumerate(read(path).splitlines(), 1):
                for m in tok.finditer(line):
                    if m.group(0) != "poc-spec/":
                        problems.append("%s:%d folder name %r, expected poc-spec/" % (rel(path), lineno, m.group(0)))
        fail_with(problems)


class PocStartTest(unittest.TestCase):
    def test_write_step_names_the_new_paths_and_wiring_matches(self):  # test 7
        text = read(skill_path("poc-start"))
        problems = []
        write = [ln for ln in text.splitlines() if re.match(r"^\d+\. \*\*Write\*\*", ln)]
        if not write:
            problems.append("poc-start has no numbered '**Write**' step")
        else:
            for need in ("poc-spec/POC.md", "poc-spec/LOG.md"):
                if need not in write[0]:
                    problems.append("poc-start write step does not name %s" % need)
        if WIRING not in text:
            problems.append("poc-start lacks the wiring block verbatim")
        if NO_OVERWRITE not in text:
            problems.append("poc-start lacks the never-overwrite sentence verbatim")
        if "write the success check from poc-spec/POC.md" not in text:
            problems.append("poc-start verify.sh stub does not point at poc-spec/POC.md")
        fail_with(problems)


class PackagerWarningTest(unittest.TestCase):
    def test_packager_has_the_warning_and_its_limits(self):  # test 8
        text = read(agent_path("packager"))
        problems = []
        for label, snippet in (("new-layout warning", WARNING_NEW), ("older-layout warning", WARNING_OLD)):
            if snippet not in text:
                problems.append("packager lacks the %s verbatim" % label)
        for need in LS_FILES_COMMANDS + ("Repo visibility:", "Deal:", "SUMMARY.md"):
            if need not in text:
                problems.append("packager does not mention %r" % need)
        if not re.search(r"never[^.\n]*\.gitignore", text, re.I):
            problems.append("packager does not say it never edits .gitignore")
        fail_with(problems)


class DocsAgreeTest(unittest.TestCase):
    def test_readme_and_workflow_use_the_new_paths(self):  # test 9
        problems = []
        for path in (ROOT / "README.md", ROOT / "docs" / "workflow.md"):
            for lineno, line in enumerate(read(path).splitlines(), 1):
                for m in DOC_NAME.finditer(line):
                    if line[:m.start()].endswith("poc-spec/") or "older layout" in line.lower():
                        continue
                    problems.append("%s:%d %s.md without poc-spec/ and not an 'older layout' line" % (rel(path), lineno, m.group(1)))
        fail_with(problems)


if __name__ == "__main__":
    unittest.main()
