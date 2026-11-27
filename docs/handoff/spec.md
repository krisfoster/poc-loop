# Spec: hand-off state, so a fresh session can pick a PoC up

Status: draft 6, revised after the second independent review of 2026-11-27 (R.3) and a check of draft 5 the same day (R.3b), see `docs/handoff/review.md`. Branch: `handoff-state-spec`, off `main` at `0317448` (v0.2.1). Implemented on this branch for 0.3.0 (plan Phases 1 and 2). The plan is `docs/handoff/plan.md`. The git rules below are checked free by `docs/handoff/tools/check_git_rules.py`.

Maintainer decisions (2026-11-26): `pause` is a new outcome of `poc-checkpoint` and not a new command; only `poc-checkpoint` writes State; only branch names are stored, never worktree paths; the version is 0.3.0; a `SessionStart` hook (option C) is built later and only if the cold-start check shows it is needed.

How to read the evidence. Statements about the plugin come from reading `skills/poc-checkpoint`, `skills/poc-log`, `skills/poc-help`, `skills/poc-start`, `skills/poc-build`, `agents/packager.md`, `docs/workflow.md` and `docs/layout/spec.md` on `main` at `0317448`. Statements about git were run in scratch repos on git 2.55.0 by the check script. Statements about Claude Code come from its docs and are marked **(docs)**: they are untested until the plan's probes run them, and the docs were read through a summarising fetch, so check the wording before quoting it outside this repo.

## Problem

The maintainer clears context between phases of a PoC (`/clear`), so a fresh session knows nothing except what is on disk. Today the plugin leaves a partial hand-off:

- `poc-spec/POC.md` (stable) and `poc-spec/LOG.md` (append only) hold the question, the assumptions and what was learned.
- The `CLAUDE.md` section that `poc-start` appends tells every session to read `POC.md` and the last 40 lines of `LOG.md`, and ends "Hand-offs, specs and plans for this PoC go under `poc-spec/`".
- `poc-checkpoint` step 3 already records the confirmed outcome (iterate, pivot, harden or stop) as a new `LOG.md` entry whose Decision line names it.
- `poc-help` reads the same two files and prints where the PoC stands and a `Next:` line.
- `SUMMARY.md` is written on stop or harden.

That is close to a hand-off for the loop's decisions. It has four gaps:

1. **No in-flight state.** Nothing records the branch, uncommitted files, a `poc-build` worktree whose branch has not been merged, or a decision waiting on the user. A fresh session cannot tell them from the log.
2. **A clear can come before the record.** Step 4 and step 7 of `poc-checkpoint` print "`/clear`, then ..." after step 3's entry, but nothing reads the entry back, and step 1 only runs the extra `poc-log` steps when the last entry is "older than this session's work", a judgement the model makes. Today's entry also carries no state.
3. **Spec and plan work has no hand-off and no outcome.** `poc-spec/handoffs/<YYYY-MM-DD>-<topic>.md` is reserved by `docs/layout/spec.md` ("written by the hand-off spec") and no skill writes it. Spec work ends without a PoC decision, and every command assumes one of iterate, pivot, harden or stop.
4. **The loop has no named phase boundaries.** `docs/workflow.md` says "`/clear` between passes" for tier 2, "start a fresh session" after iterate, and "`/spike-loop:poc-debug` or `/clear`" after two failed fixes, and nothing says which command ends which phase or what it leaves behind.

A skill cannot clear context. The docs describe `/clear` only as a user command and no skill, tool or hook output field is documented as able to clear context or start a fresh session **(docs, read 2026-11-26 and 2026-11-27, untested)**. The closest hook outputs are `initialUserMessage` (for `-p` only) and `sessionTitle`, which do neither. The design therefore makes a manual `/clear` safe, and never claims to do it.

## Goals

