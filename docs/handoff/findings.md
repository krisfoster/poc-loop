# Findings: hand-off state probes

Phase 0 of `docs/handoff/plan.md`. One run each, headless, Claude Code 2.1.325, 2026-11-27. Runner: `docs/handoff/tools/probes/run_probes.py` (isolated HOME and config dirs, the plugin loaded from the checkout, read-only grants `Read Glob Grep`, `--max-budget-usd 0.25`). Seven runs, about 0.28 USD in all. Raw event logs were kept outside the repo.

Fixtures: a small PoC repo (`app.py`, `verify.sh`, `poc-spec/POC.md`, `poc-spec/LOG.md`) on branch `spike-hmac` with one untracked file, `scratch_vectors.py`. The last log entry carries a State line made by `check_git_rules.py`, so it is what the spec's rules give for that repo. P1 entries are `iterate`, with `resume: add a 5-minute timestamp tolerance to verify_signature in app.py, then run ./verify.sh`. The P2 entry is `pause`, with `resume: read poc-spec/handoffs/2026-11-27-replay-spec.md, then write the Tolerance window section ...`. The hand-off holds a fact found nowhere else: the timestamp header `X-Vendor-Ts` is in epoch milliseconds.

Confound: every run also loaded five organisation-managed plugins (`cc-plugin-*`) that the isolated HOME does not remove. Whether any of them changes how a session reads repo files is unknown.

| Probe | Setup | What it did | Result |
|---|---|---|---|
| P0 | stream-json input, three turns: remember PELICAN, `/clear`, what was the word | Turn 1 `OK`. A `conversation_reset` event, a new `system/init`, then turn 3 answered `UNKNOWN` | A real `/clear` can be sent headless and does clear context |
| P1a | Wiring in `CLAUDE.md`, prompt "Continue with the next step." | Read `poc-spec/POC.md`, then `tail -n 40 poc-spec/LOG.md` (the wiring's exact read), `app.py`, `git status`, `scratch_vectors.py`. Tried to write `app.py` and `verify.sh` (denied). Final text quotes the `resume:` value word for word | Uses State: yes. Took the resume step directly, no `poc-help` |
| P1b | No `CLAUDE.md` (control), same prompt | First call `git diff && tail -40 poc-spec/LOG.md`, then `POC.md` and `app.py`. Tried to write `app.py` (denied). Final text names the same step | Uses State: yes, without the wiring. P1a and P1b do not differ |
| P1c | Wiring, prompt "Where are we and what should I do next?" | Read `POC.md` and the log tail. Final text gives the branch from State, the next step, and says `LOG.md` is uncommitted while State lists only `scratch_vectors.py`, "so the LOG.md edit may be newer than that entry" | Uses State: yes. Misreads the docs-folder exclusion as possible staleness. No `poc-help` |
| P2 | Wiring, a `pause` entry whose `resume:` names a hand-off file, task prompt | Read `POC.md`, the log tail, then the hand-off file (with `cat`, not Read), `spec-replay.md`, `app.py`. Tried to append a Tolerance window section using `X-Vendor-Ts` in milliseconds (denied) | Follows the `resume:` pointer: yes, and uses the fact only the hand-off holds |
| P4 | Throwaway plugin, `SessionStart` hook with matcher `startup|clear` printing a marker word | `hook_started` and `hook_response` events for `SessionStart:startup` before `init`. Answered `HERON` with no tool call | A plugin `SessionStart` hook runs under `-p` with no trust prompt, and its stdout reaches the model |
| P4b | Same, matcher `clear` only, stream-json: `OK`, `/clear`, ask for the marker | After `conversation_reset`: `SessionStart:clear` started and returned, then the answer `EGRET` | The `clear` matcher fires headless after a real `/clear`, and its output reaches the model |

## What this means for the spec

1. **Gate 0 passes.** P1a read `POC.md` and the last 40 lines of the log as the wiring says, and acted on the State's `resume:`. Option A works for a task prompt in this fixture.
2. **The control does not separate.** P1b, with no wiring, found and used the log too. In a repo this small the log is found anyway, so these runs do not show what the wiring adds. A larger repo, or one where `poc-spec/` is gitignored, might differ. Not run.
3. **The `resume:` pointer works.** P2 read the named hand-off and used its one unique fact.
4. **The unchecked route is the normal one.** No run went through `/spike-loop:poc-help`. Every task run took the `resume:` step straight from the log, so the staleness check is skipped unless the user types `poc-help`. P1c also shows that a reader without the spec's rules can call a docs-only change stale. Both point at the spec's "unchecked route" risk and are no longer hypothetical.
5. **Option C is now testable and cheap.** P0, P4 and P4b were expected to leave C untested, but they show that `/clear`, the `startup` matcher and the `clear` matcher all work headless from a `--plugin-dir` plugin, with no trust prompt and the output in context. Still unmeasured: an installed (not `--plugin-dir`) plugin, an interactive session, and any trust prompt there.
6. **Read-only grants still allowed some Bash.** P1a, P1b and P2 ran `tail`, `cat`, `git status` and `git diff` with only `Read Glob Grep` granted. Writes and redirections were denied. The probes stayed read-only in effect.

Single runs. A different model, prompt or repo size may behave differently.
