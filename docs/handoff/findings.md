# Findings: hand-off state probes

Phase 0 of `docs/handoff/plan.md`. One run each, headless, Claude Code 2.1.325, 2026-11-27. Runner: `docs/handoff/tools/probes/run_probes.py` (isolated HOME and config dirs, the plugin loaded from the checkout, read-only grants `Read Glob Grep`, `--max-budget-usd 0.25`). Seven runs, about 0.28 USD in all. Raw event logs were kept outside the repo.

Fixtures: a small PoC repo (`app.py`, `verify.sh`, `poc-spec/POC.md`, `poc-spec/LOG.md`) on branch `spike-hmac` with one untracked file, `scratch_vectors.py`. The last log entry carries a State line made by `check_git_rules.py`, so it is what the spec's rules give for that repo. P1 entries are `iterate`, with `resume: add a 5-minute timestamp tolerance to verify_signature in app.py, then run ./verify.sh`. The P2 entry is `pause`, with `resume: read poc-spec/handoffs/2026-11-27-replay-spec.md, then write the Tolerance window section ...`. The hand-off holds a fact found nowhere else: the timestamp header `X-Vendor-Ts` is in epoch milliseconds.

Confound: every run also loaded five organisation-managed plugins that the isolated HOME does not remove. Whether any of them changes how a session reads repo files is unknown.

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

# Manual cases (plan 3.3)

The real `poc-checkpoint` (Sonnet, low effort) and `poc-help` (Haiku, low effort) on scratch repos, headless, Claude Code 2.1.325, 2026-11-27, one run each. Runner and graders: `docs/handoff/tools/manual/manual_cases.py`. The expected State values come from `check_git_rules.py`. `poc-help` ran with `Read Glob Grep Bash(git *) Bash(date *)`; the checkpoint also had `Edit Write Bash(tail *)`. Every `poc-help` run is also checked for having changed no file. 15 cases, 17 runs, plus 3 re-runs after fixes: about 0.71 USD.

| Case | What | First run | After the fix |
|---|---|---|---|
| M01a | `checkpoint iterate`, an uncommitted file and an unmerged agent worktree with a commit | 12/12. State line equal to the rules' values field by field (`uncommitted: 1 paths: scratch_vectors.py`, `unmerged worktrees: worktree-agent-1`), last line of the last entry, no path, `Next: /clear, then /spike-loop:poc-help`, no commit | |
| M01b | Fresh session after M01a: `poc-help` | 4/4. Fresh (the log change is excluded) | |
| M02 | Fresh State | 5/5 | |
| M03 | A code commit after the State | 6/6. Stale, names the commit, `Next: /spike-loop:poc-checkpoint iterate` | |
| M04 | A docs-only commit | 4/4. Fresh | |
| M05 | A `poc-log` entry after the State | Right behaviour: "State: unknown ... later entries follow it", `Next:` by the last Decision. Graded fail on the exact phrase "State unknown" | Grader accepts the wording |
| M06 | Old log, no State | Right behaviour: "the state is unknown", `Next: /spike-loop:poc-checkpoint iterate`. Same grader issue | Grader accepts the wording |
| M07 | Repo with no commits | Right behaviour: fresh, `Next:` is the resume step. No separate `Resume:` line | Recorded as a wording deviation |
| M08 | Not a git repo | 4/4. Fresh | |
| M09 | Moved to a detached HEAD | 5/5. Stale, names the branch | |
| M10 | Older root layout, a new uncommitted code file | 5/5. Stale, names the file (the draft 4 blocker case) | |
| M11 | `harden` with `SUMMARY.md` written after the State | 5/5. Fresh, `Next: /spike-loop:poc-harden` | |
| M12 | `reset --hard` to before the recorded commit | 5/5. Stale | |
| M13a | `checkpoint pause replay-spec` with that name taken | 7/7 as graded, but the State's `resume:` was `read ...-replay-spec-2.md, then /spike-loop:poc-help` | 8/8: `resume: read poc-spec/handoffs/<today>-replay-spec-2.md, then test a 5-minute timestamp tolerance ...` |
| M13b | Fresh session after M13a: `poc-help` | Read the `-2` hand-off and summarised it, but `Next: /spike-loop:poc-help` (it followed the bad resume) | 7/7: `Resume:` line, `Next:` is the work step |
| M14 | `checkpoint pause ../secrets` | 4/4. Refused, no file written anywhere, no `/clear` | |
| M15 | `checkpoint iterate` with `LOG.md` read-only | Fixture did not fail: with only the file read-only, the write still succeeded (the tool replaces the file, which the folder allows), and the model correctly reported a passed read-back and `/clear` | With the folder read-only too: 3/3. `LOG.md` unchanged, no `/clear` anywhere, `Next: /spike-loop:poc-checkpoint iterate`, and it printed the State it would have recorded |

Fixes from these runs:
- **The resume field named `poc-help`** (M13a). The State table now says the resume command is the next piece of work, never `/clear` or `/spike-loop:poc-help`, which belong in the `Next:` line. Pinned in the tests and a mutation row. Re-run passed.
- **Graders.** "State unknown" and "fresh" are accepted in other words; a resume naming `poc-help` and a `Next:` of `poc-help` itself now fail.
- **Gotcha.** A read-only `LOG.md` alone does not make a write fail: the folder has to be read-only too.

Not fixed: Haiku sometimes paraphrases the fixed text (`State: unknown`, no `Resume:` line) while doing the right thing. Several runs also added a timebox nudge to `Next:` ("you may prefer `/spike-loop:poc-checkpoint` first"), which the skill allows. Single runs.
