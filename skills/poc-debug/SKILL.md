---
name: poc-debug
description: Runs the debugger agent to find the root cause of a failure that survived a fix attempt. Use when the user types /poc-debug followed by the failing command and what was already tried.
disable-model-invocation: true
context: fork
agent: spike-loop:debugger
argument-hint: "<failing command, symptom, what you tried>"
---
Diagnose this failure: "$ARGUMENTS".

You have no conversation history. If the text above is empty or names no command or symptom, reply only with `NEEDS INPUT: give me the failing command, the error, and what has been tried`. Otherwise reproduce first, then follow your method and output contract. Do not edit tracked files.