1. At each phase boundary the command that ends the phase leaves everything a fresh session needs on disk: the next question, the in-flight state, and what is waiting on the user.
2. A fresh session started in the repo can say where the PoC stands and name the next command, from files alone.
3. `Next: /clear, then ...` appears only after the state is on disk and has been read back.
4. A stale hand-off is detected and flagged, not trusted, on the route the plugin tells the user to take (see "Finding the hand-off" for the route it cannot check).
5. No new place to put customer names or secrets, and the limits of the existing warning are stated, not assumed.
6. The behaviour is checked free where it can be (text and format tests, the git check script, mutation checks) and by a cold-start run where it cannot.

## Non-goals

- Clearing context from a skill or a hook. Not documented as possible.
- A `SessionStart` hook in this change (option C below). It is recorded as future work (see "Future work").
- Changing what `POC.md` or `SUMMARY.md` contain.
- Changing the `CLAUDE.md` wiring text that `poc-start` appends. It is carried word for word in three places and checked verbatim by the layout tests, and this design does not need a new sentence in it.
- Hand-offs for this plugin's own development (the maintainer's own notes). This spec governs the PoC repos the plugin creates.
- Recording running processes automatically. A skill cannot list them reliably, so it records only what the user says.
- Comparing worktrees in the staleness check. A merge of a worktree branch moves HEAD with code commits, which the check already sees.
- Writing to any external system.
- Extending the packager's docs-folder warning to hand-off files (see "Public repos").

## Phase boundaries

Four points in the loop end a phase. Each names the command that ends it, what it writes and what its `Next:` line says. Every other mention of `/clear` in the plugin's skills and docs goes through `poc-checkpoint` first: `docs/workflow.md`'s "after two failed fix attempts" line becomes "`/spike-loop:poc-debug`, or `/spike-loop:poc-checkpoint iterate` and then `/clear`", and its tier 2 "`/clear` between passes" becomes "`/spike-loop:poc-checkpoint` between passes". No exception: no skill or doc asks for a `/clear` after `poc-start` today, and none will.

| Boundary | Ended by | Writes | `Next:` |
|---|---|---|---|
| After start, tier 2 only | `poc-start` | `POC.md`, the "PoC started" `LOG.md` entry (exists today) | Unchanged (it names no `/clear`). The files are the hand-off |
| After a working session | `poc-checkpoint iterate`, `pivot` or `pause` | The outcome entry (step 3 today) now carries a `State:` line | `/clear`, then `/spike-loop:poc-help` |
| After a spec or plan step | `poc-checkpoint pause <topic>` | The same entry, plus `poc-spec/handoffs/<date>-<topic>.md` | `/clear`, then `/spike-loop:poc-help` |
| After harden or stop | `poc-checkpoint harden` or `stop` | `SUMMARY.md` and the outcome entry with State | Unchanged |

The `Next:` after a `/clear` names `poc-help`, not the resume command itself, so the first thing a fresh session does on the plugin's route is the staleness check. `poc-help` then prints the resume command, or says the State is stale.

## The State line

An optional line inside a dated `LOG.md` entry, written only by `poc-checkpoint`. Its format is defined here and in `skills/poc-checkpoint/SKILL.md`, and **not** in the `LOG.md` template that `poc-start` copies into every PoC, so a placeholder line never sits in a fresh log for a reader to mistake for a record.

```
- State: branch: <branch>; at: <at>; uncommitted: <uncommitted>; unmerged worktrees: <worktrees>; waiting on you: <waiting>; resume: <resume>
```

Six fields, in this order, separated by `; `. Each value is one of:

| Field | Values |
|---|---|
| `branch` | the current branch name, or `detached`, or `not a git repo` |
| `at` | the short sha of HEAD, or `no commits`, or `not a git repo` |
| `uncommitted` | `none`, or `<n> paths: <p1>, <p2>, ...` listing at most 5 paths and ending `, ...` when some are not listed, or `<n> paths: ...` when none can be listed, or `not a git repo`. A path git prints in double quotes (a space, `;` or other unusual character) is counted, never listed |
| `unmerged worktrees` | `none`, or a `, `-separated list where each item is a branch name or `detached <short sha>`, followed by ` (uncommitted)` when that worktree has uncommitted changes, or `not a git repo` |
| `waiting on you` | `none`, or the decision in a few words, with no `;` |
| `resume` | one command, or one sentence naming a command, with no `;`. By outcome: iterate, the next question as a sentence; pivot, the same after the `<docs>/POC.md` edit; `pause <topic>`, `read poc-spec/handoffs/<file>, then <command>`; `pause` with no topic, the next step as a sentence; harden, `/spike-loop:poc-harden`; stop, `none, the PoC is closed`. The command is the next piece of work, never `/clear` or `/spike-loop:poc-help`: those belong in the `Next:` line |

