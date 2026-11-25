---
name: poc-package
description: Runs the packager agent to turn a working PoC into a handoff-ready repo (README, .env.example, clean-clone test, secret scan). Use when the user types /poc-package, optionally with the project path.
disable-model-invocation: true
context: fork
agent: spike-loop:packager
argument-hint: "[project path]"
---
Package the PoC. Path from the user: "$ARGUMENTS". If that is empty, use the current working directory.

You have no conversation history. Read `POC.md` and `LOG.md` if present, then follow your steps and output contract. Do not stage or commit anything.
