---
name: poc-build
description: Runs the implementer agent in an isolated worktree on one bounded chunk of an approved plan. Use only when the user types /poc-build with the task and a one-sentence done condition.
disable-model-invocation: true
context: fork
agent: spike-loop:implementer
argument-hint: "<task> | done when <condition>"
---
Implement this chunk: "$ARGUMENTS".

You have no conversation history. The text above must contain the task and a done condition. If either is missing, reply only with `NEEDS INPUT: give me the task and a one-sentence done condition`. Otherwise stay inside the stated scope, run the verification command if one is given, and report using your output contract. Do not push or open a pull request.