The only path a State line holds is the hand-off file in `resume` and the repo-relative paths in `uncommitted`. Worktree paths are never written.

### Sources

All read-only, all from the repo root, and every git call as `git --no-optional-locks -C "<root>" ...` so that `status` does not rewrite `.git/index` (a plain `git status` did, in the check script).

- **Inside a work tree?** `rev-parse --is-inside-work-tree`. If it fails or does not print `true` (not a repository, or a bare one), the four git fields are `not a git repo` and nothing else is run.
- **branch.** `branch --show-current`. It prints nothing on a detached HEAD (the value is `detached`) and works in a repository with no commits, where `rev-parse --abbrev-ref HEAD` fails.
- **at.** `rev-parse --short HEAD`. It fails with no commits, and the value is `no commits`.
- **The exclusions.** One list per layout, used by every comparison here, written in the skills as these two lines:

  Exclusions, `poc-spec` layout: `poc-spec` `.claude` `SUMMARY.md`
  Exclusions, root layout: `POC.md` `LOG.md` `SUMMARY.md` `.claude`

  Never `.`: as a pathspec, `:(exclude).` excludes the whole repository, so an older-layout PoC would always read clean. `SUMMARY.md` is excluded because the "Pivot, harden, stop" step writes it after the State is gathered. The pathspec is `-- . ":(exclude)<each>"`.
- **uncommitted.** `status --porcelain -- . <exclusions>`. The path is each line after its first three characters, and the new name for a rename (`old -> new`). Paths are listed in git's order.
- **unmerged worktrees.** `worktree list --porcelain`. The first entry is always the main checkout, also when the session's root is itself a linked worktree. Consider only entries whose path is under `<main checkout>/.claude/worktrees/`, and not the root's own worktree. For each: its name is the `branch` line without `refs/heads/`, or `detached <short sha>` when the entry says `detached`, the sha from `git --no-optional-locks -C "<worktree path>" rev-parse --short HEAD`. It has commits when `log --oneline <branch or sha> --not HEAD` prints anything (skipped when `at` is `no commits`, where it fails). It has uncommitted changes when `git --no-optional-locks -C "<worktree path>" status --porcelain` prints anything. It is listed when either holds. The worktree path is used to run the check and printed to the user, never written.
- **waiting on you.** From the conversation, `none` when nothing was said. A process the user says is running is recorded here.

### Rules for readers

- **Never recorded.** Values of environment variables, file contents, token or key paths, worktree paths, customer names when the repo is public.
- **Where a reader may use it.** Only a `State:` line inside the **last** dated `## ` entry of the log counts. A `- State:` line anywhere else, or in an earlier entry, is ignored. When any entry follows the State line, the State is older than the log and is treated as unknown.
- **Older logs.** An entry without `State:` is valid. Every reader treats a missing State as "unknown", not "clean".
- **Format.** One line, so the existing "last 40 lines of `LOG.md`" read includes it.

## Finding the hand-off from a fresh session

The wiring text in a PoC's `CLAUDE.md` says to read the last 40 lines of `poc-spec/LOG.md` at session start and that hand-offs go under `poc-spec/`. The last entry carries the State line, and `resume:` names the hand-off file when `pause <topic>` wrote one. The wiring text does not change.

