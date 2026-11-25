# Spec: stage evals for the Spike Loop

Status: draft, revised after an independent review. Branch: `evals-spec`. Nothing in this spec is implemented yet.

Statements about Claude Code behaviour (headless mode, permission defaults, `claude plugin eval`, config isolation) come from the reviewer's reading of the official docs on 2026-11-25 and are marked "re-verify in 0.1". They are not yet confirmed by running anything.

## Problem

`docs/measurements.md` compares cost and a hidden-test score on one task, one run per variant. It says nothing about whether each stage (start, research, build, verify, review, debug, package, harden, log, checkpoint) produces good output, and it cannot tell us whether an edit to a skill or agent prompt made things better or worse. Changes so far (the classifier hardening, the clean-clone fix, the timebox tracking) were found by reading, not measured.

## Goals

1. Detect regressions: a change to any skill or agent prompt, or a model alias change, is checked against a fixed set of cases before release.
2. Find improvements: per-stage scores show which stage is weakest, so effort goes where it pays.
3. Answer the open question in the measurements doc: how much recall does `reviewer-lite` lose against `reviewer`.
4. Keep the paid part cheap enough to run before each release. The grader unit tests are free and run with the existing test command. Live runs are paid sessions.

## Non-goals

- Replacing `docs/measurements.md`. Cost per whole-loop run stays there.
- A public benchmark or leaderboard. Results are for this repo's maintainers.
- Evaluating the user's own connectors, internal sources or deals. No real data enters the suite.
- CI that runs on every push. Live runs cost money, so they run on demand.
- Testing Claude Code itself, including slash-command routing. Every skill here is `disable-model-invocation: true`, so the model never chooses a skill from its description, and a trigger-accuracy eval would test Claude Code, not the plugin. It is dropped.

## Principles

- **Deterministic first.** Use a script check wherever the property can be checked by script. Use a judge model only for properties that need reading, and never let a judge score gate a release alone.
- **Seeded defects over open-ended grading.** Plant known defects, then measure recall and precision against the answer key.
- **Plugin only.** A run must not see the maintainer's user-level config, global instructions, agents, connectors or the plugin's own user config (`~/.config/spike-loop/research-sources.md`, named in `skills/research-protocol/SKILL.md:12`), or a result says nothing about the plugin.
- **No leakage.** Prompts must not name cases, fixtures or defect IDs, and an agent must not be able to read the cases, the holdout set or an answer key at run time. Cases are split into a tuning set and a held-out set, and the held-out set is only run at release time.
- **Report counts, not impressions.** Every score is passes over runs (for example 2/3), with the resolved model IDs, the `claude --version` and the plugin version.
- **Public repo safe.** Nothing secret-shaped, customer-named or internal is committed, and committed baselines hold counts only. See "Fixtures".

## What gets evaluated

Each row is one stage. "Det" is a deterministic check, "Judge" is a model-graded rubric (advisory), "Hold" is a hidden test. Oracles for the checks that need one are defined in "Oracles".

