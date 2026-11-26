# Plan: implement the `poc-spec/` layout and repo-root paths

Spec: `docs/layout/spec.md` (draft 2, read it first, its audit table is the task source). Review record: `docs/layout/review.md`. Branch: `docs-layout`, worktree `../spike-loop-layout`, fast-forwarded to `main` at `6dec01e` on 2026-11-26 (it was cut from `e1f31b8`). Status: Phase R done, task 0.1 done, the rest of Phase 0 not started. Target release: 0.2.0.

## Ground rules

- Tests come before edits. The new tests fail first for the expected reasons, then each phase turns some of them green.
- Before any commit: `typos` on changed files, `gitleaks`, no em dashes (check with Python, the system `grep` has no `-P`), trailer `Co-Authored-By: Claude`. Never `--no-verify`, never read `.env`.
- Before any push, PR or tag: the pre-push review of outgoing changes that `CLAUDE.md` requires, and the maintainer's approval. Nothing in this plan pushes by itself.
- Plugin and Claude Code behaviour claims in the docs must be true. A task that changes a claim says how it was checked. Claims marked **(docs)** in the spec are untested until Phase 0 runs them.
- This branch changes only the plugin. The evals fixtures live on `evals-spec` and are Phase 4.
- Paid probe runs: the Gate 0 condition on `evals-spec` (Anthropic's terms on scripted use of a subscription are unread, and the maintainer's organisation's own policy is unchecked) still stands. The maintainer decides whether a few single runs count as a smoke test. Do not assume they do.

## Order and dependencies

| Phase | Needs | Output |
|---|---|---|
| R. Independent review of spec and plan | drafts | Done 2026-11-26. Findings applied, record in `docs/layout/review.md` |
| 0. Preconditions and probes | R | Branch base settled, baseline audit on the real base, behaviours tested |
| 1. Tests first | 0 | `tests/test_docs_layout.py`, failing for the expected reasons |
| 2. Implementation | 1 | Skills, agents, README, workflow, changelog, version 0.2.0 |
| 3. Verification | 2 | Green tests, scans, independent diff review, manual checks in scratch repos |
| 4. Evals fixtures and cases | 3 and `evals-spec` rebased onto this branch | Old and new layout cases, packager warning cases, subdirectory case |
| 5. Release | 3, and 4 if the maintainer wants evals first | PR, review, tag, only with approval |

## Phase R: independent review (done)

| ID | Task | Status |
|---|---|---|
| R.1 | `reviewer` agent on the spec and this plan, with no conclusions from the author, asked to check the audit against the files and the tests for loopholes | Done. 2 blockers, 8 major, 5 minor. Local facts re-checked before applying |
| R.2 | Apply findings | Done in spec draft 2 and this revision. Each finding's disposition is in `docs/layout/review.md` |
| R.3 | Second review of the revised spec after Phase 0, since Phase 0 may change the rules | Do it at Gate 0, on the changed parts only |

## Phase 0: preconditions and probes

Order matters: the baseline audit runs after the branch base is settled, because the first audit on `main` missed everything `help-and-next` changed.

| ID | Task | Acceptance |
|---|---|---|
| 0.1 | **Settle the branch base.** Done 2026-11-26. `help-and-next` (0.1.2) was pre-push reviewed, smoke-tested through the eval harness, and merged to `main` as PR #2 (`6dec01e`). `docs-layout` was fast-forwarded to it. The merged `poc-help` differs from the version the first audit read: a second commit (`3ca0db3`) made the command-name path answer from its table and read no other skill file, so the `${CLAUDE_SKILL_DIR}` read is gone and line numbers moved | `skills/poc-help/SKILL.md` and `tests/test_skills_contract.py` are on this branch and `python3 -m unittest discover -s tests` passes with 29 tests (checked 2026-11-26). Line numbers in the spec's audit table that name `poc-help` are stale and are corrected by task 0.4 |
| 0.2 | **Behaviour probes.** In a throwaway repo with a subdirectory, a `poc-spec/` folder, a nested repo and a linked worktree, with the session started in the subdirectory, record: (a) whether `cd "<root>"` in one Bash call carries to the next call, in the main session and inside a forked skill's agent; (b) the working directory a `context: fork` agent starts in (the docs do not state it) and what `git rev-parse --show-toplevel` prints for it; (c) what `git -C "<path>" rev-parse` prints for a nested repo and for a linked worktree, and whether `--git-dir` differs from `--git-common-dir` there; (d) whether `./verify.sh` is found after `cd "<root>" &&` as one compound command; (e) whether a pinned `Bash(...)` grant accepts `cd "<root>" && ...` (the handoff gotcha says a compound command counts as a different command), and which grant form the evals cases need; (f) whether the harness setting `blockReadsOutsideWorkingDirectories` blocks reading the root from a subdirectory; (g) whether each new Bash call raises a permission prompt in an interactive session. Use the Phase 1 runner if rebased in, otherwise by hand. Single runs only | `docs/layout/findings.md` has each answer with the exact commands, `claude --version`, date and the observed output. Anything that contradicts Rule A or the spec's **(docs)** statements changes the spec first |
| 0.3 | **Judge skill-body injection.** Test the documented `` !`<command>` `` preprocessing and `${CLAUDE_PROJECT_DIR}` in a skill body from a subdirectory: does the model see the output, is `${CLAUDE_PROJECT_DIR}` the git root or the launch directory, and what happens when `disableSkillShellExecution` is set. Record the docs URL and date | Recorded as works, works with limits, or unusable. The spec stays correct either way, because it does not depend on injection. If it works and the limits are acceptable, the maintainer may choose to use it in the forked skills as a later change, not in 0.2.0 |
| 0.4 | **Baseline audit on the rebased tree.** Save the exact command and its output: every mention of `POC.md`, `LOG.md`, `SUMMARY.md`, `verify.sh`, `current directory`, `current working directory`, `current repo`, `current git repo`, `this directory`, `cwd`, `pwd`, `$PWD`, `./` and `gitleaks dir .` in the frontmatter and body of every file in `skills/`, `agents/`, plus `README.md`, `docs/workflow.md` | `docs/layout/findings.md` has the command and a table of file and line counts. Every row of the spec's audit table is matched against it, and any hit not in the table is added to the spec before Phase 1 |

**Gate 0.** The branch base is settled. The probes either confirm Rule A as written or have changed it. The audit table covers every hit in 0.4. Then task R.3 runs.

## Phase 1: tests first

One new file, `tests/test_docs_layout.py`, using only the standard library (same style as `tests/test_skills_contract.py`). The rule texts live in the test file as constants, and one test checks that the same text sits in `docs/layout/spec.md`.

| ID | Task | Acceptance |
|---|---|---|
| 1.1 | Constants for Rule A, Rule B, the wiring block, the legacy note and both packager warning lines, copied from the spec. Test 10: each constant equals the text in the spec | Fails if any constant differs from the spec |
| 1.2 | Tests 1 and 2: Rules A and B verbatim in the files in the spec. The file lists are constants, so adding a skill without a rule fails | Fail now for every listed file, naming it |
| 1.3 | Test 3: no bare `POC.md` or `LOG.md` anywhere in a skill or agent, frontmatter included, outside Rule B, the legacy note, the packager warning lines and `poc-start` template headings. `poc-spec/POC.md` and `poc-spec/LOG.md` allowed only in `poc-start`, the wiring block, the `poc-help` table, `README.md` and `docs/workflow.md` | Fails now with file and line for each bare mention. The count is not predicted from the 0.4 baseline, because the baseline includes mentions this test allows |
| 1.4 | Test 4: the banned phrases (`current directory`, `current working directory`, `current repo`, `current git repo`, `this directory`, `cwd`, `pwd`, `$PWD`) appear nowhere in a skill or agent, frontmatter included, except inside Rule A | Fails now with file and line |
| 1.5 | Tests 5 and 6: `SUMMARY.md` and `verify.sh` never carry a `poc-spec/` or `<docs>/` prefix, and any path token ending in `spec/` or `specs/` in `skills/`, `agents/`, `README.md`, `docs/workflow.md` is exactly `poc-spec/` | Both pass now. They are guards, so they are checked by the mutation step below, not by failing first |
| 1.6 | Tests 7, 8 and 9: the `poc-start` write step and wiring text, the packager warning lines and checks, `README.md` and `docs/workflow.md` mentions prefixed `poc-spec/` or on an "older layout" line | Fail now |
| 1.7 | Run the whole suite | Existing tests pass. Tests 1 to 4 and 7 to 9 fail only for the expected reasons. The failure list is saved in `docs/layout/findings.md` as the red baseline |

**Gate 1.** Every new test except the two guards (5 and 6) fails now, and its message names the file and line to fix. Mutation check on a scratch copy: for each of the ten tests apply one deliberate wrong edit (reword Rule A by one word, add a bare `LOG.md`, change `poc-spec/` to `specs/` and to `spec/`, add `pwd`, break a warning line, add a mention in `README.md` with no prefix) and confirm the matching test fails. A test that does not fail is a bad test and is fixed here.

## Phase 2: implementation

Work in small commits, one per task group, so a review can follow them. After each group run the new tests and note which went green. Keep edits to `poc-help`, `poc-research`, `poc-log`, `poc-checkpoint` and the contract test in their own commits, so a conflict with `help-and-next` is easy to read.

| ID | Task | Files | Acceptance |
|---|---|---|---|
| 2.1 | `poc-start`: description, Rule A, root check and linked-worktree check, writes `poc-spec/POC.md` and `poc-spec/LOG.md` (creating `poc-spec/`), `verify.sh` at the root, never overwrite any target file, new public-repo notice, new wiring block, step 7 print path, template stub comment and `echo` | `skills/poc-start/SKILL.md` | Tests 3, 4, 7 green for this file. A diff of the templates shows path text changes only, headings byte-identical |
| 2.2 | `poc-log`, `poc-checkpoint`: Rules A and B, `<docs>` in every path including the `Next:` lines, `SUMMARY.md` at the root, the neither-exists message kept | `skills/poc-log/SKILL.md`, `skills/poc-checkpoint/SKILL.md` | Tests 1 to 5 green for both |
| 2.3 | `poc-harden`: default root, Rules A and B once in the gate step, `<docs>` in both paths, agent briefs name the repo root as an absolute path, lean step 4 adds "Show its report." | `skills/poc-harden/SKILL.md` | Tests 1 to 4 green. Step numbers unchanged (no document quotes them, checked: `docs/measurements.md` and `docs/workflow.md` have no "step N" text), the one wording change in step 4 is shown in the diff |
| 2.4 | Forked skills: `poc-package`, `poc-review`, `poc-verify` per the audit table, default is the repo root. `poc-build`, `poc-debug` get Rule A, and `poc-build` tells the implementer its brief paths are relative to the repo root | `skills/poc-package/`, `poc-review/`, `poc-verify/`, `poc-build/`, `poc-debug/` | Tests 1 to 4 green. Frontmatter keys (`context`, `agent`, `argument-hint`) unchanged, only description wording where the audit says |
| 2.5 | `poc-research`: Rules A and B for step 4's `POC.md` reference. `research-protocol` says "the repo at its root". `poc-sources` untouched | `skills/poc-research/SKILL.md`, `skills/research-protocol/SKILL.md` | Tests 1 to 4 green. `git diff --stat` shows no change under `skills/poc-sources/` |
| 2.6 | `poc-help`: Rules A and B, `No PoC found.`, the legacy-layout line, table paths | `skills/poc-help/SKILL.md` | Tests green. The skill still says "Write nothing" (existing contract test) |
| 2.7 | Agents: Rule A in all seven. `packager` also gets Rule B, `verify.sh` at the root, and the warning with both lines, the `git ls-files` checks and its limiting rules, placed after step 5, with the line under "Open gaps" | `agents/*.md` | Tests 1, 2, 4, 8 green. The packager's 40-line output cap is still stated and the warning counts inside it. Frontmatter diff of every agent is empty |
| 2.8 | `README.md` and `docs/workflow.md`: `poc-spec/` paths, a Location column, one note on the older layout, SUMMARY stays at the root, Status line 0.2.0, a note that Windows is untested | `README.md`, `docs/workflow.md` | Tests 5, 9 green. No behaviour claim that Phase 3 has not checked |
| 2.9 | `CHANGELOG.md` 0.2.0: new layout, fallback for the old one, repo-root paths, `cd "<root>" &&` on every command (and the extra permission prompt if 0.2(g) found one), packager warning, how to migrate by hand, and "run `/spike-loop:poc-sources refresh` to update a generated `researcher-internal` agent". `plugin.json` 0.2.0 | `CHANGELOG.md`, `.claude-plugin/plugin.json` | Existing version test passes. The changelog says an older PoC keeps working and nothing moves automatically |

**Gate 2.** The whole suite is green, `typos` and `gitleaks` are clean, and no em dashes. If 0.1 chose a rebase onto `help-and-next`, its 0.1.2 changelog entry is intact and 0.2.0 sits above it.

## Phase 3: verification

| ID | Task | Acceptance |
|---|---|---|
| 3.1 | Re-run the 0.4 audit command and compare | Every hit is in the new form or a documented exception. The difference table is saved in `docs/layout/findings.md` |
| 3.2 | Re-run the Gate 1 mutation check on the final tree | Each test fails when it should. Recorded as a table |
| 3.3 | Independent review of the diff against the base: the `reviewer` agent with the repo root and the success check "every path is repo-root relative, the docs folder resolves one way, an old PoC still works, the packager warning fires only in its stated cases", no conclusions | Findings fixed or recorded with a reason in `docs/layout/review.md` |
| 3.4 | **Manual checks in scratch repos** (under `$TMPDIR`, plugin loaded from this branch). In a new repo: `poc-start`, `poc-log`, `poc-checkpoint stop`, `poc-help`, each from the root and from a subdirectory. Forked skills from a subdirectory: `poc-verify`, `poc-review`, `poc-package`. Old layout: `poc-log`, `poc-help` (legacy line) and `poc-checkpoint` with `POC.md` and `LOG.md` at the root. Both layouts, and a partial move (only `POC.md` moved): stops, names files. A path argument from another repo: `poc-harden ../other` acts on the other repo. A nested repo and a linked worktree: `poc-start` asks before writing. Migration by hand with untracked files: the `mv` variant works | Each case's result is written to `docs/layout/findings.md` with the date. A case that behaves otherwise than the spec says is fixed, or the spec is changed and re-reviewed |
| 3.5 | Packager warning, manual: public repo with `poc-spec/` tracked; untracked and not ignored; untracked and ignored; private with `Deal: none`; the older layout tracked | Warning in the first, second and fifth. None in the third and fourth. No file edited and no `git rm` run in any |

**Gate 3.** All pass. Anything that failed is fixed or written down as a known gap in the changelog, not left silent.

## Phase 4: evals fixtures and cases (on `evals-spec`, rebased onto this branch)

| ID | Task | Acceptance |
|---|---|---|
| 4.1 | Rebase `evals-spec` onto `docs-layout` (merged or not). Keep `evals/fixtures/poc-log-basic` as the old-layout fixture | The tree builds and `python3 -m unittest discover -s tests` passes |
| 4.2 | Fix `poc-log/basic` `allowed_tools` so Rule A's commands are permitted, in the grant form found in 0.2(e). Then check it passes | `poc-log/basic` passes, and a failure at this step is a case fix, not a plugin defect |
| 4.3 | Add fixture `poc-log-specs` and case `poc-log/poc-spec-layout` | The case passes and reads `poc-spec/LOG.md` |
| 4.4 | Check whether the runner can set a per-case working directory and whether `blockReadsOutsideWorkingDirectories` affects it (0.2(f)). If not supported, add it with a unit test using `tests/fake_claude.py` | A case can start in a fixture subdirectory, and the fake-claude test shows the directory reaches the run |
| 4.5 | Cases from the spec: `poc-start` layout, `poc-start` refuses to overwrite any target file, `poc-log` half-migrated and partial-move stops, `poc-checkpoint stop` writes `SUMMARY.md` at the root under both layouts, `poc-log` from a subdirectory | Each case has a deterministic grader and runs under its cost cap. The first live run of each is a single run |
| 4.6 | Packager warning cases: tracked in a public repo, untracked and not ignored, ignored and untracked, private with no deal | Graders check the warning line and that no file changed |
| 4.7 | Update `docs/evals/plan.md` Phase 2 so its stage cases use the new layout by default, and note the fixture decision | Plan updated, tests pass |

The Gate 0 condition on scripted subscription use still stands for any suite larger than a smoke test, so 4.5 and 4.6 run one case at a time until the maintainer clears it.

## Phase 5: release (only with the maintainer's approval at each step)

| ID | Task | Acceptance |
|---|---|---|
| 5.1 | Pre-push review of the outgoing changes: `gitleaks`, then read the diff for customer names, internal hostnames or URLs, deal data, connector or workspace IDs, and any internal-policy wording (the reviewer flagged that `docs/evals/plan.md` on `evals-spec` names an internal policy in a public repo, raise it here) | Written confirmation in the PR description that it was done |
| 5.2 | Push `docs-layout` and open a PR | PR open, attribution lines as the repo rules require |
| 5.3 | After merge, tag `v0.2.0` and create the release, only if asked | Tag and release exist |

## Risks specific to this plan

| Risk | Effect | Mitigation |
|---|---|---|
| The tests pass on wording and the skills still misbehave | False confidence | Phase 3.4 and 3.5 run the real commands, Phase 4 adds model-run cases |
| Rule A is wrong for forked agents or for `cd` across calls | Commands fail from a subdirectory | Probe 0.2 runs before any edit, and the spec changes first if it fails |
| The branch base is settled late | Conflicts in files `help-and-next` changed | Task 0.1 is first, and those files get their own commits |
| Phase 4 is skipped | The new layout is untested by a model | Gate 3 does not depend on it, but the changelog states the layout was checked by hand only until Phase 4 runs |
| A reviewer finding changes a rule after Phase 1 | Tests and constants need redoing | R.3 re-reviews after Phase 0, and the constants have one source (the spec) |
| The paid probes run before the terms question is settled | Policy breach | Single runs only, and the maintainer decides first |

## Open decisions for the maintainer

1. Phase 0.1: settled, `help-and-next` was merged first.
2. Whether Phase 4 must finish before the 0.2.0 release, or the release goes out with hand-checked results and Phase 4 follows.
3. Spec open question 2: a relative path argument is read from the session directory, only to find the root. Confirm, or choose another rule.
4. Whether the Phase 0 probes may run now as single paid runs, given the scripted-use terms are unread.
