# Spec: one docs folder inside a PoC, and one base for every path

Status: draft 2, revised after the independent review of 2026-11-26 (see `docs/layout/review.md`). Branch: `docs-layout`, off `main` at `e1f31b8`. Nothing here is implemented.

Maintainer decisions: the folder is `poc-spec/` (always that name), `SUMMARY.md` stays at the root, existing PoCs keep working from the root, the packager warns about the folder, the version is 0.2.0, and every path is relative to the repo root.

How to read the evidence. Statements about the plugin come from reading the files on `main`, plus `skills/poc-help`, `skills/poc-research`, `skills/poc-log`, `skills/poc-checkpoint` and `tests/test_skills_contract.py` as changed by `help-and-next`, which was merged to `main` on 2026-11-26 as PR #2 (`6dec01e`) after this spec was drafted from commit `0e5ad69`. The merged `poc-help` also dropped its read of other skills' files (commit `3ca0db3`), so plan task 0.4 re-ran the audit on 2026-11-26 and the audit table's line numbers come from that run. Statements about Claude Code behaviour are marked **(docs)**: they come from the reviewer's reading of code.claude.com on 2026-11-26 (pages: `/docs/en/skills`, `/docs/en/sub-agents`, `/docs/en/worktrees`, `/docs/en/tools-reference`; the pages show no version). Plan tasks 0.2 and 0.3 tested several of them on 2026-11-26 (Claude Code 2.1.325, Haiku, one run per probe, details and caveats in `docs/layout/findings.md`): those are marked **(observed)**. The rest are untested. Where the docs do not say, this spec says **not stated**.

## Problem

A PoC started with `/spike-loop:poc-start` puts its working documents (`POC.md`, `LOG.md`) beside the code, and later commands add `SUMMARY.md`. Anything else written about the PoC (a spec, a plan, findings, a hand-off for a fresh session) has no agreed home. Three consequences:

1. The repo root fills with documents that are not the product.
2. `LOG.md` is a working diary that can hold customer names. Excluding it from a public repo or a customer hand-off means remembering one file, and the next file added is easy to forget.
3. No single place defines where the files are. Each skill hard-codes the root path, so any change of layout touches all of them.

A path audit found a second problem: the skills do not agree on what "here" means. The same idea is written several ways (see "Path audit"), and several commands assume the shell is already at the repo root. Run from a subdirectory, `./verify.sh`, `gitleaks dir .` and the packager's copy step act on the wrong directory.

## Goals

1. All working documents for a PoC live in one folder, `poc-spec/`, so one exclusion rule covers them.
2. Every path in every skill and agent is relative to the repo root, defined once, so a command behaves the same from any subdirectory when the repo root is a directory the session may use. When it is not, the command says so and stops (Rule A).
3. The docs folder is resolved one way by every skill and agent.
4. A PoC started before this change keeps working with no action from the user, and can be migrated by hand with a few lines.
5. Free tests fail if a skill hard-codes a root document path or uses a vague "current directory" phrase.
6. The packager warns when `poc-spec/` would travel with the repo, so a diary with customer names is not shared by accident.
7. The layout leaves room for hand-offs and for spec, plan and findings documents, which the next specs (hand-off state, language constitutions) will write.

## Non-goals

