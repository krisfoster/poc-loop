---
name: poc-verify
description: Runs the verifier agent on the project at the repo root in its own context and returns pass or fail with only the relevant errors. Use when the user types /poc-verify, optionally with a path or a focus such as "just the api tests".
disable-model-invocation: true
context: fork
agent: spike-loop:verifier
argument-hint: "[path or focus]"
allowed-tools:
  - Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs *)
  - Bash(sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" *)
---
Verify the project. Target and focus from the user: "$ARGUMENTS". A path in the arguments is a project path only if it is a directory; a file path or a focus is not, and the root is then found from the directory the session was started in. If that is empty, use the repo root and run the project's own check.

**Prerequisites.** Before anything else, run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" poc-verify git` as a command on its own, never joined to another with `;` or `&&`, and read its output. If the last line is `prereqs: missing ...`, print each `MISSING:` line as it is, change nothing, and end with `Next: install what is missing, then run /spike-loop:poc-verify again`. Print any `skipped:` line and leave out the step that needs that tool. If the check cannot run (refused, not found, or no POSIX shell), say so in one line and continue: a command that needs a missing tool will fail with its own error. This check covers any agent this command starts: when you brief an agent, say "prerequisites checked".

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that needs the working directory (it uses a relative path or runs a script there) as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run any other command as it is (such as `date`, a script by its absolute path, or `chmod` or `tail` given a `<root>/<path>`), unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full, and use them to check, read and list files. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

Find the project's own check first (`verify.sh` at the repo root, README run steps, `Makefile`, `package.json` scripts, `compose.yaml`). Report using your output contract. Do not fix anything.

End with one line starting `Next:` (inside your line cap), chosen by your verdict. PASS: `/spike-loop:poc-log` to record it. FAIL: fix it and run `/spike-loop:poc-verify` again, and after two failed fix attempts run `/spike-loop:poc-debug <failing command, error, what was tried>`. PARTIAL: run the missing parts yourself, then `/spike-loop:poc-verify`. NEEDS HUMAN: do the manual step, then `/spike-loop:poc-log`.
