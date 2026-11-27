# Spec: hand-off state, so a fresh session can pick a PoC up

Status: draft 4, revised after the independent review of 2026-11-27 (see `docs/handoff/review.md`). Branch: `handoff-state-spec`, off `main` at `0317448` (v0.2.1). Nothing here is implemented. The plan is `docs/handoff/plan.md`.

Maintainer decisions (2026-11-26): `pause` is a new outcome of `poc-checkpoint` and not a new command; only `poc-checkpoint` writes State; only branch names are stored, never worktree paths; the version is 0.3.0; a `SessionStart` hook (option C) is built later and only if the cold-start check shows it is needed.

How to read the evidence. Statements about the plugin come from reading `skills/poc-checkpoint`, `skills/poc-log`, `skills/poc-help`, `skills/poc-start`, `skills/poc-build`, `agents/packager.md`, `docs/workflow.md` and `docs/layout/spec.md` on `main` at `0317448`. Statements about Claude Code come from its docs and are marked **(docs)**: they are untested until the plan's probes run them, and the docs were read through a summarising fetch, so check the wording before quoting it outside this repo.

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
4. **The loop has no named phase boundaries.** `docs/workflow.md` says "`/clear` between passes" for tier 2 and "start a fresh session" after iterate, and nothing says which command ends which phase or what it leaves behind.

A skill cannot clear context. The docs describe `/clear` only as a user command and no skill, tool or hook output field is documented as able to clear context or start a fresh session **(docs, read 2026-11-26, untested)**. The closest hook outputs are `initialUserMessage` and `sessionTitle`, which do neither. The design therefore makes a manual `/clear` safe, and never claims to do it.

## Goals

1. At each phase boundary the command that ends the phase leaves everything a fresh session needs on disk: the next question, the in-flight state, and what is waiting on the user.
2. A fresh session started in the repo can say where the PoC stands and name the next command, from files alone.
3. `Next: /clear, then ...` appears only after the state is on disk and has been read back.
4. A stale hand-off is detected and flagged, not trusted.
5. No new place to put customer names or secrets, and the limits of the existing warning are stated, not assumed.
6. The behaviour is checked free where it can be (text and format tests, with mutation checks) and by a cold-start run where it cannot.

## Non-goals

- Clearing context from a skill or a hook. Not documented as possible.
- A `SessionStart` hook in this change (option C below).
- Changing what `POC.md` or `SUMMARY.md` contain.
- Changing the `CLAUDE.md` wiring text that `poc-start` appends. It is carried word for word in three places and checked verbatim by the layout tests, and this design does not need a new sentence in it.
- Hand-offs for this plugin's own development (the maintainer's `~/claude_work` notes). This spec governs the PoC repos the plugin creates.
- Recording running processes automatically. A skill cannot list them reliably, so it records only what the user says.
- Writing to any external system.
- Extending the packager's docs-folder warning to hand-off files (see "Public repos").

## Phase boundaries

Four points in the loop end a phase. Each names the command that ends it, what it writes and what its `Next:` line says. Nothing else asks for a `/clear`.

| Boundary | Ended by | Writes | `Next:` |
|---|---|---|---|
| After start, tier 2 only | `poc-start` | `POC.md`, the "PoC started" `LOG.md` entry (exists today) | Unchanged. `/clear` is optional, the files are the hand-off |
| After a working session | `poc-checkpoint iterate`, `pivot` or `pause` | The outcome entry (step 3 today) now carries a `State:` line | `/clear`, then the resume command |
| After a spec or plan step | `poc-checkpoint pause <topic>` | The same entry, plus `poc-spec/handoffs/<date>-<topic>.md` | `/clear`, then the resume command |
| After harden or stop | `poc-checkpoint harden` or `stop` | `SUMMARY.md` and the outcome entry with State | Unchanged |

## The State line

