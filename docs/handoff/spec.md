# Spec: hand-off state, so a fresh session can pick a PoC up

Status: draft 1. Branch: `handoff-state-spec`, off `main` at `0317448` (v0.2.1). Nothing here is implemented. The "Decisions for the maintainer" section lists what must be settled before a plan is written.

How to read the evidence. Statements about the plugin come from reading `skills/poc-checkpoint`, `skills/poc-log`, `skills/poc-help`, `skills/poc-start`, `docs/workflow.md` and `docs/layout/spec.md` on `main` at `0317448`. Statements about Claude Code come from its docs and are marked **(docs)**: they are untested until the plan's probe phase runs them, and the docs were read through a summarising fetch, so check the wording before quoting them outside this repo.

## Problem

The maintainer clears context between phases of a PoC (`/clear`), so a fresh session knows nothing except what is on disk. Today the plugin leaves a partial hand-off:

- `poc-spec/POC.md` (stable) and `poc-spec/LOG.md` (append only) hold the question, the assumptions and what was learned.
- The `CLAUDE.md` section that `poc-start` appends tells every session to read `POC.md` and the last 40 lines of `LOG.md`.
- `poc-help` reads the same two files and prints where the PoC stands and a `Next:` line.
- `SUMMARY.md` is written on stop or harden.

That is close to a hand-off for the loop's decisions. It has four gaps:

1. **No in-flight state.** Nothing records the branch, uncommitted files, a `poc-build` worktree whose branch has not been merged, a process left running, or a decision waiting on the user. A fresh session cannot tell them from the log.
2. **`iterate` and `pivot` write nothing new.** `poc-checkpoint` step 4 and step 7 only print "`/clear`, then ...". The user can run `poc-checkpoint` without a preceding `poc-log`, and step 1 only runs the `poc-log` steps first when the last entry is "older than this session's work", a judgement the model makes. The last log entry can be stale when the user clears.
3. **Spec and plan work has no hand-off.** `poc-spec/handoffs/<YYYY-MM-DD>-<topic>.md` is reserved by `docs/layout/spec.md` ("written by the hand-off spec") and no skill writes it.
4. **The loop has no named phase boundaries.** `docs/workflow.md` says "`/clear` between passes" for tier 2 and "start a fresh session" after iterate, and nothing says which command ends which phase or what it leaves behind.

A skill cannot clear context. The docs describe `/clear` only as a user command and no skill, tool or hook output field is documented as able to clear context or start a fresh session **(docs, read 2026-11-26 for skills and again for hooks, untested)**. The closest hook outputs are `initialUserMessage` and `sessionTitle`, which do neither. The design therefore makes a manual `/clear` safe, and never claims to do it.

## Goals

1. At each phase boundary the command that ends the phase leaves everything a fresh session needs on disk: the next question, the in-flight state, and what is waiting on the user.
2. A fresh session started in the repo can say where the PoC stands and name the next command, from files alone.
3. `Next: /clear, then ...` appears only after the state is on disk and has been read back.
4. A stale hand-off is detected and flagged, not trusted.
5. No new place to put customer names or secrets. Hand-offs live under `poc-spec/`, which the packager already warns about.
6. The behaviour is checked free where it can be (text and format tests) and by a cold-start run where it cannot.

## Non-goals

- Clearing context from a skill or a hook. Not documented as possible.
- A `SessionStart` hook in this change. It is option C below, kept as a fallback if the cold-start check shows the `CLAUDE.md` wiring is not enough. The docs confirm the mechanism exists (read 2026-11-26) and are silent on the points that decide whether it is worth the trust cost.
- Changing what `POC.md` or `SUMMARY.md` contain.
- Hand-offs for this plugin's own development (the maintainer's `~/claude_work` notes). This spec governs the PoC repos the plugin creates.
- Recording running processes automatically. A skill cannot list them reliably, so it records only what the user says.
- Writing to any external system.

## Phase boundaries

Four points in the loop end a phase. Each names the command that ends it, what it writes and what its `Next:` line says. Nothing else asks for a `/clear`.

