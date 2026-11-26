---
name: poc-checkpoint
description: End-of-session summary for a PoC: what was established, what is open, and the next question. On a stop or harden decision, writes a short SUMMARY.md in the repo. Use when the user types /poc-checkpoint.
disable-model-invocation: true
model: sonnet
effort: low
argument-hint: "[iterate | pivot | harden | stop]"
---
# poc-checkpoint

Outcome from the user: "$ARGUMENTS". Never use em dashes.

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that needs the working directory (it uses a relative path or runs a script there) as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run any other command as it is (such as `date`, a script by its absolute path, or `chmod` or `tail` given a `<root>/<path>`), unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full, and use them to check, read and list files. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

**Docs folder.** Check these four paths, relative to the repo root, by reading each with the Read tool (it needs no `cd`, a missing file is just an error, and Glob can skip gitignored files, which `poc-spec/` often is): `poc-spec/POC.md`, `poc-spec/LOG.md`, `POC.md`, `LOG.md`. If files exist only under `poc-spec/`, the docs folder `<docs>` is `poc-spec`. If they exist only at the root, `<docs>` is `.` (an older PoC, use it as is). If files exist in both places, stop, say the PoC is half-migrated, name the files, and ask which to keep (an agent reports this and stops). If none exist, follow the command's own step. `<docs>/POC.md` means `poc-spec/POC.md` or `POC.md`, and likewise `<docs>/LOG.md`.

1. Resolve the docs folder by the docs-folder rule above, then read `<docs>/POC.md` and the last 60 lines of `<docs>/LOG.md`. If `<docs>/POC.md` or `<docs>/LOG.md` is missing, say to run `/spike-loop:poc-start` and stop, ending with `Next: /spike-loop:poc-start`. If the rule stops on a half-migrated PoC, end with `Next:` naming the fix: keep one layout, then run `/spike-loop:poc-checkpoint` again. If the last log entry is older than this session's work, run the `/poc-log` steps first (draft, show, append).
2. Print a summary of at most 12 lines: the question; what is now established, with the evidence (command and result), not claims; assumptions still unproven; open question for the next session; elapsed wall-clock time against timebox (if `Started:` has no time, measure from the first `<docs>/LOG.md` entry).
3. Outcome: if "$ARGUMENTS" is empty, recommend one of iterate, pivot, harden or stop with a one-line reason, and ask the user to confirm. Record the confirmed outcome in `<docs>/LOG.md` as a new entry whose Decision line names it.
4. Iterate or pivot: end with the fresh-session instruction (`/clear`, then say what to start with). Pivot also means edit `<docs>/POC.md` assumptions after the user agrees.
5. Harden: tell the user `/spike-loop:poc-harden` is next.
6. Stop or harden: write `SUMMARY.md` in the repo root, at most 25 lines: title, the question, the answer, key evidence (the command and its result), what to do differently, and what is still unproven. Everything stays in the repo. Never write to any external system (wiki, chat, CRM). No credentials, and no customer names if the repo is public. If `SUMMARY.md` exists, update it in place and say so.
7. End with one line starting `Next:`. `iterate`: `/clear`, then what to start with. `pivot`: edit the assumptions in `<docs>/POC.md`, then `/clear`. `harden`: `/spike-loop:poc-harden`. `stop`: nothing further, the PoC is closed and `SUMMARY.md` is written. If the outcome was not confirmed: `/spike-loop:poc-checkpoint <recommended outcome>` to confirm it.
8. Do not commit.
