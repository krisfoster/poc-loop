---
name: poc-harden
description: Takes a PoC from "it works" to handoff: independent review, fixes by the user, then packaging with README, .env.example and a clean-clone check. Lean path for tier 1, full path for tier 2. Use when the user types /poc-harden after deciding to harden.
disable-model-invocation: true
model: sonnet
effort: medium
argument-hint: "[project path] [full]"
allowed-tools:
  - Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs *)
  - Bash(sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" *)
---
# poc-harden

Project: "$ARGUMENTS" (default: the repo root). Never use em dashes.

**Prerequisites.** Before anything else, run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" poc-harden git rsync gitleaks:optional typos:optional` as a command on its own, never joined to another with `;` or `&&`, and read its output. If the last line is `prereqs: missing ...`, print each `MISSING:` line as it is, change nothing, and end with `Next: install what is missing, then run /spike-loop:poc-harden again`. Print any `skipped:` line and leave out the step that needs that tool. If the check cannot run (refused, not found, no POSIX shell, or a `prereqs: usage error` line), say so in one line and continue: a command that needs a missing tool will fail with its own error. This check covers any agent this command starts: when you brief an agent, say "prerequisites checked".

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that needs the working directory (it uses a relative path or runs a script there) as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run any other command as it is (such as `date`, a script by its absolute path, or `chmod` or `tail` given a `<root>/<path>`), unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full, and use them to check, read and list files. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

**Docs folder.** Check these four paths, relative to the repo root, by reading each with the Read tool (it needs no `cd`, a missing file is just an error, and Glob can skip gitignored files, which `poc-spec/` often is): `poc-spec/POC.md`, `poc-spec/LOG.md`, `POC.md`, `LOG.md`. If files exist only under `poc-spec/`, the docs folder `<docs>` is `poc-spec`. If they exist only at the root, `<docs>` is `.` (an older PoC, use it as is). If files exist in both places, stop, say the PoC is half-migrated, name the files, and ask which to keep (an agent reports this and stops). If none exist, follow the command's own step. `<docs>/POC.md` means `poc-spec/POC.md` or `POC.md`, and likewise `<docs>/LOG.md`.

1. **Gate.** Resolve the docs folder by the docs-folder rule above, then read `<docs>/POC.md` and the last 15 lines of `<docs>/LOG.md`. If `<docs>/POC.md` or `<docs>/LOG.md` is missing, say to run `/spike-loop:poc-start` and stop, ending with `Next: /spike-loop:poc-start`. If the last Decision is not `harden`, ask whether to proceed anyway. Read the `Tier:` value in the `<docs>/POC.md` header line. Use the **lean path** for tier 1 and the **full path** for tier 2, if the tier is missing, or if the arguments contain `full`. Say which path you are using.

**Next line.** However this ends, the last line you print starts with `Next:`. Stopped on BLOCKER or MAJOR findings: resolve them, then `/spike-loop:poc-harden` again. Declined at the gate: `/spike-loop:poc-checkpoint` to record the decision. Half-migrated PoC: keep one layout, then `/spike-loop:poc-harden` again. Completed: `/spike-loop:poc-checkpoint harden` to write `SUMMARY.md`.

## Lean path (tier 1)
Do each step once, in order. Do not re-read files you already have and do not fix anything yourself. Measured once on 2026-11-25: the whole loop cost $1.38 with this path against $3.16 with the full one, with the same hidden-test score (see `docs/measurements.md`).
2. **Review.** Call the `spike-loop:reviewer-lite` agent once with the repo root as an absolute path and the success check from `<docs>/POC.md` (it has no history). Show its findings as returned.
3. **Stop for the user.** If it reports a BLOCKER or MAJOR, list them and wait. Do not package until the user says they are resolved or accepted.
4. **Package.** Call the `spike-loop:packager` agent once with the repo root as an absolute path and the docs folder, no staging or committing, and at most 15 tool calls. Show its report.
5. **Final gate.** Run `./verify.sh` (or note the manual check as NEEDS HUMAN) and `gitleaks dir . --no-banner --redact` and `typos` (skip a tool that is not installed and say so) once each, and show the last 15 lines of each.
6. **Record.** Append one entry to `<docs>/LOG.md` in its format (reviewed, packaged, what was left open), Decision `harden`. End with `Next: /spike-loop:poc-checkpoint harden` to write `SUMMARY.md`. Do not commit or push.

## Full path (tier 2, customer-facing, or `full`)
2. **Constitution audit.** Run `gitleaks dir . --no-banner --redact` and `typos` if installed, and look for a missing `.gitignore`, `.env.example` or a committed `.env`. Fix plain config gaps, and ask before anything else.
3. **Review.** Call the `spike-loop:reviewer` agent through the Agent tool with the repo root as an absolute path, the branch to diff, and the success check from `<docs>/POC.md`, because the agent has no conversation history. Show its findings as returned.
4. **Stop for the user.** If there are BLOCKER or MAJOR findings, list them and wait. Do not package until the user says the blockers are resolved or accepts them. Re-run the review after fixes if asked.
5. **Package.** Call the `spike-loop:packager` agent with the repo root as an absolute path and the docs folder, and tell it not to stage or commit. Show its report.
6. **Final gate.** Run `./verify.sh` (or note the manual check as NEEDS HUMAN) and the same scans once more. Show the actual output.
7. **Record.** Append a `/poc-log` style entry: reviewed, packaged, what was accepted. End with `Next: /spike-loop:poc-checkpoint harden` to write `SUMMARY.md`. Do not commit or push.
