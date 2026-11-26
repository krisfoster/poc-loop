---
name: poc-help
description: Shows the Spike Loop commands, how to use one of them, and where the current PoC stands with the next command to run. Use when the user types /poc-help, optionally with a command name such as verify.
disable-model-invocation: true
model: haiku
effort: low
argument-hint: "[command name, for example verify]"
---
# poc-help

Arguments: "$ARGUMENTS". Never use em dashes. This command only reads and prints. Write nothing and run nothing that changes a file.

## The commands

| Command | Use it to | Then |
|---|---|---|
| `/spike-loop:poc-start` | Interview, then write `POC.md`, `LOG.md` and a failing `verify.sh` stub | `poc-research` if the question needs facts, else build and `poc-verify` |
| `/spike-loop:poc-research <question>` | Answer a factual question from primary sources, with dates and versions | Build on it, or `poc-log` if it changes an assumption |
| `/spike-loop:poc-sources [setup, status, refresh, add <note>]` | One-time setup and later updates of the internal sources the researcher may read | Restart Claude Code, then `poc-research` |
| `/spike-loop:poc-build <task> \| done when <condition>` | Hand one bounded chunk of an approved plan to the implementer | `poc-verify` |
| `/spike-loop:poc-verify [path or focus]` | Run `verify.sh` or the project's own check, get pass or fail with only the relevant errors | `poc-log` on a pass, `poc-debug` after two failed fixes |
| `/spike-loop:poc-debug <command, error, what you tried>` | Find the root cause of a failure that survived a fix | Apply the fix, then `poc-verify` |
| `/spike-loop:poc-review [path, branch or focus]` | Independent review of a diff or PoC | Fix findings, then `poc-harden` |
| `/spike-loop:poc-package [path]` | Write README and `.env.example`, run the clean-clone test and secret scan | `poc-checkpoint harden` |
| `/spike-loop:poc-harden [path] [full]` | Review, package and final gate in one go | `poc-checkpoint harden` |
| `/spike-loop:poc-log [what you tried and learned]` | Append a dated entry to `LOG.md` and see time against the timebox | Decide: iterate, pivot, harden or stop |
| `/spike-loop:poc-checkpoint [iterate, pivot, harden, stop]` | End-of-session summary, record the decision, write `SUMMARY.md` on stop or harden | `poc-harden`, a fresh session, or done |
| `/spike-loop:poc-help [command]` | This help | The command it recommends |

Every command ends with one line that starts with `Next:` and names the command to run next.

## With a command name

If the arguments name a command (`verify`, `poc-verify` or `/spike-loop:poc-verify` all mean the same), read `${CLAUDE_SKILL_DIR}/../poc-<name>/SKILL.md` and print: the command line with its `argument-hint`, what it does and when to use it in at most two short sentences taken from its `description`, and its row from the table above. If no such file exists, say the name is not a command and print the table. Then stop, ending with `Next:` set to that command's "Then" cell.

## With no arguments

1. Print the table above.
2. **Where you are.** Look for `POC.md`, `LOG.md` and `SUMMARY.md` in the current directory. If `POC.md` is missing, print `No PoC in this directory.` and end with `Next: /spike-loop:poc-start`.
3. Otherwise read the header line of `POC.md` (tier, `Started:`, timebox), its `## Question` line, and the last 25 lines of `LOG.md`. Print at most 5 lines: the question, the tier, elapsed wall-clock time since `Started:` against the timebox (use `date` for the arithmetic, and say plainly if it is over, without nagging), the last Decision in `LOG.md`, and whether `SUMMARY.md` exists.
4. End with one line starting `Next:`, chosen by the last Decision:
   - No entry beyond "PoC started", or `none yet`: `/spike-loop:poc-research <question>` if the question depends on facts not yet confirmed, otherwise build, then `/spike-loop:poc-verify` when there is something to check. If over the timebox, decide now with `/spike-loop:poc-checkpoint`.
   - `iterate`: `/clear`, then work on the last "Next question" in `LOG.md`.
   - `pivot`: edit the assumptions in `POC.md`, then `/clear`.
   - `harden`: `/spike-loop:poc-harden` (add `full` for tier 2). If `SUMMARY.md` already exists, the PoC is hardened and nothing more is needed unless you iterate.
   - `stop`: `/spike-loop:poc-checkpoint stop` if `SUMMARY.md` is missing, otherwise the PoC is closed.