| Boundary | Ended by | Writes | `Next:` |
|---|---|---|---|
| After start, tier 2 only | `poc-start` | `POC.md`, `LOG.md` entry "PoC started" (exists today) | Unchanged. `/clear` is optional here, the files are the hand-off |
| After a working session | `poc-checkpoint iterate`, `pivot` or `pause` | Closing `LOG.md` entry with a State block (new) | `/clear`, then the resume command |
| After a spec or plan step | `poc-checkpoint pause <topic>` | The closing entry plus `poc-spec/handoffs/<date>-<topic>.md` (new) | `/clear`, then the resume command |
| After harden or stop | `poc-checkpoint harden` or `stop` | `SUMMARY.md` and a closing entry (the entry is new) | Unchanged |

## The State block

A new optional line in the `LOG.md` entry format, written only by the boundary commands above:

```
- State: branch <name> at <short sha>; uncommitted: <none | list of at most 5 paths>; unmerged worktrees: <none | branch and path>; waiting on you: <none | the decision>; resume: <one command or sentence>
```

- **Sources.** Branch, short sha and uncommitted paths come from `git -C "<root>" rev-parse --abbrev-ref HEAD`, `git -C "<root>" rev-parse --short HEAD` and `git -C "<root>" status --porcelain`. Unmerged worktrees come from `git -C "<root>" worktree list --porcelain` and a `git -C "<root>" log --oneline <branch> --not HEAD` per `.claude/worktrees/` entry, which is the state `poc-build` leaves behind (v0.2.1). "Waiting on you" comes from the conversation and is `none` when nothing was said. A process the user says is running is recorded under "waiting on you".
- **Never recorded.** Values of environment variables, file contents, token or key paths, customer names when the repo is public.
- **Older logs.** An entry without `State:` is valid. Every reader treats a missing State as "unknown", not "clean".
- **Format.** One line, so the existing "last 40 lines of `LOG.md`" read always includes it.

## Commands

- **`poc-checkpoint`.** Every outcome (iterate, pivot, harden, stop, and the new `pause`) ends with a closing `LOG.md` entry, even when a `poc-log` entry was just written: the closing entry is the one with State and Decision. For `iterate` and `pivot` the entry is mandatory, today it is conditional. It reads the tail of `LOG.md` back after appending and only then prints a `Next:` that contains `/clear`. If the write or the read-back fails it says so and does not suggest `/clear`.
- **`pause` (new outcome).** Means "stop here, resume later, no loop decision". It writes Decision `pause`, so `poc-help` and `poc-log` need a rule for it. It exists because spec and plan work ends without a PoC decision.
- **`pause <topic>`.** Also writes `poc-spec/handoffs/<YYYY-MM-DD>-<topic>.md` (topic restricted to letters, digits and hyphens): what was done, the State line, decisions waiting, gotchas learned, files to read first, the next step. At most 40 lines. Never overwritten: a second pause on the same topic and day appends a section. The folder is created only now, never empty (`docs/layout/spec.md`).
- **`poc-log`.** Unchanged except that a Decision of `iterate`, `pivot` or `pause` asks to run `poc-checkpoint` for the State, so the two commands do not write two partial records.
- **`poc-help`.** Reads the newest `State:` line and the newest file in `poc-spec/handoffs/` (if any). Prints a `Resume:` line. Compares the recorded short sha and branch with the repo now: when they differ it prints `State is from <time>; the repo has moved: <what differs>` and does not use the recorded "resume" command, falling back to the Decision-based `Next:` it prints today.
- **`poc-start`.** The `CLAUDE.md` section gains one sentence: "If `poc-spec/handoffs/` exists, read the newest file there too." Existing PoCs keep their old text, so `poc-help` is their only route to a hand-off. The same sentence is added to the packager's expectations only if the packager reads that section (to be checked in the plan).

## Making a manual `/clear` safe: options

