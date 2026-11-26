# Findings: layout work

Evidence for `docs/layout/spec.md`. Each section says what was run, on which commit, when, and what it showed. Statements here are observations, not design.

## 0.4 Baseline audit on the real base (done 2026-11-26)

**Base:** `docs-layout` at `38d8a4c`, which is `main` at `6dec01e` (PR #2 merged) plus the layout docs. The tree under audit has `poc-help`, `poc-research`, `poc-log` and `poc-checkpoint` as merged.

**Command (reproducible, writes nothing):**

```
python3 docs/layout/audit.py          # counts per file
python3 docs/layout/audit.py --lines  # every hit, tagged [fm] frontmatter or [body]
```

It scans `skills/*/SKILL.md`, `agents/*.md`, `README.md` and `docs/workflow.md`. Counts are lines that match, not total matches. `poc-sources/scripts/spike_sources.py` is code, not scanned, and has no repo-relative document paths (user-level paths only).

**Result:**

| File | POC.md | LOG.md | SUMMARY.md | verify.sh | `./` | `gitleaks dir .` | "repo path" | vague base |
|---|---|---|---|---|---|---|---|---|
| `skills/poc-checkpoint/SKILL.md` | 3 | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| `skills/poc-harden/SKILL.md` | 3 | 2 | 3 | 2 | 2 | 2 | 4 | 1 |
| `skills/poc-help/SKILL.md` | 4 | 5 | 5 | 2 | 0 | 0 | 0 | 1 |
| `skills/poc-log/SKILL.md` | 3 | 5 | 0 | 0 | 0 | 0 | 0 | 1 |
| `skills/poc-package/SKILL.md` | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 1 |
| `skills/poc-research/SKILL.md` | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `skills/poc-review/SKILL.md` | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 1 |
| `skills/poc-start/SKILL.md` | 8 | 5 | 0 | 6 | 1 | 0 | 0 | 2 |
| `skills/poc-verify/SKILL.md` | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 2 |
| `skills/research-protocol/SKILL.md` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| `agents/packager.md` | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 |
| `agents/reviewer-lite.md` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 |
| `agents/verifier.md` | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 |
| `README.md` | 2 | 3 | 1 | 3 | 0 | 0 | 0 | 0 |
| `docs/workflow.md` | 8 | 5 | 2 | 2 | 1 | 0 | 0 | 0 |
| **Total** | 35 | 31 | 15 | 20 | 6 | 2 | 4 | 10 |

Files with no hit on any pattern: `poc-build`, `poc-debug`, `poc-sources`, `agents/debugger.md`, `agents/implementer.md`, `agents/researcher.md`, `agents/reviewer.md`. They still get Rule A, because they read or write repo files by path without naming a document.

**Compared with the spec's audit table (draft 2):**

| Difference | What it was | Action |
|---|---|---|
| Stale line numbers for `poc-help` | The spec read `0e5ad69`. The merged skill (`3ca0db3`) dropped the read of other skills' files. Hits are now at lines 17, 26, 27 (table rows) and 39 to 46 (the status steps) | Spec row corrected: lines 17, 26 and 39 to 46. Line 27 is the `poc-checkpoint` row, which names `SUMMARY.md` and stays |
| Stale line numbers for `poc-harden` | Spec said 17, 19, 25, 27 for the four agent briefs, and lean step 4 at line 19. Actual: "repo path" at lines 19, 21, 27, 29, lean step 4 at 21 | Spec corrected |
| `CHANGELOG.md` matches `LOG.md` | `README.md` line 49 mentions `CHANGELOG.md`, which a plain match on `LOG.md` counts. It would have failed test 3 for a correct file | Audit script and spec test 3 now require no word character before the name. `README.md` `LOG.md` count is 3, not 4 |
| "current project" not in the banned list | `poc-verify` frontmatter line 3 says "on the current project", meaning the repo | Added to the banned phrases (spec test 4, plan 1.4, audit script) and to the `poc-verify` row |
| Phrases found but deliberately not banned | "the current PoC" in the `poc-log` and `poc-help` descriptions means the PoC, not a directory. `argument-hint: "[project path]"` in `poc-harden` and `poc-package` names an argument, which Rule A defines | No change |
| Everything else | All other hits in the output are covered by a row in the spec's table (`poc-start` lines 3, 14, 17 to 19, 23, 46, 50, 65 to 71; `poc-log` lines 3, 13 to 17; `poc-checkpoint` lines 3, 13 to 16, 18, 19; `poc-package` lines 9, 11; `poc-review` line 11; `poc-research` line 16; `research-protocol` line 13; `agents/packager.md` lines 13, 20, 23; `reviewer-lite` line 34; `verifier` lines 11, 14; `README.md` and `docs/workflow.md`) | None |

No hit was found that the spec's table missed, apart from the line-number drift above. The post-change audit (plan task 3.1) compares against this output.

## Phase 1: tests first (done 2026-11-26)

**What was built.** `tests/test_docs_layout.py` (12 tests, standard library only). The rule texts in it are generated from `docs/layout/spec.md`, and `test_constants_equal_the_spec` fails if they drift. `SPIKE_LAYOUT_ROOT` points the tests at another copy of the tree. Two helper scripts in `docs/layout/tools/`: `make_standin.py` builds a mechanically compliant stand-in of the plugin tree (not the implementation, only a proof the tests can pass) and `mutate.py` runs the mutation check. Plan task 3.2 re-runs `mutate.py` on the real tree after Phase 2.

**1.7 Red baseline** (real tree, `docs-layout` at `6a8cbfd` plus the new test file). `python3 -m unittest discover -s tests` gives 41 tests, 7 failures. The 7 failing tests are the new ones, and each message names the file and line:

| Test (spec number) | Result | Problem lines reported |
|---|---|---|
| Rule A in every skill and agent (1) | FAIL | 18 (11 skills and 7 agents) |
| Rule B in every file that resolves the docs folder (2) | FAIL | 8 |
| No hard-coded root path (3) | FAIL | 53 |
| No vague base (4) | FAIL | 11 |
| `poc-start` write step, wiring, stub (7) | FAIL | 4 |
| Packager warning and its limits (8) | FAIL | 7 |
| README and workflow use the new paths (9) | FAIL | 18 |
| Root files stay at the root (5) | ok, guard | 0 |
| Folder name is exactly `poc-spec/` (6) | ok, guard | 0 |
| Constants equal the spec (10) | ok | 0 |
| Every skill listed for Rule A or exempt | ok | 0 |
| `poc-start` does not carry Rule B | ok | 0 |

The suite is red on this branch on purpose until Phase 2. Nothing else is affected: the 29 tests that were green are still green.

**Gate 1: passed.**

1. *The tests can pass.* On the stand-in tree all 12 pass.
2. *The tests catch what they are for.* `python3 docs/layout/tools/make_standin.py . <dir>` then `python3 docs/layout/tools/mutate.py <dir>`: 25 deliberate wrong edits each fail exactly the intended test, and 4 negative controls (a `CHANGELOG.md` mention in the README, "the current PoC" in a description, a README line that names `poc-spec/POC.md`, a README line with "older layout") fail nothing. Result: 29 rows, 0 wrong. The edits cover a reworded Rule A and Rule B, a bare `LOG.md` in a body and in frontmatter, a hard-coded `poc-spec/POC.md`, `pwd` and "current directory" and "current project", `poc-spec/SUMMARY.md` and `<docs>/verify.sh`, `specs/`, `spec/` and `poc_spec/`, a lost log path and wiring block in `poc-start`, a broken warning line and three weakened `git ls-files` checks, bare names in the README and workflow, drift between the spec and the constants, and a new skill with no Rule A.

**Defects in the tests found by the stand-in and the mutation run (all fixed before the commit):**

| Defect | How it showed | Fix |
|---|---|---|
| Test 3 flagged the packager's own `git ls-files` commands, which name `POC.md`, `LOG.md` and `poc-spec/POC.md` on purpose | The stand-in failed test 3 | The four commands are exempt, and only when verbatim |
| Test 8 required a bare `git ls-files`, which the packager's existing clean-clone step already contains, so it would pass without the new check | Review of the red baseline | The spec now names the four exact commands and test 8 requires them |
| Spec said a drift to `.poc/` is caught by test 6, but a name not ending in `spec/` or `specs/` cannot be | Writing test 6 | Spec text corrected. Test 7 still requires the exact `poc-spec/` paths in `poc-start` |
| Three mutation expectations were wrong (an edited Rule B, warning line or command also fails test 3, because the exemption is verbatim; one edit hit the wrong line) | First mutation runs | Expectations and the edit corrected. The verbatim effect is kept on purpose and documented in `mutate.py` |

## 0.2 and 0.3 Behaviour probes (done 2026-11-26)

**Run.** `docs/layout/tools/probes/probe_run.py`, a separate runner that borrows the token helper from an `evals-spec` checkout (the Phase 1 harness cannot start a case below the workspace root, see the last table) with a throwaway plugin (`probe`, in `docs/layout/tools/probes/plugin/`) so the results describe Claude Code and not the spike-loop skills. Claude Code 2.1.325, Haiku (the init event of the fork runs says Sonnet, but there the main session took 0 turns with synthetic text and `modelUsage` lists only `claude-haiku-5-5`), isolated HOME, the subscription token read by the harness helper and never printed. One run per probe, 17 runs, about $0.04 in total on the plan allowance. Anthropic's terms on scripted use of a subscription were still unread, and the maintainer approved single runs. Raw event logs stay in the session scratch directory because they contain local paths.

**Fixture.** A repo with `verify.sh` and `poc-spec/` at the root, `sub/deep/`, an untracked nested git repo `nested/`, and a linked worktree `wt/`. Paths below are written `<root>`, `<start>` (the directory the session was launched in) and `<work>`.

| ID | Question | Observation |
|---|---|---|
| R1 | Main session started in `<root>/sub/deep` | `pwd` is `<start>`. `git rev-parse --show-toplevel` is `<root>`. A lone `cd "<root>"` returns `Shell cwd was reset to <start>`. The agent put that `cd` and the following `pwd` in one assistant message, so the `pwd` says nothing about persistence. The compound `cd "<root>" && pwd && ls verify.sh && ./verify.sh` ran in `<root>` |
| R2, R2b | Forked skill (`context: fork`, `agent:`) from the same directory | The agent's `pwd` is `<start>`, the same as the session. Its `git rev-parse --show-toplevel` is `<root>`. The compound `cd "<root>" && ...` worked in the agent. The agent's lone `cd` returned `(Bash completed with no output)`, with no reset notice. Persistence of a lone `cd` in an agent is **not decided**: both times the agent put the `cd` and the `pwd` in one assistant message (it said so the second time) despite an instruction to go one at a time. The docs, as the reviewer read them, say it does not persist |
| R3 | Session started in the nested repo | `--show-toplevel` is the nested repo, not the outer one. `git -C "<outer>/sub/deep" rev-parse --show-toplevel` is the outer root. R3 is the one main-session probe where the lone `cd` and the following `pwd` were separate turns: the `cd` was reset and the `pwd` printed the launch directory |
| R4 | Session started in a linked worktree | `--show-toplevel` is the worktree. `--git-dir` is `<root>/.git/worktrees/wt` and `--git-common-dir` is `<root>/.git`. A lone `cd "<root>"` is reset to the worktree (the `cd` and `pwd` were again in one assistant message) |
| R5 | `` !`cmd` `` in a skill body (main session) | Works. `` !`pwd` `` printed `<start>`. `` !`git rev-parse --show-toplevel` `` printed `<root>`. `${CLAUDE_PROJECT_DIR}` printed **`<start>`, the launch directory, not the git root**. `${CLAUDE_SKILL_DIR}` printed the skill's own directory |
| R6 | The same in a forked skill | Works the same. The agent's task text already held `<root>` |
| R7 | Same with `disableSkillShellExecution: true` | The two injected lines became `[shell command execution disabled by policy]`. `${CLAUDE_PROJECT_DIR}` still expanded |
| R8 | `blockReadsOutsideWorkingDirectories: true` (the Phase 1 harness setting), `Read` of `<root>/poc-spec/POC.md` from `<start>`, absolute and relative path | Both blocked: "is outside `<start>`; the ... setting blocks reads outside the working directories. Ask the user to add the directory with /add-dir, or to remove that setting". The working directory is the launch directory |
| R16 | The same two reads with default settings | Both succeeded, no denial |
| R9 | Grant `Bash(./verify.sh)` only, command `cd "<root>" && ./verify.sh` | Blocked: "cd in `<root>` was blocked. For security, Claude Code may only change directories to the allowed working directories for this session: `<start>`" |
| R10 | Grant `Bash(cd *)` only, same command | "This Bash command contains multiple operations. The following parts require approval: cd "<root>", ./verify.sh". The `cd` is listed as needing approval despite the grant, which shows `Bash(cd *)` does not cover a `cd` outside the session's directories |
| R11 | Grant `Bash(cd * && ./verify.sh)` (a pattern for the whole compound) | Same message as R10. A compound-pattern grant does not allow the compound |
| R12 | Grants `Bash(cd *)` and `Bash(./verify.sh)` | Still blocked with the R9 message: the `cd` to a root above the launch directory is refused even when `cd` is granted |
| R13 | R12 plus `permissions.additionalDirectories: [<root>]` | Ran in `<root>`. No `Shell cwd was reset` notice appeared, unlike R1, R3, R4 and R15. There was no control run without `Bash(cd *)`, so it is not shown that the grant was needed |
| R15 | Broad grant `Bash`, same compound | Ran in `<root>`, then `Shell cwd was reset to <start>` |
| R14 | `"<root>/verify.sh"` by absolute path, no `cd` | Ran, but `verify.sh` saw `<start>` as its working directory |

Also found:

- **Every run showed extra `cc-plugin-*` plugins in the init event** (`cc-plugin-sec-default`, `cc-plugin-agents-md` and others). Their `path` is `builtin`, so they ship inside Claude Code and are not loaded from the isolated HOME. The Phase 1 isolation allowlist already accounts for init contents.
- **`git rev-parse --git-dir` and `--git-common-dir` are not comparable as printed.** In `<root>/sub/deep` of an ordinary repo, `--git-dir` is absolute and `--git-common-dir` is `../../.git`, so a plain comparison calls every subdirectory session a linked worktree. With `--path-format=absolute` (git 2.55.0 here, the minimum git version for the flag is not checked) the two are identical in an ordinary repo and in the nested repo, and differ in the linked worktree.
- **Not measurable headless:** whether an interactive session in default permission mode prompts for the `cd` or for each part of a compound command. The headless denials above show the same rules, so a prompt is likely, but that is an inference.

**What the results mean for the spec.**

| Result | Effect |
|---|---|
| The shell is reset after a `cd` that leaves the session's directories (R3 as separate turns), and a compound `cd "<root>" && ...` works under a broad grant or with the root added. Persistence in an agent is undecided, and the docs say a `cd` inside an allowed directory does carry in the main session | Rule A says the shell can be reset and is in an agent, and uses the compound form, so it does not depend on persistence |
| File tools resolve a relative path against the launch directory (R16, `../../poc-spec/POC.md` read the root file) | Rule A tells file tools to take `<root>/<path>` in full |
| A `cd` adds a refusal or a prompt that `git -C` and `date` do not need (the docs on `cd` with `git` are the reviewer's reading, not tested) | Rule A uses `git -C "<root>"` for git and no `cd` for commands that need no directory. The packager's `git ls-files` commands become `git -C "<root>" ls-files ...` |
| The root above the launch directory is outside the allowed working directories, so `cd` there is blocked under narrow grants and fixed by `/add-dir` or `additionalDirectories` | Rule A gets a stop-and-explain clause (do not work around the refusal, tell the user to start the session at the repo root or run `/add-dir "<root>"`). The goal "behaves the same from any subdirectory" holds only when the root is a permitted directory |
| Each part of a compound command needs its own approval, and a compound-pattern grant does not work | A changelog note, and the eval cases need one grant per part |
| `git-dir` vs `git-common-dir` compared as printed gives a false linked-worktree result in subdirectories | `poc-start` uses `--path-format=absolute` |
| `` !`cmd` `` works in main and forked skills, and `${CLAUDE_PROJECT_DIR}` is the launch directory | A forked skill could name the root by injection. Not used in 0.2.0 (it can be disabled by policy, and the agent resolves the root with git anyway). Recorded as an option, spec open question 3 |
| Absolute-path `verify.sh` runs in the launch directory | It is no substitute for `cd "<root>" &&` unless a `verify.sh` locates its own directory |
| The Phase 1 harness starts every case in the workspace root with a fixed `SETTINGS` | Subdirectory eval cases need a per-case working directory, `additionalDirectories` or no `blockReads` setting, and one grant per compound part. Plan 4.4 is no longer an open question: it must be added |

## R.3 second review: facts checked by the author (2026-11-26)

Before applying the review, the author re-checked what could be checked locally.

| Reviewer claim | Check | Result |
|---|---|---|
| R1 and R4 issued the lone `cd` and `pwd` in one assistant message | Grouped the event logs by message id | True for R1, R4, R2 and R2b. R3 issued them separately |
| Reset notices: R13 none, R1 and R15 present | Counted `Shell cwd was reset` in tool results | R1 2, R3 2, R4 2, R15 1, R13 0, R2 and R2b 0 |
| Fork runs' `modelUsage` is haiku only | Read the result events | True |
| The `cc-plugin-*` plugins are `path: builtin` | Read the init event | True |
| `git rev-parse --show-prefix` is empty at the root, also through a symlink | Ran it in a temporary repo and a symlink to it | True (the symlink resolved to `/private/var/...` in `--show-toplevel`, `pwd` kept `/var/...`, the prefix was empty) |
| Bare repo: `--show-toplevel` fails | Ran it | "this operation must be run in a work tree" |
| First `git worktree list --porcelain` entry is the main checkout | Ran it | True for an ordinary repo. The `bare` case was not re-run here |
| `--path-format` first shipped in git 2.31.0 | Not checked by the author | The reviewer's reading of the git release notes |

Not re-run: the `GIT_DIR`, submodule and worktree-of-a-bare-repo cases, and whether a `cd` into the packager's `$TMPDIR` clone is refused under narrow grants. A `cd` plus `git` probe with `additionalDirectories` was suggested and not run, to keep to the maintainer's approval of the original probes.
