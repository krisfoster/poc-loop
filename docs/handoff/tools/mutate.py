#!/usr/bin/env python3
"""Mutation check for the hand-off state tests (plan 1.10 and 3.1).

Copies the repo (without .git) once per row, applies one deliberate wrong edit to a skill or doc,
runs the whole test suite in the copy, and checks that at least one test fails. The negative
control (a harmless edit) must fail nothing. A target that is not found counts as wrong. No model runs.

Run: python3 docs/handoff/tools/mutate.py
Exit 0 only if every row behaves.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CP = "skills/poc-checkpoint/SKILL.md"
HELP = "skills/poc-help/SKILL.md"
LOG = "skills/poc-log/SKILL.md"
START = "skills/poc-start/SKILL.md"
WF = "docs/workflow.md"
CHECKER = "scripts/check-prereqs"
TIME = "skills/poc-log/scripts/time_check.py"


def move_line_before(text, line_start, before_start):
    lines = text.split("\n")
    i = next(n for n, l in enumerate(lines) if l.startswith(line_start))
    moved = lines.pop(i)
    j = next(n for n, l in enumerate(lines) if l.startswith(before_start))
    lines.insert(j, moved)
    return "\n".join(lines)


def drop_line(text, line_start):
    return "\n".join(l for l in text.split("\n") if not l.startswith(line_start))


# (name, file, old, new) for a text replacement, or (name, file, function) for a structural edit.
ROWS = [
    ("drop the read-back step", CP, lambda t: drop_line(t, "9. **Read back.**")),
    ("make the closing entry conditional", CP, "to `<docs>/LOG.md` for every outcome:",
     "to `<docs>/LOG.md` if the last entry is older than this session's work:"),
    ("/clear before the read-back", CP, "with the `State:` line from the State step as its last line.",
     "with the `State:` line from the State step as its last line, then suggest `/clear`."),
    ("Next before the read-back", CP, lambda t: move_line_before(t, "10. **Next.**", "9. **Read back.**")),
    ("Next before the POC.md and SUMMARY.md step", CP,
     lambda t: move_line_before(t, "10. **Next.**", "8. **Pivot, harden, stop.**")),
    ("hand-off written after the entry", CP,
     lambda t: move_line_before(t, "7. **Closing entry.**", "6. **Hand-off file.**")),
    ("drop the read-back failure rule", CP, "say so, print no `/clear`, and end with", "say so, and end with"),
    ("worktree path added to State", CP, "or `detached <short sha>`, followed by",
     "or `detached <short sha>` or `<worktree path>`, followed by"),
    ("worktree paths written", CP, "printed, never written to the file", "printed and written to the file"),
    ("topic restriction removed", CP, " and it must then match `[a-z0-9-]+`", ""),
    ("bare pause writes a file", CP, "With no topic, pause writes the entry and State and no hand-off file. ", ""),
    ("hand-off file overwritten", CP, "An existing file is never overwritten.", "An existing file is overwritten."),
    ("older layout writes a hand-off", CP,
     "in the older root layout no hand-off file is written (that would create `poc-spec/`, which only "
     "`/spike-loop:poc-start` creates), and the user is told to migrate to get hand-off files.",
     "in the older root layout the hand-off file is written under `poc-spec/handoffs/` too."),
    ("pause dropped from the recommendation", CP, "recommend one of iterate, pivot, harden, stop or pause",
     "recommend one of iterate, pivot, harden or stop"),
    ("exclude . in the older layout", CP, "Exclusions, root layout: `POC.md` `LOG.md` `SUMMARY.md` `.claude`",
     "Exclusions, root layout: `.`"),
    ("no --no-optional-locks in the checkpoint", CP,
     '`git --no-optional-locks -C "<root>" branch --show-current`', '`git -C "<root>" branch --show-current`'),
    ("SUMMARY.md not excluded in poc-help", HELP,
     "Exclusions, `poc-spec` layout: `poc-spec` `.claude` `SUMMARY.md`", "Exclusions, `poc-spec` layout: `poc-spec` `.claude`"),
    ("merge-base dropped from poc-help", HELP,
     'stale when `git --no-optional-locks -C "<root>" merge-base --is-ancestor <recorded sha> HEAD` fails (a reset to before it, or a sha that does not exist), or when ', "stale when "),
    # Rows from the R.4 implementation review: each passed the tests before the clauses were pinned.
    ("merge-base fails flipped to succeeds", HELP, "merge-base --is-ancestor <recorded sha> HEAD` fails",
     "merge-base --is-ancestor <recorded sha> HEAD` succeeds"),
    ("log prints anything flipped to nothing", HELP, "<exclusions>` prints anything (a commit",
     "<exclusions>` prints nothing (a commit"),
    ("listed path rule flipped", HELP, "a listed path is no longer uncommitted", "a listed path is still uncommitted"),
    ("count rule deleted", HELP, "stale when the count of uncommitted paths differs from the recorded count, or ", "stale "),
    ("sha-only guard dropped", HELP, "Otherwise, when both are shas: stale", "Stale"),
    ("poc-help writes State", HELP, "7. **Next.** End with one line",
     "7. **Next.** First append a `- State:` line with the fresh values to `<docs>/LOG.md` with the Edit tool. End with one line"),
    ("poc-help read-only weakened", HELP, "Write nothing and run nothing that changes a file.",
     "Write nothing unless the State is stale, then record it again."),
    ("hand-off Read rule flipped", CP, "use the first whose Read fails as not found", "use the first whose Read succeeds"),
    ("exclude conversion dropped in poc-checkpoint", CP, ' As a pathspec each name becomes `":(exclude)<name>"` after `-- .`, written `<exclusions>` below.', " Written `<exclusions>` below."),
    ("exclude conversion dropped in poc-help", HELP, ', where `<exclusions>` is each name on the line for the layout as `":(exclude)<name>"`', ""),
    ("poc-log always writes State", LOG, "Never write a `State:` line", "Always write a `State:` line"),
    ("closing entry skips pause", CP, "for every outcome:", "for every outcome except pause:"),
    ("topic refuses nothing", CP, "Refuse anything else (a `.`, a `/`, an empty result) and ask the user for another topic.",
     "Refuse nothing: replace a `.` or `/` with `-`."),
    ("fresh row loops", HELP, "| `Resume:` and the `resume:` value | The `resume:` command |",
     "| `Resume:` and the `resume:` value | `/spike-loop:poc-checkpoint <Decision>` |"),
    ("most-recent fallback", HELP, "Read no other hand-off file: only the one `resume:` names.",
     "If `resume:` names no file, read the most recent file in `poc-spec/handoffs/`."),
    ("worktree filter dropped", CP, " Take only entries under `<main checkout>/.claude/worktrees/`, not the root's own worktree.", ""),
    ("first heading instead of last", HELP, "(the last `## ` heading)", "(the first `## ` heading)"),
    ("worktree path in the hand-off", CP, "files to read first, the next step.", "files to read first, each worktree path, the next step."),
    ("State not the last line", CP, "as its last line.", "as its first line, before the Decision."),
    ("read-back failure suggests /clear in Next", CP, "If the outcome was not confirmed:",
     "If the read-back failed: `/clear` and run it again. If the outcome was not confirmed:"),
    ("resume may name poc-help", CP, " The command is the next piece of work, never `/clear` or `/spike-loop:poc-help`: those belong in the `Next:` line", ""),
    ("checkpoint commits", CP, "Never use em dashes. Do not commit.", "Never use em dashes. Commit the log when done."),
    ("merge-base arguments swapped", HELP, "merge-base --is-ancestor <recorded sha> HEAD`",
     "merge-base --is-ancestor HEAD <recorded sha>`"),
    ("later-entry rule dropped", HELP,
     ", and a State line with any entry after it means \"State unknown\", as does no State line",
     ", and no State line means \"State unknown\""),
    ("newest-file fallback re-added", HELP, "Read no other hand-off file: only the one `resume:` names.",
     "If `resume:` names no file, read the newest file in `poc-spec/handoffs/`."),
    ("/clear in the stale row", HELP, "to record the state again.", "to record the state again, then `/clear`."),
    ("/clear in a poc-help Decision rule", HELP, "- `iterate`, `pivot` or `pause`: `/spike-loop:poc-checkpoint <Decision>`",
     "- `iterate`, `pivot` or `pause`: `/clear`, then `/spike-loop:poc-checkpoint <Decision>`"),
    ("/clear in a poc-log Next", LOG, "`iterate`: `/spike-loop:poc-checkpoint iterate`.",
     "`iterate`: `/clear` and start a fresh session."),
    ("poc-log writes State", LOG, "Never write a `State:` line: only `/spike-loop:poc-checkpoint` records the state.",
     "End the entry with a line `- State: <branch and commit>`."),
    ("State placeholder in the template", START, "- Later: <ideas parked, out of scope for now>",
     "- Later: <ideas parked, out of scope for now>\n- State: <>"),
    ("bare /clear in the workflow", WF, "use `/spike-loop:poc-debug`, or `/spike-loop:poc-checkpoint iterate` and then `/clear`.",
     "use `/spike-loop:poc-debug` or `/clear`."),
    # Prerequisites (docs/prereqs/spec.md, Tests 4)
    ("poc-log without its guard", LOG, lambda t: drop_line(t, "**Prerequisites.**")),
    ("poc-log does not check python3", LOG, "check-prereqs\" poc-log git python3:optional`", "check-prereqs\" poc-log git`"),
    ("packager does not check rsync", "agents/packager.md", "check-prereqs\" packager git rsync gitleaks:optional`",
     "check-prereqs\" packager git gitleaks:optional`"),
    ("agent guard without the skip", "agents/implementer.md",
     "Skip this if the command that started you, or your brief, says prerequisites were checked. Otherwise, before",
     "Before"),
    ("skill without the quoted checker rule", "skills/poc-verify/SKILL.md",
     '  - Bash(sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" *)\n', ""),
    ("checker passes a missing required tool", CHECKER, '  echo "prereqs: missing${missing}"\n  exit 1',
     '  echo "prereqs: missing${missing}"\n  exit 0'),
    ("checker accepts Python 3.0", CHECKER, ">= (3, 9)", ">= (3, 0)"),
    ("time check counts the template line", TIME, r'ENTRY_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})',
     r'ENTRY_RE = re.compile(r"^## (\S+)'),
    ("poc-log works out the time itself", LOG, "never work out elapsed time or count entries yourself.",
     "then work out elapsed time and count entries yourself."),
    ("over-timebox Next keyed on the model again", LOG, "if the time check printed `timebox: over` and",
     "if the timebox looks exceeded and"),
]
CONTROL = ("negative control: a harmless sentence", CP, "2. **Summary.** Print a summary",
           "2. **Summary.** Be brief. Print a summary")


def apply(root, row):
    name, rel = row[0], row[1]
    path = root / rel
    text = path.read_text(encoding="utf-8")
    if callable(row[2]):
        new = row[2](text)
    else:
        if text.count(row[2]) != 1:
            return False
        new = text.replace(row[2], row[3])
    if new == text:
        return False
    path.write_text(new, encoding="utf-8")
    return True


def run_suite(root):
    r = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=str(root),
                       capture_output=True, text=True, timeout=300)
    failed = re.findall(r"^(?:FAIL|ERROR): (\S+)", r.stderr, re.M)
    return r.returncode, failed


def main():
    tmp = Path(tempfile.mkdtemp(prefix="handoff-mutate-"))
    wrong = 0
    try:
        for row in ROWS + [CONTROL]:
            root = tmp / "copy"
            if root.exists():
                shutil.rmtree(str(root))
            shutil.copytree(str(REPO), str(root), ignore=shutil.ignore_patterns(".git", "__pycache__", ".env"))
            # The eval harness tests list files with git, so the copy must be a repository.
            genv = {"PATH": os.environ.get("PATH", ""), "HOME": str(tmp), "GIT_CONFIG_NOSYSTEM": "1",
                    "GIT_CONFIG_GLOBAL": os.devnull}
            for args in (["init", "-q"], ["add", "-A"]):
                subprocess.run(["git", *args], cwd=str(root), env=genv, capture_output=True, check=True)
            if not apply(root, row):
                print("NOT FOUND  %s" % row[0])
                wrong += 1
                continue
            rc, failed = run_suite(root)
            if row is CONTROL:
                ok = rc == 0
                print("%s  %s" % ("ok      " if ok else "WRONG   ", row[0]) + ("" if ok else " %s" % failed))
            else:
                ok = rc != 0 and bool(failed)
                print("%s  %s: %s" % ("caught  " if ok else "MISSED  ", row[0], ", ".join(failed[:3]) or "nothing failed"))
            wrong += not ok
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    print("%d rows, %d wrong" % (len(ROWS) + 1, wrong))
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
