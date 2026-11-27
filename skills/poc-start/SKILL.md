---
name: poc-start
description: Starts a PoC the Spike Loop way. Interviews for the question, riskiest assumptions, success check and timebox, then writes poc-spec/POC.md, poc-spec/LOG.md and a verify.sh stub at the repo root. Use when the user types /poc-start, optionally with the answers already given.
disable-model-invocation: true
model: opus
effort: medium
argument-hint: "[title and any answers you already know]"
---
# poc-start

Arguments: "$ARGUMENTS". Treat anything useful there as answers already given and do not ask for it again. Never use em dashes in anything you write. The arguments are the interview answers, never a project path: the root is always found from the directory the session was started in.

**Paths.** Every path in this command is relative to the repo root. Find the root with `git -C "<target>" rev-parse --show-toplevel`, where `<target>` is the project path given in the arguments if this command takes one and one is given, otherwise the directory the session was started in (an agent uses the repo root named in its brief, and outside a git repository the root is `<target>`). The shell can be reset to the start directory between calls, and is in an agent, so run a command that needs the working directory (it uses a relative path or runs a script there) as `cd "<root>" && <command>`, run git as `git -C "<root>" <subcommand>`, and run any other command as it is (such as `date`, a script by its absolute path, or `chmod` or `tail` given a `<root>/<path>`), unless a step names another directory. File tools (Read, Write, Edit, Glob, Grep) resolve a relative path against the start directory, so give them `<root>/<path>` in full, and use them to check, read and list files. If a shell command or tool is refused (for example `cd ... was blocked`) because the repo root is outside the directories this session may use, do not work around it: say so (an agent reports it and stops), and tell the user to start the session at the repo root or run `/add-dir "<root>"`. A relative project path in the arguments is relative to the directory the session was started in, only to find the root. Everything else is relative to the root.

1. **Tier.** If the work can be described in one sentence and needs no files (tier 0), say so, offer to just do it, and stop, ending with `Next: no PoC files are needed, just ask for the change`. Otherwise it is tier 1 (bounded, under a few hours) or tier 2 (multi-day or customer-facing). Pick from the answers or ask once.
2. **Where.** First run `git -C "<target>" rev-parse --is-bare-repository`: if it prints `true`, stop and say bare repositories are not supported. Then find the repo root by the paths rule above. If there is no git repository, offer to run `git init`, and the new repository is the root. Before writing anything, check three things. (a) At the root? Run `git -C "<target>" rev-parse --show-prefix` (the target, not the root: run against the root it always prints nothing). It prints nothing when the session directory is the root. If it prints a path, name the root and ask whether to write there. (b) Linked worktree? If the two paths printed by `git -C "<root>" rev-parse --path-format=absolute --git-dir --git-common-dir` differ, say so, name the main checkout from the first `worktree` line of `git -C "<root>" worktree list --porcelain` (if that entry says `bare`, say there is no main checkout), and ask where `poc-spec/` should live, because a worktree holds only committed files and a gitignored `poc-spec/` would be missing from the other worktrees. (c) Nested in another repository? If `git -C "<root>/.." rev-parse --show-toplevel` succeeds, name that outer repository and ask which one should hold `poc-spec/`. If any question in this step needs an answer and you cannot ask (a non-interactive run), including the `git init` offer and the public-repo question below, stop without writing anything and without running `git init`, say what you found, and end with a `Next:` line telling the user what to answer or fix. Then ask whether the repo is or will be public, and if so tell the user to keep customer names and deal details out of `poc-spec/`, or to add `poc-spec/` to `.gitignore` before the first push. Do not edit `.gitignore`.
3. **Deal link.** Ask if the PoC is tied to a deal. If yes, take the deal name and any success criteria the user pastes. Do not fetch anything from a CRM or other external system yet, just record what the user gives you.
4. **Interview**, one short round, only for what is missing: the question; the two or three riskiest assumptions and why they might be wrong; the success check (one command if possible, otherwise exact manual steps); in and out of scope; the timebox for the first pass.
5. **Write** (use `date '+%Y-%m-%d %H:%M'` for `Started:`). First check that nothing will be overwritten, using the file tools: If `poc-spec/POC.md`, `poc-spec/LOG.md` or `verify.sh` already exists, or a `POC.md` or `LOG.md` sits at the repo root (an older PoC), stop and ask. Only then write the three files with the Write tool, giving it `<root>/poc-spec/POC.md`, `<root>/poc-spec/LOG.md` and `<root>/verify.sh` in full (the tool creates `poc-spec/`), using the templates at the bottom of this skill, verbatim except for filling placeholders. Keep every heading and the header line exactly as given, one page maximum for `poc-spec/POC.md`. `poc-spec/LOG.md`: keep the header and entry format, then append a first entry "PoC started" in that format. `verify.sh`: if the success check is scriptable, replace everything after the `set -euo pipefail` line with the check, otherwise leave the stub, then `chmod +x "<root>/verify.sh"`. Afterwards confirm `verify.sh` is executable and that `poc-spec/POC.md` has no left-over `<...>` placeholders.
6. **Wire in.** Append this section to the repo's `CLAUDE.md` at the repo root (create it if needed), exactly as written:

> Docs folder: `poc-spec/`. All paths are relative to the repo root. At session start read `poc-spec/POC.md` and the last 40 lines of `poc-spec/LOG.md`. Stay within `poc-spec/POC.md`. Park new ideas in `poc-spec/LOG.md` under Later. Never claim done without the output of `./verify.sh` or the manual check. Hand-offs, specs and plans for this PoC go under `poc-spec/`.
7. **Finish.** Print `poc-spec/POC.md`, tell the user to read and correct it because that review matters most, then end with one line starting `Next:` that names the next command: `/spike-loop:poc-research <question>` if the question depends on facts that cannot be confirmed from the code, otherwise start building and run `/spike-loop:poc-verify` when there is something to check. Do not commit.

## Templates

### POC.md
````markdown
# POC: <short title>

Started: <YYYY-MM-DD HH:MM> | Timebox (first pass): <N hours> | Tier: <1 or 2> | Deal: <name or none> | Repo visibility: <private or public>

## Question
<One or two sentences. What are we trying to find out or prove?>

## Success check
<How we will know it worked. Observable, ideally one command. If it cannot be scripted, write the manual check in the last section.>

## Assumptions and risks (riskiest first)
1. <assumption, why it could be wrong>
2.
3.

## In scope
- <>

## Out of scope
- <>

## Manual check (only if verify.sh cannot do it)
<Exact steps and the expected observation, or "none".>
````

### LOG.md
````markdown
# Log

Append only. Newest entry last. Format per entry:

## <YYYY-MM-DD HH:MM> <one-line title>
- Tried: <>
- Learned: <>
- Dead ends: <>
- Decision: <iterate | pivot | harden | stop | pause | none yet>
- Next question: <>
- Later: <ideas parked, out of scope for now>
````

### verify.sh
````bash
#!/usr/bin/env bash
# Builds and runs the PoC and exits non-zero if the success check in poc-spec/POC.md fails.
# Replace the body. An unedited stub fails on purpose so it cannot pass by accident.
set -euo pipefail
echo "verify.sh is still a stub: write the success check from poc-spec/POC.md" >&2
exit 1
````