- Moving this plugin repo's own documentation. `docs/` and, on `evals-spec`, `docs/evals/` and `docs/handoffs/` stay where they are. This spec governs the PoC repos the plugin creates.
- Writing hand-offs. What a phase writes to disk is the hand-off spec. This spec only reserves `poc-spec/handoffs/`.
- An automatic migration command. Moving a user's files without being asked is a risk this spec does not take (see "Migration").
- Changing what `POC.md`, `LOG.md` or `SUMMARY.md` contain, or their templates beyond the paths they name.
- PoCs that live in a subdirectory of a larger repo. The repo root is the PoC root, which is the decision.
- Bare repositories and environments that set `GIT_DIR` or `GIT_WORK_TREE`. In a bare repository `git rev-parse --show-toplevel` fails ("this operation must be run in a work tree", observed locally and by the reviewer), so Rule A's outside-git fallback would apply the start directory, which is wrong. `poc-start` stops and says bare repositories are not supported. A submodule is treated as a repository of its own: the worktree check does not flag it, because its git directory and common directory are equal (reported by the reviewer, not re-run). With `GIT_DIR` set, `--show-toplevel` returns the working directory the reviewer measured, so the root can be wrong. Not handled.
- Making a session started below the repo root work when its permissions exclude the root. The probes show Claude Code blocks `cd` to a directory outside the session's allowed directories under narrow grants (see Rule A). The plugin reports it and does not work around it.
- Windows. The shell snippets assume a POSIX shell. PowerShell 5.1 has no `&&`, and `C:\` paths and symlink-resolved roots are untested. State this in the README, do not claim support.
- The research sources file (`~/.config/spike-loop/research-sources.md`), the helper script under `${CLAUDE_SKILL_DIR}`, and the generated user-level agent file. They are user-level and plugin-level paths, outside every repo on purpose.

## Decisions

| Question | Decision | Reason |
|---|---|---|
| Folder name | `poc-spec/`, always, never `specs/` | Maintainer's choice. The `poc-` prefix matches the commands and avoids a clash with a plain `specs/` folder. |
| Moves into `poc-spec/` | `POC.md`, `LOG.md`, `handoffs/`, and `<feature>/{spec,plan,findings}.md` for spec-driven work | These are working documents, and `LOG.md` can hold customer names. |
| Stays at the root | `README.md`, `CLAUDE.md`, `verify.sh`, `.env.example`, `.gitignore`, `.envrc`, and `SUMMARY.md` | The first six are tools or conventions that expect the root. `SUMMARY.md` can be a deliverable, and its own rule already bars customer names in a public repo. |
| Existing PoCs | Root layout keeps working through a fallback. No automatic move | Zero-effort upgrade, and nothing moves without the user asking. |
| Path base | The repo root. See Rule A for how it is found | Maintainer's decision. One base means one behaviour. |
| Packager warning | Yes, see "Packager warning" | Stops a diary with customer names travelling with a hand-off. |
| Version | 0.2.0 | A new PoC's files are in a different place. If `help-and-next` ships as 0.1.2 first, this is the next minor. |

## Layout

```
<repo root>/
  README.md  CLAUDE.md  verify.sh  .env.example  SUMMARY.md     (root, unchanged)
  poc-spec/
    POC.md
    LOG.md
    handoffs/<YYYY-MM-DD>-<topic>.md          (reserved, written by the hand-off spec)
    <feature>/{spec,plan,findings}.md          (spec-driven work, written by the user or other skills)
