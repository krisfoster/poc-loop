# Plan: implement hand-off state

Spec: `docs/handoff/spec.md` (draft 6, read it first). Review record: `docs/handoff/review.md`. Branch: `handoff-state-spec`, off `main` at `0317448`. Status: Phase R done (two reviews and a check of the fixes on 2026-11-27, all findings applied, the git rules checked by `docs/handoff/tools/check_git_rules.py`). Nothing is implemented.

## Ground rules

- Tests come before edits. New tests fail first for the expected reasons, then each phase turns some green. Each rule a test claims is also checked by mutation: break the skill text, the test must fail (the F1 review showed substring tests pass broken skills). Where the spec says a test parses, it parses.
- Before any commit: `typos` on changed files, `gitleaks`, no em dashes (check with Python, the system `grep` has no `-P`), trailer `Co-Authored-By: Claude`. Never `--no-verify`, never read `.env`.
- Before any push, PR, merge or tag: the pre-push review of outgoing changes that `CLAUDE.md` requires, and the maintainer's explicit yes for each step.
- A claim about Claude Code behaviour in a skill or doc must be true. Claims marked **(docs)** in the spec are untested until a probe runs them. Everything measured so far is headless on Claude Code 2.1.325.
- Paid runs: single runs per case, as for the layout checks and F1. Anthropic's terms on scripted use of a subscription are still unread and the organisation's policy unchecked, so nothing larger than a smoke set runs. Budget: 6 probe runs (Phase 0) and 15 manual cases (3.3), two of them two sessions each, so 17 runs there and 23 single runs in all, plus an allowance of 5 re-runs after fixes: 28 runs at most. Each run has a `--max-budget-usd 0.25` cap, as the layout probes use. A cap can be overshot (by up to about half on a small cap, `docs/evals/spike-findings.md` section 0.5), so the ceiling is about 28 x 0.25 x 1.5, roughly 10 USD. A probe or case that needs more than one run comes out of the re-run allowance, and when that is spent the maintainer is asked.
- The `CLAUDE.md` wiring text is not changed by this plan. It is carried word for word in three places (`skills/poc-start/SKILL.md` step 6, the blockquote in `docs/layout/spec.md`, the `WIRING` literal in `tests/test_docs_layout.py`), and the existing layout tests must keep passing untouched. Hand-offs are found through the `resume:` field of the last log entry.
- Rule A and Rule B stay word for word in every skill and agent that carries them. `poc-checkpoint`, `poc-log` and `poc-help` are edited around them, never inside them.

## Order and dependencies

| Phase | Needs | Output |
|---|---|---|
| R. Independent review of spec and plan | drafts | Done, twice. Record in `docs/handoff/review.md`. Git rules checked free |
| 0. Probes (done, `docs/handoff/findings.md`) | R | Baseline for option A: does a fresh headless session read the log tail and follow a `resume:` pointer, with and without the wiring |
| 1. Tests first | 0 | `tests/test_handoff_state.py` and changes to the contract tests, failing for the expected reasons |
| 2. Implementation | 1 | Skills, template Decision list, docs, changelog, version 0.3.0 |
| 3. Verification | 2 | Green tests, mutation check, scans, independent diff review, manual runs in scratch repos |
| 4. Cold-start evals | 3, and evals Phase 2 | Blocked until the terms are read and the harness can grade final text. Not part of 0.3.0 |
| 5. Release | 3 | PR, review, merge, tag, each only on the maintainer's yes |

## Phase R: independent review (done)

| ID | Task | Status |
|---|---|---|
| R.1 | `reviewer` agent on the spec and this plan, given the files and not the author's conclusions | First run failed on a network error with no output. Re-run on 2026-11-27: 1 blocker, 10 major, 4 minor |
| R.2 | Re-check each claim that can be checked locally before applying it. Record how each was handled | Done, in `docs/handoff/review.md` |
| R.3 | Re-review draft 4 and this plan, because the changes were large | Done on 2026-11-27: 1 blocker, 4 major, 8 minor, all applied in draft 5 |
| R.4 | Check the git rules free | `docs/handoff/tools/check_git_rules.py` on git 2.55.0. Each mutation restoring an earlier rule fails at least one check. Counts in `review.md` |
| R.5 | Independent check of the fixes in draft 5 | Done on 2026-11-27: 12 of 13 resolved, 1 partly, 2 major and 5 minor new, all applied in draft 6 |

