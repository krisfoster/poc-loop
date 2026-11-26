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
