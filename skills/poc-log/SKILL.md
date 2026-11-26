---
name: poc-log
description: Appends a short dated entry to the PoC's log and shows time used against the timebox. Use when the user types /poc-log, optionally with the entry text, at the end of a working session or after learning something.
disable-model-invocation: true
model: haiku
effort: low
argument-hint: "[what you tried and learned]"
---
# poc-log

Entry text from the user: "$ARGUMENTS". Never use em dashes.

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that uses a relative path or runs a script as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run a command that needs no directory, such as `date` or a script under `${CLAUDE_SKILL_DIR}`, as it is, unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

**Docs folder.** Check these four paths, relative to the repo root, with the file tools (Glob or Read, which need no `cd`): `poc-spec/POC.md`, `poc-spec/LOG.md`, `POC.md`, `LOG.md`. If files exist only under `poc-spec/`, the docs folder `<docs>` is `poc-spec`. If they exist only at the root, `<docs>` is `.` (an older PoC, use it as is). If files exist in both places, stop, say the PoC is half-migrated, name the files, and ask which to keep (an agent reports this and stops). If none exist, follow the command's own step. `<docs>/POC.md` means `poc-spec/POC.md` or `POC.md`, and likewise `<docs>/LOG.md`.

1. Resolve the docs folder by the docs-folder rule above. If `<docs>/POC.md` or `<docs>/LOG.md` is missing, say to run `/poc-start` and stop, ending with `Next: /spike-loop:poc-start`. If the rule stops on a half-migrated PoC, end with `Next:` naming the fix: keep one layout, then run `/spike-loop:poc-log` again.
2. Build the entry in the format at the top of `<docs>/LOG.md` (Tried, Learned, Dead ends, Decision, Next question, Later). Use the user's text. If it is empty, draft it from this conversation in 2 to 5 lines. Use `none yet` for Decision unless one was stated. Use `date '+%Y-%m-%d %H:%M'` for the timestamp.
3. Show the entry, then append it to the end of `<docs>/LOG.md`. Never edit or reorder earlier entries.
4. Time check: read `Started:` and `Timebox` from `<docs>/POC.md`, compute elapsed wall-clock time since Started (if Started has no time, use the timestamp of the first `<docs>/LOG.md` entry), and count the log entries. Print one line: `Elapsed <x> of <timebox>, <n> entries.` If elapsed exceeds the timebox, say so plainly and suggest deciding: iterate, pivot, harden or stop. It is a soft limit, so do not nag.
5. End with one line starting `Next:`, chosen by the entry's Decision. `none yet`: keep building and run `/spike-loop:poc-verify` when there is something to check (if over the timebox, decide now with `/spike-loop:poc-checkpoint <iterate | pivot | harden | stop>`). `iterate`: `/clear` and start a fresh session on the next question. `pivot`: edit the assumptions in `<docs>/POC.md`, then `/clear`. `harden`: `/spike-loop:poc-harden`. `stop`: `/spike-loop:poc-checkpoint stop`.
6. Do not commit.
