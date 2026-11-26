---
name: poc-harden
description: Takes a PoC from "it works" to handoff: independent review, fixes by the user, then packaging with README, .env.example and a clean-clone check. Lean path for tier 1, full path for tier 2. Use when the user types /poc-harden after deciding to harden.
disable-model-invocation: true
model: sonnet
effort: medium
argument-hint: "[project path] [full]"
---
# poc-harden

Project: "$ARGUMENTS" (default: current repo). Never use em dashes.

1. **Gate.** Read `POC.md` and the last 15 lines of `LOG.md`. If the last Decision is not `harden`, ask whether to proceed anyway. Read the `Tier:` value in the `POC.md` header line. Use the **lean path** for tier 1 and the **full path** for tier 2, if the tier is missing, or if the arguments contain `full`. Say which path you are using.

**Next line.** However this ends, the last line you print starts with `Next:`. Stopped on BLOCKER or MAJOR findings: resolve them, then `/spike-loop:poc-harden` again. Declined at the gate: `/spike-loop:poc-checkpoint` to record the decision. Completed: `/spike-loop:poc-checkpoint harden` to write `SUMMARY.md`.

## Lean path (tier 1)
Do each step once, in order. Do not re-read files you already have and do not fix anything yourself. Measured once on 2026-11-25: the whole loop cost $1.38 with this path against $3.16 with the full one, with the same hidden-test score (see `docs/measurements.md`).
2. **Review.** Call the `spike-loop:reviewer-lite` agent once with the repo path and the success check from `POC.md` (it has no history). Show its findings as returned.
3. **Stop for the user.** If it reports a BLOCKER or MAJOR, list them and wait. Do not package until the user says they are resolved or accepted.
4. **Package.** Call the `spike-loop:packager` agent once with the repo path, no staging or committing, and at most 15 tool calls.
5. **Final gate.** Run `./verify.sh` (or note the manual check as NEEDS HUMAN) and `gitleaks dir . --no-banner --redact` and `typos` (skip a tool that is not installed and say so) once each, and show the last 15 lines of each.
6. **Record.** Append one entry to `LOG.md` in its format (reviewed, packaged, what was left open), Decision `harden`. End with `Next: /spike-loop:poc-checkpoint harden` to write `SUMMARY.md`. Do not commit or push.

## Full path (tier 2, customer-facing, or `full`)
2. **Constitution audit.** Run `gitleaks dir . --no-banner --redact` and `typos` if installed, and look for a missing `.gitignore`, `.env.example` or a committed `.env`. Fix plain config gaps, and ask before anything else.
3. **Review.** Call the `spike-loop:reviewer` agent through the Agent tool with the repo path, the branch to diff, and the success check from `POC.md`, because the agent has no conversation history. Show its findings as returned.
4. **Stop for the user.** If there are BLOCKER or MAJOR findings, list them and wait. Do not package until the user says the blockers are resolved or accepts them. Re-run the review after fixes if asked.
5. **Package.** Call the `spike-loop:packager` agent with the repo path and tell it not to stage or commit. Show its report.
6. **Final gate.** Run `./verify.sh` (or note the manual check as NEEDS HUMAN) and the same scans once more. Show the actual output.
7. **Record.** Append a `/poc-log` style entry: reviewed, packaged, what was accepted. End with `Next: /spike-loop:poc-checkpoint harden` to write `SUMMARY.md`. Do not commit or push.
