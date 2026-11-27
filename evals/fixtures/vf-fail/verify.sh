#!/usr/bin/env bash
set -euo pipefail
want=hello
got="$(cat greeting.txt)"
if [ "$got" != "$want" ]; then
  echo "check failed: expected greeting $want, got $got" >&2
  exit 1
fi
echo "check passed: greeting is $want"
