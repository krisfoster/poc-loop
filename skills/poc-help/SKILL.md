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

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that needs the working directory (it uses a relative path or runs a script there) as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run any other command as it is (such as `date`, a script by its absolute path, or `chmod` or `tail` given a `<root>/<path>`), unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full, and use them to check, read and list files. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

**Docs folder.** Check these four paths, relative to the repo root, by reading each with the Read tool (it needs no `cd`, a missing file is just an error, and Glob can skip gitignored files, which `poc-spec/` often is): `poc-spec/POC.md`, `poc-spec/LOG.md`, `POC.md`, `LOG.md`. If files exist only under `poc-spec/`, the docs folder `<docs>` is `poc-spec`. If they exist only at the root, `<docs>` is `.` (an older PoC, use it as is). If files exist in both places, stop, say the PoC is half-migrated, name the files, and ask which to keep (an agent reports this and stops). If none exist, follow the command's own step. `<docs>/POC.md` means `poc-spec/POC.md` or `POC.md`, and likewise `<docs>/LOG.md`.

## The commands

| Command | Use it to | Then |
|---|---|---|
| `/spike-loop:poc-start` | Interview, then write `poc-spec/POC.md`, `poc-spec/LOG.md` and a failing `verify.sh` stub | `poc-research` if the question needs facts, else build and `poc-verify` |
| `/spike-loop:poc-research <question>` | Answer a factual question from primary sources, with dates and versions | Build on it, or `poc-log` if it changes an assumption |
| `/spike-loop:poc-sources [setup, status, refresh, add <note>]` | One-time setup and later updates of the internal sources the researcher may read | Restart Claude Code, then `poc-research` |
| `/spike-loop:poc-build <task> \| done when <condition>` | Hand one bounded chunk of an approved plan to the implementer in a worktree | merge its branch, then `poc-verify` |
| `/spike-loop:poc-verify [path or focus]` | Run `verify.sh` or the project's own check, get pass or fail with only the relevant errors | `poc-log` on a pass, `poc-debug` after two failed fixes |
| `/spike-loop:poc-debug <command, error, what you tried>` | Find the root cause of a failure that survived a fix | Apply the fix, then `poc-verify` |
| `/spike-loop:poc-review [path, branch or focus]` | Independent review of a diff or PoC | Fix findings, then `poc-harden` |
| `/spike-loop:poc-package [path]` | Write README and `.env.example`, run the clean-clone test and secret scan | `poc-checkpoint harden` |
| `/spike-loop:poc-harden [path] [full]` | Review, package and final gate in one go | `poc-checkpoint harden` |
| `/spike-loop:poc-log [what you tried and learned]` | Append a dated entry to the log (`poc-spec/LOG.md`) and see time against the timebox | Decide: iterate, pivot, harden, stop or pause |
| `/spike-loop:poc-checkpoint [iterate, pivot, harden, stop, pause [topic]]` | End-of-session summary, record the decision with a State line, write a hand-off on pause with a topic and `SUMMARY.md` on stop or harden | `poc-help` in a fresh session, `poc-harden`, or done |
| `/spike-loop:poc-help [command]` | This help | The command it recommends |

Every command ends with one line that starts with `Next:` and names the command to run next.

## With a command name

If the arguments name a command (`verify`, `poc-verify` or `/spike-loop:poc-verify` all mean the same), find its row in the table above. The paths and docs-folder rules above are for the no-arguments mode only. Do not read any other file: the table holds everything needed. Print the command with its arguments (the first cell), what it does and when to use it in at most two short sentences made from the "Use it to" cell, and the "Then" cell. If no row matches, say the name is not a command and print the table. Then stop, ending with `Next:` set to that command's "Then" cell.

## With no arguments

