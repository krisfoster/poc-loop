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

1. Read `POC.md` and the last 60 lines of `LOG.md`. If missing, say to run `/poc-start` and stop, ending with `Next: /spike-loop:poc-start`. If the last log entry is older than this session's work, run the `/poc-log` steps first (draft, show, append).
2. Print a summary of at most 12 lines: the question; what is now established, with the evidence (command and result), not claims; assumptions still unproven; open question for the next session; elapsed wall-clock time against timebox (if `Started:` has no time, measure from the first `LOG.md` entry).
3. Outcome: if "$ARGUMENTS" is empty, recommend one of iterate, pivot, harden or stop with a one-line reason, and ask the user to confirm. Record the confirmed outcome in `LOG.md` as a new entry whose Decision line names it.
4. Iterate or pivot: end with the fresh-session instruction (`/clear`, then say what to start with). Pivot also means edit `POC.md` assumptions after the user agrees.
5. Harden: tell the user `/spike-loop:poc-harden` is next.
6. Stop or harden: write `SUMMARY.md` in the repo root, at most 25 lines: title, the question, the answer, key evidence (the command and its result), what to do differently, and what is still unproven. Everything stays in the repo. Never write to any external system (wiki, chat, CRM). No credentials, and no customer names if the repo is public. If `SUMMARY.md` exists, update it in place and say so.
7. End with one line starting `Next:`. `iterate`: `/clear`, then what to start with. `pivot`: edit the assumptions in `POC.md`, then `/clear`. `harden`: `/spike-loop:poc-harden`. `stop`: nothing further, the PoC is closed and `SUMMARY.md` is written. If the outcome was not confirmed: `/spike-loop:poc-checkpoint <recommended outcome>` to confirm it.
8. Do not commit.
