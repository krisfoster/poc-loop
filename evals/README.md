# Stage evals

Evals for the Spike Loop skills and agents. Design: `docs/evals/spec.md`. Plan: `docs/evals/plan.md`. What was learned about headless runs: `docs/evals/spike-findings.md`. Plugin defects found along the way: `docs/evals/findings.md`.

Status: Phase 1 (harness core) and Phase 2 in progress: the grader library, 11 `poc-log` cases run as a smoke set, and 23 `poc-start`, `poc-checkpoint` and `poc-verify` cases run once each (23 of 23 passed). Everything else is in the plan.

## Free and paid

- **Free:** `python3 -m unittest discover -s tests` runs the harness and grader tests with no model, no network and no token. `python3 evals/run_eval.py list` and `dry-run` also call nothing.
- **Paid:** `run_eval.py run` starts real headless Claude Code sessions on your subscription. The dollar figures are estimates against your plan allowance, not a bill. Live results are stochastic and will not match a previous run exactly.

## Setup for live runs

1. Run `claude setup-token` in a separate terminal (not in a shared transcript).
2. Put the token in `.env` (gitignored) as a 1Password reference, `SPIKE_EVALS_OAUTH_TOKEN=op://vault/item/field`, which the runner resolves with `op read`. That is the repo rule for secrets. A plaintext value in `.env` also works, but `run` prints a warning and it should be temporary. The variable is named `SPIKE_EVALS_OAUTH_TOKEN`, and not `CLAUDE_CODE_OAUTH_TOKEN`, so that Claude Code sessions you start in this repo do not pick it up and authenticate with it instead of your own login. (direnv still exports it under its own name, because `.envrc` loads `.env`.) The runner maps it onto `CLAUDE_CODE_OAUTH_TOKEN` for each isolated child run only.
3. Read Anthropic's terms on scripted use of a subscription, and check your employer's policy, before running anything larger than a smoke test.

## Commands

```
python3 evals/run_eval.py list
python3 evals/run_eval.py dry-run
python3 evals/run_eval.py run --case 'poc-log/*' --runs 1 --suite-cap 0.5
python3 evals/run_eval.py report  evals/results/<timestamp>
python3 evals/run_eval.py baseline evals/results/<timestamp> --out evals/baselines/<version>.json
python3 evals/run_eval.py compare evals/baselines/<version>.json evals/results/<timestamp> [--allow-missing]
```

`compare` exits 0 when nothing fell, 1 on a regression, and 3 when a case could not be judged (no valid runs, absent from the new results unless `--allow-missing`, or needing a rerun). Exit 3 is not a pass. Stage pools use only cases present on both sides in the same set.

Runs write per-run JSON and an event log under `evals/results/` (gitignored). The token is redacted from both, but model output, prompts and tool inputs are kept, so treat results as private. `summary.md` is the table. A committed baseline holds counts only. `run` exits 2 if the suite cap stopped it, and always writes the summary for the runs it did.

## How a run is isolated

