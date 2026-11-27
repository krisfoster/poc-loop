# Plan: implementing the stage evals

Implements `docs/evals/spec.md`. Branch: `evals-spec`. Revised after an independent review. Each phase ends with a gate. Do not start a phase until the previous gate passes. Nothing is committed, pushed or opened as a PR without the maintainer asking.

## Target layout

```
evals/
  README.md                 how to run, add a case, read a result, refresh a baseline
  run_eval.py               CLI entry: list, dry-run, run, grade, compare
  harness/
    runner.py               custom runner (decided at Gate 0)
    fixtures.py             builds fixture repos at run time, plants defects, writes answer keys outside the run dir
    graders.py              deterministic graders and oracles
    judge.py                advisory model-graded rubrics
    report.py               per-run JSON, Markdown summary, two-set comparison
  cases/<stage>/<id>.json   prompt, fixture, graders, allowed tools, n_runs, set (tune or holdout), cost cap
  fixtures/<name>/          templates with no secret-shaped literals
  rubrics/                  judge rubrics with stored calibration figures
  baselines/<version>.json  committed counts only
  results/                  gitignored raw output
tests/test_eval_graders.py  unit tests for graders and fixture builder, no model calls, no network
```

`evals/` ships to users with the plugin, so keep it text only and under 200 KB, with no answer keys and no results committed. `tests/test_eval_graders.py` is picked up by the existing `python3 -m unittest discover -s tests`, so it must need no network, no model and nothing beyond the standard library, and it skips cleanly when `git` or `gitleaks` is missing.

## Phase 0: feasibility spike (decides the design)

Status as of 2026-11-25: all tasks run except 0.1, which is mostly covered by the docs pages read for 0.7 and 0.8. 0.4 is partly done: the token route and init-event isolation work, but Anthropic's terms on scripted use of a subscription are unread and plan usage over a larger run is not measured. 0.9 found a plugin defect, logged as F1 in `docs/evals/findings.md`. See `docs/evals/spike-findings.md`.

Consequences already decided: graders read the `result` event with the highest `result_index`, because a background subagent can produce an earlier stale one. A `budget_exhausted` stop is a harness failure, not a stage failure, and per-run caps are never below $0.10. Agent call counts come from `subagent_stats`. Fork and subagent activity is read from events carrying `parent_tool_use_id`, and tool calls are counted from events, not from `num_turns`. `--allowedTools` rules must allow for compound commands being separate commands.

Goal: find out what headless runs can and cannot do, before building anything. Time-box: one day. Output: `docs/evals/spike-findings.md` with the exact commands that worked, the `claude --version` used, and a doc URL and date for every claim. Anything not confirmed by running it or reading the docs is marked unverified.

| ID | Task | Acceptance |
|---|---|---|
| 0.1 | Read the Claude Code docs for headless mode, permission mode defaults, plugin loading, config isolation, `claude plugin eval` and its options. Re-verify each claim in the spec marked "re-verify in 0.1" | Findings list each flag or variable used, with URL and date. The spec is amended where the docs differ |
| 0.2 | Run `poc-log` headlessly against a throwaway repo with the plugin loaded from a copy of this tree | The slash command is accepted despite `disable-model-invocation: true`, the entry is appended, the event log is captured. The minimum `--allowedTools` that lets it write is recorded |
| 0.3 | Run one `context: fork` skill (`poc-verify`) and one skill that calls a subagent (`poc-research` with the question given) | Subagent tool calls, the subagent's resolved model and the forked-skill events (which may arrive after the fork ends and carry a parent id) are visible in the event log, or the gap is recorded |
| 0.4 | Establish isolation: temporary `HOME`, `CLAUDE_CONFIG_DIR` and `XDG_CONFIG_HOME`, authentication by a subscription OAuth token from `claude setup-token` supplied by `op run` (API key only as a fallback), sandboxed | The `system/init` event shows only the allowlisted tools, MCP servers, plugins and agents. A planted `~/.config/spike-loop/research-sources.md` in the real home is not read. No token is printed or stored in the repo. Anthropic's terms on automated use of a subscription are read and the result recorded. Plan usage consumed by one run and rate-limit behaviour are recorded. Whether bare mode and `--tools` can keep the Agent tool is recorded |
| 0.5 | Check budget flags and the result event fields (cost, usage, resolved model IDs, `permission_denials`) | A deliberately over-budget prompt is stopped. The amount by which the cap was exceeded is recorded and sets the headroom for the suite cap |
| 0.6 | Try `AskUserQuestion` paths headlessly (`poc-start`, `poc-research` first use) | Behaviour recorded: skipped, denied or defaulted |
| 0.7 | Try `claude plugin eval` on one trivial case with the ablation arm off, and keep its temporary output | Recorded: is the retained output (event log, file diff, worktree) enough for post-hoc graders. The result is the hybrid or custom decision |
| 0.8 | Check whether the marketplace can exclude `evals/` from the installed copy | Recorded. If there is no exclude, the size budget above stands |
| 0.9 | Check `isolation: worktree` on a subagent: where its changes land and how a grader can read them | The path or git ref is recorded, or the gap is recorded |
| 0.10 | Check that `skills:` preloading in the agents (`researcher`, `reviewer`, `debugger`) works under headless and isolated runs | The preloaded skill text is visible in the event log, or the gap is recorded |