- **The checked route.** The checkpoint's `Next:` is `/clear`, then `/spike-loop:poc-help`, which runs the staleness check before it prints the resume command.
- **The unchecked route.** A fresh session that reads the log through the wiring and acts on `resume:` by itself, or a user who types the resume command straight away, skips the check. The design cannot close this without changing the wiring or adding a hook (option C). It is stated in Risks, and probes P1a and P2 show whether a session acts on `resume:` unprompted.
- **One route to a hand-off file.** There is no "newest file in `handoffs/`" fallback: Glob can skip gitignored files and `poc-spec/` often is ignored, and the newest file may belong to an earlier phase. A named file is read with the Read tool.
- PoCs wired by 0.2.x carry this wiring text, so they work the same way. PoCs wired before 0.2.0 carry a paraphrase the model wrote, so for them this is an assumption to check, not a promise.
- If the last entry has no State (an older log, or a `poc-log` entry after the outcome entry), `poc-help` says the state is unknown and prints the Decision-based `Next:` below.

## Commands

### `poc-checkpoint`

- **Outcomes.** iterate, pivot, harden, stop and `pause` ("stop here, resume later, no loop decision"). With no arguments, step 3 recommends one of the five, `pause` when the work stopped mid-step with no loop decision to make, and asks the user to confirm.
- **One closing entry.** Step 3's outcome entry (today written once the outcome is confirmed, for every outcome) becomes the one closing entry and gains the `State:` line. No second entry is added. Step 1's extra `poc-log` entry, run when the last entry is stale, stays as it is and is written before the closing entry.
- **Order of work after the outcome is confirmed.**
  1. For `pause <topic>`: check the topic (below).
  2. Gather the State (Sources above).
  3. For `pause <topic>` in the `poc-spec` layout: choose the file name, then write the hand-off file (below), so `resume:` can name the file that was actually written.
  4. Append the closing entry with the `State:` line.
  5. The existing steps: pivot edits `<docs>/POC.md` after the user agrees, harden and stop write `SUMMARY.md`. Both are excluded from the comparison, so neither makes the State stale.
  6. Read the tail of `<docs>/LOG.md` back with the Read tool, and the hand-off file if one was written. Check the entry, its `State:` line and the file are there.
  7. Last, the `Next:` line. Only after a read-back that passed may it contain `/clear`. If a write or the read-back fails, say so, print no `/clear`, and end with `Next: /spike-loop:poc-checkpoint <outcome>` to try again.
- **`pause` with no topic.** Allowed. It writes the entry and State and no hand-off file, and `resume:` is the next step as a sentence. With no arguments at all, a recommended `pause` asks for an optional topic.
- **Topic.** Lower-case it and replace spaces with hyphens. It must then match `[a-z0-9-]+`. Anything else (a `.`, a `/`, an empty result) is refused and the user is asked for another. In a public repo it must not be a customer or deal name.
- **Hand-off file.** `poc-spec/handoffs/<YYYY-MM-DD>-<topic>.md`: what was done, the State line, decisions waiting, gotchas learned, files to read first, the next step, at most 40 lines. To choose the name, try to Read `<root>/poc-spec/handoffs/<name>.md`, then `-2`, `-3` and so on: the first name whose Read fails as not found is used (Read, because Glob can skip ignored files). The file is created with the Write tool and an existing file is never overwritten. The folder is created only now, never empty. In a PoC in the older root layout, no hand-off file is written (that would create `poc-spec/`, which only `poc-start` creates, `docs/layout/spec.md`): the entry and State are written, and the command says to migrate to the new layout to get hand-off files.
- **`Next:`** iterate, pivot and pause: `/clear`, then `/spike-loop:poc-help` (for pivot, the `POC.md` edit is already done in step 5). Harden and stop are unchanged.

### `poc-log`

Does not write a State line. It accepts `pause` as a Decision. For iterate, pivot or pause its `Next:` becomes `/spike-loop:poc-checkpoint <outcome>` (which writes State and then asks for the `/clear`), instead of "`/clear` and start a fresh session".

### `poc-help`

Reads the last 25 lines of the log as today, and stays read-only (every git call with `--no-optional-locks`). Then, by the last entry:

