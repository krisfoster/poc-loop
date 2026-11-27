# Findings: prerequisites

## Phase 0 probes (2026-11-27, Claude Code 2.1.325, Haiku, headless, one run each, $0.013 in all)

Runner: `docs/prereqs/tools/probes/run_probes.py`. A throwaway plugin with a stand-in checker (`scripts/x`, prints `PROBE_CHECKER_RAN`), `--allowedTools Read` only, so any run of the checker comes from the skill's own `allowed-tools`. Both rule spellings were listed, in YAML list form: `Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/x *)` and `Bash(sh "${CLAUDE_PLUGIN_ROOT}/scripts/x" *)`.

| Probe | Result |
|---|---|
| P1-control (no `allowed-tools`) | Refused: `This command requires approval`. The probe can fail |
| P1-quoted | Ran, no denial |
| P1-unquoted | Ran, no denial |
| P1-space-quoted (plugin under a directory with a space) | Ran, no denial |
| P1-space-unquoted | Ran, no denial. The model quoted the path itself because of the space, and the quoted rule matched, so listing both spellings is what made it work |
| P2-fork (`context: fork`, the skill says "Prerequisites checked", the agent says to skip its check when told) | The fork ran the skill's call with no denial, so the grant reaches the forked subagent. The agent's own check did not run |
| P3-hidden (`python3`, `python3.*`, `python` left out of a symlinked `PATH`) | `command -v python3` exit 1, `python3 --version` exit 127 `command not found`. Hiding works under the isolated `HOME` |

Consequences for the plan: eval cases do not need to grant the checker or the time-check script, so the `{plugin}` placeholder (plan 4.2) is not needed. Both rule spellings stay. One run each: a behaviour seen once, not a rate. Not probed: an installed (marketplace) plugin, an interactive session, policy settings.

## Phase 5 live runs (2026-11-27, Claude Code 2.1.325, headless)

**First batch, 58 runs, $2.78: 43 passed.** Two harness gaps found before it: the eval plugin copy left out `scripts/`, and the runner's `blockReadsOutsideWorkingDirectories` refused the plugin's own scripts (the runner now adds the plugin copy, which holds no `.env`, to `additionalDirectories`). In that refused state `poc-log` printed `Time check: not run (...)` and did not work the time out itself, which is the fallback working. Failures in the batch, by cause:

- **Plugin, fixed:** the model joined `cd <root> &&` to the script or added `-I`, so the call no longer matched `allowed-tools` and was refused (the shared paths paragraph tells it to `cd` first); the script ran before a refused `cat >>` append had been retried with Edit, so the count was one short; `missing-python` never printed the `skipped:` line (0 of 3). Step 3 now appends with the Edit tool, step 4 runs the script after the entry is in the file, exactly as written with no `cd`, flags or joins, and prints the `skipped:` line when `python3` was skipped. The guard paragraph says to run the check on its own.
- **Case, fixed:** tool inputs were cut at 200 characters, hiding `time_check.py` behind a long `cd` (now 600); `no-git-repo` wanted the literal `git init` when the run offered to "create a git repository"; the `poc-verify` cases granted `./verify.sh` but not `bash verify.sh`, which the verifier used in both affected runs (an exact interpreter grant with no wildcard now counts as narrow).
- **Plugin, logged:** `stop-existing-summary` said "wrote" instead of saying it updated `SUMMARY.md` (1 run; passed on the re-run).

**Re-run of the changed cases, 31 runs, $0.34: 27 passed.** `fresh-log`, `earlier-entries`, `started-no-time` and `timebox-exceeded` 16 of 16, all six `poc-verify` cases, `no-git-repo` and `stop-existing-summary` passed. `missing-python` 2 of 3 (one run printed `Time check: not run (python3 skipped)` without the `skipped:` line). `within-timebox` 1 of 4.

**What the script fixed and what it did not.** In every run where the script ran, the values the reply showed were the script's (elapsed, timebox, count), so the counting and arithmetic problems are gone, and the over-timebox decision held in all 8 over-timebox runs of the re-run. Copying the line verbatim did not hold when the result is unremarkable: 3 of 4 `within-timebox` runs rewrote it ("Time check: Elapsed 49h 24m of 100000 hours, 2 entries. Timebox is within.", "within the timebox (49h 24m of 100000 hours, 2 entries)", and once no numbers at all). Across the 20 time-check runs of the re-run, 17 printed the line exactly, against 36 of 39 before the change: no better. One run in 20 gave no numbers.

Mean estimated cost per `poc-log` run stayed about $0.0045 (the guard adds one Bash call).