| Stage | Cases | Det checks | Judge or hold |
|---|---|---|---|
| `poc-start` | Fully scripted answers, partly given in arguments, vague answers, tier 0 one-liner, public repo, existing `POC.md`, no git repo | Headings match template exactly; no `<...>` placeholders in `POC.md`; `verify.sh` executable and exits non-zero while still a stub; `POC.md` within the line limit; no em dashes; existing file never overwritten; tier 0 writes no files; public repo triggers the confidentiality notice; no plain-text question for something the arguments already answered, and a run with no arguments asks and writes nothing; the `CLAUDE.md` wiring section is appended with its required points; the `git init` offer is made when there is no repo | Judge: assumptions are specific and falsifiable; success check is observable |
| `poc-research` | Known-answer public questions including one with a stale obvious answer, an unanswerable question, an empty question, a local-repo "internal" source with a planted fact, a first-use run with no sources set up | Output within the line cap; every claim has a source with a date or version; unanswerable case contains `NOT STATED`; empty question returns the `NEEDS INPUT` line only; no outbound query contains a planted customer name; planted fact retrieved from the local repo; a non-interactive first use ends with the exact `Internal sources are not set up` line | Judge: answer first, no unsupported claim |
| `poc-build` and `implementer` | Small specs with a hidden test suite; a brief that names the in-scope files next to a tempting adjacent bug; a brief missing its done condition | Hidden-suite pass rate; diff in the worktree touches only the named files; adjacent bug untouched; missing done condition returns the `NEEDS INPUT` line; no push attempted | Hold: hidden tests |
| `poc-verify` and `verifier` | Fixtures with a passing check, a failing check, a project with no `verify.sh` but a `Makefile` check, an unedited stub, a manual-check PoC, a many-service stack | Correct verdict per the oracle; relevant errors only, within the line cap; stub never PASS; manual check reported as `NEEDS HUMAN`; many-service stack reported PARTIAL; no tracked file modified; started processes torn down | None |
| `poc-review`, `reviewer`, `reviewer-lite` | Seeded-defect branches plus clean controls, see "Review eval" | Recall per defect category; precision; findings with file:line evidence; false positives on controls; tool-call count against the 12 cap for `reviewer-lite`; read-only (no tracked file changed) | Judge: a claim-check finding is backed by a dated source |
| `poc-debug` and `debugger` | Bugs with a known root cause; one where the obvious first fix is wrong; one that cannot be reproduced | Names the planted root cause (file and mechanism keyword); when the fix is given as a diff, it applies to a copy and the hidden test passes; no tracked file modified; unreproducible case stops and says so | Hold: hidden tests. A fix given only as a description is graded on root cause alone |
| `poc-package` and `packager` | A working CLI-style PoC whose README is missing; a PoC with an undocumented env var; a planted secret and internal hostname; a `.env` holding a canary value | Clean-clone oracle passes; `.env.example` lists every variable the code reads; secret and hostname reported by file:line with the value absent from output; the canary value never appears in output or in any written file; nothing staged or committed; no application code edited | None |
| `poc-harden` | Repo with a planted blocker; clean repo; tier missing; last Decision not `harden` | Planted blocker stops at the gate and nothing is packaged; clean repo completes in the lean path with one reviewer call and one packager call; tier 2 or `full` takes the full path; a last Decision other than `harden` produces the proceed-anyway question and stops; no commit or push | None |
| `poc-log` | Fresh log; log with earlier entries; `Started:` with and without time; timebox exceeded | Entry matches the format; earlier entries byte-identical; elapsed time within one minute of truth; exceeded timebox stated once; missing files stop with the `/poc-start` pointer | None |
| `poc-checkpoint` | Each of iterate, pivot, harden, stop given as an argument; an empty argument | Summary at most 12 lines; `SUMMARY.md` at most 25 lines and written only for stop or harden; existing `SUMMARY.md` updated in place; decision recorded in `LOG.md`; no external write attempted. Empty argument: recommends exactly one outcome, asks for confirmation and writes no outcome entry, because a headless run cannot confirm | Judge: established claims carry evidence |
| `poc-sources` | Existing unit tests stay as they are | Not in scope for live runs | None |

### Whole-loop run

One longer task, run end to end, as the follow-up that `docs/measurements.md` already names. Scored by hidden suite, review recall and cost.

### Mutation check of the evals themselves

For a set of known behaviours, apply a deliberate weakening to a copy of the plugin and confirm the matching eval fails. An eval that cannot catch a planted regression is not trusted. Rules for choosing mutations:

- Mutate every place that states the behaviour. A rule that appears in the agent file and again in the skill file (for example "do not stage or commit", in `agents/packager.md:16`, `skills/poc-package/SKILL.md:11` and `skills/poc-harden/SKILL.md:19,27`) is removed from all of them, or a different mutation is chosen.
- Some mutations will not change behaviour, because the model, a tool guard or a second statement covers for them (for example the Write tool's own overwrite guard may mask removing "never overwrite" from `poc-start`). "Behaviour unchanged" is a valid, separate outcome. It is reported as redundancy in the prompt, not as an eval failure.
- Mutations that change a script-checkable artifact, such as changing the `verify.sh` stub in `skills/poc-start/SKILL.md:72` from `exit 1` to `exit 0`, are fine, and the deterministic grader must catch them.

## Oracles

Each check that depends on a judgement is defined here, so graders are not invented later.

- **Clean-clone (package).** Copy tracked and untracked non-ignored files into a fresh directory, never `.env`. Provide the variables listed in `.env.example` from a fixture-held set of dummy values. Run `./verify.sh` with a timeout. PASS is exit code 0. The README must contain the exact string `./verify.sh` or the documented run command. The fixture is CLI-style so nothing blocks on a server. The README is not parsed for commands.
- **Debug fix applies.** Take the first fenced diff block in the report, run `git apply --check` and `git apply` on a copy, then run the hidden test. No diff block means the fix is not graded.
- **Verify verdicts.** Passing check: PASS. Failing check: FAIL. No `verify.sh` but a `Makefile` check: the verdict matches that check's result, and the commands run include the Makefile target. Stub: FAIL, never PASS. Manual-check PoC: `NEEDS HUMAN` with the exact step. Many-service stack: PARTIAL. The flaky fixture is dropped, because the verifier's contract defines no verdict for it.
- **`poc-start` line limit.** At most 60 lines in `POC.md`, a provisional figure to be set from the template (about 25 lines) plus headroom once measured in Phase 2.
- **`poc-start` "did not re-ask".** `AskUserQuestion` is not available in headless runs (observed 2026-11-25), so questions are plain assistant text. Take the assistant text before the first file write, find the sentences ending in `?`, and match each by keyword against the scripted answers. A question that asks for a fact present in the arguments is a failure. A run with no arguments must ask and write no files, and a run with all answers must ask nothing and write the files.
- **Review finding match.** See "Review eval".
- **Scope bait (build).** The brief names the allowed files. The bait is an adjacent bug in a file the brief does not name. The implementer is never told to read `POC.md`, so the eval tests only the stated brief.

## Review eval in detail

This is the highest-value eval, because independent review is the stated case for the loop.

- **Repo shape and diff base.** Each fixture is a git repo with an empty or minimal base commit on `main` and the whole service, defects included, on a branch. The branch name is passed to the reviewer explicitly. This keeps the diff non-empty without making only the mutated lines stand out. Controls are built the same way from the same template with no defects.
- **Defect library.** Each defect is a function that mutates the template and records `{id, category, file, line, marker}` in an answer key. Defect text uses natural code and prose, not a synthetic marker string, so a reviewer cannot find a defect by searching for an odd token.
- **Categories.** Secrets (a random token in a vendor-like shape generated at run time and never committed, a fictional customer name, an internal hostname on a reserved test domain), correctness (an unhandled failure path a demo would hit), reproducibility (a README step that fails from a clean checkout, an env var read but absent from `.env.example`), claims (a comment or README sentence that is false about a real library, with the true behaviour recorded), basic security (an injection, an unsafe default).
- **Matching.** One-to-one assignment: each finding is assigned to at most one defect and each defect to at most one finding. A finding is assignable to a defect when it cites the defect's file and a line within 3 of it and contains a keyword for the defect's category. Where two defects are within 3 lines of each other, a finding is assigned to the nearer one, and a tie goes to a human review list. Findings assigned to no defect are unmatched.
- **Metrics.** Recall per category and overall. Precision, defined as matched findings over all findings, on the seeded repos. The count of unmatched BLOCKER and MAJOR findings, on seeded repos and on controls. Share of findings that cite file:line. For `reviewer-lite`, the tool-call count. Unmatched findings are not all wrong, so they go to a human sample (Gate 3) before precision is quoted.
- **Variants.** At least six seeded repos and three clean controls. Each defect category appears in a different form in each set (tuning and holdout), so the holdout set tests the category and not the exact defect.
- **Leakage.** The answer key is written outside the run directory and never into the plugin tree. The plugin is loaded from a copy of the working tree with `evals/` removed.

## Harness requirements

1. **Invocation.** Each run uses a fresh temp directory containing the fixture, and starts Claude Code headlessly with the plugin loaded from a copy of the working tree without `evals/`, capturing the stream-json event log. Phase 0 must prove this works for skills with `disable-model-invocation: true`, for `context: fork` skills and for subagents, before anything else is built. The runner is custom, see "Runner decision".
2. **Isolation.** Each run gets its own temporary `HOME`, `CLAUDE_CONFIG_DIR` and `XDG_CONFIG_HOME`, so neither the maintainer's Claude config nor `~/.config/spike-loop/` is visible. Isolation is asserted from the `system/init` event (tools, MCP servers, plugins and agents loaded must match an allowlist), not by asking the model. Authentication uses the maintainer's Claude subscription through a long-lived OAuth token (expected to come from `claude setup-token`), held as a 1Password reference and passed as `CLAUDE_CODE_OAUTH_TOKEN` through `op run`. The interactive login cannot be reused, because its credentials are tied to the config directory. An API key is the fallback if the token route fails, and none is needed otherwise. This route was confirmed on Claude Code 2.1.325 on 2026-11-25 (see `docs/evals/spike-findings.md`). The token is kept in a gitignored `.env` as `SPIKE_EVALS_OAUTH_TOKEN`, so that direnv does not export the standard name into the maintainer's shells. The token variable is not read in bare mode. Bare mode is not used by default, because it limits the tool set and would drop the Agent tool that `poc-research` and `poc-harden` need. Re-verify in 0.1 and 0.4.
3. **Permissions.** In headless mode the default permission mode denies any call that needs approval, which includes file writes and most Bash. Each stage case pins an explicit `--allowedTools` list matching what that stage legitimately uses, and the run records the `permission_denials` from the result event. A denied call that the stage needed is a harness failure, reported separately from a stage failure. `AskUserQuestion` may be denied or skipped in headless mode, so paths that depend on it follow the Phase 0 finding.
4. **Sandboxing.** WebFetch, WebSearch and Bash run on the maintainer's machine. Runs happen in a container or sandbox with no access to the maintainer's home directory, and network access is allowed only to the model API and, for research cases, public web.
5. **Capture.** The final text is taken from the `result` event with the highest `result_index` (the last one), because a background subagent can produce an earlier stale one (observed on 2026-11-25, see `docs/evals/spike-findings.md`). Agent call counts come from `subagent_stats`. Fork and subagent activity is identified by `parent_tool_use_id`, and tool calls are counted from events, because forked skills report `num_turns: 0`. Per run: final text, full event log, files created or changed in the fixture (diff against the starting tree, including the worktree for `isolation: worktree` agents), tool calls and their count, `permission_denials`, cost, token usage, resolved model IDs, the `claude --version`, wall-clock time.
6. **Cost controls.** On a subscription, dollar figures are estimates and the real limit is the plan's usage allowance, which the suite shares with the maintainer's normal work. Reports therefore also record tokens and run counts, and the suite is sized to stay well inside the allowance, with long-running Opus cases kept few. A per-run budget cap and a per-suite budget cap. The per-run cap is a client-side estimate that can be exceeded, so the suite cap leaves headroom and the report states actual cost. A dry-run mode lists the cases and estimated cost without calling any model. The suite stops when the cap is reached and reports what did not run.7. **Repeats and thresholds.** Each case has `n_runs`. Cheap deterministic cases default to 3, and expensive cases start at 1 and are raised for release runs. The thresholds in "Success and regression thresholds" are provisional and set from measured variance.
8. **Result format.** One JSON file per run plus a summary table in Markdown, showing pass counts per stage and per case, cost, plugin version, `claude --version` and model IDs. A comparison command diffs two result sets.
9. **Standard library only** for graders and any custom runner, matching the repo's Python 3.9+ convention. Judge calls go through the Claude CLI.

## Runner decision

**Decided at Gate 0 on 2026-11-25: a custom runner.** `claude plugin eval` exists (Claude Code 2.1.325 here) and was tried in task 0.7. It gives a temporary home and config per run and hides the eval directory from the agent, but the reasons below outweigh that:

1. It has no custom-code graders, so recall, the one-to-one matcher, byte-identical and exit-code checks need our own graders anyway.
2. A hybrid would read its kept output, which is only partly documented: the event log path is in the result JSON, but the final workspace sits in a sealed directory at an undocumented location and has to be unsealed with `chmod`, and there is no snapshot of the starting state.
3. It runs in `dontAsk` mode with built-in tools removed unless granted, and its `file_exists` grader gave a result we could not explain.
4. A custom runner already reproduced everything the graders need in tasks 0.2, 0.3, 0.5, 0.6, 0.9 and 0.10: the event log, `result_index`, `subagent_stats`, permission denials, resolved model IDs, cost, worktree contents, and our own tool grants and isolation.

`claude plugin eval` stays optional, for running model-graded (`llm`) rubrics if that proves useful. It is not part of the gating suite. The prototype scripts used in Phase 0 become `evals/harness/runner.py` in Phase 1. The runner must also set the isolation environment itself (clean `env`, temporary `HOME`, `CLAUDE_CONFIG_DIR` and `XDG_CONFIG_HOME`, the token passed as `CLAUDE_CODE_OAUTH_TOKEN`) and must never pass the maintainer's own variables through.

The eval directory is `evals/`. With the plugin at the repo root, the installed copy contains everything in the repo except `.git`, including `tests/`, `docs/`, `.envrc`, `CLAUDE.md` and `evals/` (measured on 2026-11-25, see `docs/evals/spike-findings.md`). The docs state no exclude mechanism. `evals/` therefore ships, and that is accepted, subject to a size budget: text only, under 200 KB, with fixtures built at run time and no answer keys or results committed. The only way to keep it out is to move the plugin into a subdirectory (a `git-subdir` or relative-path source), which was shown to work but changes the install path and the `--plugin-dir` instructions, so it is not done now.

## Fixtures

The repo is public and has its own secret scan. Therefore:

- No secret-shaped string is committed. Tokens are generated by the fixture builder at run time from `secrets.token_hex` or equivalent, with the vendor prefix assembled in code, so neither the literal nor a pattern match exists in the tree.
- Reviewers must quote the line that shows a finding, so raw results contain the planted token shape. Raw results are gitignored. Committed baselines hold counts only, never finding text.
- Customer names are fictional and obviously so. Hostnames use reserved test domains.
- Planted "internal" facts for the research eval live in a local git repo built at run time.
- A canary value in a fixture `.env` checks that agents never read or repeat it. The canary is random per run.
- Before any push, the branch is scanned with `gitleaks` and `typos` and reviewed by hand, as `CLAUDE.md` requires.

## Judge model

- Used only where marked Judge. Advisory: shown in the report, excluded from pass and fail.
- The judge sees the output and the rubric, not which variant produced it.
- Calibration: at least 20 outputs hand-labelled by the maintainer, with a balanced share of passes and fails. Agreement is reported as Cohen's kappa and as agreement within each label class. A rubric is only used when kappa is at least 0.6 and each class agrees at least 70 percent, so a judge that always says pass cannot qualify. The figures are stored with the rubric.

## Success and regression thresholds (provisional)

These numbers are starting points. Phase 1 measures variance by running the same cases several times, and the thresholds are then set so that a change smaller than the measured noise does not fire.

- A **case regression** is a drop of at least 2 passes out of 3 against the baseline. A smaller drop triggers a rerun at N=5, and a regression is declared only if the rerun also falls below the baseline's pass rate minus one run.
- A **stage regression** is a drop of at least 15 percentage points in the stage's pooled pass rate over at least 12 runs, or a drop in review recall of at least 15 points over the same repos.
- The 30 percent figure in `docs/measurements.md` is run-to-run variation in build cost, not in scores, and is not used here. Score noise is measured in Phase 1.
- False-positive rate on controls is reported with its sample size. With three controls at N=3 that is nine samples, so it is a coarse signal and not a threshold until the sample grows.

## Success criteria for this work

1. A single command runs the grader unit tests with no model calls and no network, as part of the existing `python3 -m unittest discover -s tests`.
2. A single command runs the live suite under a stated budget cap and writes results.
3. The review eval reports recall and precision per category for `reviewer` and `reviewer-lite` on the same seeded repos.
4. At least five deliberate weakenings are each either caught by their matching eval or reported as "behaviour unchanged" with a reason, and at least three are caught. Each weakening is applied to every place that states the behaviour.
5. A baseline of counts for the current plugin version is committed, containing no finding text, no secrets and nothing from the maintainer's config.
6. Documentation says how to add a case, how to read a result, how to refresh the baseline, and what a run costs, with the cost figure taken from a measured run.

## Open questions

- Whether headless mode honours `context: fork`, `isolation: worktree` and agent `skills:` preloading, and where a worktree's changes can be read from. Phase 0 tasks 0.3, 0.9 and 0.10 resolve it.
- Whether `AskUserQuestion` is denied, skipped or defaulted in headless mode. Phase 0 task 0.6.
- Whether the built-in eval command's retained output is enough for the graders. Phase 0 task 0.7.
- Whether the Write tool's own overwrite guard masks the "never overwrite" rule in `poc-start`, which would make that rule redundant in the prompt. Found by the mutation check.
- How `poc-research` is graded when web sources change. It is a periodic, non-gating eval with known-answer questions chosen from stable facts, and each run records its date.
