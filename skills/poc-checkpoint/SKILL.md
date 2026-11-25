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

1. Read `POC.md` and the last 60 lines of `LOG.md`. If missing, say to run `/poc-start` and stop. If the last log entry is older than this session's work, run the `/poc-log` steps first (draft, show, append).
2. Print a summary of at most 12 lines: the question; what is now established, with the evidence (command and result), not claims; assumptions still unproven; open question for the next session; elapsed against timebox.
3. Outcome: if "$ARGUMENTS" is empty, recommend one of iterate, pivot, harden or stop with a one-line reason, and ask the user to confirm. Record the confirmed outcome in `LOG.md` as a new entry whose Decision line names it.
4. Iterate or pivot: end with the fresh-session instruction (`/clear`, then say what to start with). Pivot also means edit `POC.md` assumptions after the user agrees.
5. Harden: tell the user `/poc-harden` is next.
6. Stop or harden: write `SUMMARY.md` in the repo root, at most 25 lines: title, the question, the answer, key evidence (the command and its result), what to do differently, and what is still unproven. Everything stays in the repo. Never write to any external system (wiki, chat, CRM). No credentials, and no customer names if the repo is public. If `SUMMARY.md` exists, update it in place and say so.
7. Do not commit.
