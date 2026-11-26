---
name: poc-build
description: Runs the implementer agent in an isolated worktree on one bounded chunk of an approved plan. Use only when the user types /poc-build with the task and a one-sentence done condition.
disable-model-invocation: true
context: fork
agent: spike-loop:implementer
argument-hint: "<task> | done when <condition>"
---
Implement this chunk: "$ARGUMENTS".

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that uses a relative path or runs a script as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run a command that needs no directory, such as `date` or a script under `${CLAUDE_SKILL_DIR}`, as it is, unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

File paths named in the task are relative to the repo root.

You have no conversation history. The text above must contain the task and a done condition. If either is missing, reply only with `NEEDS INPUT: give me the task and a one-sentence done condition`. Otherwise stay inside the stated scope, run the verification command if one is given, and report using your output contract. Do not push or open a pull request.

End with one line starting `Next:` (inside your line cap): `/spike-loop:poc-verify` to check the chunk, or after a `NEEDS INPUT` reply, `/spike-loop:poc-build <task> | done when <condition>` with the missing part.
