---
name: poc-build
description: Runs the implementer agent in an isolated git worktree on one bounded chunk of an approved plan. Use only when the user types /poc-build with the task and a one-sentence done condition.
disable-model-invocation: true
argument-hint: "<task> | done when <condition>"
---
Implement this chunk: "$ARGUMENTS".

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that needs the working directory (it uses a relative path or runs a script there) as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run any other command as it is (such as `date`, a script by its absolute path, or `chmod` or `tail` given a `<root>/<path>`), unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full, and use them to check, read and list files. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

File paths named in the task are relative to the repo root.

1. **Check the arguments.** They must hold a task and a one-sentence done condition. If either is missing, reply only with `NEEDS INPUT: give me the task and a one-sentence done condition`, then the `Next:` line below.
2. **Call the agent.** Find the repo root, then call the `spike-loop:implementer` agent once through the Agent tool (do not run it as a fork of this skill: a forked skill ran it in the main working tree, so the agent's `isolation: worktree` was not applied). The agent has no conversation history, so the brief holds the task, the done condition, the verification command if the user gave one, and the repo root as an absolute path. Tell it not to push or open a pull request.
3. **Report.** Show the agent's report as returned, then say where the change is: the worktree path and branch from the Agent tool result, or that no worktree was reported. The worktree branches from the repo's default branch, not from the current branch, so uncommitted work and unmerged branches are not in it. A user who needs them in it can commit first or set `worktree.baseRef` to `"head"`. The change stays in the worktree until the user brings it over. Do not merge, cherry-pick or copy it, and do not remove the worktree.

End with one line starting `Next:`: `git merge <branch>` (the branch you reported) and then `/spike-loop:poc-verify` to check the chunk, or after a `NEEDS INPUT` reply, `/spike-loop:poc-build <task> | done when <condition>` with the missing part.
