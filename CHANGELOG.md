# Changelog

## 0.1.1

- Classifier: `edit`, `append`, `insert`, `replace`, `save`, `push`, `submit`, `import`, `attach`, `tag`, `store`, `modify` and similar verbs now make a tool write-class, so compound names such as `search_and_replace` are no longer offered as read.
- `render-agent` refuses a base agent with no `tools:` line, `init-sources` and `render-agent` accept a bare relative `--out`, and `status` no longer reads stdin.
- The packager's clean-clone test copies the working tree, so the files it just wrote are part of the test.
- `POC.md` `Started:` now includes the time, and `poc-log` and `poc-checkpoint` measure wall-clock time against the timebox.
- Reworded the read-only and no-external-access claims, and documented the limits in `docs/updating-sources.md`.
- Install, update and uninstall steps in the README, a plugin icon, and manifest metadata.

## 0.1.0

Initial release.