An optional line inside a dated `LOG.md` entry, written only by `poc-checkpoint`. Its format is defined here and in `skills/poc-checkpoint/SKILL.md`, and **not** in the `LOG.md` template that `poc-start` copies into every PoC, so a placeholder line never sits in a fresh log for a reader to mistake for a record.

```
- State: branch <name | detached at <sha> | none>; at <short sha | no commits | not a git repo>; uncommitted: <none | up to 5 paths>; unmerged worktrees: <none | branch names, each marked "(uncommitted)" when its worktree has changes>; waiting on you: <none | the decision>; resume: <one command or one sentence>
```

- **Sources.** All read-only: `git -C "<root>" branch --show-current` (empty on a detached HEAD, and it works in a repository with no commits, where `rev-parse --abbrev-ref HEAD` fails), `git -C "<root>" rev-parse --short HEAD` (fails with no commits, so the value is `no commits`), and `git -C "<root>" status --porcelain` with the docs folder and `.claude/` left out. Outside a git repository none of these work, and the line says `not a git repo` for all three. Unmerged worktrees come from `git -C "<root>" worktree list --porcelain` (strip `refs/heads/` from branch names) and, for each entry under `.claude/worktrees/`, `git -C "<root>" log --oneline <branch> --not HEAD` for commits and `git -C "<worktree path>" status --porcelain` for uncommitted changes. The worktree path is used to run the check and printed to the user, and is never written to the file. "Waiting on you" comes from the conversation and is `none` when nothing was said. A process the user says is running is recorded there.
- **Never recorded.** Values of environment variables, file contents, token or key paths, worktree paths, customer names when the repo is public.
- **Where a reader may use it.** Only a `State:` line inside the **last** dated `## ` entry of the log counts. A `- State:` line anywhere else, or in an earlier entry, is ignored. When any entry follows the State line, the State is older than the log and is treated as unknown.
- **Older logs.** An entry without `State:` is valid. Every reader treats a missing State as "unknown", not "clean".
- **Format.** One line, so the existing "last 40 lines of `LOG.md`" read includes it.

## Finding the hand-off from a fresh session

The wiring text in a PoC's `CLAUDE.md` says to read the last 40 lines of `poc-spec/LOG.md` at session start and that hand-offs go under `poc-spec/`. The last entry carries the State line. When `pause <topic>` wrote a hand-off file, `resume:` names it, for example `resume: read poc-spec/handoffs/2026-11-27-topic.md, then run <command>`. The wiring text does not change.

- This is the only route to a hand-off. There is no "newest file in `handoffs/`" fallback: Rule B itself notes that Glob can skip gitignored files and `poc-spec/` often is ignored, and the newest file may belong to an earlier phase. A named file is read with the Read tool.
- PoCs wired by 0.2.x carry this wiring text, so they work the same way. PoCs wired before 0.2.0 carry a paraphrase the model wrote, so for them this is an assumption to check, not a promise.
- If the last entry has no State (an older log, or a `poc-log` entry after the outcome entry), `poc-help` says the state is unknown and prints the Decision-based `Next:` it prints today.

## Commands

- **`poc-checkpoint`.**
  - Step 3's outcome entry (today written once the outcome is confirmed, for every outcome) becomes the one closing entry and gains the `State:` line. No second entry is added. Step 1's extra `poc-log` entry, run when the last entry is stale, stays as it is and is written before the closing entry.
  - It reads the tail of the log back after appending, checks the entry and its `State:` line are there, and only then prints a `Next:` that contains `/clear`. If the write or the read-back fails it says so and does not suggest `/clear`.
  - New outcome `pause`: "stop here, resume later, no loop decision". The entry's Decision is `pause`.
  - `pause <topic>`: the topic must match `[a-z0-9-]+` after lower-casing and replacing spaces with hyphens. Anything else (a `.`, a `/`, an empty result) is refused and the user is asked for another. In a public repo the topic must not be a customer or deal name. It also writes `poc-spec/handoffs/<YYYY-MM-DD>-<topic>.md`: what was done, the State line, decisions waiting, gotchas learned, files to read first, the next step, at most 40 lines. The file is created with the Write tool and never overwritten: if the name exists, the next free name with `-2`, `-3` is used. The folder is created only now, never empty. In a PoC in the older root layout, no hand-off file is written (that would create `poc-spec/`, which only `poc-start` creates, `docs/layout/spec.md`): the entry and State are written, and the command says to migrate to the new layout to get hand-off files.
  - `pause` `Next:`: `/clear`, then the `resume:` command.
