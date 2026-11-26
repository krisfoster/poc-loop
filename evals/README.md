# Stage evals

Evals for the Spike Loop skills and agents. Design: `docs/evals/spec.md`. Plan: `docs/evals/plan.md`. What was learned about headless runs: `docs/evals/spike-findings.md`. Plugin defects found along the way: `docs/evals/findings.md`.

Status: Phase 1 (harness core). One case exists, `poc-log/basic`. Everything else is in the plan.

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

Each run gets a clean environment (only `PATH` is inherited), a temporary `HOME`, `CLAUDE_CONFIG_DIR` and `XDG_CONFIG_HOME`, the token, a setting that stops file tools reading outside the working directory (without it a granted `Read` could read this repo's `.env`, which was tested), and the plugin loaded from a copy of the working tree that contains only plugin directories (no `evals/`, `docs/`, `tests/`, `.env` or `.git`). The `system/init` event is checked on every run against an allowlist (plugins, agents, skills, MCP servers and connector tools), and also confirms that the memory path is under the temporary config directory and the working directory is the workspace. Instruction files in directories above the workspace are checked for before the run. A run that fails any of this is marked `invalid` and not scored. A run that hits its budget cap, times out, crashes with no output or raises any error in the harness is a `harness_failure`, reported separately from a stage failure. A run whose cost is unknown counts as its full cap against the suite cap.

Cases that grant `Bash`, `WebFetch` or `WebSearch` without a narrow pattern run on your machine without an OS sandbox, so `run` refuses them unless you pass `--unsandboxed-ok`. A `Bash` pattern that starts with a shell or interpreter (`sh`, `python3`, `curl`, `env` and similar) counts as broad. Sandboxing is not implemented yet.

## Measured cost and noise

`poc-log/basic`, 10 runs in two batches of 5 (Claude Code 2.1.325, Haiku, 2026-11-26):

- **Pass rate:** 10 of 10 passed in both batches, so pass-rate noise on this case is zero and `compare` reports it as `same`.
- **Cost:** mean $0.0039 per run, range $0.0038 to $0.0044 (1.17x), an estimate against the plan allowance. Mean duration 10.9 seconds (9.7 to 11.9).
- **Behaviour that varies:** turns 5 to 7, and three different tool-call sequences. Every run had one permission denial (the skill's `printf >>` append is denied by the narrow `Bash(date *)` grant, and the skill then uses `Read` and `Edit`), which is why this case does not use the `no_permission_denials` grader.
- **What this does not tell us:** a case that always passes cannot show score noise, so the provisional thresholds in `thresholds.json` are not yet replaced. The variance measurement is repeated on the Phase 2 cases (plan, Gate 2).

## Adding a case

Add `evals/cases/<stage>/<id>.json` (the file name must equal `id`, the directory must equal `stage`) and, if it needs one, a fixture directory under `evals/fixtures/`. Fields are validated before any model call, and an error names the file and the field. Fields: `id`, `stage`, `set` (`tune` or `holdout`), `prompt`, `fixture`, `allowed_tools`, `graders`, and optionally `n_runs`, `timeout_s`, `max_cost_usd` (at least 0.10), `git`, `description`. Do not run the `holdout` set while tuning prompts.
