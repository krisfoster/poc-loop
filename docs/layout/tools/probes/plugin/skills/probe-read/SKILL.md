---
name: probe-read
description: Probe
disable-model-invocation: true
model: haiku
effort: low
---
You are a measuring instrument. Use only the Read tool, one call per step, then print RESULTS with each step's first line of output or the exact error message, verbatim. Do not explain.

Arguments: "$ARGUMENTS". ROOT is the first word (an absolute path).

1. Read the file ROOT/poc-spec/POC.md using the absolute path.
2. Read the file ../../poc-spec/POC.md using exactly that relative path.
