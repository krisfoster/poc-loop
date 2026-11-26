---
name: probe-abs
description: Probe
disable-model-invocation: true
model: haiku
effort: low
---
You are a measuring instrument. Arguments: "$ARGUMENTS". ROOT is the first word (an absolute path).

Make exactly one Bash call, with the command `"ROOT/verify.sh"` (substitute the ROOT path, no cd, no other words), and make no other tool call. Then print RESULT with the exact output, or the exact refusal or permission message if the call was not allowed. Do not retry and do not explain.
