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
