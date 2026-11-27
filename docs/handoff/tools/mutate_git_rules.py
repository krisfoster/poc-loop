"""Mutation check for check_git_rules.py: each row restores an earlier or broken rule in a copy
of the script, and the copy must fail at least one check. No model runs.

Run: python3 docs/handoff/tools/mutate_git_rules.py
Exit 0 when every mutation is caught.
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "check_git_rules.py")

MUTATIONS = [
    ("older layout excludes '.'",
     '"old": ["POC.md", "LOG.md", "SUMMARY.md", ".claude"]', '"old": ["."]'),
    ("SUMMARY.md not excluded",
     '"new": ["poc-spec", ".claude", "SUMMARY.md"]', '"new": ["poc-spec", ".claude"]'),
    (".claude/ not excluded from the log comparison",
     'elif git(root, "log", "--oneline", "%s..HEAD" % rec_at, *pathspec(layout))',
     'elif git(root, "log", "--oneline", "%s..HEAD" % rec_at, "--", ".", ":(exclude)poc-spec", '
     '":(exclude)POC.md", ":(exclude)LOG.md")'),
    ("no exclusions on status",
     'git(root, "status", "--porcelain", *pathspec(layout))', 'git(root, "status", "--porcelain")'),
    ("no ancestor check",
     'if rc != 0:\n            reasons.append("recorded commit not in history")\n        elif',
     'if False:\n            pass\n        elif'),
    ("ancestor arguments swapped",
     '"merge-base", "--is-ancestor", rec_at, "HEAD"', '"merge-base", "--is-ancestor", "HEAD", rec_at'),
    ("no count in the uncommitted comparison",
     'if count != len(now_paths) or any', 'if any'),
    ("quoted names listed",
     "listable = [p for p in paths if not p.startswith('\"')][:LISTED]", "listable = paths[:LISTED]"),
    ("worktrees: commits only",
     "if commits or dirty:", "if commits:"),
    ("worktrees: base is the root, not the main checkout",
     'main = os.path.realpath(entries[0]["path"])', "main = os.path.realpath(root)"),
    ("worktrees: the root's own worktree listed",
     "if not p.startswith(under) or p == me:", "if not p.startswith(under):"),
    ("no --no-optional-locks",
     '["git", "--no-optional-locks", "-C", cwd_root, *args]', '["git", "-C", cwd_root, *args]'),
    ("a command the spec does not write",
     '"merge-base --is-ancestor <recorded sha> HEAD",', '"merge-base --is-ancestor HEAD <recorded sha>",'),
]


def main():
    src = open(SRC, encoding="utf-8").read()
    tmp = tempfile.mkdtemp(prefix="handoff-mut-")
    missed = 0
    try:
        for i, (name, old, new) in enumerate(MUTATIONS):
            if src.count(old) != 1:
                print("STALE  %s (the text to mutate is not in the script once)" % name)
                missed += 1
                continue
            copy = os.path.join(HERE, ".mut_%d.py" % i)  # beside the original, so SPEC resolves
            with open(copy, "w", encoding="utf-8") as fh:
                fh.write(src.replace(old, new))
            try:
                r = subprocess.run([sys.executable, copy, "--work", os.path.join(tmp, str(i))],
                                   capture_output=True, text=True)
            finally:
                os.remove(copy)
            fails = sum(1 for l in r.stdout.splitlines() if l.startswith("FAIL"))
            ok = r.returncode != 0 and fails > 0
            print("%s  %s (%d failing)" % ("caught" if ok else "MISSED", name, fails))
            missed += not ok
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("%d mutations, %d missed" % (len(MUTATIONS), missed))
    return 1 if missed else 0


if __name__ == "__main__":
    sys.exit(main())
