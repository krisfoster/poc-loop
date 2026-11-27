# Plan: implement hand-off state

Spec: `docs/handoff/spec.md` (draft 4, read it first). Review record: `docs/handoff/review.md`. Branch: `handoff-state-spec`, off `main` at `0317448`. Status: Phase R done (first attempt failed on a network error, re-run on 2026-11-27, findings applied). Nothing is implemented.

## Ground rules

- Tests come before edits. New tests fail first for the expected reasons, then each phase turns some green. Each rule a test claims is also checked by mutation: break the skill text, the test must fail (the F1 review showed substring tests pass broken skills). Where the spec says a test parses, it parses.
- Before any commit: `typos` on changed files, `gitleaks`, no em dashes (check with Python, the system `grep` has no `-P`), trailer `Co-Authored-By: Claude`. Never `--no-verify`, never read `.env`.
- Before any push, PR, merge or tag: the pre-push review of outgoing changes that `CLAUDE.md` requires, and the maintainer's explicit yes for each step.
- A claim about Claude Code behaviour in a skill or doc must be true. Claims marked **(docs)** in the spec are untested until a probe runs them. Everything measured so far is headless on Claude Code 2.1.325.
- Paid runs: single runs per case, as for the layout checks and F1. Anthropic's terms on scripted use of a subscription are still unread and the organisation's policy unchecked, so nothing larger than a smoke set runs. Budget: about 15 single runs plus an allowance of 5 re-runs after fixes, a few dollars in all. Each run has a `--max-budget-usd` cap.
- The `CLAUDE.md` wiring text is not changed by this plan. It is carried word for word in three places (`skills/poc-start/SKILL.md` step 6, the blockquote in `docs/layout/spec.md`, the `WIRING` literal in `tests/test_docs_layout.py`), and the existing layout tests must keep passing untouched. Hand-offs are found through the `resume:` field of the last log entry.
- Rule A and Rule B stay word for word in every skill and agent that carries them. `poc-checkpoint`, `poc-log` and `poc-help` are edited around them, never inside them.

## Order and dependencies

| Phase | Needs | Output |
|---|---|---|
| R. Independent review of spec and plan | drafts | Done. Record in `docs/handoff/review.md` |
| 0. Probes | R | Baseline for option A: does a fresh headless session read the log tail and follow a `resume:` pointer, with and without the wiring |
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
| R.3 | Re-review the delta if a rule changes in response | Run once more on draft 4 and this plan before Phase 1 starts, because the changes were large |

## Phase 0: probes (paid, single runs, headless)

Scratch PoC repos built by a script kept under `docs/handoff/tools/` (no model needed to build them). Each probe runs in a fresh `claude -p` session with only the repo on disk, the plugin loaded from the checkout, read-only grants and a budget cap.

| ID | Probe | Answers |
|---|---|---|
| P0 | No model run needed first: check whether a headless run can send `/clear` mid-session (the Agent SDK documents a `conversation_reset` for `/clear` in `query()`), by a cheap two-turn stream-json run | Whether a real `/clear` boundary can be tested, or only separate fresh sessions |
| P1a | Repo with the 0.2.1 wiring text in `CLAUDE.md`, a `POC.md`, a `LOG.md` whose last entry carries a `State:` line. First prompt is a **task** ("continue with the next step"), not a question about status | Does the wiring alone make a fresh session read the log tail and use State |
| P1b | The same repo with **no** wiring (no `CLAUDE.md`). Same prompt | The control: what the model does without the wiring, so P1a means something |
| P1c | The same repo and wiring, first prompt "Where are we and what should I do next?" | The status-question case, which reads the files either way, as a comparison only |
| P2 | Wiring unchanged, a hand-off file under `poc-spec/handoffs/`, a last `State:` line whose `resume:` names it. Task prompt as in P1a | Does the session follow the `resume:` pointer to the hand-off from the log tail alone |
| P4 | `claude -p` in a throwaway plugin with a trivial `SessionStart` hook that prints a marker | Whether SessionStart runs headless (the `startup` matcher only: `clear` cannot fire headless unless P0 shows otherwise) and whether the marker reaches the model. Informs option C only |

The staleness check cannot be probed before `poc-help` implements it, so it moves to 3.3. The earlier P3 is dropped.

Gate 0: P1a, P1b, P2 results recorded in `docs/handoff/findings.md` with "one run each". If P1a shows the wiring is ignored for a task prompt, the spec's recommendation A is reconsidered before Phase 1 and the maintainer is asked. P0 and P4 do not gate anything.

## Phase 1: tests first