```

The plugin never creates empty subfolders.

## The two rules

Both rules are stated here once and copied verbatim into each file that needs them. A shared file would need a read per command and add a way to fail. Injecting the text by a skill's shell preprocessing might avoid the read, but depends on a feature that plan task 0.3 judged: it works, but policy can switch it off (see below). Tests compare the copies to this text.

### Rule A: paths

> **Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the path given in the arguments if there is one, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that uses a relative path or runs a script as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run a command that needs no directory, such as `date`, as it is, unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

Rule A goes in every skill and agent except `poc-sources`, which touches only user-level paths, and `research-protocol`, which is read inside agents that carry Rule A.

Why each part is there:

- `git -C "<target>"` so that `/spike-loop:poc-harden ~/repos/other` acts on the other repo, not on the session's repo.
- `cd "<root>" && <command>` for commands that use a relative path or run a script, because the shell does not reliably stay where a lone `cd` left it. **(observed)** In the main session a lone `cd` to a directory outside the session's directories returned `Shell cwd was reset to <start>` (R1, R3, R4), and R3, the one probe that made the `cd` and the following `pwd` as separate turns, then printed `<start>`. R1, R4, R2 and R2b put the `cd` and the `pwd` in the same assistant message, so they say nothing about persistence. The compound form ran in the root under a broad grant (R1, R15) and with the root added (R13). The Claude Code docs, as the reviewer read them, say a `cd` inside the project or an added directory does carry over in the main session, and no `cd` carries over inside a subagent **(docs, `/docs/en/tools-reference` and `/docs/en/sub-agents`)**, so the rule does not rely on persistence either way. The exception ("unless a step names another directory") covers the packager's clean-clone directory and the debugger's scratch copy under `$TMPDIR`. Whether a `cd` into that scratch directory is refused under narrow grants was not tested.
- `git -C "<root>" <subcommand>` for git, and no `cd` for a command that needs no directory (`date`, which `poc-log` and `poc-start` use), because a `cd` adds a refusal or a prompt that these commands do not need. The docs, as the reviewer read them, say a `cd` combined with `git` prompts whenever the `cd` changes directory **(docs, `/docs/en/permissions`, not tested)**.
- `<root>/<path>` in full for the file tools, because they resolve a relative path against the start directory **(observed, R16)**: `../../poc-spec/POC.md` read from `<root>/sub/deep` returned the root file. `poc-start` writes its files with the Write tool and Rule B's existence check reads files, so a relative `poc-spec/LOG.md` would act on `<start>/poc-spec/`.
- The refusal clause is there because the probes showed the repo root can be outside what the session may use **(observed)**: with narrow grants, `cd "<root>" && ./verify.sh` from a subdirectory was refused ("cd in `<root>` was blocked ... may only change directories to the allowed working directories for this session: `<start>`"), even with `cd` granted (R12). It ran when the root was added (`permissions.additionalDirectories`, R13) and under a broad `Bash` grant (R15). The refusal text of the `cd` does not name `/add-dir`. The Read refusal under `blockReadsOutsideWorkingDirectories` does ("Ask the user to add the directory with /add-dir", R8), so the advice is supported by that message and by the docs, but no probe used `/add-dir` itself and the quoted form `/add-dir "<root>"` was not tested. Each part of a compound command needs its own grant, and a compound-pattern grant does not work **(observed, R10, R11)**.
- A relative path argument is read from the session directory, only to find the root, because a root cannot be found from a path that is itself relative to the root. Open question 2 records this.

How the agent learns the root depends on how it is called:

- `poc-harden` calls agents through the Agent tool, so its brief names the repo root as an absolute path.
- The forked skills (`context: fork`: `poc-build`, `poc-debug`, `poc-package`, `poc-review`, `poc-verify`) pass their body to the agent as its task, and Rule A is in both the body and the agent file, so the agent resolves the root itself.
- A forked skill can have the root put into its body before the model sees it **(observed)**: `` !`git rev-parse --show-toplevel` `` gave the git root in both a main-session skill and a forked skill, and `${CLAUDE_PROJECT_DIR}` was the launch directory, not the git root. With `disableSkillShellExecution: true` the command text became `[shell command execution disabled by policy]`. So injection could name the root for forked skills, but it can be switched off by policy, and the agent resolves the root with git in any case, so this spec does not use it. Open question 3.
- A forked agent starts in the session's launch directory **(observed)**: its `pwd` was `<start>` and its `git rev-parse --show-toplevel` was the root. Task 0.2 results are in `docs/layout/findings.md`.
- An agent with `isolation: worktree` (`implementer`) gets a worktree, whose root is the worktree. Subagent worktrees branch from the repository's default branch unless `worktree.baseRef` is set to `"head"` **(docs, `/docs/en/sub-agents` and `/docs/en/worktrees`)**, so the implementer does not see uncommitted files and may not see the current branch's commits. It does not read `POC.md` or `LOG.md`, so this does not matter today. Finding F1 on `evals-spec` records that a forked `poc-build` was seen to run in the main tree, so what the implementer sees is not settled.

### Rule B: the docs folder

> **Docs folder.** Check these four paths, relative to the repo root: `poc-spec/POC.md`, `poc-spec/LOG.md`, `POC.md`, `LOG.md`. If files exist only under `poc-spec/`, the docs folder `<docs>` is `poc-spec`. If they exist only at the root, `<docs>` is `.` (an older PoC, use it as is). If files exist in both places, stop, say the PoC is half-migrated, name the files, and ask which to keep (an agent reports this and stops). If none exist, follow the command's own step. `<docs>/POC.md` means `poc-spec/POC.md` or `POC.md`, and likewise `<docs>/LOG.md`.

This closes three gaps. It checks fixed paths, not a search. It checks `LOG.md` as well as `POC.md`, so a partial move (only `POC.md` moved) is "half-migrated" and stops with a clear message instead of telling the user to run `poc-start`, which would then refuse. `<docs>` is `poc-spec` or `.`, so `<docs>/LOG.md` is never `/LOG.md`.

Rule B goes in `poc-log`, `poc-checkpoint`, `poc-harden`, `poc-package`, `poc-review`, `poc-research`, `poc-help` and `agents/packager.md`. `poc-start` does not carry it: it creates the files, and has its own check (below).

What each command does when no file exists:

| Command | Behaviour |
|---|---|
| `poc-log`, `poc-checkpoint`, `poc-harden` | Say to run `/spike-loop:poc-start` and stop (as today). |
| `poc-package`, `poc-review`, `poc-research`, `agents/packager.md` | Carry on without the documents. They already say "if present". |
| `poc-help` | Prints `No PoC found.` and ends with `Next: /spike-loop:poc-start`. |
| `poc-start` | Creates the files. |

Rules that follow:

- Skills write `<docs>/POC.md` and `<docs>/LOG.md`, and never a bare `POC.md` or `LOG.md` outside the cases named in "Tests".
- `SUMMARY.md` and `verify.sh` are always at the repo root, whatever `<docs>` is.
- Only `poc-start` creates `poc-spec/`. No other command creates or moves a docs folder.
- Existence is checked by file, not by parsing `CLAUDE.md`, so the rule works for agents and for PoCs wired by an older version.
- With Rule A, `./verify.sh`, `gitleaks dir .` and `typos` mean the repo root and are kept as written, because every shell command starts with `cd "<root>" &&`.

### Outside a git repository

Rule A's fallback is the directory the session was started in. Commands do not stop for lack of git.

| Command | Behaviour |
|---|---|
| `poc-start` | Offers `git init` (as today). The new repo is the root. |
| All other commands | Use the start directory as the root. `poc-help` with no files prints `No PoC found.` and `Next: /spike-loop:poc-start`. |

An earlier draft made `poc-verify` and `poc-review` stop outside git. That was a regression, because both work on any project, so it is dropped.

### `poc-start` and nested repos and worktrees

`poc-start` finds the root by Rule A and then checks three things before writing anything.

1. **At the root?** `git rev-parse --show-prefix` prints nothing when the session directory is the root. A path comparison against `--show-toplevel` is wrong, because `--show-toplevel` resolves symlinks (on macOS `/var` and `/tmp` are symlinks). **(observed here with git 2.55.0, and by the reviewer)** At the root through a symlink the prefix is empty, in a subdirectory it is `a/b/`. If it is not empty, `poc-start` names the root and asks whether to write there.
2. **Linked worktree?** The two paths printed by `git rev-parse --path-format=absolute --git-dir --git-common-dir` differ. `--path-format=absolute` is needed, because in a subdirectory of an ordinary repo `--git-dir` prints an absolute path and `--git-common-dir` prints `../../.git` **(observed, git 2.55.0)**. The flag first shipped in git 2.31.0 **(docs, git release notes, read by the reviewer)**. If they differ, `poc-start` says so, names the main checkout from the first `worktree` line of `git worktree list --porcelain` (if that entry is `bare`, it says there is no main checkout), and asks where `poc-spec/` should live, because a worktree holds only committed files and a gitignored `poc-spec/` would be missing from every other worktree.
3. **Nested in another repository?** `git -C "<root>/.." rev-parse --show-toplevel` succeeds. A nested repo started at its own root is not otherwise detectable **(observed, R3)**. `poc-start` names the outer repository and asks which one should hold `poc-spec/`.

**Never overwrite** keeps its present meaning: if any file it would write exists (`poc-spec/POC.md`, `poc-spec/LOG.md`, `verify.sh`, or a root `POC.md` or `LOG.md`), it stops and asks.

## Path audit

Every path phrase in `skills/` and `agents/` on `main`, plus the files changed on `help-and-next`, what it means today, and the change. This table is the checklist for the implementation, and the plan will turn each row into a task. Task 0.4 re-ran the audit on the rebased tree on 2026-11-26 (results in `docs/layout/findings.md`), because the first audit was made on `main` and missed `help-and-next`.

| File | Today | Change |
|---|---|---|
| `skills/poc-start/SKILL.md` line 3 (frontmatter description) | "in the current repo" | "at the repo root" (the description names the files in prose, `poc-spec/POC.md`) |
| `skills/poc-start/SKILL.md` step 2 | "the current git repo" | Rule A. Offers `git init` when there is none. The nested repo and worktree checks above. |
| `skills/poc-start/SKILL.md` step 5 | writes bare `POC.md`, `LOG.md`; `verify.sh` at the cwd | Writes `poc-spec/POC.md`, `poc-spec/LOG.md` (creates `poc-spec/`), `verify.sh` at the repo root. Never overwrite, as defined above. |
| `skills/poc-start/SKILL.md` step 6 | wiring text names bare `POC.md`, `LOG.md`, `./verify.sh` | New wiring text (below). |
| `skills/poc-start/SKILL.md` step 7 (line 19) | "Print `POC.md`" | "Print `poc-spec/POC.md`". |
| `skills/poc-start/SKILL.md` templates (lines 23, 50, 65 to 71) | section headings `### POC.md`, `### LOG.md`; stub comment (line 68) and stub `echo` (line 71) say "POC.md" | Headings unchanged (they name template blocks). Stub comment and `echo` say `poc-spec/POC.md`. |
| `skills/poc-log/SKILL.md` line 3 and step 1 | description names `LOG.md` in prose; "in the current repo root" | Rules A and B. Reads `<docs>/POC.md`, appends to `<docs>/LOG.md`. On `help-and-next` step 1 and step 5 also name the files and a `Next:` line, which get the same treatment. |
| `skills/poc-checkpoint/SKILL.md` line 3 and steps 1, 2, 3, 4, 6 | bare `POC.md`, `LOG.md` (step 2 names `LOG.md` too); `SUMMARY.md` "in the repo root" | Rules A and B. `SUMMARY.md` stays at the root. A pivot edits `<docs>/POC.md`. On `help-and-next` step 7's `Next:` line names `POC.md` and gets the same change. |
| `skills/poc-harden/SKILL.md` header and step 1 | "(default: current repo)"; bare `POC.md`, `LOG.md` | Default is the repo root. Rules A and B once in the gate step. |
| `skills/poc-harden/SKILL.md` lines 19, 21, 27, 29 (agent briefs) | "the repo path" (four places) | "the repo root as an absolute path". |
| `skills/poc-harden/SKILL.md` lean step 4 (line 21) | "Call the packager ... at most 15 tool calls." No instruction to show its output | Add "Show its report." so the packager warning reaches the user. The full path's step 5 already says it. |
| `skills/poc-harden/SKILL.md` lean steps 5, 6 and full steps 2, 6 | `./verify.sh`, `gitleaks dir .`, `typos` | Text unchanged. Correct from any directory because of Rule A. Full step 2 is included, which an earlier draft left out. |
| `skills/poc-package/SKILL.md` (forked, `agent: spike-loop:packager`) | "current working directory"; bare `POC.md`, `LOG.md` | Rules A and B in the skill body, which becomes the agent's task. Default is the repo root. |
| `skills/poc-review/SKILL.md` (forked) | "review the current working directory"; bare `POC.md` / `LOG.md` | Rules A and B. Default is the repo root. A missing docs folder is not an error. |
| `skills/poc-verify/SKILL.md` (forked) | line 3 "on the current project" (banned phrase, so the description changes to "on the project at the repo root"); "the current working directory"; finds `verify.sh` | Rule A. Default is the repo root, and `verify.sh` is at the repo root. |
| `skills/poc-research/SKILL.md` step 4 (on `help-and-next`) | "edit `POC.md`" in the `Next:` rule | Rules A and B. Earlier drafts wrongly said `poc-research` has no path phrases. |
| `skills/poc-help/SKILL.md` lines 17, 26 and 39 to 46 | table rows for `poc-start` (line 17) and `poc-log` (line 26) name bare files; the "Where you are" step (line 39) says "in the current directory" and prints "No PoC in this directory." | Rules A and B. Table names `poc-spec/POC.md`. Messages become `No PoC found.` Prints the legacy note (see "Migration"). |
| `skills/poc-build/SKILL.md`, `skills/poc-debug/SKILL.md` | no path phrases. `poc-build` takes a task whose files are named in the brief | Rule A added. `poc-build` tells the implementer that file paths in the brief are relative to the repo root. |
| `skills/research-protocol/SKILL.md` line 13 | "plus the current repo" | "plus the repo at its root". The `~/.config` sources path is outside the repo and unchanged. |
| `skills/poc-sources/` | user-level paths only | No change, and no Rule A. |
| `agents/packager.md` lines 13, 20, 23, 24 | `verify.sh` named as a script it may write; bare `POC.md`, `LOG.md`; `rsync ... ./ <dir>/` | Rules A and B (uses the folder named in its brief, else resolves it). `verify.sh` is at the repo root. The `./` in the copy step is the repo root by Rule A. Adds the warning below. |
| `agents/reviewer-lite.md` line 34 | runs `./verify.sh` once | Rule A added, so `./verify.sh` is the repo root's. |
| `agents/reviewer.md`, `agents/verifier.md`, `agents/implementer.md` | "the repo", "find them in the repo", "files named in the brief" | Rule A added. For `implementer`, brief files are relative to the root. |
| `agents/debugger.md` line 19 | scratch copy under `$TMPDIR` | Rule A added. The scratch path is outside the repo and named as the exception. |
| `agents/researcher.md` | reads "the repo" through `research-protocol` | Rule A added. |
| `README.md` | command table, "Three files carry the state" line, `Status: 0.1.1` | Names `poc-spec/POC.md`, `poc-spec/LOG.md`. SUMMARY stays at the root. Status line says 0.2.0. A note that Windows is untested. |
| `docs/workflow.md` | 11 mentions, bare names | Files table gets a Location column. Prose uses `poc-spec/`, with one note on the older root layout. |
| `CHANGELOG.md`, `.claude-plugin/plugin.json` | n/a | New entry, version 0.2.0. The entry says a user who has run `/spike-loop:poc-sources` must run `/spike-loop:poc-sources refresh` to get the new rules in their generated `researcher-internal` agent. |