| Last entry | Prints | `Next:` |
|---|---|---|
| State, fresh | `Resume:` with the `resume:` value. If it names a hand-off file, that file is read first and summarised | The `resume:` command |
| State, stale | `State is from <entry date>; it may be stale: <what differs>` | iterate, pivot: `/spike-loop:poc-checkpoint <Decision>` to record the state again. pause: the hand-off file named in `resume:`, if any, is still read and summarised, marked as possibly stale, and `Next:` is `/spike-loop:poc-checkpoint pause <topic>` with the topic taken from that file name without the date (and without a `-<n>` ending only when the file without it also exists), or `/spike-loop:poc-checkpoint pause` when there is no file. harden, stop: unchanged |
| No State, or a State line with any entry after it | "State unknown" | By the last entry's Decision. iterate, pivot or pause: `/spike-loop:poc-checkpoint <Decision>`. harden, stop, none yet: unchanged |

No row's `Next:` contains `/clear`, so a stale or missing State never leads back to itself.

### `poc-start`

Only the Decision list in the `LOG.md` template changes, to add `pause`. The wiring text and the rest of the template are untouched.

### Staleness check

`poc-help` gathers the State again with the same sources and compares. It is stale when any of these holds, and the message names which:

- **branch** differs (a name, `detached`, `not a git repo`).
- **commit.** If either `at` is `no commits` or `not a git repo`, stale when they differ. Otherwise stale when `merge-base --is-ancestor <recorded sha> HEAD` fails (a reset to before it, or a sha that does not exist), or when `log --oneline <recorded sha>..HEAD -- . <exclusions>` prints anything. A commit that only touches the exclusions (the log, `SUMMARY.md`, `.claude/`) does not count, because the natural step after a checkpoint, which does not commit, is to commit the log.
- **uncommitted.** Stale when the count differs, or when a listed path is no longer uncommitted. It is not exact, and the spec accepts that: a further edit to a file that was already uncommitted is not seen, and with paths not listed (more than 5, or quoted names) a change that keeps the count and the listed paths is missed.
A State line with an entry after it never reaches this check: it is "State unknown" (Rules for readers).

The three git reasons are cases in `docs/handoff/tools/check_git_rules.py`, which passes on git 2.55.0 and fails under each mutation that brings back an earlier rule. The script does not parse `LOG.md`: the last-entry and later-entry rules are text rules, held by the tests below. The script also holds the list of git commands used here and checks that this spec writes each one.

## Making a manual `/clear` safe: options

| Option | What | For | Against |
|---|---|---|---|
| A | `Next: /clear, then /spike-loop:poc-help` only after the state is on disk and read back, plus the `CLAUDE.md` read at session start | No new mechanism, works in every mode. **(docs)** `/clear` reloads `CLAUDE.md` | Relies on the user typing the `Next:` line, or on the model following the wiring after a clear |
| B | `context: fork` for non-interactive phases | A fork does not see the conversation | `poc-build` showed a fork does not behave like a normal subagent call (F1). `poc-start` and `poc-harden` ask questions, so they are not fork-safe |
| C | A plugin `SessionStart` hook with a `clear` matcher that prints the State and resume line | Does not rely on the model reading `CLAUDE.md`. **(docs)** The `clear` matcher fires after `/clear`, plain stdout or `additionalContext` is added to the model's context, and a plugin can ship the hook in `hooks/hooks.json` with `CLAUDE_PROJECT_DIR` set | **(docs)** Silent on a plugin hook's working directory, on any trust or approval step for plugin hooks, and on user visibility. Measured headless (findings P4, P4b, one run each, `--plugin-dir`): both the `startup` and the `clear` matcher fire, with no trust prompt, and stdout reaches the model. An installed plugin and an interactive session are unmeasured. Output is dropped if `/clear` runs again while a hook is still running. It adds a hook to the trust surface of a public plugin |
| D | Cold-start evals: run phase N in one headless session, then the next command in a fresh one with only the repo on disk, and grade it | Measures the result instead of arguing about it | Needs runner support for two linked sessions, and the terms-of-use condition still stands for anything beyond a smoke test. **(docs)** The Agent SDK reports `/clear` inside a `query()` as a `conversation_reset` and says `/clear` is usable in streaming input mode, and probe P0 showed a real `/clear` in one headless stream-json session resets context, so the boundary is testable |