| ID | Test | File |
|---|---|---|
| 1.1 | Format agreement: the State line in the spec and in `poc-checkpoint` have the same field names in the same order (parsed). The `poc-start` template contains no `- State:` line | `tests/test_handoff_state.py` |
| 1.2 | Read-back before `/clear`: in `poc-checkpoint` the read-back step precedes every step whose text contains `/clear`, and a failure branch forbids `/clear`. In `poc-log` and `poc-help`, no `Next:` rule contains a bare `/clear`. No exemption | same |
| 1.3 | One closing entry: `poc-checkpoint` has exactly one step that appends an outcome entry and it names `State:` | same |
| 1.4 | `pause` and topic: argument hint lists `pause`, topic pattern `[a-z0-9-]+` with `.` and `/` refused, the file created by Write and never overwritten (`-2`, `-3`), no hand-off file in the older layout | same |
| 1.5 | Place of use: State only from the last entry, a later entry makes it stale, no newest-file fallback anywhere in `poc-help` | same |
| 1.6 | Staleness: `poc-help` names branch, commits outside the docs folder (with the exclude), uncommitted comparison, later-entry rule, sha compared as a prefix | same |
| 1.7 | No path field in the State line, and the `poc-checkpoint` text says worktree paths are printed, not stored | same |
| 1.8 | Every place that lists the outcomes has `pause`, from an explicit list: `poc-checkpoint` argument hint and steps, `poc-help` row and Next rules, `poc-log` Decision step and Next rule, `poc-start` template Decision list, `docs/workflow.md`, `README.md` | `tests/test_skills_contract.py` |
| 1.9 | The existing layout tests (Rule A, Rule B, wiring, packager commands) pass without edits | existing suite |
| 1.10 | Mutation check: a script like `docs/layout/tools/mutate.py` with one row per rule above (drop the read-back, make an entry conditional, drop the later-entry rule, add a worktree path to State, re-add the newest-file fallback, put `/clear` in a `poc-log` Next, remove the topic restriction, put `- State:` in the template). Every mutation fails at least one test | `docs/handoff/tools/mutate.py` |

Run the suite: the new tests fail for the expected reasons, the existing 87 still pass.

## Phase 2: implementation

| ID | Change |
|---|---|
| 2.1 | `skills/poc-start/SKILL.md`: the Decision list in the `LOG.md` template gains `pause`. Nothing else, and the wiring text is not touched |
| 2.2 | `skills/poc-checkpoint/SKILL.md`: `pause [topic]`, the one outcome entry gains `State:`, State gathering with the read-only git calls (`branch --show-current`, `rev-parse --short HEAD` with the `no commits` and `not a git repo` values, `status --porcelain` with the docs folder and `.claude/` excluded, worktree branches and per-worktree status), the read-back before any `/clear`, the failure path, the hand-off file rules and the older-layout rule, the public-repo naming rule. Paths and docs-folder rules word for word |
| 2.3 | `skills/poc-log/SKILL.md`: accept `pause`, no State line, iterate, pivot and pause point at `/spike-loop:poc-checkpoint <outcome>`, no bare `/clear` |
| 2.4 | `skills/poc-help/SKILL.md`: `pause` row and Next rule, last-entry State read, `Resume:` line, the staleness check, no fallback, read-only kept, iterate and pivot Next rules point at the checkpoint or the `resume:` command |
| 2.5 | `docs/workflow.md`: the four boundaries, `pause`, the manual `/clear` rule, the State line and the `resume:` route |
| 2.6 | `README.md` checkpoint row mentions `pause`. `CHANGELOG.md` 0.3.0 entry saying what was tested, what was not (interactive, `clear` matcher, older-than-0.2.0 wiring), and the packager gap for hand-offs. `plugin.json` 0.3.0 |
| 2.7 | `docs/layout/spec.md`: its "reserved, written by the hand-off spec" lines point at `docs/handoff/spec.md` |

## Phase 3: verification

| ID | Task |
|---|---|
| 3.1 | Tests, mutation checks (36 layout rows plus the new ones), `typos`, `gitleaks`, em dash check |
| 3.2 | Independent `reviewer` on the diff, told to try to break the tests by editing the skills |
| 3.3 | Manual runner cases on scratch repos, single runs, recorded in `docs/handoff/findings.md`: checkpoint iterate with uncommitted files and an unmerged worktree branch, then a fresh session; `poc-help` with fresh state, state after a code commit, state after a docs-only commit, state with a later `poc-log` entry, an old log without State, a repo with no commits, not a git repo, detached HEAD; `pause <topic>` then a fresh session reading the hand-off; a bad topic; a failed write |
| 3.4 | The changelog and docs say which behaviours were checked only headless and that no interactive session was run |
| 3.5 | Pre-push review: `gitleaks`, a read of the diff for personal paths, hostnames, deal data, connector IDs |

## Phase 4: cold-start evals (not in 0.3.0)

A case type that runs phase N then a fresh session, graded from files on disk and the final text. Needs a final-text grader and runner support for two linked sessions (see `docs/evals/plan.md` Phase 2), and the terms to have been read. The 0.3.0 changelog says the cold-start behaviour was measured by hand only.

## Phase 5: release

PR, `reviewer` re-run on the final diff if anything changed after Phase 3, then merge, tag `v0.3.0` (signed, annotated) and release, each only on the maintainer's explicit yes.

## Risks to the plan

- P1a may show the model ignores the wiring for a task prompt. Then option A alone is not enough and the maintainer decides on C before Phase 1.
- P4 runs the `startup` matcher at best. If SessionStart does not run headless, C stays untested and stays out.
- The model may not follow a `resume:` pointer. P2 measures it.
- Single runs hide variance. Findings say "one run each", as the layout findings do.
- Optional, separate branch: commit a sync script for Rule A, Rule B and the wiring with a `--check` mode, so a future text change is one command.
- Known gap carried to the changelog: the packager warns only about `POC.md` and `LOG.md`, not hand-off files.