`spike_sources.py` builds `~/.claude/agents/researcher-internal.md` from `agents/researcher.md`. A copy already generated has no Rule A until the user refreshes, which is why the changelog says so. The old copy keeps working as it does today.

## The `CLAUDE.md` wiring

`poc-start` step 6 currently appends a section telling a session to read `POC.md` and the last 40 lines of `LOG.md`. It becomes:

> Docs folder: `poc-spec/`. All paths are relative to the repo root. At session start read `poc-spec/POC.md` and the last 40 lines of `poc-spec/LOG.md`. Stay within `poc-spec/POC.md`. Park new ideas in `poc-spec/LOG.md` under Later. Never claim done without the output of `./verify.sh` or the manual check. Hand-offs, specs and plans for this PoC go under `poc-spec/`.

The main session reads this text directly, so it needs the literal path. A PoC wired by an older version keeps its old text, which is correct for its layout.

## Public repos and customer hand-offs

`poc-start` step 2 already tells the user not to put customer names or deal details in `POC.md` or `LOG.md` when the repo is or will be public. The notice becomes: keep customer names and deal details out of `poc-spec/`, or add `poc-spec/` to `.gitignore` before the first push. `poc-start` only tells the user. It does not edit `.gitignore`.

### Packager warning

The packager exists to prepare a hand-off, so it checks whether the diary would travel with the repo. After its step 5 it checks the docs folder files (`poc-spec/POC.md` and `poc-spec/LOG.md`, or `POC.md` and `LOG.md` for the older layout, by name, so the root layout never selects the whole repo):