**Gate 0: passed on 2026-11-25, with conditions.** 0.2 (a slash command runs headlessly with the plugin loaded) and 0.4 (the subscription token authenticates an isolated run) both worked, so the design is available as written. **Decision: a custom runner**, for the reasons in `docs/evals/spec.md` under "Runner decision". `claude plugin eval` stays optional for model-graded rubrics.

Conditions carried forward: (1) Anthropic's terms on scripted use of a subscription must be read, and the maintainer's organisation's own policy checked, before the first suite larger than a smoke test, which means before Gate 1 runs more than a handful of cases. (2) Plan usage over a larger run is measured in Phase 1 (task 1.8). (3) Finding F1 is fixed on a separate branch, not here.

## Phase 1: harness core

Status as of 2026-11-26: 1.1 to 1.7 and 1.9 done and unit-tested (37 harness tests, no model needed), plus live `poc-log/basic` runs through the runner (passed, about $0.004 estimated). An independent review of the code found six major and seven minor issues, all fixed and covered by tests (see `docs/evals/spike-findings.md`). 1.8 (variance measurement) was run on 2026-11-26 on the one existing case: 10 of 10 passed, cost about $0.0039 per run (see `evals/README.md`). That case cannot show score noise, so the provisional thresholds stay and the measurement is repeated on the Phase 2 cases. The Gate 0 condition about reading Anthropic's terms was not confirmed before this run, and still stands for larger suites. Sandboxing (spec, harness requirement 4) is not implemented: the runner refuses `Bash`, `WebFetch` and `WebSearch` grants unless `--unsandboxed-ok` is passed.

| ID | Task | Files | Acceptance |
|---|---|---|---|
| 1.1 | Runner (custom, per Gate 0), built from the Phase 0 prototype scripts: temp dir per run, plugin loaded from a copy without `evals/`, per-case `--allowedTools`, per-run budget, capture of event log, file diff and worktree | `harness/runner.py` | One `poc-log` case runs and writes a result JSON with final text, tool calls, `permission_denials`, cost, model IDs and file diff |
| 1.2 | Isolation assertion run on every case, comparing `system/init` to the allowlist | `harness/runner.py` | A run that sees an unexpected tool, MCP server or agent is marked invalid, not scored |
| 1.3 | Case schema and loader, with validation errors that name the file and field | `run_eval.py`, `cases/` | A malformed case is rejected before any model call |
| 1.4 | Dry-run: list cases, `n_runs`, caps and estimated cost, no model calls. Estimates come from measured costs once available, otherwise printed as `unmeasured` | `run_eval.py` | Dry-run makes zero network calls (checked with the network disabled) |
| 1.5 | Suite-level budget cap with headroom from 0.5, clean stop reporting what did not run | `run_eval.py`, `report.py` | A tiny cap stops the suite part-way and lists skipped cases |
| 1.6 | Reporter: per-run JSON, Markdown table of passes over runs per case and stage, plugin version, `claude --version`, resolved model IDs, date. Baselines hold counts only | `report.py` | Table renders from fixture result files without calling a model, and a baseline file contains no free text from model output |
| 1.7 | Compare command implementing the regression rules in the spec, including the N=5 rerun trigger | `report.py` | Given synthetic result sets it flags exactly the cases and stages that meet the rule and none that do not |
| 1.8 | Variance measurement: run the cheap deterministic cases 5 times, twice | `results/` | Observed score noise recorded, and the provisional thresholds in the spec are replaced with measured ones. Done for cost and behaviour on `poc-log/basic` (zero score noise, so the thresholds are not replaced). Repeat on the Phase 2 cases before Gate 2 |
| 1.9 | `.gitignore` entry for `evals/results/` | `.gitignore` | `git status` shows no result files after a run |

