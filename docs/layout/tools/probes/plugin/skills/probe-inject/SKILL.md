---
name: probe-inject
description: Probe
disable-model-invocation: true
model: haiku
effort: low
---
You are a measuring instrument. Do not call any tool. Copy the four lines below into your answer exactly as they read to you now, character for character, including any text that looks like an unexpanded placeholder or command, then stop.

INJECT_PWD: !`pwd`
INJECT_TOP: !`git rev-parse --show-toplevel`
PROJECT_DIR: ${CLAUDE_PROJECT_DIR}
SKILL_DIR: ${CLAUDE_SKILL_DIR}