- **Would travel** means the file is tracked, or untracked and not ignored. The packager runs these exact commands (the older-layout forms replace the paths with `POC.md LOG.md`): `git -C "<root>" ls-files poc-spec/POC.md poc-spec/LOG.md` and `git -C "<root>" ls-files --others --exclude-standard poc-spec/POC.md poc-spec/LOG.md`. They use `git -C`, not `cd`, because a `cd` combined with `git` prompts (docs, not tested). The second case matters because the clean-clone step copies untracked, unignored files and the next `git add -A` stages them.
- It reads the `Repo visibility:` and `Deal:` values from the `POC.md` header.

If any file would travel and either the visibility is `public` or the deal is not `none`, it adds one of these lines under "Open gaps" in its output (one place, not two):

New layout: `poc-spec/ would travel with this repo (<n> files tracked or not ignored) and this PoC is public or tied to a deal. LOG.md can hold customer names. Add poc-spec/ to .gitignore and run git rm -r --cached poc-spec before sharing. Anything already pushed stays in history.`

Older layout: `POC.md and LOG.md would travel with this repo and this PoC is public or tied to a deal. LOG.md can hold customer names. Add both to .gitignore and run git rm --cached POC.md LOG.md before sharing. Anything already pushed stays in history.`

Rules for the warning:

- It reports and never edits `.gitignore`, never runs `git rm`, and the check itself reads no file contents. The packager's step 5 still greps tracked files for obvious customer-name patterns as it does today, so the warning is an addition to that, not the only guard. Gitleaks finds secrets, not customer names, and the grep finds only obvious patterns.
- It does not fire when no file would travel, or when the repo is private and has no deal.
- It does not fire for `SUMMARY.md`, which is meant to be shared and has its own rule.
- A symlinked `poc-spec` is not handled. The check counts what `git ls-files` returns. Recorded as a known gap.
- The warning reaches the user through `poc-harden` because lean step 4 now says "Show its report". In the lean path it is not a BLOCKER or MAJOR, so it does not stop the flow.

## Migration

Existing PoCs need nothing. The fallback in Rule B reads the root files.

To move one by hand, in a POSIX shell at the repo root:

```
mkdir poc-spec && git mv POC.md LOG.md poc-spec/
```

If either file is untracked, `git mv` fails for it, so use `mv POC.md LOG.md poc-spec/` instead. Then change the paths in the wiring section of the PoC's `CLAUDE.md` to match the text above. That is one command and one edit.

`poc-help` prints one line when it finds the root layout: `Older layout: POC.md and LOG.md are at the repo root. It works as is. To move them: mkdir poc-spec && git mv POC.md LOG.md poc-spec/ (use mv if they are untracked), then update CLAUDE.md.` It does not move anything, because `poc-help` writes nothing.

No command migrates automatically. The half-migrated case (files in both places, including a partial move) stops, names the files and asks which to keep. An agent reports it and stops.

## Tests

The free tests run in `python3 -m unittest discover -s tests` and need no model. Wording the reviewer showed could pass a weaker test is closed here.

