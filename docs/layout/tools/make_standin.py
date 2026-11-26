#!/usr/bin/env python3
"""Build a compliant stand-in of the plugin tree for the Gate 1 check (plan task 1.7 and Gate 1).

Copies SRC to DST and applies the layout rules mechanically: Rule A and Rule B appended where the spec says,
bare document names rewritten, vague phrases replaced, the warning and wiring text added. It is NOT the
implementation (Phase 2 does that, by hand). Its job is to prove the tests in tests/test_docs_layout.py can pass,
so the mutation check in mutate.py means something.

Usage: python3 docs/layout/tools/make_standin.py <src root> <dst root>
"""
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "tests"))
import test_docs_layout as T  # noqa: E402  (constants only)

POC_START = "skills/poc-start/SKILL.md"
POC_HELP = "skills/poc-help/SKILL.md"
VAGUE = [
    ("(default: current repo)", "(default: the repo root)"),
    ("in the current repo root", "at the repo root"),
    ("in the current repo", "at the repo root"),
    ("current working directory", "repo root"),
    ("the current git repo", "the repo root"),
    ("in the current directory", "at the repo root"),
    ("No PoC in this directory.", "No PoC found."),
    ("on the current project", "on the project at the repo root"),
    ("plus the current repo", "plus the repo at its root"),
]
NAME = re.compile(r"(?<![\w/>])(POC|LOG)\.md")


def rewrite_names(text, prefix_for_line):
    """Rewrite bare document names. prefix_for_line(line) gives the prefix for that line."""
    out = []
    for line in text.splitlines(keepends=True):
        if re.match(r"^### (?:POC|LOG)\.md\s*$", line):
            out.append(line)
        else:
            prefix = prefix_for_line(line)
            out.append(NAME.sub(lambda m: "%s%s.md" % (prefix, m.group(1)), line))
    return "".join(out)


def prefix_rule(rel):
    if rel == POC_START:
        return lambda line: "poc-spec/"
    if rel == POC_HELP:  # poc-spec/ only on table rows, <docs>/ in the steps
        return lambda line: "poc-spec/" if line.lstrip().startswith("|") else "<docs>/"
    return lambda line: "<docs>/"


def main(src, dst):
    src, dst = Path(src), Path(dst)
    if dst.exists():
        shutil.rmtree(str(dst))
    shutil.copytree(str(src), str(dst), ignore=shutil.ignore_patterns(".git", "__pycache__", "evals"))
    for path in sorted(dst.glob("skills/*/SKILL.md")) + sorted(dst.glob("agents/*.md")):
        rel = path.relative_to(dst).as_posix()
        text = path.read_text(encoding="utf-8")
        for a, b in VAGUE:
            text = text.replace(a, b)
        text = rewrite_names(text, prefix_rule(rel))
        text = text.rstrip("\n") + "\n"
        name = path.parent.name if path.name == "SKILL.md" else path.stem
        is_agent = rel.startswith("agents/")
        if (is_agent) or name in T.RULE_A_SKILLS:
            text += "\n" + T.RULE_A + "\n"
        if (is_agent and name in T.RULE_B_AGENTS) or (not is_agent and name in T.RULE_B_SKILLS):
            text += "\n" + T.RULE_B + "\n"
        if rel == "skills/poc-start/SKILL.md":
            text += "\n" + T.WIRING + "\n" + T.NO_OVERWRITE + "\n"
        if rel == "skills/poc-help/SKILL.md":
            text += "\n" + T.LEGACY_NOTE + "\n"
        if rel == "agents/packager.md":
            text += ("\nWarning check: " + ", ".join("`%s`" % c for c in T.LS_FILES_COMMANDS) + ". "
                     "Read `Repo visibility:` and `Deal:` from the header. Never edit `.gitignore`. Not for SUMMARY.md.\n"
                     + T.WARNING_NEW + "\n" + T.WARNING_OLD + "\n")
        path.write_text(text, encoding="utf-8")
    for rel in ("README.md", "docs/workflow.md"):
        p = dst / rel
        p.write_text(rewrite_names(p.read_text(encoding="utf-8"), lambda line: "poc-spec/"), encoding="utf-8")
    print("stand-in written to %s" % dst)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