Recommendation: A for the build, D to measure it (a handful of single runs), and C only if D shows the wiring is ignored. Not B.

## Public repos

The existing notice in `poc-start` step 2 says to keep customer names and deal details out of `poc-spec/`, or add `poc-spec/` to `.gitignore` before the first push. That covers hand-offs. The **packager warning does not**: it runs `git ls-files` on `poc-spec/POC.md` and `poc-spec/LOG.md` by name only (`agents/packager.md`, step 6), so a tracked hand-off file can travel with no warning when `POC.md` and `LOG.md` are ignored. This is a known gap and it is not fixed here, because the four `ls-files` commands are compared verbatim by `tests/test_docs_layout.py`. The changelog says so. A hand-off, a topic name and the `resume:` text must not carry customer or deal names in a public repo, and the checkpoint step says so.

## Tests

Free, in a new `tests/test_handoff_state.py`. A substring is not enough for these rules, so each test parses:

- **Format agreement.** The State template line and the value table in this spec and in `skills/poc-checkpoint/SKILL.md` agree: the same six field names in the same order, and for each field the same set of fixed values (`detached`, `no commits`, `not a git repo`, `none`, `(uncommitted)`, `detached <short sha>`, `<n> paths:`). The `poc-start` template does not contain a `- State:` line.
- **Exclusions agree.** The exclusion lists for both layouts are the same in this spec, in `poc-checkpoint` and in `poc-help`, and in `docs/handoff/tools/check_git_rules.py`. Neither list contains `.` on its own.
- **Read-back before `/clear`.** In `poc-checkpoint`, the read-back step comes before any step whose text contains `/clear`, and the failure branch says to print no `/clear`. In `poc-log` and `poc-help` no `Next:` rule contains `/clear`. In `docs/workflow.md` every `/clear` is preceded in the same sentence by `/spike-loop:poc-checkpoint`. No exemption.
- **One closing entry.** `poc-checkpoint` has exactly one step that appends an outcome entry, and that step names `State:`. The hand-off file is written before that entry.
- **`pause` and topic.** The argument hint lists `pause`. The topic rule is the stated pattern and says to refuse `.` and `/`. The name is chosen by Read with `-2`, `-3`, the file is created with Write and never overwritten, and the text says no hand-off is written in the older layout.
- **Place of use.** `poc-help` uses a State line only from the last entry, treats a State with any later entry as "State unknown" (not stale), and has no fallback that reads the newest file in `handoffs/`.
- **Staleness and commands.** Every git command written in `poc-help` and in the State step of `poc-checkpoint` is parsed out of the text and must be one of the `COMMANDS` in `check_git_rules.py`, argument order included, and each command the rules need must appear (`merge-base --is-ancestor <recorded sha> HEAD` in `poc-help`, the worktree commands in `poc-checkpoint`). Each is run with `--no-optional-locks`. `poc-help` names the count-and-listed-paths comparison.
- **Field set.** The State template has exactly the six fields. The `unmerged worktrees` value grammar is exactly `<branch> | detached <short sha>`, optionally followed by `(uncommitted)`, so adding a path to it fails the test. The `poc-checkpoint` text says worktree paths are printed, not written.
- **Every place that lists the outcomes** includes `pause`: the `poc-checkpoint` argument hint and steps (including the no-argument recommendation), the `poc-help` table row and Next rules, the `poc-log` Decision step, the `poc-start` template's Decision list, `docs/workflow.md` and `README.md`. The test holds the explicit list.
- **Git rules.** `docs/handoff/tools/check_git_rules.py` runs in the suite (it is free and needs only git) and passes.
- **Wiring untouched.** The existing layout tests pass unchanged.
- **Mutation check** (`docs/handoff/tools/mutate.py`, as for the layout tests): drop the read-back, make an entry conditional again, drop the later-entry rule, add a worktree path to State, re-add the newest-file fallback, put `/clear` in a `poc-log` Next, remove the topic restriction, put `- State:` in the template, exclude `.` in the older layout, drop `SUMMARY.md` from the exclusions, drop `--no-optional-locks`, drop `merge-base --is-ancestor`, swap its arguments, write the hand-off after the entry, put `/clear` in a stale-row `Next:`, print `Next:` before the `POC.md` or `SUMMARY.md` step. Every mutation must fail at least one test. A reviewer pass then tries to break the tests by editing the skills, as in the F1 review.