1. **Rule A present.** The Rule A text appears verbatim in every skill and agent except `poc-sources` and `research-protocol`. The file list is a constant in the test, so a new skill without it fails.
2. **Rule B present.** Same for Rule B, in the fixed list: `poc-log`, `poc-checkpoint`, `poc-harden`, `poc-package`, `poc-review`, `poc-research`, `poc-help`, `agents/packager.md`. `poc-start` is deliberately not in it.
3. **No hard-coded root path.** In every skill and agent file, including the frontmatter, each mention of `POC.md` or `LOG.md` (matched with no word character before the name, so `CHANGELOG.md` is not a hit: the 0.4 audit found `README.md` line 49 would otherwise match) must be `<docs>/POC.md`, `<docs>/LOG.md`, or inside one of these texts, each exempt only in the files that should carry it and only when verbatim: Rule B (the files that carry it), the legacy note (`poc-help`), the packager warning lines and the four `git -C "<root>" ls-files` commands (`agents/packager.md`, they name the document files on purpose), or a `poc-start` template heading. A `poc-spec/POC.md` or `poc-spec/LOG.md` mention is allowed only in `poc-start` and on table rows (lines that start with `|`) of `poc-help`, so a skill cannot carry Rule B and still hard-code the new path in a step. `README.md` and `docs/workflow.md` are covered by test 9. Anything else fails with file and line.
4. **No vague base.** These phrases do not appear anywhere in a skill or agent, frontmatter included, except inside Rule A: `current directory`, `current working directory`, `current repo`, `current git repo`, `current project`, `this directory`, `cwd`, `pwd`, `$PWD`.
5. **Root files stay at the root.** `SUMMARY.md` and `verify.sh` never appear with a `poc-spec/` or `<docs>/` prefix.
6. **Folder name.** In `skills/`, `agents/`, `README.md` and `docs/workflow.md`, any path-like token that ends in `spec/` or `specs/` must be exactly `poc-spec/`. `specs/`, `spec/` and `poc_spec/` fail. A drift to a name that does not end in `spec/` or `specs/` (for example `.poc/`) is not caught by a test, and test 7 still requires the exact `poc-spec/` paths in `poc-start`.
7. **poc-start.** The step that writes the files names `poc-spec/POC.md` and `poc-spec/LOG.md`, and the wiring text matches the block above.
8. **Packager warning.** `agents/packager.md` contains both warning lines verbatim, the four exact `git -C "<root>" ls-files` commands (new and older layout, tracked and untracked-not-ignored), and the limiting rules. A bare `git ls-files` is not enough, because the clean-clone step already uses one. The warning lines are exempt from test 3 by their text, which is checked here.
9. **Docs agree.** In `README.md` and `docs/workflow.md`, every mention of `POC.md` or `LOG.md` is prefixed `poc-spec/` or is on a line containing "older layout".
10. **Spec and tests agree.** The constants in the test file equal the text in this spec.

These are text checks. They show the skills say the right thing, not that a model follows them, which the evals and the manual checks in the plan cover.

## Evals

This work depends on the Phase 2 evals (see `docs/evals/plan.md` on `evals-spec`) and changes their fixtures. The fixtures must not be built twice, so the rule for the evals branch is:

