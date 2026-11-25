---
name: poc-log
description: Appends a short dated entry to LOG.md in the current PoC and shows time used against the timebox. Use when the user types /poc-log, optionally with the entry text, at the end of a working session or after learning something.
disable-model-invocation: true
model: haiku
effort: low
argument-hint: "[what you tried and learned]"
---
# poc-log

Entry text from the user: "$ARGUMENTS". Never use em dashes.

1. Find `LOG.md` and `POC.md` in the current repo root. If either is missing, say to run `/poc-start` and stop.
2. Build the entry in the format at the top of `LOG.md` (Tried, Learned, Dead ends, Decision, Next question, Later). Use the user's text. If it is empty, draft it from this conversation in 2 to 5 lines. Use `none yet` for Decision unless one was stated. Use `date '+%Y-%m-%d %H:%M'` for the timestamp.
3. Show the entry, then append it to the end of `LOG.md`. Never edit or reorder earlier entries.
4. Time check: read `Started:` and `Timebox` from `POC.md`, compute elapsed wall-clock time since Started (if Started has no time, use the timestamp of the first `LOG.md` entry), and count the log entries. Print one line: `Elapsed <x> of <timebox>, <n> entries.` If elapsed exceeds the timebox, say so plainly and suggest deciding: iterate, pivot, harden or stop. It is a soft limit, so do not nag.
5. Do not commit.
