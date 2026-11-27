---
name: poc-checkpoint
description: End-of-session summary for a PoC: what was established, what is open, and the next question. Records the outcome with a State line a fresh session can resume from, writes a hand-off file on pause with a topic, and writes a short SUMMARY.md on a stop or harden decision. Use when the user types /poc-checkpoint.
disable-model-invocation: true
model: sonnet
effort: low
argument-hint: "[iterate | pivot | harden | stop | pause [topic]]"
allowed-tools:
  - Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs *)
  - Bash(sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" *)
---
# poc-checkpoint

Outcome from the user: "$ARGUMENTS". Never use em dashes. Do not commit.

**Prerequisites.** Before anything else, run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" poc-checkpoint git` as a command on its own, never joined to another with `;` or `&&`, and read its output. If the last line is `prereqs: missing ...`, print each `MISSING:` line as it is, change nothing, and end with `Next: install what is missing, then run /spike-loop:poc-checkpoint again`. Print any `skipped:` line and leave out the step that needs that tool. If the check cannot run (refused, not found, no POSIX shell, or a `prereqs: usage error` line), say so in one line and continue: a command that needs a missing tool will fail with its own error. This check covers any agent this command starts: when you brief an agent, say "prerequisites checked".

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that needs the working directory (it uses a relative path or runs a script there) as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run any other command as it is (such as `date`, a script by its absolute path, or `chmod` or `tail` given a `<root>/<path>`), unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full, and use them to check, read and list files. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

**Docs folder.** Check these four paths, relative to the repo root, by reading each with the Read tool (it needs no `cd`, a missing file is just an error, and Glob can skip gitignored files, which `poc-spec/` often is): `poc-spec/POC.md`, `poc-spec/LOG.md`, `POC.md`, `LOG.md`. If files exist only under `poc-spec/`, the docs folder `<docs>` is `poc-spec`. If they exist only at the root, `<docs>` is `.` (an older PoC, use it as is). If files exist in both places, stop, say the PoC is half-migrated, name the files, and ask which to keep (an agent reports this and stops). If none exist, follow the command's own step. `<docs>/POC.md` means `poc-spec/POC.md` or `POC.md`, and likewise `<docs>/LOG.md`.

**State line.** One line, the last line of the closing entry, so the "last 40 lines" read of `<docs>/LOG.md` at session start includes it. Six fields in this order, separated by `; `:

```
- State: branch: <branch>; at: <at>; uncommitted: <uncommitted>; unmerged worktrees: <worktrees>; waiting on you: <waiting>; resume: <resume>
```

| Field | Values |
|---|---|
| `branch` | the current branch name, or `detached`, or `not a git repo` |
| `at` | the short sha of HEAD, or `no commits`, or `not a git repo` |
| `uncommitted` | `none`, or `<n> paths: <p1>, <p2>, ...` listing at most 5 paths and ending `, ...` when some are not listed, or `<n> paths: ...` when none can be listed, or `not a git repo`. A path git prints in double quotes (a space, `;` or other unusual character) is counted, never listed |
| `unmerged worktrees` | `none`, or a `, `-separated list where each item is a branch name or `detached <short sha>`, followed by ` (uncommitted)` when that worktree has uncommitted changes, or `not a git repo` |
| `waiting on you` | `none`, or the decision in a few words, with no `;` |
| `resume` | one command, or one sentence naming a command, with no `;`. By outcome: iterate, the next question as a sentence; pivot, the same after the `<docs>/POC.md` edit; `pause <topic>`, `read poc-spec/handoffs/<file>, then <command>`; `pause` with no topic, the next step as a sentence; harden, `/spike-loop:poc-harden`; stop, `none, the PoC is closed`. The command is the next piece of work, never `/clear` or `/spike-loop:poc-help`: those belong in the `Next:` line |

The comparisons leave out the docs files, `SUMMARY.md` and `.claude/`, by name, never `.` (a `:(exclude).` pathspec excludes the whole repository). Use the line for the layout: `<docs>` is `poc-spec` for the first, `.` for the second. As a pathspec each name becomes `":(exclude)<name>"` after `-- .`, written `<exclusions>` below.

Exclusions, `poc-spec` layout: `poc-spec` `.claude` `SUMMARY.md`
Exclusions, root layout: `POC.md` `LOG.md` `SUMMARY.md` `.claude`

Never record values of environment variables, file contents, token or key paths, worktree paths, or customer names when the repo is public.

1. **Read.** Resolve the docs folder by the docs-folder rule above, then read `<docs>/POC.md` and the last 60 lines of `<docs>/LOG.md`. If `<docs>/POC.md` or `<docs>/LOG.md` is missing, say to run `/spike-loop:poc-start` and stop, ending with `Next: /spike-loop:poc-start`. If the rule stops on a half-migrated PoC, end with `Next:` naming the fix: keep one layout, then run `/spike-loop:poc-checkpoint` again. If the last log entry is older than this session's work, run the `/poc-log` steps first (draft, show, append).
2. **Summary.** Print a summary of at most 12 lines: the question; what is now established, with the evidence (command and result), not claims; assumptions still unproven; open question for the next session; elapsed wall-clock time against timebox (if `Started:` has no time, measure from the first `<docs>/LOG.md` entry).
3. **Outcome.** The outcomes are iterate, pivot, harden, stop and pause ("stop here, resume later, no loop decision"). If "$ARGUMENTS" is empty, recommend one of iterate, pivot, harden, stop or pause with a one-line reason (pause when the work stopped mid-step with no loop decision to make, and offer an optional topic), and ask the user to confirm. If the user does not confirm, go straight to the Next step.
4. **Topic.** Only for pause. With no topic, pause writes the entry and State and no hand-off file. With a topic: lower-case it and replace spaces with hyphens, and it must then match `[a-z0-9-]+`. Refuse anything else (a `.`, a `/`, an empty result) and ask the user for another topic. In a public repo the topic must not be a customer or deal name.
5. **State.** Gather the values with read-only git calls, all from the repo root:
   - `git --no-optional-locks -C "<root>" rev-parse --is-inside-work-tree`. If it fails or does not print `true`, the four git fields are `not a git repo`: skip the rest of this step.
   - branch: `git --no-optional-locks -C "<root>" branch --show-current`, and `detached` when it prints nothing.
   - at: `git --no-optional-locks -C "<root>" rev-parse --short HEAD`, and `no commits` when it fails.
   - uncommitted: `git --no-optional-locks -C "<root>" status --porcelain -- . <exclusions>`. The path is each line after its first three characters, and the new name for a rename (`old -> new`), in git's order.
   - unmerged worktrees: `git --no-optional-locks -C "<root>" worktree list --porcelain`. The first entry is the main checkout. Take only entries under `<main checkout>/.claude/worktrees/`, not the root's own worktree. Name each by its `branch` line without `refs/heads/`, or `detached <short sha>` when it says `detached`, with the sha from `git --no-optional-locks -C "<worktree path>" rev-parse --short HEAD`. It has commits when `git --no-optional-locks -C "<root>" log --oneline <branch or sha> --not HEAD` prints anything (skip this when at is `no commits`). It has uncommitted changes when `git --no-optional-locks -C "<worktree path>" status --porcelain` prints anything. List it when either holds, adding ` (uncommitted)` for the second. Print each listed worktree path to the user: the worktree path is used to run the check and printed, never written to the file.
   - waiting on you: from the conversation, `none` when nothing was said. A process the user says is running goes here.
   - resume: by the table above.
6. **Hand-off file.** Only for pause with a topic, and only in the `poc-spec` layout: in the older root layout no hand-off file is written (that would create `poc-spec/`, which only `/spike-loop:poc-start` creates), and the user is told to migrate to get hand-off files. Choose the name first: try to Read `<root>/poc-spec/handoffs/<YYYY-MM-DD>-<topic>.md`, then the same name with `-2`, `-3` and so on, and use the first whose Read fails as not found (Read, because Glob can skip ignored files). Create the file at `poc-spec/handoffs/<YYYY-MM-DD>-<topic>.md` (or the suffixed name) with the Write tool, at most 40 lines: what was done, the State line, decisions waiting, gotchas learned, files to read first, the next step. An existing file is never overwritten. The folder is created only now, never empty. The `resume:` field names the file actually written. No customer or deal names in a public repo.
7. **Closing entry.** Append the closing entry to `<docs>/LOG.md` for every outcome: a new dated entry in the log's format whose Decision line names the outcome, with the `State:` line from the State step as its last line. It is the one entry this command writes after the Read step, so there is no second entry.
8. **Pivot, harden, stop.** Pivot: edit the assumptions in `<docs>/POC.md` after the user agrees. Stop or harden: write `SUMMARY.md` in the repo root, at most 25 lines: title, the question, the answer, key evidence (the command and its result), what to do differently, and what is still unproven. Everything stays in the repo. Never write to any external system (wiki, chat, CRM). No credentials, and no customer names if the repo is public. If `SUMMARY.md` exists, update it in place and say so. Neither file makes the State stale, because both are excluded from the comparison.
9. **Read back.** Read the tail of `<docs>/LOG.md` with the Read tool, and the hand-off file if one was written. Check that the closing entry, its `State:` line and the file are there. If a write or the read-back fails, say so, print no `/clear`, and end with `Next: /spike-loop:poc-checkpoint <outcome>` to try again.
10. **Next.** End with one line starting `Next:`, only after a read-back that passed, or, when the outcome was not confirmed, without one. `iterate`, `pivot` and `pause`: `/clear`, then `/spike-loop:poc-help` (it checks the State and prints the resume command). `harden`: `/spike-loop:poc-harden`. `stop`: nothing further, the PoC is closed and `SUMMARY.md` is written. If the outcome was not confirmed: `/spike-loop:poc-checkpoint <recommended outcome>` to confirm it.