## Phase 0: probes (paid, single runs, headless)

Scratch PoC repos built by a script kept under `docs/handoff/tools/` (no model needed to build them). Each probe runs in a fresh `claude -p` session with only the repo on disk, the plugin loaded from the checkout, read-only grants and a budget cap.

| ID | Probe | Answers |
|---|---|---|
| P0 | One cheap model run: a two-turn `--input-format stream-json` session that sends `/clear` as the second turn (the Agent SDK documents a `conversation_reset` for `/clear` in `query()` and says `/clear` works in streaming input mode). Observed: a reset event or system message in the output, and whether turn 3 can still see turn 1 | Whether a real `/clear` boundary can be tested, or only separate fresh sessions |
| P1a | Repo with the 0.2.1 wiring text in `CLAUDE.md`, a `POC.md`, a `LOG.md` whose last entry carries a `State:` line. First prompt is a **task** ("continue with the next step"), not a question about status | Does the wiring alone make a fresh session read the log tail and use State |
| P1b | The same repo with **no** wiring (no `CLAUDE.md`). Same prompt | The control: what the model does without the wiring, so P1a means something |
| P1c | The same repo and wiring, first prompt "Where are we and what should I do next?" | The status-question case, which reads the files either way, as a comparison only |
| P2 | Wiring unchanged, a hand-off file under `poc-spec/handoffs/`, a last `State:` line whose `resume:` names it. Task prompt as in P1a | Does the session follow the `resume:` pointer to the hand-off from the log tail alone |
| P4 | `claude -p` in a throwaway plugin with a trivial `SessionStart` hook that prints a marker | Whether SessionStart runs headless (the `startup` matcher only: `clear` cannot fire headless unless P0 shows otherwise) and whether the marker reaches the model. Informs option C only |

P4b (added after P0 showed `/clear` works headless): the same throwaway plugin with a `clear`-only matcher, `/clear` sent in stream-json. Answers whether the `clear` matcher fires headless. Paid from the re-run allowance.

Result (2026-11-27, 7 runs, about 0.28 USD): gate 0 passes. See `docs/handoff/findings.md`. 4 of the 5 re-runs remain. Maintainer decision the same day: ship option A in 0.3.0 with the skipped check as a stated limit, and record the hook as future work.

The staleness check cannot be probed before `poc-help` implements it, so it moves to 3.3. The earlier P3 is dropped.

What counts as "uses State", read from the stream-json event log: (1) a Read tool call on `poc-spec/LOG.md` before the first tool call that edits a file or runs a non-read command, and (2) the final text names the branch, the `resume:` command or the hand-off file from the State line. P2 passes when there is a Read of the named hand-off file. P1b passes as a control whatever it shows; it is recorded, and P1a means something only if it differs from P1b. Each probe also records whether the session ran `/spike-loop:poc-help` or acted on `resume:` by itself, for the unchecked route in the spec's Risks.

Gate 0: P1a, P1b, P2 results recorded in `docs/handoff/findings.md` with "one run each". If P1a shows the wiring is ignored for a task prompt, the spec's recommendation A is reconsidered before Phase 1 and the maintainer is asked. P0 and P4 do not gate anything.

## Phase 1: tests first

