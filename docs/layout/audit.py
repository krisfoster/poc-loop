#!/usr/bin/env python3
"""Path audit for docs/layout (plan task 0.4, re-run in task 3.1).

Lists every mention of the PoC document names, the root-assuming commands and the vague "here" phrases
in the frontmatter and body of each skill, agent and the two user-facing docs.

Run from anywhere:  python3 docs/layout/audit.py [--lines]
Standard library only. Reads files, writes nothing.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FILES = (
    sorted(ROOT.glob("skills/*/SKILL.md"))
    + sorted(ROOT.glob("agents/*.md"))
    + [ROOT / "README.md", ROOT / "docs" / "workflow.md"]
)

PATTERNS = [
    ("POC.md", r"(?<![\w])POC\.md"),
    ("LOG.md", r"(?<![\w])LOG\.md"),
    ("SUMMARY.md", r"(?<![\w])SUMMARY\.md"),
    ("verify.sh", r"verify\.sh"),
    ("./", r"(?<![\w.])\./"),
    ("gitleaks dir .", r"gitleaks dir \."),
    ("repo path", r"repo path"),
    ("vague base", r"current (?:working )?director(?:y|ies)|current (?:git )?repo\b|current project|this directory|\bcwd\b|\bpwd\b|\$PWD"),
]


def split_frontmatter(lines):
    """Return the number of frontmatter lines (0 if there is none)."""
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return i + 1
    return 0


def main(argv):
    show_lines = "--lines" in argv
    totals = {name: 0 for name, _ in PATTERNS}
    print("file | " + " | ".join(name for name, _ in PATTERNS))
    detail = []
    for path in FILES:
        if not path.is_file():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        fm = split_frontmatter(lines)
        counts = {}
        for name, pat in PATTERNS:
            flags = re.I if name == "vague base" else 0  # test 4 is case-insensitive too
            hits = [i for i, line in enumerate(lines, 1) if re.search(pat, line, flags)]
            counts[name] = len(hits)
            totals[name] += len(hits)
            for i in hits:
                where = "fm" if i <= fm else "body"
                detail.append("%s:%d [%s] %s: %s" % (path.relative_to(ROOT), i, where, name, lines[i - 1].strip()[:110]))
        if any(counts.values()):
            print("%s | %s" % (path.relative_to(ROOT), " | ".join(str(counts[n]) for n, _ in PATTERNS)))
    print("TOTAL | " + " | ".join(str(totals[n]) for n, _ in PATTERNS))
    print("(counts are lines that match, not total matches)")
    if show_lines:
        print()
        print("\n".join(detail))


if __name__ == "__main__":
    main(sys.argv[1:])