- **`poc-log`.** Does not write a State line. It accepts `pause` as a Decision. For iterate, pivot or pause its `Next:` becomes `/spike-loop:poc-checkpoint <outcome>` (which writes State and then asks for the `/clear`), instead of "`/clear` and start a fresh session".
- **`poc-help`.** Reads the last 25 lines of the log as today. If the last entry has a State line, it prints a `Resume:` line from it, after the staleness check below. Its own iterate and pivot `Next:` lines point at `/spike-loop:poc-checkpoint <outcome>` when there is no usable State, and at the `resume:` command when there is. If `resume:` names a hand-off file it is read. The Decision `pause` maps to the `resume:` command, or to `/spike-loop:poc-checkpoint pause` when there is none. It stays read-only.
- **`poc-start`.** Only the Decision list in the `LOG.md` template changes, to add `pause`. The wiring text and the rest of the template are untouched.

### Staleness check

`poc-help` compares the recorded State with the repo now, with read-only git calls, and prints `State is from <time>; it may be stale: <what differs>` and uses the Decision-based `Next:` instead of `resume:` when any of these differ:

- The branch, or a detached or no-commits state.
- Commits since the recorded sha that touch anything outside the docs folder: `git -C "<root>" log --oneline <sha>..HEAD -- . ":(exclude)<docs>"` is not empty. A commit that only changes the docs folder does not count, because the natural step after a checkpoint (which does not commit) is to commit the log. The recorded sha is compared as a prefix, since the short length can change. A sha that no longer exists counts as stale.
- The uncommitted paths, compared with the same exclusions. Paths added or removed since count as stale.
- Any entry after the State line (see above).

## Making a manual `/clear` safe: options

| Option | What | For | Against |
|---|---|---|---|
| A | `Next: /clear, then <command>` only after the state is on disk and read back, plus the `CLAUDE.md` read at session start | No new mechanism, works in every mode. **(docs)** `/clear` keeps project memory and reloads `CLAUDE.md` | Relies on the model following the instruction after a clear |
| B | `context: fork` for non-interactive phases | A fork does not see the conversation | `poc-build` showed a fork does not behave like a normal subagent call (F1). `poc-start` and `poc-harden` ask questions, so they are not fork-safe |
| C | A plugin `SessionStart` hook with a `clear` matcher that prints the State and resume line | Does not rely on the model reading `CLAUDE.md`. **(docs)** The `clear` matcher fires after `/clear`, plain stdout or `additionalContext` is added to the model's context, and a plugin can ship the hook in `hooks/hooks.json` with `CLAUDE_PROJECT_DIR` set | **(docs)** Silent on a plugin hook's working directory, on any trust or approval step for plugin hooks, and on user visibility. The docs suggest `SessionStart` runs under `claude -p` (through `initialUserMessage`) without saying so, and a headless run fires the `startup` matcher, not `clear`. Output is dropped if `/clear` runs again while a hook is still running. It adds a hook to the trust surface of a public plugin |
| D | Cold-start evals: run phase N in one headless session, then the next command in a fresh one with only the repo on disk, and grade it | Measures the result instead of arguing about it | Needs runner support for two linked sessions, and the terms-of-use condition still stands for anything beyond a smoke test. **(docs)** The Agent SDK reports `/clear` inside a `query()` as a `conversation_reset`, so the real boundary might be testable in one session, not checked |

Recommendation: A for the build, D to measure it (a handful of single runs), and C only if D shows the wiring is ignored. Not B.

