---
name: poc-start
description: Starts a PoC the Spike Loop way. Interviews for the question, riskiest assumptions, success check and timebox, then writes POC.md, LOG.md and a verify.sh stub in the current repo. Use when the user types /poc-start, optionally with the answers already given.
disable-model-invocation: true
model: opus
effort: medium
argument-hint: "[title and any answers you already know]"
---
# poc-start

Arguments: "$ARGUMENTS". Treat anything useful there as answers already given and do not ask for it again. Never use em dashes in anything you write.

1. **Tier.** If the work can be described in one sentence and needs no files (tier 0), say so, offer to just do it, and stop. Otherwise it is tier 1 (bounded, under a few hours) or tier 2 (multi-day or customer-facing). Pick from the answers or ask once.
2. **Where.** Use the current git repo. If there is none, offer to run `git init`. Ask whether the repo is or will be public, and if so tell the user not to put customer names or deal details in `POC.md` or `LOG.md`.
3. **Deal link.** Ask if the PoC is tied to a deal. If yes, take the deal name and any success criteria the user pastes. Do not fetch anything from a CRM or other external system yet, just record what the user gives you.
4. **Interview**, one short round, only for what is missing: the question; the two or three riskiest assumptions and why they might be wrong; the success check (one command if possible, otherwise exact manual steps); in and out of scope; the timebox for the first pass.
5. **Write** (use `date '+%Y-%m-%d %H:%M'` for `Started:`) the three files with the Write tool using the templates at the bottom of this skill, verbatim except for filling placeholders. Keep every heading and the header line exactly as given, one page maximum for `POC.md`. Never overwrite an existing file: if one exists, stop and ask. `LOG.md`: keep the header and entry format, then append a first entry "PoC started" in that format. `verify.sh`: if the success check is scriptable, replace everything after the `set -euo pipefail` line with the check, otherwise leave the stub, then `chmod +x verify.sh`. Afterwards confirm `verify.sh` is executable and that `POC.md` has no left-over `<...>` placeholders.
6. **Wire in.** Append to the repo's `CLAUDE.md` (create if needed) one short section: read `POC.md` and the last 40 lines of `LOG.md` at session start, stay within `POC.md`, park new ideas in `LOG.md` under Later, and never claim done without the output of `./verify.sh` or the manual check.
7. **Finish.** Print `POC.md`, tell the user to read and correct it because that review matters most, and name the next command (research with `/poc-research <question>`, or start building). Do not commit.

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
- Decision: <iterate | pivot | harden | stop | none yet>
- Next question: <>
- Later: <ideas parked, out of scope for now>
````

### verify.sh
````bash
#!/usr/bin/env bash
# Builds and runs the PoC and exits non-zero if the success check in POC.md fails.
# Replace the body. An unedited stub fails on purpose so it cannot pass by accident.
set -euo pipefail
echo "verify.sh is still a stub: write the success check from POC.md" >&2
exit 1
````
