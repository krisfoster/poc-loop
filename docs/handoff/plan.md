# Plan: implement hand-off state

Spec: `docs/handoff/spec.md` (draft 2, read it first). Branch: `handoff-state-spec`, off `main` at `0317448`. Status: Phase R re-run after a failed first attempt (network error), on the spec and plan with the wiring change removed. Nothing is implemented.

## Ground rules

- Tests come before edits. New tests fail first for the expected reasons, then each phase turns some green. Each rule a test claims is also checked by mutation: break the skill text, the test must fail (the F1 review showed substring tests pass broken skills).
- Before any commit: `typos` on changed files, `gitleaks`, no em dashes (check with Python, the system `grep` has no `-P`), trailer `Co-Authored-By: Claude`. Never `--no-verify`, never read `.env`.
- Before any push, PR, merge or tag: the pre-push review of outgoing changes that `CLAUDE.md` requires, and the maintainer's explicit yes for each step.
- A claim about Claude Code behaviour in a skill or doc must be true. Claims marked **(docs)** in the spec are untested until a probe runs them. Everything measured so far is headless on Claude Code 2.1.325.
- Paid runs: single runs per case, as for the layout checks and F1. Anthropic's terms on scripted use of a subscription are still unread and the organisation's policy unchecked, so nothing larger than a smoke set runs. Budget for this plan: about 15 single runs, a few dollars. Each run has a `--max-budget-usd` cap.
- The `CLAUDE.md` wiring text is not changed by this plan. It is carried word for word in three places (`skills/poc-start/SKILL.md` step 6, the blockquote in `docs/layout/spec.md`, the `WIRING` literal in `tests/test_docs_layout.py`) and the existing layout tests must keep passing untouched. Hand-offs are found through the `resume:` field of the closing log entry instead.

## Order and dependencies

| Phase | Needs | Output |
|---|---|---|
| R. Independent review of spec and plan | drafts | Findings applied, record in `docs/handoff/review.md` |
| 0. Probes | R | Baseline for option A: does a fresh headless session read the wiring and use a State line |
| 1. Tests first | 0 | `tests/test_handoff_state.py` and changes to the contract and layout tests, failing for the expected reasons |
| 2. Implementation | 1 | Skills, template, wiring, docs, changelog, version 0.3.0 |
| 3. Verification | 2 | Green tests, mutation check, scans, independent diff review, manual runs in scratch repos |
| 4. Cold-start evals | 3, and evals Phase 2 | Blocked until the terms are read and the harness can grade final text. Not part of 0.3.0 |
| 5. Release | 3 | PR, review, merge, tag, each only on the maintainer's yes |

## Phase R: independent review

| ID | Task |
|---|---|
| R.1 | `reviewer` agent on the spec and this plan, given the files and not the author's conclusions. Asked to check every claim about the current skills against the files, to find where the State line, `pause` or the `/clear` rule can mislead a model, and to look for holes in the tests. |
| R.2 | Re-check each claim that can be checked locally before applying it. Record findings and how each was handled in `docs/handoff/review.md`. |
| R.3 | Re-review the delta if a rule changes in response. |

## Phase 0: probes (paid, single runs, headless)

Scratch PoC repos built by a script kept under `docs/handoff/tools/`, no model needed to build them. Each probe runs in a fresh `claude -p` session with only the repo on disk, the plugin loaded from the checkout, and read-only grants.

| ID | Probe | Answers |
|---|---|---|
| P1 | Repo with the 0.2.1 wiring text, a `POC.md`, a `LOG.md` whose last entry carries a `State:` line. Prompt: "Where are we and what should I do next?" | Does a plain first prompt make the session read `POC.md` and the log tail from the wiring alone, and use the State line |
| P2 | Same repo, the 0.2.1 wiring text unchanged, a hand-off file, and a last `State:` line whose `resume:` names it. Same prompt | Does the session follow the `resume:` pointer to the hand-off from the log tail alone |
| P3 | Same as P1 with a commit made after the State line | Does the model notice the repo moved when told to compare, and when not told |
| P4 | `claude -p` with a trivial `SessionStart` hook in a throwaway plugin that prints a marker | Whether SessionStart runs headless and whether the marker reaches the model (answers a spec **(docs)** gap; informs option C only) |

Gate 0: P1 and P2 results recorded in `docs/handoff/findings.md`. If the model ignores the wiring in P1, the spec's recommendation A is reconsidered before Phase 1 and the maintainer is asked. P4 does not gate anything.

## Phase 1: tests first

