# Review record: layout spec and plan

Phase R, 2026-11-26. Reviewer: the `reviewer` agent, given `docs/layout/spec.md` and `docs/layout/plan.md` with no conclusions from the author. It read the files in the worktree and fetched Claude Code docs pages (code.claude.com, pages show no version). Statements it made about Claude Code behaviour are marked as the reviewer's reading and are untested.

Before applying, the author re-checked the local facts it could check: `poc-research` on `help-and-next` names `POC.md` (line 16); `poc-harden` lean step 4 says "Call" with no "Show" while the full path's step 5 says "Show its report"; `poc-start` refuses to overwrite any existing file; `poc-start` lines 19 and 71 name `POC.md`; `docs/evals/` and `docs/handoffs/` are not on `main`; `docs/measurements.md` and `docs/workflow.md` contain no "step N" text; the packager's step 5 greps for customer names; `README.md` has a `Status: 0.1.1` line; `poc-log` and `poc-checkpoint` on `help-and-next` carry `Next:` lines that name the files. All held.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | BLOCKER | Tests 3 and 8 contradict: the warning line and the `poc-start` template headings contain bare `LOG.md` and `POC.md`. Line 71 of `poc-start` missing from the audit | Applied. Test 3 exempts Rule B, the legacy note, the warning lines and template headings. Line 71 and others added to the audit |
| 2 | BLOCKER | "Run every shell command from the repo root" fails because `cd` does not persist between calls, and it conflicts with the clean-clone directory and the debugger scratch copy | Applied. Rule A now says to start every command with `cd "<root>" &&` unless a step names another directory. Probe 0.2(a), (d), (e) test it |
| 3 | MAJOR | Behaviour stated as fact despite the "no claims" line: forked skills cannot name the root (docs describe skill-body command injection and `${CLAUDE_PROJECT_DIR}`), the fork starting directory is "not known" (docs: a subagent starts in the main conversation's directory), worktree sees only committed files (docs: branches from the default branch unless `worktree.baseRef` is `"head"`) | Applied. Spec rewritten with **(docs)** markers and "not stated" where the docs are silent. Injection is judged in 0.3 and the spec does not depend on it |
| 4 | MAJOR | Audit built on `main`, missing `help-and-next` changes (`poc-research`, `poc-log` step 5, `poc-checkpoint` step 7, `poc-help` lines 39 to 46) and main items (`poc-start` 19, `poc-checkpoint` 14, `poc-harden` 24 and the vague "repo path" briefs, `packager.md` 13, frontmatter descriptions), plus the generated `researcher-internal` agent | Applied. Audit table extended, task 0.4 now runs after the rebase, changelog tells users to refresh |
| 5 | MAJOR | Root was resolved from the session, not the path argument; nested repos and linked worktrees give an inner root and `poc-start` would create a second `poc-spec/` | Applied. Rule A uses `git -C "<target>"`. `poc-start` checks the root and `--git-dir` against `--git-common-dir` and asks. The relative-argument consequence is open question 2 |
| 6 | MAJOR | Packager warning faults: may not reach the user on the lean path, misses untracked unignored files, `.gitignore` advice does not untrack, root layout `git rm -r --cached .`, contradictions about reading contents and "only guard", two output locations | Applied. Lean step 4 adds "Show its report". Check covers tracked and untracked-not-ignored. Two separate warning lines with the right commands and a history note. Contradictions removed. One output location |
| 7 | MAJOR | Rule B ambiguous: recursive reading, `<docs>/LOG.md` with the root layout, partial move dead end, no follow-up for "ask which to keep", symlinked folder | Applied except symlinks, which are recorded as a known gap. Rule B checks four fixed paths, `<docs>` is `poc-spec` or `.`, a partial move is "half-migrated", agents report and stop |
| 8 | MAJOR | Eval plan fails for unrelated reasons: `poc-log/basic` does not allow `git rev-parse` or `cd`, `blockReadsOutsideWorkingDirectories` may block subdirectory reads, a new permission prompt per command | Applied. Spec "Evals" and plan 0.2(e) to (g), 4.2, 4.4 |
| 9 | MAJOR | Test loopholes: `poc-spec/POC.md` allowed anywhere, banned-phrase list too short and frontmatter exempt, test 6 exception meaningless, test 9 unscriptable, test 2 scope | Applied. Tests rewritten (allowed-path list, longer phrase list including frontmatter, regex for any `*spec*/` token, scriptable test 9, fixed list for test 2, new test 10) |
| 10 | MAJOR | Plan order: baseline before rebase, "merged result" before merge, no forked-skill or nested-repo or worktree manual case | Applied. 0.4 after 0.1, 4.1 rebases onto the branch, 3.4 extended |
| 11 | MINOR | Not-a-repo stops for `poc-verify` and `poc-review` are a regression | Applied. Commands fall back to the start directory, no stops |
| 12 | MINOR | Never-overwrite narrowed to `POC.md` | Applied. Covers every target file |
| 13 | MINOR | Plan errors: "28 plus" tests, Gate 1 vs 1.5, 2.3's step-number reason, 1.3 predicted count, 2.9 omits README status | Applied |
| 14 | MINOR | Migration fragile (`git mv` on untracked files, "two commands", Windows) | Applied. `mv` variant, "one command and one edit", Windows listed as a non-goal |
| 15 | MINOR | Repo rules: employer policy named in plan, "Names the plugin" wording, `docs/evals/` and `docs/handoffs/` not on `main` | Applied in this branch. The policy wording on `evals-spec` is flagged for the pre-push review (plan 5.1) |

## Not independently confirmed

Everything marked **(docs)** in the spec, and the reviewer's note that the `blockReadsOutsideWorkingDirectories` setting may block reads. The reviewer also noted that the plan's earlier claim that the probe would not trigger the scripted-use terms cannot be established while the terms are unread. The claim is removed.

Second review (R.3) is due after Phase 0, on the parts Phase 0 changes.

## R.3: second review (2026-11-26)

Reviewer: the `reviewer` agent again, with no conclusions from the author. Scope: everything added since the first review (the Phase 1 tests and tools, the probes, the spec changes made after them). It read the raw probe event logs and checked the claims in `docs/layout/findings.md` against them, and ran the tests, the stand-in and the mutation script without writing to the repo. No blockers. Statements it took from the Claude Code docs or git release notes are marked as its reading in the spec and are untested here. The author re-checked the locally checkable facts first, see the last section of `docs/layout/findings.md`.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | MAJOR | "Shell state does not carry" over-reads the logs: every lone-`cd` probe left the session's directories, which resets the shell, and R1, R4, R2 and R2b put the `cd` and the `pwd` in one message | Applied. Rule A says the shell can be reset (and is in an agent). Spec and findings now say only R3 was a separate-turn test, and that persistence inside an agent is undecided |
| 2 | MAJOR | Rule A covers shell commands only. File tools resolve relative paths against the launch directory (R16) | Applied. Rule A: file tools take `<root>/<path>` in full |
| 3 | MAJOR | `cd "<root>" &&` on every command adds refusals and prompts that `git`, `date` and others do not need, the refusal clause had no agent form, the `$TMPDIR` exception was not addressed | Applied. `git -C "<root>"` for git, no `cd` for commands that need no directory, "an agent reports it and stops", the packager's `git ls-files` commands use `git -C`. The `cd` into the `$TMPDIR` clone is recorded as untested. The suggested extra `cd` plus `git` probe was not run |
| 4 | MAJOR | Test 3 lets `poc-help` hard-code `poc-spec/` anywhere in the file | Applied. Only table rows (lines starting with `|`) |
| 5 | MINOR | The `/add-dir` advice is not shown by a probe, and the `cd` refusal text does not name it | Applied. Reworded: the Read refusal (R8) names it, the quoted form was not tested |
| 6 | MINOR | Eval note says `Bash(cd *)` is needed, which was not shown, and R10 shows it does not cover a `cd` outside the session's directories | Applied |
| 7 | MINOR | Findings omit: parallel calls in R1 and R4, no reset notice for the agent and R13, why the fork runs say Sonnet, the plugins are built in | Applied, each checked against the logs |
| 8 | MINOR | Root and worktree checks miss bare repos, submodules, `GIT_DIR`, symlinks, nested repos started at their own root | Applied: `--show-prefix` for "at the root", `git worktree list --porcelain` to name the main checkout, a nested-repo check, bare repository stops, `GIT_DIR` and submodules recorded as not handled |
| 9 | MINOR | Test 3 exemptions apply to every file | Applied. Per file |
| 10 | MINOR | Test 7 requires the step to be numbered exactly 5 | Applied. Any number |
| 11 | MINOR | `mutate.py` aborts or silently no-ops on hand-written text | Applied. Targets come from the test constants, a missing target or a no-op edit is its own row |
| 12 | MINOR | `audit.py` vague-phrase regex is case-sensitive | Applied |
| 13 | MINOR | Stale spec sentences about tasks 0.3 and 0.4 | Applied |
| 14 | MINOR | The probe runner is called standalone but imports the harness | Applied. Wording corrected in findings and the script |

After the changes: the stand-in tree passes all 12 tests, the mutation check is 34 rows with 0 wrong (up from 29: new rows for the `poc-help` step, a pasted legacy note, capitalised "Current Directory", and a `cd`-based packager command, plus a control for `poc-help` table rows), and the real tree is still 41 tests with 7 failures, the Phase 2 work.

## 3.3 Independent diff review, and a delta review (2026-11-26)

Reviewer: the `reviewer` agent, twice more, with no conclusions from the author. First on the whole implementation diff against `main`, then on the delta that fixed its findings and changed Rule B after the first manual run. Both ran the test suite and read only. The author re-checked the checkable claims first (the `git rev-parse --show-prefix` behaviour and the packager `.gitignore` contradiction were reproduced).

**Diff review** (no blockers, 3 major, 7 minor), all applied in `8b17d9f`:

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | MAJOR | `poc-start`'s at-the-root check run against the root always prints nothing, so it could never fire | Applied: run it against the target |
| 2 | MAJOR | Rule A treats any path in the arguments as the target, so a path inside a log entry or question could move the root | Applied: the target is a project path only for a command that takes one |
| 3 | MAJOR | The packager's `.gitignore` ban contradicted its scope of writes | Applied: scoped to the warning |
| 4 | MINOR | "Do not read file contents" contradicted reading the POC header | Applied: reads the header only, not `LOG.md` |
| 5 | MINOR | `poc-harden` had no Next text for a half-migrated PoC | Applied |
| 6 | MINOR | `poc-help`'s older-layout branch could be read as skipping the status | Applied: "then continue with step 3" |
| 7 | MINOR | `poc-start` could leave an empty `poc-spec/` and had no non-interactive rule | Applied |
| 8 | MINOR | A bare repository fell into the `git init` branch | Applied: bare check first |
| 9 | MINOR | Rule A put a needless `cd` in front of `poc-research`'s setup script | Applied (reworded again below) |
| 10 | MINOR | README and changelog claimed more than the evidence | Applied: "designed to" |

**Delta review** (no blockers, 1 major, 9 minor), applied in `3e3d904`; one more tuning of Rule B came from the first manual run (C10, in `8379d33`):

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | MAJOR | The C10 fix covered only Rule B's four paths: other checks and reads (`ls`, `chmod`, `tail`) could still be written with a `cd` | Applied: Rule A says commands that only take file arguments get `<root>/<path>` and need no `cd`, and file tools check, read and list files. `poc-start` uses `chmod +x "<root>/verify.sh"` |
| 2 | MINOR | `poc-start`'s first write could happen before the never-overwrite check | Applied: the check opens step 5 |
| 3 | MINOR | Step 2 said "first" but the root lookup came before the bare check | Applied |
| 4 | MINOR | The non-interactive stop did not cover the `git init` offer or the public-repo question | Applied |
| 5 | MINOR | The model may not see `argument-hint`, so "if this command takes one" was not visible | Applied: `poc-start`, `poc-review` and `poc-verify` say what counts as a project path |
| 6 | MINOR | Glob can skip a gitignored `poc-spec/` | Applied: Rule B reads each path with Read |
| 7 | MINOR | `${CLAUDE_SKILL_DIR}` is literal text in agent files | Applied: "a script by its absolute path" |
| 8 | MINOR | The packager's scoped ban left a back door for another step | Applied: a rule that no step adds the docs folder to `.gitignore` |
| 9 | MINOR | C10 evidence was not in the repo | Applied: `docs/layout/findings.md` |
| 10 | MINOR | `poc-help`'s command-name mode contradicted Rule B | Applied |

After the changes: 41 tests pass, the mutation check on the real tree is 36 rows with 0 wrong, and the 22 manual cases all behave (see findings).