Manual and cold-start (paid, single runs, headless): see the plan.

## Risks

- **A longer closing ritual.** Mitigation: one line, gathered with read-only git calls.
- **Model-written State is wrong.** Git facts are read, not recalled. "Waiting on you" is the only judgement, and stale or missing State is flagged, not trusted.
- **The unchecked route.** A session that acts on `resume:` straight from the log tail, or a user who skips `poc-help`, gets no staleness check. The plugin's own `Next:` lines always go through `poc-help`. P1a and P2 measure whether a session acts on `resume:` unprompted, and option C is the fix if that turns out to matter.
- **Uncommitted comparison is approximate.** Further edits to an already uncommitted file, and changes hidden behind unlisted paths, are missed. Stated in the staleness check.
- **`pause` is a new loop word.** Every reader that maps Decisions needs a rule for it. The outcome-list test above holds the places.
- **The model may not follow a `resume:` pointer** from the log tail after a clear. The probes measure it, interactively unmeasured.
- **Branch names and topic names can be descriptive.** `LOG.md` already can hold such text. The rule against customer names in a public repo covers them, and the packager gap above is stated.
- **Worktrees outside `.claude/worktrees/`.** The Claude Code docs say the Desktop app's `worktree.location` setting (Desktop SSH sessions) can put worktrees elsewhere **(docs, 2026-11-27)**. The State would then miss them.
- **Interactive behaviour is unmeasured.** Everything measured so far is headless on Claude Code 2.1.325.

## Future work: a `SessionStart` hook for the staleness check (option C)

Decided 2026-11-27, after Phase 0: 0.3.0 ships option A, and the 0.3.0 changelog states that the staleness check runs only when the user types `/spike-loop:poc-help`. A hook is possible later work, a separate change (0.4.0 or later), once 0.3.0 has been used.

Why it is worth doing. In every Phase 0 task run the model acted on `resume:` straight from the log and never ran `poc-help`, and the model cannot run it (`disable-model-invocation: true`). So the check the spec relies on is skipped on the route a session actually takes (findings 4).

What is already known (findings P4, P4b, one run each, headless, `--plugin-dir`): a plugin `SessionStart` hook fires on both the `startup` and the `clear` matcher, with no trust prompt, and its stdout reaches the model.

Sketch. A `hooks/hooks.json` entry on `startup|clear` running a small script shipped with the plugin. The script finds the repo root and docs folder, reads the last `LOG.md` entry, and if it has a State line, runs the same comparison as `docs/handoff/tools/check_git_rules.py` and prints one or two lines: the resume command, or "State may be stale: <what differs>, run `/spike-loop:poc-checkpoint <Decision>`". That moves the check from skill prose into code, which the check script already tests.

To settle before building it:
- Behaviour as an installed plugin (not `--plugin-dir`) and in an interactive session, including any trust or approval prompt.
- The hook's working directory and `CLAUDE_PROJECT_DIR`, and what it does outside a PoC repo (it must print nothing).
- Cost and latency at every session start, in every repo, for every user of the plugin.
- The trust surface: a public plugin that runs a script at every session start. The script must be read-only (`--no-optional-locks`), print no file contents, and never print secrets.
- Output dropped if `/clear` runs again while the hook is running **(docs)**.
- Tests: the script shares the reference implementation and its mutation checks, plus a headless cold-start case.

## Open questions

- Whether the packager's warning should cover hand-offs (a separate change that touches the verbatim `ls-files` test).
- The 40-line cap on hand-offs is a guess.
- Whether the real `/clear` boundary can be exercised headless (plan probe P0).
- Whether the Write tool refuses to overwrite a file it has not read. The design does not rely on it: the name is chosen by Read first.