| ID | Test | File |
|---|---|---|
| 1.1 | The `LOG.md` template in `poc-start` and `poc-checkpoint`'s step text agree on the State line's field names and order | `tests/test_handoff_state.py` |
| 1.2 | Every `Next:` rule containing `/clear` sits in a command whose steps append an entry and read the tail back before printing it | same |
| 1.3 | `poc-checkpoint`'s argument hint lists `pause`, iterate and pivot write the closing entry unconditionally, `pause <topic>` writes the hand-off file, the topic is restricted, an existing file is appended to, never overwritten | same |
| 1.4 | `poc-log` does not write a `State:` line and points a Decision of iterate, pivot or pause at `poc-checkpoint` | same |
| 1.5 | `poc-help` reads the newest `State:` and newest hand-off, names the sha and branch comparison, and the fallback `Next:` | same |
| 1.6 | The stored State line holds a branch name and no path: the template and step text contain no path placeholder | same |
| 1.7 | `pause` is accepted by `poc-help`, `poc-log` and the docs where the other outcomes are listed (every place that lists iterate, pivot, harden, stop) | `tests/test_skills_contract.py` |
| 1.8 | `poc-checkpoint` says `resume:` names the hand-off file when `pause <topic>` wrote one. The wiring text is untouched: the existing layout tests that compare it pass without edits | `tests/test_handoff_state.py` |
| 1.9 | Mutation check: a script like `docs/layout/tools/mutate.py` with one row per rule above (remove the read-back, make iterate conditional again, drop the sha comparison, add a path to the State line, and so on). Every mutation must fail at least one test | `docs/handoff/tools/mutate.py` |

Run the suite: the new tests fail for the expected reasons, the existing 87 still pass.

## Phase 2: implementation

| ID | Change |
|---|---|
| 2.1 | `skills/poc-start/SKILL.md`: add `- State:` to the LOG template as an optional line. Do not touch the wiring text |
| 2.2 | `skills/poc-checkpoint/SKILL.md`: `pause [topic]`, mandatory closing entry for every outcome, State gathering with the three read-only git calls and the worktree check, read-back before any `/clear` line, hand-off file rules, failure path. Keep the paths and docs-folder rules word for word |
| 2.3 | `skills/poc-log/SKILL.md`: accept `pause` as a Decision, point iterate, pivot and pause at `poc-checkpoint`, no State line |
| 2.4 | `skills/poc-help/SKILL.md`: `pause` row text, newest `State:` and hand-off read, `Resume:` line, staleness comparison, fallback |
| 2.5 | `docs/workflow.md`: name the four boundaries and what each leaves, the `pause` outcome, the manual `/clear` rule |
| 2.6 | `README.md`: the checkpoint row mentions `pause`. `CHANGELOG.md` 0.3.0 entry that says what was and was not tested. `plugin.json` 0.3.0 |
| 2.7 | `docs/layout/spec.md`: its "reserved, written by the hand-off spec" line now points at `docs/handoff/spec.md` |
| 2.8 | Check `tests/test_docs_layout.py` and the 87-test suite pass with the wiring text and the Rule A and B copies unchanged, and say so in the changelog |

## Phase 3: verification

| ID | Task |
|---|---|
| 3.1 | Tests, mutation check (36 layout rows plus the new ones), `typos`, `gitleaks`, em dash check |
| 3.2 | Independent `reviewer` on the diff, told to try to break the tests by mutating the skills |
| 3.3 | Manual runner cases on scratch repos, single runs: checkpoint iterate with uncommitted files and an unmerged worktree branch, then `poc-help` fresh; stale state; old log without State; `pause <topic>` then a fresh session; a failed write (read-only docs folder). Record in `docs/handoff/findings.md` |
| 3.4 | The changelog and docs say which behaviours were checked only headless and that no interactive session was run |
| 3.5 | Pre-push review: `gitleaks`, a read of the diff for personal paths, hostnames, deal data, connector IDs |

## Phase 4: cold-start evals (not in 0.3.0)

A case type that runs phase N then a fresh session, graded from files on disk and the final text. Needs a final-text grader and runner support for two linked sessions (see `docs/evals/plan.md` Phase 2), and the terms to have been read. Recorded here so it is not forgotten: the 0.3.0 changelog says the cold-start behaviour was measured by hand only.

## Phase 5: release

PR, `reviewer` re-run on the final diff if anything changed after Phase 3, then merge, tag `v0.3.0` (signed, annotated) and release, each only on the maintainer's explicit yes.

## Risks to the plan

- P1 may show the model ignores the wiring after a clear. Then option A alone is not enough and the maintainer decides on C before Phase 1.
- The `SessionStart` probe (P4) may not run headless. Then C stays untested and stays out.
- The model may not follow a `resume:` pointer from the log tail. P2 measures it. A later `poc-log` entry can sit after the closing entry, which the manual runs in 3.3 include.
- A separate, optional change worth its own branch: commit the Rule A, Rule B and wiring sync script with a `--check` mode, so a future text change is one command. Not part of this plan.
- Single runs hide variance. Findings say "one run each", as the layout findings do.