**Gate 1: passed on 2026-11-26, with one carry-over.** Cost per `poc-log` run and the measured noise are recorded in `evals/README.md`. The score-noise measurement is only partial (one case, always passing), so the Phase 2 gate repeats it.

## Phase 2: deterministic graders and cheap stage evals

Write each grader with its unit test first, using hand-made good and bad outputs, then add the live case.

**Status (2026-11-27).** 2.1 done: the grader library, including `final_text_regex` for stop and refusal messages, with unit tests in `tests/test_eval_graders.py`. A `command_exit` grader makes its case count as unsandboxed. 2.2 done as a smoke result: six new `poc-log` cases, 17 of 18 runs passed, one plugin defect logged as F2. 2.3 to 2.5 written, not run: 7 `poc-start`, 10 `poc-checkpoint` and 6 `poc-verify` cases, each checked against a hand-made correct result and a planted defect (`docs/evals/tools/selfcheck/`), with three more graders (`questions_before_write`, `git_clean_history`, `files_matching`, and glob targets). What is not graded yet is listed in `evals/README.md`. Gate 2 is not started, and runs beyond a smoke set still wait on reading Anthropic's terms.

**Layout note (2026-11-26).** The `poc-spec/` layout is on `main` (see `docs/layout/spec.md`). Stage cases from here on use the new layout by default and add one older-layout case where the stage reads `POC.md` or `LOG.md`. The runner now takes two optional case fields, `cwd` and `add_root_dir`, so a case can start in a subdirectory with or without the repo root added as a directory. Fixtures: `poc-log-basic` is the older layout, `poc-log-specs` the new one (with `sub/deep`), `poc-log-both` has both. A skill that runs `git -C` needs `Bash(git *)`, and each part of a compound command needs its own grant. Five `poc-log` cases exist for this (`basic`, `poc-spec-layout`, `subdir-root-added`, `subdir-root-not-added` which expects a clean refusal under the harness's strict read setting, and `both-layouts`). The remaining layout cases in `docs/layout/spec.md` (`poc-start`, `poc-checkpoint`, packager warning) are ported from the manual checks in `docs/layout/tools/manual/` as the Phase 2 stages are built.

| ID | Task | Acceptance |
|---|---|---|
| 2.1 | Grader library: file exists and absent, regex, heading match, no placeholders, line cap, em dash absence, file byte-identical, executable bit, exit code of a command in the fixture, tool-call count, no tracked file modified, canary absent | Each grader has a passing and a failing unit test |
| 2.2 | `poc-log` cases (fresh log, earlier entries, with and without time, timebox exceeded, missing files) | Spec row satisfied, N=3 |
| 2.3 | `poc-start` cases with scripted answers, tier 0, public repo, existing file, no git repo, and the `CLAUDE.md` wiring check. Set the `POC.md` line limit from the measured template | Spec row satisfied, N=3. Paths that need `AskUserQuestion` follow the 0.6 finding |
| 2.4 | `poc-checkpoint` cases for the four outcomes given as arguments, and an empty argument graded as recommend-and-ask | Spec row satisfied, N=3 |
| 2.5 | `poc-verify` fixtures per the verdict oracle (pass, fail, Makefile only, stub, manual, many-service) | Verdicts match the oracle, stub never PASS, no tracked file modified, started processes torn down |

**Gate 2.** Repeat the 1.8 variance measurement on the Phase 2 cases (5 runs, twice) and replace the provisional thresholds in `thresholds.json` and the spec with measured ones. The deterministic suite runs end to end under its budget cap and produces a result table. Failures are triaged: each one is a real plugin defect (logged, not fixed here) or a bad case (fixed here).

## Phase 3: review eval

| ID | Task | Files | Acceptance |
|---|---|---|---|
| 3.1 | Fixture builder: Python service template, empty base commit on `main`, the service with defects on a branch, a defect library using natural code text, an answer key written outside the run directory | `harness/fixtures.py`, `fixtures/` | A unit test opens each key line in a built repo and checks the planted defect is there, and that `git diff main..<branch>` is non-empty for seeded repos and for controls |
| 3.2 | Secret-safety checks | `tests/test_eval_graders.py` | A unit test greps the committed tree for secret-shaped literals and fails if any exist. A separate test runs `gitleaks dir evals/` and is skipped when `gitleaks` is missing |
| 3.3 | Finding parser for the reviewer output contract (rank, file:line, evidence) and the one-to-one matcher with the nearer-defect and human-list tie rules | `harness/graders.py` | Unit tests on hand-written outputs: a finding with no file:line, an off-by-one line, one finding between two close defects, fifteen scattered findings that must not raise recall |
| 3.4 | Metrics: recall per category, precision, unmatched BLOCKER and MAJOR counts, evidenced-findings rate, tool-call count | `harness/graders.py`, `report.py` | Unit-tested against synthetic outputs |
| 3.5 | Six seeded repos and three clean controls, with each defect category in a different form in tune and holdout | `cases/review/` | Each category appears in both sets, and no defect instance appears in both |
| 3.6 | Run `reviewer` and `reviewer-lite` on the tuning set, N=3 | `results/` | Report shows recall and precision by category for both |
| 3.7 | Read-only check: no tracked file changed by either reviewer | `harness/graders.py` | Passes on the live runs |

**Gate 3.** A human reads a sample of at least 10 results from 3.6, covering ambiguous matches and unmatched findings, and confirms the matcher credited no wrong finding and missed no right one. If the matcher disagrees with the human in more than 2 of 10, fix the matcher before trusting any recall or precision figure. The holdout set is not run until the matcher passes.

## Phase 4: package, harden, debug, build

| ID | Task | Acceptance |
|---|---|---|
| 4.1 | `poc-package` cases: missing README, undocumented env var, planted secret and hostname, canary `.env`. Clean-clone oracle runs `./verify.sh` in a fresh copy with dummy variables | Spec row satisfied. Secret value and canary are absent from output and written files (grep) |
| 4.2 | `poc-harden` cases: planted blocker stops at the gate, clean repo completes lean, tier 2 and `full` take the full path, last Decision not `harden` stops with the question. Fixtures set the last Decision to `harden` except in that case | Spec row satisfied, including reviewer and packager call counts from the event log |
| 4.3 | `poc-debug` cases with hidden tests, including the wrong-obvious-fix and unreproducible cases. Fix graded only when a diff block is present | Root cause named, diff applies and passes hidden test on a copy, or recorded as not graded |
| 4.4 | `poc-build` cases with hidden tests, a brief naming allowed files beside an adjacent bug, and the missing-done-condition brief. Run the skill as shipped and also the implementer through the Agent tool. Read changes from the worktree found with `git worktree list --porcelain` when one exists, otherwise from the main tree, ignoring the untracked `.claude/`. Report whether a worktree was created, which is finding F1 | Hidden pass rate reported, adjacent bug untouched, worktree creation reported per path |

**Gate 4.** Same triage rule as Gate 2.

## Phase 5: research eval (periodic, non-gating)

| ID | Task | Acceptance |
|---|---|---|
| 5.1 | Local-repo "internal" source fixture with a planted fact and a decoy stale document, with the sources file written into the run's temporary config directory | Planted fact retrieved, decoy flagged as stale |
| 5.2 | Known-answer public questions chosen from slow-changing facts, with a stale-answer trap, an unanswerable question, an empty question, and a first-use non-interactive run. Each case records the date its answer was last confirmed | Cases carry a confirmation date. A run on a case older than 90 days warns |
| 5.3 | Citation and freshness graders (each claim has a source with date or version) and the outbound-query privacy check using a planted customer name | Unit-tested on hand-made outputs |

**Gate 5.** Results are reported separately from the gating suite, with the run date.

## Phase 6: judge rubrics

| ID | Task | Acceptance |
|---|---|---|
| 6.1 | Judge wrapper that hides the variant and records the judge model ID | Unit test confirms variant labels are stripped from the prompt |
| 6.2 | Rubrics for `poc-start` assumptions, `poc-research` answer quality, `poc-checkpoint` evidence | Each rubric stored with its calibration figures |
| 6.3 | Calibration: the maintainer labels at least 20 outputs per rubric with a balanced pass and fail mix. Compute kappa and per-class agreement | A rubric below kappa 0.6, or with a class below 70 percent agreement, is marked unusable and excluded from the report |

**Gate 6.** Judge scores appear in the report as advisory columns only.

## Phase 7: trust the evals, then document

| ID | Task | Acceptance |
|---|---|---|
| 7.1 | Mutation check script: apply a weakening to a copy of the plugin, run the matching eval, restore. Five weakenings at minimum, each applied to every place that states the behaviour: remove "never overwrite" from `poc-start`, change the `verify.sh` stub from `exit 1` to `exit 0`, remove the evidence requirement from `reviewer` and `reviewer-lite`, remove the no-staging rule from `packager`, `poc-package` and `poc-harden`, drop the tier check from `poc-harden` | Each weakening ends as caught, or as "behaviour unchanged" with the reason, and at least three are caught. The original tree is unchanged afterwards (checked with `git status`) |
| 7.2 | Whole-loop run on one longer task, scored by hidden suite, review recall and cost | Result recorded next to `docs/measurements.md` and referenced from it |
| 7.3 | Baseline of counts for the current plugin version, committed after a secret and confidentiality review | `gitleaks`, `typos` and a manual read find no finding text, secrets, or anything from the maintainer's config, deals or customers |
| 7.4 | `evals/README.md`: add a case, read a result, refresh a baseline, measured cost per suite, known limits, the free versus paid split | A reader follows it from a clean clone and reproduces the grader unit test results exactly. Live results are described as stochastic and are not expected to match |
| 7.5 | Add an Unreleased entry to `CHANGELOG.md`, link the evals from the main `README.md` | Typos clean, no em dashes |

**Final gate.** The six success criteria in the spec are each demonstrated, then `typos`, `gitleaks` and the em dash grep pass on the whole branch, and a fresh independent review of the branch finds no blocker.

## Rules for this branch

- Run `typos` on changed files and `gitleaks dir .` before each commit. Add intentional words to `_typos.toml`.
- No em dashes in any file.
- Never print, read or commit `.env`. API keys come from 1Password references loaded through `op run`.
- Findings about plugin defects discovered by the evals are logged in `docs/evals/findings.md` and fixed on a separate branch, so a score change is never confused with an eval change.
- Before any push or PR, review the outgoing diff for secrets and confidential information.

## Risks

| Risk | Effect | Mitigation |
|---|---|---|
| Headless mode cannot run these skills as written | Design invalid | Phase 0 gate, amend the spec |
| User or plugin config leaks into runs | Scores describe the maintainer's setup | Temporary `HOME`, `CLAUDE_CONFIG_DIR` and `XDG_CONFIG_HOME`, init-event allowlist on every run |
| Subscription token route fails, or automated use is not permitted, or runs exhaust the plan allowance | No way to authenticate, or normal work is rate-limited | 0.4 check before anything is built, API key fallback, small suite sizes and run counts, usage recorded per run |
| Headless permission defaults deny writes | Stages fail for harness reasons | Pinned `--allowedTools`, `permission_denials` recorded and reported separately |
| Runs execute web and shell tools on the maintainer's machine | Exposure of local files | Container or sandbox with no home directory access |
| Claude Code changes the stream-json event format or result fields between versions | Graders misread runs | Record `claude --version` per run, a unit test on a saved event log per version, and an isolation check on every run |
| Model aliases drift (`opus`, `sonnet`, `haiku` resolve to new versions) | Baselines stop being comparable | Record resolved IDs and `claude --version`, compare only like with like |
| Run-to-run variance hides small changes | False confidence | Measured noise in Phase 1, counts over N runs, rerun at N=5 before calling a regression |
| Matcher credits the wrong finding or rewards scattered findings | Recall wrong | One-to-one matching, precision reported, Gate 3 human check |
| Cost grows with N | Evals stop being run | Budget caps with headroom, dry-run, cheap deterministic cases |
| Prompts tuned to the cases, or agents reading the cases | Overfitting or leakage | Tune and holdout split, plugin loaded from a copy without `evals/`, keys outside the run dir |
| Fixtures trip the repo's secret scan or leak a real value | Blocked push or exposure | Run-time generation, counts-only baselines, unit test for committed literals |
| `evals/` bloats the installed plugin | Slower install for users | Size budget, text only. 0.8 confirmed it ships and cannot be excluded without moving the plugin to a subdirectory |
| Web-dependent research cases rot | Flaky or wrong cases | Periodic, non-gating, dated, 90 day warning |
| A mutation does not change behaviour | Looks like an eval failure | "Behaviour unchanged" is a separate, reported outcome |
