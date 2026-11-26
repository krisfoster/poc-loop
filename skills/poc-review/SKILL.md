---
name: poc-review
description: Runs the reviewer agent for an independent review of a diff or a PoC before handoff. Use when the user types /poc-review, optionally with a path, branch or focus.
disable-model-invocation: true
context: fork
agent: spike-loop:reviewer
argument-hint: "[path, branch or focus]"
---
Review the work. Scope from the user: "$ARGUMENTS".

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that uses a relative path or runs a script as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run a command that needs no directory, such as `date` or a script under `${CLAUDE_SKILL_DIR}`, as it is, unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

**Docs folder.** Check these four paths, relative to the repo root: `poc-spec/POC.md`, `poc-spec/LOG.md`, `POC.md`, `LOG.md`. If files exist only under `poc-spec/`, the docs folder `<docs>` is `poc-spec`. If they exist only at the root, `<docs>` is `.` (an older PoC, use it as is). If files exist in both places, stop, say the PoC is half-migrated, name the files, and ask which to keep (an agent reports this and stops). If none exist, follow the command's own step. `<docs>/POC.md` means `poc-spec/POC.md` or `POC.md`, and likewise `<docs>/LOG.md`.

If that is empty, review the repo at the repo root: `git diff` against the default branch (use `git merge-base`), plus any untracked files. If it names a branch, diff that branch against the default branch. You have no conversation history, so work only from the repo and `<docs>/POC.md` / `<docs>/LOG.md` if present (resolve the docs folder by the docs-folder rule above, and carry on without them if no file exists). If the docs-folder rule stops on a half-migrated PoC, report that and end with `Next:` naming the fix: keep one layout, then run `/spike-loop:poc-review` again. Apply your PoC rubric and output contract. Do not edit anything.

End with one line starting `Next:` (inside your line cap). With any BLOCKER or MAJOR finding: fix them, then run `/spike-loop:poc-review` again. With none: `/spike-loop:poc-harden` to package and run the final gate (add `full` for a tier 2 PoC), or `/spike-loop:poc-package` if you only need packaging.
