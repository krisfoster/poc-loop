---
name: poc-review
description: Runs the reviewer agent for an independent review of a diff or a PoC before handoff. Use when the user types /poc-review, optionally with a path, branch or focus.
disable-model-invocation: true
context: fork
agent: spike-loop:reviewer
argument-hint: "[path, branch or focus]"
---
Review the work. Scope from the user: "$ARGUMENTS".

If that is empty, review the current working directory: `git diff` against the default branch (use `git merge-base`), plus any untracked files. If it names a branch, diff that branch against the default branch. You have no conversation history, so work only from the repo and `POC.md` / `LOG.md` if present. Apply your PoC rubric and output contract. Do not edit anything.