- Keep `evals/fixtures/poc-log-basic` as the **old-layout** fixture. The existing case `poc-log/basic` allows only `Read`, `Edit`, `Write` and `Bash(date *)`, so under Rule A it cannot run `git rev-parse` or `cd`. The case's `allowed_tools` must gain the commands Rule A uses, and a pinned Bash grant treats a compound command (`cd "<root>" && ...`) as a different command, so the grant form is checked in task 0.2. Until that is done the case fails for a reason unrelated to the fallback. Only after it is fixed does the case test the fallback.
- The harness setting `blockReadsOutsideWorkingDirectories` (in `evals/harness/runner.py` on `evals-spec`) blocks a subdirectory case from reading the root, by absolute or relative path **(observed)**. With default settings the same reads succeed **(observed)**. A subdirectory case needs the root added as an additional directory, or that setting off.
- Add `poc-log-specs`, the same content under `poc-spec/`, and a case `poc-log/poc-spec-layout` whose graders read `poc-spec/LOG.md`.
- Phase 2 cases for `poc-start`, `poc-checkpoint` and `poc-harden` use the new layout by default. Each also has one old-layout case where the stage reads files.
- Cases to add: `poc-start` writes `poc-spec/POC.md` and `poc-spec/LOG.md` and nothing at the root except `verify.sh` and `CLAUDE.md`; `poc-start` stops without overwriting when any of its target files exists; `poc-log` stops with the half-migrated message when both layouts or a partial move are present; `poc-checkpoint stop` writes `SUMMARY.md` at the root under both layouts; `poc-log` run from a subdirectory writes to the root's docs folder and not to the subdirectory.
- Packager cases: docs folder tracked in a public repo warns; untracked and not ignored warns; ignored and untracked is quiet; a private repo with `Deal: none` is quiet.
- The subdirectory case needs a per-case working directory. The Phase 1 runner starts every case in the workspace root with a fixed `SETTINGS` object, so adding a working directory and per-case additional directories to the runner is part of this work **(observed from the runner's code, `run_once` and `SETTINGS`)**.
- Each part of a compound command needs its own grant **(observed, R10, R11)**, and `Bash(cd *)` did not cover a `cd` to a root outside the session's directories (R12). So a case that runs `cd "<root>" && ...` from a subdirectory needs the root as an additional directory (R13). Whether `Bash(cd *)` is needed at all for a `cd` inside the session's directories was not tested, and the docs, as the reviewer read them, classify it as read-only. Whether an interactive session prompts for each part is not measurable headless, and the changelog says so.

## Sequencing

1. `help-and-next` is merged (done 2026-11-26) and this branch is fast-forwarded to it, because `poc-help`, `poc-research`, `poc-log`, `poc-checkpoint` and the contract test file changed there and are part of the blast radius.
2. Implementation on this branch, with the tests above passing.
3. The evals branch rebases onto this branch (merged or not), then Phase 2 starts on the new fixtures.
4. The hand-off spec and the language-constitutions spec build on `poc-spec/`.

## Risks

| Risk | Effect | Mitigation |
|---|---|---|
| A skill still says a bare `POC.md` | Command fails or writes to the wrong place on a new PoC | Test 3 fails the build |
| A skill still says "current directory" | Behaves differently from a subdirectory | Test 4 fails the build |
| Rules A and B are copied in about a dozen places and drift | Inconsistent behaviour between commands | Tests 1, 2 and 10 compare the text verbatim |
| A model runs `cd` and the command as separate calls | `./verify.sh` not found | Rule A says to start every command with `cd "<root>" &&`. The subdirectory cases measure it |
| A session started below the repo root has permissions that exclude the root | `cd "<root>" &&` is refused | **(observed)** Rule A says to stop, explain and suggest `/add-dir`, not to work around it |
| Each part of a compound command prompts in an interactive session | More prompts than before the change | Not measurable headless. The changelog says to expect it, and `/add-dir` or a broad grant avoids it |
| A bare repository, or `GIT_DIR` or `GIT_WORK_TREE` in the environment | Wrong or failing root | Not supported (non-goal). `poc-start` stops in a bare repository |
| A forked agent starts somewhere other than the session directory | Wrong root | Not the case **(observed)**: it starts in the launch directory, and Rule A resolves the root with git |
| Skill-body injection is turned off by `disableSkillShellExecution` or unavailable | The root cannot be injected | **(observed)** the command text becomes a policy notice. The spec does not depend on injection |
| A user wires a PoC with the old text, then migrates only the files | The main session reads a missing path at start | Migration steps say to update the wiring text. `poc-help` names both steps |
| Half-migrated PoC, including a partial move | Command stops, user is confused | The stop message names the files and asks which to keep |
| `poc-spec/` is gitignored in a linked worktree setup | The folder is missing from other worktrees | `poc-start` says so and asks where it should live |
| `poc-spec/` is gitignored for a public repo | `CLAUDE.md` wiring points at files a clone does not have | Intended. Clones of a public repo do not need the diary. The README, which stays tracked, is the entry point |
| The packager warning fires too often and gets ignored | Real warnings missed | Four conditions limit it, and an eval case checks the quiet cases |
| A generated `researcher-internal` agent is stale | Old behaviour until refreshed | The changelog says to run `/spike-loop:poc-sources refresh`. It keeps working as before |
| The legacy fallback is never removed | Two layouts to test forever | Revisit at the next minor version, and drop the fallback only with a changelog note |

## Open questions

1. **Reading "warn".** I read "it should warn in order to stop collisions" as the packager warning in "Packager warning", which protects the diary from travelling. If you meant a warning when `poc-spec/` already holds other content, or a clash with another tool, say so. The name `poc-spec/` already avoids a clash with a plain `specs/` folder.
2. **Relative path arguments.** Taken as written below on 2026-11-26, when the maintainer said to go ahead with the recommendations. You asked for all paths to be relative to the repo root. A path argument cannot be, because the root is found from it. This spec reads a relative path argument from the directory the session was started in, only to find the root, and everything else is root-relative. Someone who types `../other-project` from a subdirectory of repo A gets repo B. Say if you want a different rule.
3. **Inject the root into forked skills?** The probes show a forked skill can carry `` !`git rev-parse --show-toplevel` `` so the agent is told the root, and that `${CLAUDE_PROJECT_DIR}` is the launch directory, not the git root. It would save the agent one git call, but it can be disabled by policy and Rule A still needs the git fallback. Not used in 0.2.0, on the same instruction. Say if you want it adopted later.
