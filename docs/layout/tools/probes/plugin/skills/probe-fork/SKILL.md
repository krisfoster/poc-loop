---
name: probe-fork
description: Probe
disable-model-invocation: true
model: haiku
effort: low
context: fork
agent: probe:probe-agent
---
You are a measuring instrument. Do exactly these steps with the Bash tool, one Bash call per step, in order. Then print a section RESULTS with each step number and its exact output, copied verbatim. Do not explain or fix anything. If a call is refused or fails, copy the exact message.

Arguments: "$ARGUMENTS". ROOT is the first word (an absolute path). TARGET is the second word, if there is one.

1. Run `pwd`.
2. Run `git rev-parse --show-toplevel`.
3. Run `git rev-parse --git-dir; git rev-parse --git-common-dir`.
4. Run `cd "ROOT"` alone (substitute the ROOT path). Then, in a separate next Bash call, run `pwd`.
5. In one Bash call run `cd "ROOT" && pwd && ls verify.sh && ./verify.sh` (substitute the ROOT path).
6. If TARGET is given, run `git -C "TARGET" rev-parse --show-toplevel`. Otherwise write "no target".
