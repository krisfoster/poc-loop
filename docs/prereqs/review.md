# Reviews: prerequisites spec

## R.1, draft 1 (2026-11-27, independent `reviewer` agent)

No blockers, 8 major, 6 minor. Not checked by the reviewer: the full `allowManagedPermissionRulesOnly` entry, whether a plugin install keeps the exec bit, and `context: fork` substitution beyond what it read. File-based findings (items 5, 7 and 11) were confirmed by reading the files before draft 2.

| # | Severity | Finding | Handled in draft 2 |
|---|---|---|---|
| 1 | MAJOR | `python3` required for `poc-log` would stop logging entirely, against goal 3 | `python3:optional` for `poc-log`: the entry is appended, the time line skipped |
| 2 | MAJOR | No fallback when `time_check.py` is refused or fails, so the model would compute time itself (the F2 bug) | Step 4: print `Time check: not run (<reason>)` and never compute it; graded by `poc-log/missing-python` |
| 3 | MAJOR | Moving the append after the script was justified wrongly (the guard already runs first) and adds work | Order kept: append, then run the script with no `--pending`; the count reads the real file |
| 4 | MAJOR | Existing pins on the F2 and F3 text would break unannounced | Section 4 lists the tests, mutation rows and findings entries to update |
| 5 | MAJOR | `rsync` in `agents/packager.md:28` missing from the audit | Added as required for `packager`, `poc-package`, `poc-harden`; replacing it is open question 3 |
| 6 | MAJOR | Per-check timeouts are not possible in POSIX `sh` without temp files or orphans | Dropped; the Bash tool's own timeout covers a hang; test removed |
| 7 | MAJOR | Agent guard doubles the check in forked skills and `poc-build`, maybe with a prompt | Agents skip the check when the command or brief says prerequisites were checked; Probe 2 tests the grant reaching a fork |
| 8 | MAJOR | Quoting of the `allowed-tools` rule unverified; string form ambiguous with spaces | YAML list form with quoted and unquoted rules; Probe 1 covers both and a path with a space |
| 9 | MINOR | Injection trade-off understated | Stated in full; first step kept because an abort replaces the registry message with Claude Code's error |
| 10 | MINOR | Windows without Git Bash defaults to PowerShell | Baseline note reworded; the "cannot run" rule covers it |
| 11 | MINOR | `poc-help` also uses `date`; no file has `allowed-tools` today | Audit row fixed; "adds the field" stated |
| 12 | MINOR | Entry regex misses a heading with no title; compound timeboxes like `1h 30m` | Regex ends `(\s|$)`; timebox parts are summed |
| 13 | MINOR | Hiding tools from `PATH` is overstated (absolute paths, versioned aliases) | Aliases hidden too; a grader fails an absolute-path call to a hidden tool |
| 14 | MINOR | `time check:` reasons could carry absolute paths into the log | Reasons name files relative to the root, and nothing from the time check is written to `LOG.md`; the bare-repo `allowed-tools` note added to Risks |

Also from the review: the `engines` manifest field exists for a Claude Code version range (open question 1).

Decided after the review: the checker is always run as `sh <path>`, so it does not depend on the executable bit surviving a plugin install.

## R.2, implementation (2026-11-27, independent `reviewer` agent, on `git diff evals-phase-2..prereqs`)

No blockers, 2 major, 8 minor. Unit tests passed in the reviewer's run (205). Not checked by the reviewer: the full diffs of `tests/test_skills_contract.py`, `tests/test_eval_harness.py` and `tests/fake_claude.py`, `docs/prereqs/plan.md`, real Git Bash and Debian runs, daylight-saving edge cases. Findings 2 and 3 were reproduced before fixing.

| # | Severity | Finding | Handled |
|---|---|---|---|
| 1 | MAJOR | The plugin copy, now an additional directory, was shared by every run in a suite and could be edited by a run with `Edit` or `Write`, unnoticed | Each run copies the plugin into its own temp directory; a run that changes its copy is marked `invalid`. Tests: an editing run is invalid, the shared copy is untouched, the next run is fine |
| 2 | MAJOR | An invalid date or time (`2026-02-30`, `25:00`) crashed with a traceback that printed absolute paths | Caught: `time check: the Started: date in <docs>/POC.md is not a valid date and time`, exit 3; an invalid log heading time is skipped; a bad `--now` is a clean error |
| 3 | MINOR | A timebox with no number (`nd`) could come out `over` | At least one number-and-unit part is required, joined only by spaces, commas, `+` or `and`; otherwise `unknown` |
| 4 | MINOR | `TIMEBOX_RE` crossed lines; `Started:` was taken from anywhere; an unpadded hour fell back silently | Only the header line starting `Started:` is read; `9:05` is accepted |
| 5 | MINOR | A dated heading inside a code fence was counted | Fenced lines are skipped |
| 6 | MINOR | Windows git version kept a trailing dot; no `.gitattributes`, so a CRLF checkout broke the checker; the guard did not say what to do on `prereqs: usage error` | Version pattern fixed (test with `2.45.1.windows.1`); `.gitattributes` keeps the checker, `*.sh` and `*.py` LF; the guard treats a usage error as "the check cannot run" |
| 7 | MINOR | "The graders check the script's values" was overstated: the pattern matched fixture constants, so a made-up elapsed time passed | New grader `reply_echoes_tool_output`: one line of the reply must hold every number the script printed, read from the event log. Re-graded on the saved re-run, only the no-numbers run fails. Wording in findings and the changelog corrected |
| 8 | MINOR | The spec still described a `poc-research/missing-python` case that stops; it said the contract test catches any new tool | Spec text corrected: the case is `poc-sources/missing-python`, the public-only path has no eval, and the test catches only registry tools |
| 9 | MINOR | `input_regex` (and `pattern`) were not compiled at load; inputs are cut at 600 characters | Both compiled when cases load (test); the 600-character limit is documented |
| 10 | MINOR | An exact interpreter grant counts as narrow but can run a workspace file the model edits | Documented in `evals/README.md`; the `poc-verify` cases that use it grant no `Edit` or `Write` (checked) |

Claims the reviewer confirmed: PowerShell is the Windows shell without Git Bash (and a PowerShell tool may be offered with it, now noted in `docs/prerequisites.md`), `additionalDirectories` lets a directory through the read block, the packager's `rsync` flags work with macOS openrsync, the run and case counts in the changelog, and the checker's whole-word matching.
