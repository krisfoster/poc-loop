# Changelog

## 0.1.2

- New `/spike-loop:poc-help`: prints the command table, explains one command (`/spike-loop:poc-help verify`), and reads `POC.md` and `LOG.md` to say where the PoC stands and what to run next. It writes nothing.
- Every command now ends with one line starting `Next:` that names the next command, chosen by the outcome: verify on a pass or fail, review with or without blocking findings, harden when blocked or complete, log by the entry's Decision, and so on. The forked commands (`poc-build`, `poc-verify`, `poc-debug`, `poc-review`, `poc-package`) add it in the skill, not in the agent, so the agents' output contracts used by `poc-harden` are unchanged.
- A test checks that every command has a `Next:` rule, that `poc-help` lists every command, and that the README lists them too.

## 0.1.1

- Classifier: `edit`, `append`, `insert`, `replace`, `save`, `push`, `submit`, `import`, `attach`, `tag`, `store`, `modify` and similar verbs now make a tool write-class, so compound names such as `search_and_replace` are no longer offered as read.
- `render-agent` refuses a base agent with no `tools:` line, `init-sources` and `render-agent` accept a bare relative `--out`, and `status` no longer reads stdin.
- The packager's clean-clone test copies the working tree, so the files it just wrote are part of the test.
- `POC.md` `Started:` now includes the time, and `poc-log` and `poc-checkpoint` measure wall-clock time against the timebox.
- Reworded the read-only and no-external-access claims, and documented the limits in `docs/updating-sources.md`.
- Install, update and uninstall steps in the README, a plugin icon, and manifest metadata.

## 0.1.0

Initial release.
