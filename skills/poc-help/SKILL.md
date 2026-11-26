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

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that uses a relative path or runs a script as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run a command that needs no directory, such as `date` or a script under `${CLAUDE_SKILL_DIR}`, as it is, unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

**Docs folder.** Check these four paths, relative to the repo root, with the file tools (Glob or Read, which need no `cd`): `poc-spec/POC.md`, `poc-spec/LOG.md`, `POC.md`, `LOG.md`. If files exist only under `poc-spec/`, the docs folder `<docs>` is `poc-spec`. If they exist only at the root, `<docs>` is `.` (an older PoC, use it as is). If files exist in both places, stop, say the PoC is half-migrated, name the files, and ask which to keep (an agent reports this and stops). If none exist, follow the command's own step. `<docs>/POC.md` means `poc-spec/POC.md` or `POC.md`, and likewise `<docs>/LOG.md`.

## The commands

| Command | Use it to | Then |
|---|---|---|
| `/spike-loop:poc-start` | Interview, then write `poc-spec/POC.md`, `poc-spec/LOG.md` and a failing `verify.sh` stub | `poc-research` if the question needs facts, else build and `poc-verify` |
| `/spike-loop:poc-research <question>` | Answer a factual question from primary sources, with dates and versions | Build on it, or `poc-log` if it changes an assumption |
| `/spike-loop:poc-sources [setup, status, refresh, add <note>]` | One-time setup and later updates of the internal sources the researcher may read | Restart Claude Code, then `poc-research` |
| `/spike-loop:poc-build <task> \| done when <condition>` | Hand one bounded chunk of an approved plan to the implementer | `poc-verify` |
| `/spike-loop:poc-verify [path or focus]` | Run `verify.sh` or the project's own check, get pass or fail with only the relevant errors | `poc-log` on a pass, `poc-debug` after two failed fixes |
| `/spike-loop:poc-debug <command, error, what you tried>` | Find the root cause of a failure that survived a fix | Apply the fix, then `poc-verify` |
| `/spike-loop:poc-review [path, branch or focus]` | Independent review of a diff or PoC | Fix findings, then `poc-harden` |
| `/spike-loop:poc-package [path]` | Write README and `.env.example`, run the clean-clone test and secret scan | `poc-checkpoint harden` |
| `/spike-loop:poc-harden [path] [full]` | Review, package and final gate in one go | `poc-checkpoint harden` |
| `/spike-loop:poc-log [what you tried and learned]` | Append a dated entry to the log (`poc-spec/LOG.md`) and see time against the timebox | Decide: iterate, pivot, harden or stop |
| `/spike-loop:poc-checkpoint [iterate, pivot, harden, stop]` | End-of-session summary, record the decision, write `SUMMARY.md` on stop or harden | `poc-harden`, a fresh session, or done |
| `/spike-loop:poc-help [command]` | This help | The command it recommends |

Every command ends with one line that starts with `Next:` and names the command to run next.

## With a command name

If the arguments name a command (`verify`, `poc-verify` or `/spike-loop:poc-verify` all mean the same), find its row in the table above. Do not read any other file: the table holds everything needed. Print the command with its arguments (the first cell), what it does and when to use it in at most two short sentences made from the "Use it to" cell, and the "Then" cell. If no row matches, say the name is not a command and print the table. Then stop, ending with `Next:` set to that command's "Then" cell.

## With no arguments

1. Print the table above.
2. **Where you are.** Resolve the docs folder by the docs-folder rule above and look for `<docs>/POC.md`, `<docs>/LOG.md` and `SUMMARY.md` (at the repo root). If the rule stops on a half-migrated PoC, print what it says and end with `Next:` naming the fix: keep one layout, then run `/spike-loop:poc-help` again. If no PoC file exists, print `No PoC found.` and end with `Next: /spike-loop:poc-start`. If the docs folder is the repo root (the older layout), print this line, and change nothing: `Older layout: POC.md and LOG.md are at the repo root. It works as is. To move them: mkdir poc-spec && git mv POC.md LOG.md poc-spec/ (use mv if they are untracked), then update CLAUDE.md.` Then continue with step 3.
3. Otherwise read the header line of `<docs>/POC.md` (tier, `Started:`, timebox), its `## Question` line, and the last 25 lines of `<docs>/LOG.md`. Print at most 5 lines: the question, the tier, elapsed wall-clock time since `Started:` against the timebox (use `date` for the arithmetic, and say plainly if it is over, without nagging), the last Decision in `<docs>/LOG.md`, and whether `SUMMARY.md` exists.
4. End with one line starting `Next:`, chosen by the last Decision:
   - No entry beyond "PoC started", or `none yet`: `/spike-loop:poc-research <question>` if the question depends on facts not yet confirmed, otherwise build, then `/spike-loop:poc-verify` when there is something to check. If over the timebox, decide now with `/spike-loop:poc-checkpoint`.
   - `iterate`: `/clear`, then work on the last "Next question" in `<docs>/LOG.md`.
   - `pivot`: edit the assumptions in `<docs>/POC.md`, then `/clear`.
   - `harden`: `/spike-loop:poc-harden` (add `full` for tier 2). If `SUMMARY.md` already exists, the PoC is hardened and nothing more is needed unless you iterate.
   - `stop`: `/spike-loop:poc-checkpoint stop` if `SUMMARY.md` is missing, otherwise the PoC is closed.
