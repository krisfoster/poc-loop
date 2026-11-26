# Changelog

## 0.2.1

- **`/spike-loop:poc-build` now runs the implementer in a worktree, as documented.** Until now the command was a `context: fork` skill, and in a headless test on Claude Code 2.1.325 that ran the implementer in your main working tree: the agent's `isolation: worktree` was not applied, so edits landed in your tree and no worktree was made. The command now calls the agent through the Agent tool, which did create a worktree in the same test. The Claude Code docs do not say whether a forked skill honours `isolation`, so this is based on that one observation, not on the docs. Not checked in an interactive session.
- **What changes for you.** The change is on the worktree's branch, not in your tree. The command reports the worktree path and branch, and its `Next:` line is `git merge <branch>` then `/spike-loop:poc-verify`. It never merges for you. The worktree branches from the repo's default branch, so uncommitted work and unmerged branches are not in it: commit first, or set `worktree.baseRef` to `"head"`.
- Three tests: `poc-build` is not a fork and calls the agent through the Agent tool, it says where the change is and does not merge, and no forked skill names an agent that sets `isolation`.

## 0.2.0

- **New layout.** `/spike-loop:poc-start` now writes `poc-spec/POC.md` and `poc-spec/LOG.md` (and `verify.sh` at the repo root), and appends a `CLAUDE.md` section that points at them. One folder holds the working documents, so it can be left out of a public repo or a customer hand-off. `SUMMARY.md`, `README.md`, `CLAUDE.md`, `verify.sh` and `.env.example` stay at the repo root.
- **Older PoCs keep working.** A PoC with `POC.md` and `LOG.md` at the repo root is read as it is. Nothing is moved for you. To move one: `mkdir poc-spec && git mv POC.md LOG.md poc-spec/` (use `mv` if they are untracked), then update the paths in the `CLAUDE.md` section. If both layouts are present, or only one file was moved, most commands stop, name the files and ask which to keep (`poc-research` answers anyway and says so in its Next line). `/spike-loop:poc-help` prints this as a one-line note when it finds the older layout.
- **Every path is relative to the repo root.** The skills and agents find the root with `git -C <path> rev-parse --show-toplevel`, run shell commands as `cd "<root>" && ...`, use `git -C` for git, and give file tools full paths, so a command is designed to behave the same from a subdirectory. It needs the session to be allowed to use the repo root. If it is refused (for example `cd ... was blocked`) the command says so and does not work around it: start the session at the repo root, or run `/add-dir` with the root.
- **Expect more approval prompts in a session started below the repo root.** Each part of a compound command needs its own approval, and a `cd` outside the session's directories can be refused. Headless runs showed this. Whether an interactive session prompts for each part was not measured.
- **`poc-start` checks before it writes.** It asks if the session directory is not the repo root, if this is a linked worktree (a gitignored `poc-spec/` would be missing from the other worktrees), or if the repo sits inside another repository. It stops in a bare repository. It never overwrites `poc-spec/POC.md`, `poc-spec/LOG.md`, `verify.sh` or an older root `POC.md` or `LOG.md`. The public-repo notice now names `poc-spec/` and does not edit `.gitignore`.
- **The packager warns when `poc-spec/` would travel.** If the docs folder is tracked, or untracked and not ignored, and the PoC is public or tied to a deal, the packager adds a line under Open gaps: `LOG.md` can hold customer names, add the folder to `.gitignore` and untrack it before sharing, anything already pushed stays in history. It reports only and never edits `.gitignore` or runs `git rm`. `/spike-loop:poc-harden` lean path now shows the packager's report, so the warning reaches you.
- **If you ran `/spike-loop:poc-sources`,** run `/spike-loop:poc-sources refresh` to regenerate your `researcher-internal` agent with the new rules. The old copy keeps working as before.
- Checked by hand: the real commands were run headless on 22 scratch repos (a new PoC, the older layout, both layouts, a partial move and none, from the repo root and from a subdirectory, in a bare repository, a nested repository and a linked worktree, and five packager warning cases) on Claude Code 2.1.325, one run each. All behaved as described above, after one fix: a `poc-log` run below the repo root was refused for a check that needed no `cd`. This is one run per case, not a measured pass rate. `poc-checkpoint`, `poc-harden`, `poc-review`, `poc-research`, `poc-build` and `poc-debug` were not run on the new layout, and a model-run eval suite is a follow-up. The packager's clean-clone test cannot run in a session whose permissions exclude a temp directory outside the repo: it says so and the README run steps are then checked in the working tree only.
- Twelve text tests check that every skill and agent carries the two rules word for word, that no skill hard-codes a root document path or a vague "current directory", and that the packager warning and the `poc-start` wording are present. Windows is untested: the shell snippets assume a POSIX shell.

## 0.1.2

- New `/spike-loop:poc-help`: prints the command table, explains one command (`/spike-loop:poc-help verify`), and reads `POC.md` and `LOG.md` to say where the PoC stands and what to run next. It writes nothing.
- Every command now ends with one line starting `Next:` that names the next command, chosen by the outcome: verify on a pass or fail, review with or without blocking findings, harden when blocked or complete, log by the entry's Decision, and so on. The forked commands (`poc-build`, `poc-verify`, `poc-debug`, `poc-review`, `poc-package`) add it in the skill, not in the agent, so the agents' output contracts used by `poc-harden` are unchanged.
- A test checks that every command has a `Next:` rule, that `poc-help` lists every command, and that the README lists them too.

## 0.1.1

- Classifier: `edit`, `append`, `insert`, `replace`, `save`, `push`, `submit`, `import`, `attach`, `tag`, `store`, `modify` and similar verbs now make a tool write-class, so compound names such as `search_and_replace` are no longer offered as read.
- `render-agent` refuses a base agent with no `tools:` line, `init-sources` and `render-agent` accept a bare relative `--out`, and `status` no longer reads stdin.
- The packager's clean-clone test copies the working tree, so the files it just wrote are part of the test.
- `POC.md` `Started:` now includes the time, and `poc-log` and `poc-checkpoint` measure wall-clock time against the timebox.
- Reworded the read-only and no-external-access claims, and documented the limits in `docs/updating-sources.md`.
- Install, update and uninstall steps in the README, a plugin icon, and manifest metadata.

## 0.1.0

Initial release.
