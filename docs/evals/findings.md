# Plugin findings from the evals work

Defects and doubtful claims found while building the evals. They are logged here and fixed on a separate branch, so a change in eval scores is never confused with a change to the evals.

## F1: `/spike-loop:poc-build` does not run in a worktree (observed, headless only so far)

- **Claim:** `README.md:18` ("in a git worktree"), `docs/workflow.md:43` ("own worktree") and `skills/poc-build/SKILL.md:3` ("in an isolated worktree") say the implementer runs isolated. `agents/implementer.md:7` sets `isolation: worktree`.
- **Observed:** Claude Code 2.1.325, headless, 2026-11-25, on a fixture git repo. Running `/spike-loop:poc-build <task> | done when <condition>` (a `context: fork` skill with `agent: spike-loop:implementer`) made the implementer run in the main working tree. Its first command printed the fixture's own root from `git rev-parse --show-toplevel`, `hello.txt` appeared untracked in the main tree, and `git worktree list` showed no extra worktree.
- **Contrast:** calling the same agent through the Agent tool (`subagent_type: spike-loop:implementer`) did create a worktree at `<repo>/.claude/worktrees/agent-<id>`, on branch `worktree-agent-<id>`, with the change inside it and nothing in the main tree except an untracked `.claude/`.
- **Not known:** whether an interactive session behaves the same as a headless one. Not checked against the docs yet.
- **Why it matters:** a user who runs `/poc-build` expecting isolation gets edits in their working tree. This is a claim about the product that is not true in the tested path.
- **Possible fixes, for the separate branch:** have `poc-build` call the agent through the Agent tool instead of `context: fork`, or change the claims. Confirm against the Claude Code docs for `isolation` and `context: fork` first.