| ID | Test | File |
|---|---|---|
| 1.1 | Format agreement: the State template and the value table in the spec and in `poc-checkpoint` have the same six field names in the same order and the same fixed values per field (parsed). The `poc-start` template contains no `- State:` line | `tests/test_handoff_state.py` |
| 1.1b | Exclusions agree between the spec, `poc-checkpoint`, `poc-help` and `check_git_rules.py`, for both layouts, and neither list contains `.` alone | same |
| 1.2 | Read-back before `/clear`: in `poc-checkpoint` the read-back step precedes every step whose text contains `/clear`, and a failure branch forbids `/clear`. In `poc-log` and `poc-help`, no `Next:` rule contains `/clear`. In `docs/workflow.md` every `/clear` follows `/spike-loop:poc-checkpoint` in the same sentence | same |
| 1.3 | One closing entry and order: `poc-checkpoint` has exactly one step that appends an outcome entry and it names `State:`. The hand-off file is written before it, the `POC.md` and `SUMMARY.md` step comes before the read-back, and the `Next:` step is last | same |
| 1.4 | `pause` and topic: argument hint lists `pause`, the no-argument recommendation includes `pause`, `pause` with no topic writes no file, the stale-pause `Next:` passes the topic from the file name, the `resume` value is defined for every outcome, topic pattern `[a-z0-9-]+` with `.` and `/` refused, the name chosen by Read with `-2`, `-3`, the file created by Write and never overwritten, no hand-off file in the older layout | same |
| 1.5 | Place of use: State only from the last entry, a State with any later entry is "State unknown" (not stale), no newest-file fallback anywhere in `poc-help` | same |
| 1.6 | Staleness and commands: every git command written in `poc-help` and the State step of `poc-checkpoint` is parsed out and must be one of `COMMANDS` in `check_git_rules.py` (argument order included), the needed ones must all appear, each with `--no-optional-locks`. `poc-help` names the count-and-listed-paths comparison. The stale and no-State rows' `Next:` never contain `/clear` | same |
| 1.7 | Field set: exactly six fields, and the `unmerged worktrees` grammar is exactly `<branch> | detached <short sha>` with optional `(uncommitted)`, so a path added to it fails. The `poc-checkpoint` text says worktree paths are printed, not written | same |
| 1.8 | Every place that lists the outcomes has `pause`, from an explicit list: `poc-checkpoint` argument hint and steps, `poc-help` row and Next rules, `poc-log` Decision step and Next rule, `poc-start` template Decision list, `docs/workflow.md`, `README.md` | `tests/test_handoff_state.py` |
| 1.8b | `docs/handoff/tools/check_git_rules.py` runs from the suite and passes | `tests/test_handoff_state.py` |
| 1.9 | The existing layout tests (Rule A, Rule B, wiring, packager commands) pass without edits. Deviation, 2026-11-27: `tests/test_docs_layout.py` gained one verbatim-snippet exemption, `ROOT_EXCLUSIONS`, for the root-layout exclusion line in `poc-checkpoint` and `poc-help`, which must name `POC.md` and `LOG.md` bare. It uses the same mechanism as the `LEGACY_NOTE` exemption, and the 36 layout mutation rows still all behave | existing suite |
| 1.10 | Mutation check: a script like `docs/layout/tools/mutate.py` with one row per rule above (drop the read-back, make an entry conditional, drop the later-entry rule, add a worktree path to State, re-add the newest-file fallback, put `/clear` in a `poc-log` Next, remove the topic restriction, put `- State:` in the template, exclude `.` in the older layout, drop `SUMMARY.md` from the exclusions, drop `--no-optional-locks`, drop `merge-base --is-ancestor`, write the hand-off after the entry, put `/clear` in a stale-row `Next:`, swap the `merge-base` arguments, print `Next:` before the `POC.md` or `SUMMARY.md` step). Every mutation fails at least one test | `docs/handoff/tools/mutate.py` |

Run the suite: the new tests fail for the expected reasons, the existing 87 still pass.

Status 2026-11-27: Phases 1, 2 and 3 done. 117 tests pass. Phase 3.2 review applied (`review.md`). Phase 3.3: 15 cases, 17 runs and 3 re-runs, about 0.71 USD, results in `findings.md`; 1 of the 5 re-runs remains. Earlier: 113 tests passed after Phase 2. `docs/handoff/tools/mutate.py`: 27 mutations of the skills and docs, each fails at least one test, and the negative control fails none (the first run missed two, the later-entry rule and a `/clear` in a `poc-help` Decision rule, and both tests were tightened).

## Phase 2: implementation

