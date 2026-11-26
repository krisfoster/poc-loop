---
name: poc-verify
description: Runs the verifier agent on the current project in its own context and returns pass or fail with only the relevant errors. Use when the user types /poc-verify, optionally with a path or a focus such as "just the api tests".
disable-model-invocation: true
context: fork
agent: spike-loop:verifier
argument-hint: "[path or focus]"
---
Verify the project. Target and focus from the user: "$ARGUMENTS". If that is empty, use the current working directory and run the project's own check.

Find the project's own check first (`verify.sh`, README run steps, `Makefile`, `package.json` scripts, `compose.yaml`). Report using your output contract. Do not fix anything.

End with one line starting `Next:` (inside your line cap), chosen by your verdict. PASS: `/spike-loop:poc-log` to record it. FAIL: fix it and run `/spike-loop:poc-verify` again, and after two failed fix attempts run `/spike-loop:poc-debug <failing command, error, what was tried>`. PARTIAL: run the missing parts yourself, then `/spike-loop:poc-verify`. NEEDS HUMAN: do the manual step, then `/spike-loop:poc-log`.
