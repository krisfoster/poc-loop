# Plan: prerequisites and the scripted time check

Spec: `docs/prereqs/spec.md` (draft 2). Reviews: `docs/prereqs/review.md`. Branch: `prereqs`.

Order: probes first (they decide two design points), then the free work with tests written before the code, then paid checks, then an implementation review. Each phase ends with `python3 -m unittest discover -s tests` passing, `typos` clean and no em dashes.

## Phase 0: probes (paid, one run each, capped at $0.25 per run). Done 2026-11-27, see `findings.md`: all three as hoped, $0.013

| ID | Task | Decides |
|---|---|---|
| P1 | A throwaway plugin skill whose `allowed-tools` lists `Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/x *)` and the quoted form, run headless with `--allowedTools` not granting it: does the call run or get denied? Repeat with the plugin copied to a directory whose path holds a space | Whether eval cases must grant the checker (and need the `{plugin}` placeholder), and whether both rule spellings are needed |
| P2 | The same skill with `context: fork` and a throwaway agent whose body also says to run the checker unless told it ran | Whether the grant reaches the fork, and whether the skip sentence works |
| P3 | A headless run with `python3`, `python3.*` and `python` hidden by the planned `PATH` mechanism, asked to report `command -v python3` and to run `python3 --version` | Whether hiding works under the runner's isolated `HOME` |

Probe scripts go in `docs/prereqs/tools/probes/`, reusing `docs/layout/tools/probes/probe_run.py` for isolation and token handling. Results in `docs/prereqs/findings.md`. Estimated cost under $0.15.

## Phase 1: checker and registry (free)

| ID | Task | Acceptance |
|---|---|---|
| 1.1 | `tests/test_check_prereqs.py` first (spec, Tests 1) | Fails: no checker yet |
| 1.2 | `scripts/check-prereqs`: registry for `git`, `python3`, `rsync`, `gitleaks`, `typos`; output and exit codes per spec section 1 | 1.1 passes on macOS; `sh -n` clean; `shellcheck` clean if installed |
| 1.3 | `docs/prerequisites.md` and a test that it matches the registry; README Requirements points at it | Test passes; a changed message in the script fails it |

## Phase 2: time check script (free)

| ID | Task | Acceptance |
|---|---|---|
| 2.1 | `tests/test_time_check.py` first (spec, Tests 2) | Fails: no script yet |
| 2.2 | `skills/poc-log/scripts/time_check.py` per spec section 3, standard library, 3.9+ | 2.1 passes |

## Phase 3: skills and agents (free)

| ID | Task | Acceptance |
|---|---|---|
| 3.1 | Contract tests first (spec, Tests 3), including the rewritten F2 and F3 pins | Fail on the current skills |
| 3.2 | Prerequisites paragraph and `allowed-tools` in the 11 skills plus `poc-sources`; the agent paragraph with the skip sentence in the 7 agents; "prerequisites checked" in the briefs `poc-build` and the forked skills give | 3.1 passes |
| 3.3 | `poc-log` steps 4 and 5 per spec section 4 | 3.1 passes; `poc-log` frontmatter has both script rules |
| 3.4 | Mutation rows (spec, Tests 4) in `docs/handoff/tools/mutate.py`; stale rows that quote the old `poc-log` text updated | Every row caught, negative control passes |
| 3.5 | `docs/evals/findings.md` F2 and F3: note that both move to the script | Text only |

## Phase 4: eval support (free)

| ID | Task | Acceptance |
|---|---|---|
| 4.1 | Runner: `hide_tools` case field (spec, Evals), with unit tests using the fake runner | A hidden tool is not on the run's `PATH`; versioned aliases hidden; nothing else changes |
| 4.2 | `tool_call_count` gains `input_regex`, with tests. (The `{plugin}` placeholder is not needed: P1 showed the skill's own grant applies headless) | Unit tests pass |
| 4.3 | Cases: `poc-log/missing-python`, `poc-research/missing-python`, `poc-start/missing-git`; existing `poc-log` time graders tightened to the script's format plus checker and script call counts | Self-check (good and planted-bad result per case) passes |

## Phase 5: paid verification

| ID | Task | Est. cost |
|---|---|---|
| 5.1 | The three new cases, 3 runs each | about $0.40 (`poc-research` on Sonnet, `poc-start` on Opus) |
| 5.2 | `poc-log` cases at the F2 sample size, about 20 runs | about $0.10 |
| 5.3 | Every other Phase 2 stage case once, because every skill gains a first step | about $2.10 |

Smoke sizes only, as for the rest of Phase 2 until the terms are read.

## Phase 6: review and docs

| ID | Task |
|---|---|
| 6.1 | Independent `reviewer` on the implementation diff, findings recorded in `review.md` and handled |
| 6.2 | CHANGELOG (Unreleased), README, `docs/workflow.md` if it describes a first step |
| 6.3 | Pre-push review for secrets and private data, then a PR on the user's yes |

## Defaults taken for the spec's open questions (change on request)

1. `engines` in `plugin.json`: not in this change.
2. `poc-checkpoint` and `poc-help` keep their own elapsed text.
3. `rsync` stays, recorded as a packager requirement.