## Public repos

The existing notice in `poc-start` step 2 says to keep customer names and deal details out of `poc-spec/`, or add `poc-spec/` to `.gitignore` before the first push. That covers hand-offs. The **packager warning does not**: it runs `git ls-files` on `poc-spec/POC.md` and `poc-spec/LOG.md` by name only (`agents/packager.md`, step 6), so a tracked hand-off file can travel with no warning when `POC.md` and `LOG.md` are ignored. This is a known gap and it is not fixed here, because the four `ls-files` commands are compared verbatim by `tests/test_docs_layout.py`. The changelog says so. A hand-off, a topic name and the `resume:` text must not carry customer or deal names in a public repo, and the checkpoint step says so.

## Tests

Free, in a new `tests/test_handoff_state.py` plus changes to `tests/test_skills_contract.py`. A substring is not enough for these rules, so each test parses:

- **Format agreement.** The State line in this spec and in `skills/poc-checkpoint/SKILL.md` have the same field names in the same order (parsed, as `test_constants_equal_the_spec` does for the layout). The `poc-start` template does not contain a `- State:` line.
- **Read-back before `/clear`.** In `poc-checkpoint`, the step that reads the log tail back comes before any step whose text contains `/clear`, and a failure branch says not to print `/clear`. In `poc-log` and `poc-help` no `Next:` rule contains a bare `/clear`: each names `/spike-loop:poc-checkpoint <outcome>` or the `resume:` command. No exemption.
- **One closing entry.** `poc-checkpoint` still has exactly one step that appends an outcome entry, and that step names `State:`.
- **`pause` and topic.** The argument hint lists `pause`. The topic rule is the stated pattern and says to refuse `.` and `/`. The hand-off file is created with the Write tool and never overwritten (`-2`, `-3`), and the text says no hand-off is written in the older layout.
- **Place of use.** `poc-help` uses a State line only from the last entry, treats any later entry as stale, and has no fallback that reads the newest file in `handoffs/`.
- **Staleness.** `poc-help` names the branch, the commits-outside-docs check (with the exclude), the uncommitted comparison and the later-entry rule.
- **No path in State.** The State line text names no path field.
- **Every place that lists the outcomes** includes `pause`: the `poc-checkpoint` argument hint and steps, the `poc-help` table row and Next rules, the `poc-log` Decision step, the `poc-start` template's Decision list, `docs/workflow.md` and `README.md`. The test holds the explicit list.
- **Wiring untouched.** The existing layout tests pass unchanged.
- **Mutation check** (`docs/handoff/tools/mutate.py`, as for the layout tests): drop the read-back, make an entry conditional again, drop the later-entry rule, add a worktree path to State, re-add the newest-file fallback, put `/clear` in a `poc-log` Next, remove the topic restriction, put `- State:` in the template. Every mutation must fail at least one test. A reviewer pass then tries to break the tests by editing the skills, as in the F1 review.

Manual and cold-start (paid, single runs, headless): see the plan.

## Risks

- **A longer closing ritual.** Mitigation: one line, gathered with read-only git calls.
- **Model-written State is wrong.** Git facts are read, not recalled. "Waiting on you" is the only judgement, and stale or missing State is flagged, not trusted.
- **`pause` is a new loop word.** Every reader that maps Decisions needs a rule for it. The outcome-list test above holds the places.
- **The model may not follow a `resume:` pointer** from the log tail after a clear. The probes measure it, interactively unmeasured.
- **Branch names and topic names can be descriptive.** `LOG.md` already can hold such text. The rule against customer names in a public repo covers them, and the packager gap above is stated.
- **Interactive behaviour is unmeasured.** Everything measured so far is headless on Claude Code 2.1.325.

## Open questions

- Whether the packager's warning should cover hand-offs (a separate change that touches the verbatim `ls-files` test).
- The 40-line cap on hand-offs is a guess.
- Whether the real `/clear` boundary can be exercised headless (plan probe P0).
