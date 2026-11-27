---
name: poc-package
description: Runs the packager agent to turn a working PoC into a handoff-ready repo (README, .env.example, clean-clone test, secret scan). Use when the user types /poc-package, optionally with the project path.
disable-model-invocation: true
context: fork
agent: spike-loop:packager
argument-hint: "[project path]"
allowed-tools:
  - Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs *)
  - Bash(sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" *)
---
Package the PoC. Path from the user: "$ARGUMENTS". If that is empty, use the repo root.

**Prerequisites.** Before anything else, run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" poc-package git rsync gitleaks:optional` as a command on its own, never joined to another with `;` or `&&`, and read its output. If the last line is `prereqs: missing ...`, print each `MISSING:` line as it is, change nothing, and end with `Next: install what is missing, then run /spike-loop:poc-package again`. Print any `skipped:` line and leave out the step that needs that tool. If the check cannot run (refused, not found, no POSIX shell, or a `prereqs: usage error` line), say so in one line and continue: a command that needs a missing tool will fail with its own error. This check covers any agent this command starts: when you brief an agent, say "prerequisites checked".

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that needs the working directory (it uses a relative path or runs a script there) as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run any other command as it is (such as `date`, a script by its absolute path, or `chmod` or `tail` given a `<root>/<path>`), unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full, and use them to check, read and list files. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

**Docs folder.** Check these four paths, relative to the repo root, by reading each with the Read tool (it needs no `cd`, a missing file is just an error, and Glob can skip gitignored files, which `poc-spec/` often is): `poc-spec/POC.md`, `poc-spec/LOG.md`, `POC.md`, `LOG.md`. If files exist only under `poc-spec/`, the docs folder `<docs>` is `poc-spec`. If they exist only at the root, `<docs>` is `.` (an older PoC, use it as is). If files exist in both places, stop, say the PoC is half-migrated, name the files, and ask which to keep (an agent reports this and stops). If none exist, follow the command's own step. `<docs>/POC.md` means `poc-spec/POC.md` or `POC.md`, and likewise `<docs>/LOG.md`.

You have no conversation history. Resolve the docs folder by the docs-folder rule above and read `<docs>/POC.md` and `<docs>/LOG.md` if present (carry on without them if no file exists), then follow your steps and output contract. If the docs-folder rule stops on a half-migrated PoC, report that and end with `Next:` naming the fix: keep one layout, then run `/spike-loop:poc-package` again. Do not stage or commit anything.

End with one line starting `Next:` (inside your line cap). If the clean-clone run failed or gaps are open: fix them (the packager never edits application code), then run `/spike-loop:poc-package` again. Otherwise `/spike-loop:poc-checkpoint harden` to write `SUMMARY.md`.