| Option | What | For | Against |
|---|---|---|---|
| A | `Next: /clear, then <command>` only after the state is on disk, plus the `CLAUDE.md` read at session start | No new mechanism. Works in every mode | Relies on the model following the `CLAUDE.md` instruction after a clear |
| B | `context: fork` for non-interactive phases | A fork does not see the conversation, so it cannot depend on it | `poc-build` showed a fork does not behave like a normal subagent call (F1). `poc-start` and `poc-harden` ask questions, so they are not fork-safe |
| C | A plugin `SessionStart` hook with a `clear` matcher that prints the State and resume line | Does not rely on the model reading `CLAUDE.md`. **(docs)** The matcher `clear` fires after `/clear`, plain stdout or `additionalContext` is added to the model's context, and a plugin can ship the hook in `hooks/hooks.json` with `CLAUDE_PROJECT_DIR` set | **(docs)** The docs are silent on a plugin hook's working directory, on any trust or approval step for plugin hooks, on whether the text is also shown to the user, and on whether it runs under `claude -p`, so it could not be tested headless without a harness change. It adds a hook to the trust surface of a public plugin |
| D | Cold-start evals: run phase N in one headless session, then the next command in a fresh one with only the repo on disk, and grade it | Measures the result instead of arguing about it | Needs runner support for two linked sessions, and the terms-of-use condition on eval runs still stands for anything beyond a smoke test |

Recommendation: A for the build, D to measure it (a handful of single runs, as with the layout checks), and C only if D shows the wiring is ignored. Not B.

## Tests

Free, in `tests/test_skills_contract.py` and a new `tests/test_handoff_state.py`:

- The `LOG.md` template in `poc-start` and the `poc-checkpoint` step text agree on the State line's fields.
- Every `Next:` rule that contains `/clear` sits in a command whose steps append and read back an entry first.
- `poc-checkpoint` lists `pause` in its argument hint and every outcome writes a closing entry, with iterate and pivot unconditional.
- `poc-help` names the staleness comparison and the fallback.
- The `CLAUDE.md` wiring text in `poc-start` and `docs/workflow.md` match, and `poc-start`'s copy mentions `handoffs/`.
- A mutation check as for the layout tests (break the rule, the test must fail), and a reviewer pass that tries to break the tests, as in the F1 review.

Manual and cold-start (paid, single runs, headless): checkpoint on a scratch PoC with an unmerged `poc-build` worktree and uncommitted files, then `poc-help` in a fresh session. Cases: fresh state, stale state (a commit made after the checkpoint), old log without State, `pause <topic>` then a fresh session reading the hand-off, a failed write.

## Risks

- **A longer closing ritual.** Every iterate or pivot now takes a checkpoint. Mitigation: the State block is one line, gathered with three read-only git calls.
- **Model-written State is wrong.** Git facts are read, not recalled. "Waiting on you" is the only judgement, and a stale or empty value is flagged by the comparison, not trusted.
- **`pause` is a new loop word.** `poc-log` and `poc-help` must accept it, or older copies of the docs mislead. Covered by the tests above.
- **A recorded worktree path is a local path.** The State line can hold a path under the user's home. `LOG.md` already can, and `poc-spec/` is covered by the packager warning. The plan must decide whether to record the branch only.
- **Interactive behaviour is unmeasured.** Everything measured so far is headless on Claude Code 2.1.325. Whether the model reads `CLAUDE.md` the same way after `/clear` interactively is the thing option D cannot show.

## Decisions for the maintainer

1. **New outcome `pause`, or a separate command.** Recommended: `pause` on `poc-checkpoint`, so there is still one command that ends a phase. The alternative is a new `/spike-loop:poc-handoff <topic>` (a 13th command, no overload of the loop's decision words).
2. **Does `poc-log` write State.** Recommended: no, only `poc-checkpoint`, to keep one writer.
3. **Record the worktree path or only its branch.** Recommended: branch only, with the path printed to the user but not stored.
4. **Version.** Recommended: 0.3.0, because the `LOG.md` format and a command's outcomes change.
5. **Whether option C is built later** if the cold-start check says the wiring is not enough.

## Open questions

- Whether a plugin `SUMMARY.md` or hand-off should be allowed to name a deal when the PoC is tied to one (today the rule is: not in a public repo).
- Whether tier 1 PoCs need `pause` at all, or only tier 2.
- The cap on hand-off length (40 lines is a guess).