| ID | Change |
|---|---|
| 2.1 | `skills/poc-start/SKILL.md`: the Decision list in the `LOG.md` template gains `pause`. Nothing else, and the wiring text is not touched |
| 2.2 | `skills/poc-checkpoint/SKILL.md`: `pause [topic]` and `pause` in the no-argument recommendation, the order of work from the spec (topic, State, hand-off file, entry, `POC.md` and `SUMMARY.md`, read-back, `Next:` last), `pause` with no topic, the `resume` value per outcome, the State format and value table, the sources with `--no-optional-locks` and the per-layout exclusions, the worktree rules (main checkout's `.claude/worktrees/`, not the root's own, detached, no commits), the failure path, the file-name rule by Read, the older-layout rule, the public-repo naming rule. `Next:` for iterate, pivot, pause is `/clear`, then `/spike-loop:poc-help`. Paths and docs-folder rules word for word |
| 2.3 | `skills/poc-log/SKILL.md`: accept `pause`, no State line, iterate, pivot and pause point at `/spike-loop:poc-checkpoint <outcome>`, no bare `/clear` |
| 2.4 | `skills/poc-help/SKILL.md`: `pause` row, the three-row table from the spec (fresh, stale, no State or a later entry), the stale-pause topic from the hand-off file name, last-entry State read, the staleness check as in the spec with `--no-optional-locks`, the hand-off read for pause, no fallback, read-only kept, no `/clear` in any `Next:` |
| 2.5 | `docs/workflow.md`: the four boundaries, `pause`, the manual `/clear` rule, the State line and the route through `poc-help`. Line 20 ("`/spike-loop:poc-debug` or `/clear`") becomes "`/spike-loop:poc-debug`, or `/spike-loop:poc-checkpoint iterate` and then `/clear`", and the tier 2 "`/clear` between passes" becomes "`/spike-loop:poc-checkpoint` between passes" |
| 2.6 | `README.md` checkpoint row mentions `pause`. `CHANGELOG.md` 0.3.0 entry saying what was tested, what was not (interactive, an installed plugin, older-than-0.2.0 wiring), the packager gap for hand-offs, and the known limit that the staleness check runs only through `poc-help` (a hook is possible future work). `plugin.json` 0.3.0 |
| 2.7 | `docs/layout/spec.md`: its "reserved, written by the hand-off spec" lines point at `docs/handoff/spec.md` |

## Phase 3: verification

| ID | Task |
|---|---|
| 3.1 | Tests (including `check_git_rules.py`), mutation checks (36 layout rows plus the new ones), `typos`, `gitleaks`, em dash check |
| 3.2 | Independent `reviewer` on the diff, told to try to break the tests by editing the skills |
| 3.3 | Manual runner cases on scratch repos, single runs, recorded in `docs/handoff/findings.md`: checkpoint iterate with uncommitted files and an unmerged worktree branch, then a fresh session; `poc-help` with fresh state, state after a code commit, state after a docs-only commit, state with a later `poc-log` entry (expected: "State unknown"), an old log without State, a repo with no commits, not a git repo, detached HEAD, an older root-layout PoC with an uncommitted code file, `checkpoint harden` then `poc-help` (`SUMMARY.md` must not make it stale), a `reset --hard` to before the recorded commit; `pause <topic>` then a fresh session reading the hand-off; a bad topic; a failed write. 15 cases, 17 runs. The git outcome of each case is already checked free; these runs check that the model follows the skill text |
| 3.4 | The changelog and docs say which behaviours were checked only headless and that no interactive session was run |
| 3.5 | Pre-push review: `gitleaks`, a read of the diff for personal paths, hostnames, deal data, connector IDs |

## Phase 4: cold-start evals (not in 0.3.0)

A case type that runs phase N then a fresh session, graded from files on disk and the final text. Needs a final-text grader and runner support for two linked sessions (see `docs/evals/plan.md` Phase 2), and the terms to have been read. The 0.3.0 changelog says the cold-start behaviour was measured by hand only.

## Phase 5: release

PR, `reviewer` re-run on the final diff if anything changed after Phase 3, then merge, tag `v0.3.0` (signed, annotated) and release, each only on the maintainer's explicit yes.

## Future work (not in 0.3.0)

- **A `SessionStart` hook that runs the staleness check** (option C). Decided on 2026-11-27 after Phase 0: possible later work, a separate change once 0.3.0 has been used. The reason, what is known and what to settle first are in the spec's "Future work" section. The 0.3.0 changelog names it as a known limit: the check runs only when the user types `poc-help`.

## Risks to the plan

- P1a may show the model ignores the wiring for a task prompt. Then option A alone is not enough and the maintainer decides on C before Phase 1.
- P4 runs the `startup` matcher at best. If SessionStart does not run headless, C stays untested and stays out.
- The model may not follow a `resume:` pointer. P2 measures it.
- `check_git_rules.py` proves the git rules, not that the model follows them. The 3.3 runs check that, one run each.
- Single runs hide variance. Findings say "one run each", as the layout findings do.
- Optional, separate branch: commit a sync script for Rule A, Rule B and the wiring with a `--check` mode, so a future text change is one command.
- Known gap carried to the changelog: the packager warns only about `POC.md` and `LOG.md`, not hand-off files.
