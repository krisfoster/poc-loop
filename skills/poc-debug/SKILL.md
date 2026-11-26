---
name: poc-debug
description: Runs the debugger agent to find the root cause of a failure that survived a fix attempt. Use when the user types /poc-debug followed by the failing command and what was already tried.
disable-model-invocation: true
context: fork
agent: spike-loop:debugger
argument-hint: "<failing command, symptom, what you tried>"
---
Diagnose this failure: "$ARGUMENTS".

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the path given in the arguments if there is one, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that uses a relative path or runs a script as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run a command that needs no directory, such as `date`, as it is, unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

You have no conversation history. If the text above is empty or names no command or symptom, reply only with `NEEDS INPUT: give me the failing command, the error, and what has been tried`. Otherwise reproduce first, then follow your method and output contract. Do not edit tracked files.

End with one line starting `Next:` (inside your line cap): apply the proposed fix in the main session and run `/spike-loop:poc-verify`, or if you could not reproduce the failure, run `/spike-loop:poc-debug` again with the exact command and environment. After a `NEEDS INPUT` reply, run `/spike-loop:poc-debug <failing command, error, what was tried>`.
