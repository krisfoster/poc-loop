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
