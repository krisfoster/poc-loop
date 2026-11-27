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