Each run gets a clean environment (only `PATH` is inherited), a temporary `HOME`, `CLAUDE_CONFIG_DIR` and `XDG_CONFIG_HOME`, the token, a setting that stops file tools reading outside the working directory (without it a granted `Read` could read this repo's `.env`, which was tested), and the plugin loaded from a copy of the working tree that contains only plugin directories, including `scripts/` (no `evals/`, `docs/`, `tests/`, `.env` or `.git`). The `system/init` event is checked on every run against an allowlist (plugins, agents, skills, MCP servers and connector tools), and also confirms that the memory path is under the temporary config directory and the working directory is the workspace. Instruction files in directories above the workspace are checked for before the run. A run that fails any of this is marked `invalid` and not scored. A run that hits its budget cap, times out, crashes with no output or raises any error in the harness is a `harness_failure`, reported separately from a stage failure. A run whose cost is unknown counts as its full cap against the suite cap.

Cases that grant `Bash`, `WebFetch` or `WebSearch` without a narrow pattern run on your machine without an OS sandbox, so `run` refuses them unless you pass `--unsandboxed-ok`. A `Bash` pattern that starts with a shell or interpreter (`sh`, `python3`, `curl`, `env` and similar) counts as broad, unless it names one exact command with no wildcard (`Bash(bash verify.sh)`). Note that such a grant, like `Bash(./verify.sh)`, still runs a workspace file the model can edit in the same case; the `poc-verify` cases grant it to run the fixture's own `verify.sh`, and give the model no `Edit` or `Write`. Each run gets its own copy of the plugin, added to `additionalDirectories` so the bundled scripts can run under the read block, and a run that changes its copy is marked `invalid`. Sandboxing is not implemented yet.

## Measured cost and noise

`poc-log/basic`, 10 runs in two batches of 5 (Claude Code 2.1.325, Haiku, 2026-11-26):

- **Pass rate:** 10 of 10 passed in both batches, so pass-rate noise on this case is zero and `compare` reports it as `same`.
- **Cost:** mean $0.0039 per run, range $0.0038 to $0.0044 (1.17x), an estimate against the plan allowance. Mean duration 10.9 seconds (9.7 to 11.9).
- **Behaviour that varies:** turns 5 to 7, and three different tool-call sequences. Every run had one permission denial (the skill's `printf >>` append is denied by the narrow `Bash(date *)` grant, and the skill then uses `Read` and `Edit`), which is why this case does not use the `no_permission_denials` grader.
- **What this does not tell us:** a case that always passes cannot show score noise, so the provisional thresholds in `thresholds.json` are not yet replaced. The variance measurement is repeated on the Phase 2 cases (plan, Gate 2).

## Layout cases (2026-11-26)

Five `poc-log` cases for the `poc-spec/` layout, run 3 times each on Claude Code 2.1.325 (Haiku): `basic` (older layout) 3/3, `poc-spec-layout` 3/3, `subdir-root-added` 3/3, `both-layouts` 3/3, `subdir-root-not-added` 3/3 (a clean refusal, see above). Mean estimated cost about $0.003 to $0.004 per run. Two further runs of `subdir-root-not-added` were recorded as `harness_failure` (`API Error: Can't reach the API server`, the network was down and the retries ran for nearly an hour each) and are not in the counts. Three runs per case is a smoke result, not a measured noise level: the variance measurement on these cases is still to be done (plan, Gate 2).

## Phase 2 `poc-log` cases (2026-11-27)

Six more `poc-log` cases, run 3 times each on Claude Code 2.1.325 (Haiku): `fresh-log` 3/3, `earlier-entries` 3/3, `started-no-time` 3/3, `timebox-exceeded` 3/3, `within-timebox` 2/3, `missing-files` 3/3. The one failure printed the time-check line in its own words (finding F2 in `docs/evals/findings.md`), a plugin defect, not a bad case. Mean estimated cost $0.0036 per run, mean 9.5 seconds, $0.066 for all 18. Before the live runs, each case's graders were checked against a hand-made correct result and one with a planted defect. Still a smoke result, not a noise measurement (plan, Gate 2).

## Phase 2 stage cases (2026-11-27)

Seven `poc-start` cases (`all-answers`, `public-repo`, `partial-answers`, `no-arguments`, `tier-0`, `existing-poc`, `no-git-repo`), ten `poc-checkpoint` cases (the five outcomes, `stop-existing-summary`, `pause-bad-topic`, `empty-argument`, `root-layout`, `missing-files`) and six `poc-verify` cases (`pass`, `fail`, `makefile-only`, `stub`, `manual`, `many-service`). The `POC.md` line limit is 40: the template is 23 lines, a filled one measured 24 (spike-findings 0.6), so 40 leaves room for filled assumptions and scope. It is provisional until the live runs.

Smoke run, 1 run per case, Claude Code 2.1.325: all 23 passed, $2.06 estimated in total. `poc-start` (Opus) $0.08 to $0.23 per run, $1.09 for 7. `poc-checkpoint` (Sonnet) $0.06 to $0.13, $0.97 for 10. `poc-verify` (Haiku, forked) about $0.0015 each, $0.009 for 6 (the fork's tokens are in the result's `modelUsage`, matching spike-findings 0.3). 17 of the 23 runs had permission denials, all of the same two kinds and all recovered from: a compound command the narrow grants do not cover (`cd ... && ./verify.sh; echo "exit=$?"`, a `R=...; git ...` chain), retried as a plain command, and `cat >> LOG.md`, after which the run used `Edit`. So these cases do not use `no_permission_denials`. One run per case shows the cases work, not how often a stage passes. `poc-start/all-answers` and `public-repo` run the written `verify.sh` through `command_exit`, so they need `--unsandboxed-ok`. `poc-verify/many-service` grants no `docker`, so nothing is started.

Not graded yet: the 12-line limit on the checkpoint summary (it cannot be told apart from the rest of the reply), process teardown in `poc-verify`, elapsed time within a minute of truth in `poc-log`, the `poc-start` vague-answers case (no deterministic oracle), the pivot edit to `POC.md` (it needs the user's agreement, which a headless run cannot give), and a State with uncommitted work (the runner commits the whole fixture).

## Checking the cases themselves

`docs/evals/tools/selfcheck/` builds a correct result and a result with one planted defect for each Phase 2 case and runs the case's graders on both, with no model call. A case passes the self-check when the correct result passes and the defect fails. The unit tests run both scripts. Run this after changing a case or a grader.

## Graders

`file_exists`, `files_matching` (glob count), `file_regex` (a path or a glob), `final_text_regex`, `headings_match`, `no_placeholders`, `line_cap`, `no_em_dash`, `file_unchanged`, `file_prefix_unchanged`, `executable`, `no_tracked_file_modified` (optionally no new files either), `git_clean_history`, `command_exit` (runs a command in the workspace with only `PATH` and a temporary `HOME`, and makes its case need `--unsandboxed-ok`), `tool_call_count` (optionally only calls whose input matches `input_regex`), `tool_not_used`, `no_permission_denials`, `questions_before_write` (questions in the reply before the first file write, from the event log), `reply_echoes_tool_output` (one line of the reply holds every number a matching tool call printed, in order) and `canary_absent`. Tool inputs are kept to 600 characters, so `input_regex` cannot see past that. Text graders take `path`, `glob`, or `target` (`final_text`, or `changed` for every added or modified file). Parameters are checked when cases load. Code: `harness/graders.py`. Tests: `tests/test_eval_graders.py`.

## Adding a case

Add `evals/cases/<stage>/<id>.json` (the file name must equal `id`, the directory must equal `stage`) and, if it needs one, a fixture directory under `evals/fixtures/`. Fields are validated before any model call, and an error names the file and the field. Fields: `id`, `stage`, `set` (`tune` or `holdout`), `prompt`, `fixture`, `allowed_tools`, `graders`, and optionally `n_runs`, `timeout_s`, `max_cost_usd` (at least 0.10), `git`, `description`, `cwd`, `add_root_dir` and `hide_tools`. `hide_tools` lists tools to leave off the session's `PATH` (a directory of symlinks to everything else; `python3` also hides `python3.*` and `python`), to test the prerequisite guard (`docs/prereqs/spec.md`). It hides what the session's Bash tool can find, not Claude Code's own use of `git`. `cwd` is a subdirectory of the fixture in which the session starts (it must exist in the fixture, default the workspace root). `add_root_dir` adds the workspace root as an additional directory, like `/add-dir` in a session. Without it, a session started below the root has the root outside what it may use: a `cd` to the root is refused, and because every run keeps `blockReadsOutsideWorkingDirectories` on (so a granted `Read` cannot reach the repo's own `.env`), reads of the root's files are refused too. So `poc-log/subdir-root-not-added` measures a clean refusal, not success. With default read settings the same command succeeds using file tools only (manual case C10), which this harness cannot test. Diffs and graders always look at the whole workspace. Do not run the `holdout` set while tuning prompts.

## Layout fixtures

The plugin keeps a PoC's documents in `poc-spec/` (see `docs/layout/spec.md`) and still reads the older layout, with `POC.md` and `LOG.md` at the repo root. Fixtures: `poc-log-basic` is the **older layout**, so `poc-log/basic` is the fallback case. `poc-log-specs` is the new layout and has a `sub/deep` directory for the subdirectory cases. `poc-log-both` has both layouts, for the half-migrated stop. A command that runs `git -C "<root>" ...` needs `Bash(git *)` in `allowed_tools`, and each part of a compound command needs its own grant (a pattern for the whole compound does not work, see `docs/layout/findings.md`). New stage cases use the new layout by default and add one older-layout case where the stage reads the documents.
