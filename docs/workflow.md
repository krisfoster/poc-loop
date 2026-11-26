# The Spike Loop

No framework. Each PoC carries a question, and a small loop answers it. Three files in the PoC repo hold all persistent state.

| File | Location | What it holds |
|---|---|---|
| `poc-spec/POC.md` | `poc-spec/` | One page, written once: the question, ranked assumptions and risks, the success check, scope in and out, timebox for the first pass |
| `poc-spec/LOG.md` | `poc-spec/` | Append-only dated entries of a few lines: what was tried, learned, dead ends, decision, next question |
| `verify.sh` | repo root | Runs the PoC and exits non-zero if the success check fails. An unedited stub fails on purpose. If a PoC cannot be scripted, `poc-spec/POC.md` declares a manual check with exact steps |

`SUMMARY.md` (written on stop or harden), `README.md`, `CLAUDE.md` and `.env.example` stay at the repo root. In the older layout, from before 0.2.0, `POC.md` and `LOG.md` sit at the repo root too: it still works, and README.md says how to move it by hand.

## The loop

Lost? `/spike-loop:poc-help` lists the commands and reads `poc-spec/POC.md` and `poc-spec/LOG.md` to say what to run next. Every command also ends with a `Next:` line.

1. **Start** (about 10 minutes). `/spike-loop:poc-start`. It asks the tier, whether the PoC is tied to a deal, and interviews you for the question, the riskiest assumptions, how you will know it worked, and the timebox. Read and correct `poc-spec/POC.md`: that review matters most.
2. **Research** (only if the question depends on facts). `/spike-loop:poc-research <question>`. Public docs from vendor sources, internal documents from the sources you set up. Returns a cited half page.
3. **Build** (timeboxed, one unit of work per session). In the main session, staying within `poc-spec/POC.md`. New ideas go in `poc-spec/LOG.md` under Later. `/spike-loop:poc-build <task> | done when <condition>` hands a bounded chunk to an isolated worktree.
4. **Verify.** `/spike-loop:poc-verify`. Pass or fail with only the relevant errors. A manual check comes back as needs-human, never passed. After two failed fix attempts use `/spike-loop:poc-debug` or `/clear`.
5. **Capture** (about 2 minutes). `/spike-loop:poc-log`.
6. **Decide**, and write one outcome in `poc-spec/LOG.md`:
   - **Iterate**: refine the question and start a fresh session.
   - **Pivot**: edit `poc-spec/POC.md` because the learning invalidated an assumption.
   - **Harden**: `/spike-loop:poc-harden`.
   - **Stop**: record the answer and run `/spike-loop:poc-checkpoint stop` to write `SUMMARY.md`.

## Match the ceremony to the task

| Tier | When | What you do |
|---|---|---|
| 0 | You can describe the change in one sentence | Just ask. No files |
| 1 | A bounded experiment, under a few hours | `poc-spec/POC.md` as a few lines, one or two `poc-spec/LOG.md` entries, lean harden |
| 2 | A multi-day or customer-facing PoC | Full loop, `/clear` between passes, the Opus reviewer and a full harden |
| 3 | Production-bound work growing out of a PoC | Write a real spec in a fresh session |

## Who does what

| Step | Agent | Model |
|---|---|---|
| Verify | `verifier` | Haiku, Bash and Read only |
| Review, tier 2 | `reviewer` | Opus, read-only |
| Review, tier 1 | `reviewer-lite` | Sonnet, read-only, 12 tool calls |
| Debug | `debugger` | Opus, read-only |
| Research | `researcher`, or `researcher-internal` after setup | Sonnet, read-only |
| Package | `packager` | Sonnet, writes README, docs, `.env.example` and run scripts only, never stages or commits |
| Build chunk | `implementer` | Sonnet, own worktree, no MCP tools |

## Harden

`/spike-loop:poc-harden` reads the tier in `poc-spec/POC.md`. Tier 1 takes the lean path: one `reviewer-lite` call, a stop for you on any BLOCKER or MAJOR finding, one `packager` call, one final gate (`./verify.sh` plus `gitleaks` and `typos` if installed), one log entry. Tier 2, a missing tier, or `/spike-loop:poc-harden full` takes the full path: a scan up front, the Opus `reviewer`, then packaging and the gate. Neither path stages, commits or pushes.

## Rules that keep it honest

- Ask for evidence (the command and its output), not a claim of done.
- Agents declare success early. A concrete check and your reading of its output are the defense.
- The timebox is soft. `/spike-loop:poc-log` and `/spike-loop:poc-checkpoint` show elapsed against budget. Nothing nags in the background.
- Nothing from the workflow is written to any external system. The outcome lives in `SUMMARY.md` in the repo. In a public repo, keep customer names and deal details out of every file.