1. Print the table above.
2. **Where you are.** Resolve the docs folder by the docs-folder rule above and look for `<docs>/POC.md`, `<docs>/LOG.md` and `SUMMARY.md` (at the repo root). If the rule stops on a half-migrated PoC, print what it says and end with `Next:` naming the fix: keep one layout, then run `/spike-loop:poc-help` again. If no PoC file exists, print `No PoC found.` and end with `Next: /spike-loop:poc-start`. If the docs folder is the repo root (the older layout), print this line, and change nothing: `Older layout: POC.md and LOG.md are at the repo root. It works as is. To move them: mkdir poc-spec && git mv POC.md LOG.md poc-spec/ (use mv if they are untracked), then update CLAUDE.md.` Then continue with step 3.
3. Otherwise read the header line of `<docs>/POC.md` (tier, `Started:`, timebox), its `## Question` line, and the last 25 lines of `<docs>/LOG.md`. Print at most 5 lines: the question, the tier, elapsed wall-clock time since `Started:` against the timebox (use `date` for the arithmetic, and say plainly if it is over, without nagging), the last Decision in `<docs>/LOG.md`, and whether `SUMMARY.md` exists.
4. **State.** Only a `State:` line in the last dated entry (the last `## ` heading) of `<docs>/LOG.md` counts. A `- State:` line in an earlier entry is ignored, and a State line with any entry after it means "State unknown", as does no State line. Its fields are `branch`, `at`, `uncommitted`, `unmerged worktrees`, `waiting on you` and `resume`, separated by `; `. An `uncommitted` value is `none`, `not a git repo`, or `<n> paths: ` followed by the listed paths.
5. **Staleness.** Only when the last entry has a State line. Gather the same values now with read-only git calls from the repo root, and compare:
   - `git --no-optional-locks -C "<root>" rev-parse --is-inside-work-tree`. If it fails or does not print `true`, the current branch, at and uncommitted are `not a git repo`: skip the other calls.
   - `git --no-optional-locks -C "<root>" branch --show-current` (`detached` when it prints nothing), and `git --no-optional-locks -C "<root>" rev-parse --short HEAD` (`no commits` when it fails).
   - `git --no-optional-locks -C "<root>" status --porcelain -- . <exclusions>`, where `<exclusions>` is each name on the line for the layout as `":(exclude)<name>"`. The path is each line after its first three characters.

   Exclusions, `poc-spec` layout: `poc-spec` `.claude` `SUMMARY.md`
   Exclusions, root layout: `POC.md` `LOG.md` `SUMMARY.md` `.claude`

   It is stale when any of these holds:
   - The branch differs.
   - The commit: if either at is `no commits` or `not a git repo`, stale when the two differ. Otherwise, when both are shas: stale when `git --no-optional-locks -C "<root>" merge-base --is-ancestor <recorded sha> HEAD` fails (a reset to before it, or a sha that does not exist), or when `git --no-optional-locks -C "<root>" log --oneline <recorded sha>..HEAD -- . <exclusions>` prints anything (a commit that only touches the excluded files does not count).
   - Uncommitted, unless the repo is `not a git repo`: stale when the count of uncommitted paths differs from the recorded count, or when a listed path is no longer uncommitted.

   Changes to `<docs>/LOG.md`, `SUMMARY.md` and `.claude/` never make it stale. If stale, print `State is from <entry date>; it may be stale: <what differs>`.
6. **Hand-off.** If `resume:` names a file under `poc-spec/handoffs/`, read that one file with the Read tool and summarise it in at most 5 lines, marked as possibly stale when the State is stale. Read no other hand-off file: only the one `resume:` names.
7. **Next.** End with one line starting `Next:`, from this table:

| Last entry | Prints | `Next:` |
|---|---|---|
| State, fresh | `Resume:` and the `resume:` value | The `resume:` command |
| State, stale | `State is from <entry date>; it may be stale: <what differs>` | iterate, pivot: `/spike-loop:poc-checkpoint <Decision>` to record the state again. pause: `/spike-loop:poc-checkpoint pause <topic>` with the topic taken from the hand-off file name without the date (and without a `-<n>` ending only when the file without it also exists, checked with Read), or `/spike-loop:poc-checkpoint pause` when there is no file. harden, stop: as in the list below |
| No State, or a State line with any entry after it | `State unknown` | By the last Decision, as in the list below |

   By the last Decision:
   - No entry beyond "PoC started", or `none yet`: `/spike-loop:poc-research <question>` if the question depends on facts not yet confirmed, otherwise build, then `/spike-loop:poc-verify` when there is something to check. If over the timebox, decide now with `/spike-loop:poc-checkpoint`.
   - `iterate`, `pivot` or `pause`: `/spike-loop:poc-checkpoint <Decision>`, which records the state and then names the fresh-session step.
   - `harden`: `/spike-loop:poc-harden` (add `full` for tier 2). If `SUMMARY.md` already exists, the PoC is hardened and nothing more is needed unless you iterate.
   - `stop`: `/spike-loop:poc-checkpoint stop` if `SUMMARY.md` is missing, otherwise the PoC is closed.
