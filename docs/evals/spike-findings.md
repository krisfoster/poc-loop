# Phase 0 findings

Claude Code 2.1.325, 2026-11-25, macOS. Everything below was observed by running it, unless marked otherwise. Tasks not listed here have not been run.

## 0.4 Isolation and authentication (partly done)

- `claude setup-token` exists in 2.1.325.
- A headless run authenticates with only `CLAUDE_CODE_OAUTH_TOKEN` set, in a clean environment (`env -i`) with a temporary `HOME`, `CLAUDE_CONFIG_DIR` and `XDG_CONFIG_HOME`. The `system/init` event reports `apiKeySource: "none"`, so it used the subscription token and no API key. The maintainer's normal login was not used.
- Under that isolation the init event shows no MCP servers, 27 built-in tools and only the built-in agents (`claude`, `Explore`, `general-purpose`, `Plan`, `statusline-setup`). None of the maintainer's own agents or connectors loaded.
- The init event lists five built-in plugins (`cc-plugin-sec-default`, `cc-plugin-agents-md`, `cc-plugin-telemetry`, `cc-plugin-privacy`, `cc-plugin-plugin-authoring`). The isolation allowlist must include them.
- Not yet done: proving that a real `~/.config/spike-loop/research-sources.md` is not read (needs the research case), reading Anthropic's terms on scripted use of a subscription, measuring plan usage per real run, and testing bare mode with `--tools`.
- The token is kept in `.env` as `SPIKE_EVALS_OAUTH_TOKEN` (gitignored) and mapped to `CLAUDE_CODE_OAUTH_TOKEN` only for the child process. The raw event logs were checked for `sk-ant` and contain none.

## 0.2 Running `poc-log` headlessly (done)

- Command shape: run from the fixture directory, `claude -p "/spike-loop:poc-log <text>" --plugin-dir <copy of the tree from git archive HEAD> --allowedTools Read Edit Write 'Bash(date *)' --output-format stream-json --verbose`.
- The slash command is accepted even though the skill has `disable-model-invocation: true`. The init event lists all 11 `spike-loop` skills, the `research-protocol` skill, and all 7 agents.
- The entry was appended in the right format, earlier entries were untouched, and `POC.md` was not modified. The skill ran on Haiku (`claude-haiku-5-5`), 5 turns, an estimated cost of $0.004.
- The elapsed-time line was correct against the fixture's `Started:` time and said the timebox was exceeded.
- Default permission mode is `default`. Read-only Bash (`ls`, `cat`) ran without approval, but a Bash `printf >>` append was denied and listed in the result's `permission_denials`. The skill recovered by using Read and Edit. A grader should treat a denial that changes the route as a harness signal.
- The result event carries `num_turns`, `permission_denials`, `modelUsage` (resolved model IDs) and `total_cost_usd`. The init event carries `claude_code_version`, `permissionMode`, `plugins`, `skills`, `agents` and `slash_commands`, which is enough for the isolation assertion.
- A line of non-JSON output appeared in my first two attempts at parsing, before the script was made tolerant. I did not capture what it was. It does not appear in the final run, where stderr was empty.

## 0.3 Forked skill and subagent events (done)

Both ran headlessly in the isolated setup with the plugin copy.

**Forked skill (`poc-verify`, `context: fork`, agent `verifier`)**
- The fork runs as a `local_agent` task. The log has a top-level `system task_started` and `system task_notification` (status `completed`), and every message the verifier produced carries a `parent_tool_use_id`, so a grader can separate fork activity from the top level.
- The verifier's model is visible on the child assistant messages: `claude-haiku-5-5`.
- The top-level `result` is the verifier's output unchanged (`VERDICT: PASS`, commands run, `NEEDS HUMAN: none`), cost about $0.0015. It reports `num_turns: 0`, so turn counts from the result event cannot be used for forked skills. Count tool calls from the events instead.
- One permission denial: the verifier ran `./verify.sh; echo "exit=$?"`, which did not match the pinned `Bash(./verify.sh)` rule. It retried with plain `./verify.sh`. A compound command is a different command to the allowlist, so rules must be written with this in mind.
- The verdict was right, and the verifier added that a script that only echoes proves only that it runs.

**Subagent (`poc-research`, calling `spike-loop:researcher`)**
- The `Agent` tool call appears at the top level with `subagent_type: "spike-loop:researcher"`. The subagent's own calls (`ToolSearch`, then `WebFetch` on the vendor docs) are child events with `parent_tool_use_id`, and its model is `claude-sonnet-5-5`. The init event lists the tool as `Task`, but the tool call is named `Agent`, and pinning `Task` in `--allowedTools` worked with no denials.
- **The subagent ran in the background.** The stream has a `task_started`, `background_tasks_changed`, `task_notification` sequence, and **two `init` and two `result` events**. The first `result` is a stale "the researcher agent is still running, so I don't have an answer yet". The second `result`, after the task completed, holds the real answer. **Graders must use the last `result` event, not the first.** Cost on both is the cumulative total (about $0.09).
- The final answer was within the line cap, cited the vendor page with a fetch date, and ended with the exact line `Internal sources are not set up: run /spike-loop:poc-sources once.`, so the non-interactive branch of `poc-research` behaves as written.
- The skill's status helper (`python3 .../spike_sources.py status`) ran from the plugin copy with `${CLAUDE_SKILL_DIR}` resolved correctly.
- `modelUsage` lists Haiku as well as Sonnet, though no Haiku agent ran in this case. The source of that usage is not identified.
- Not covered here: which model ran the top-level `poc-research` skill step (the skill says Sonnet).

## 0.6 `AskUserQuestion` and `poc-start` (done)

`AskUserQuestion` is not in the tool list of a headless run (`tools` in the init event does not contain it, in both the plain and the `plugin eval` runs). In the first-use `poc-research` run the skill therefore took its non-interactive branch and continued with the public researcher.

`poc-start` ran on Opus (`claude-opus-5-5`) in two fixture git repos, each with one empty commit, with `Read Write Edit Bash` granted and no permission denials.

- **All answers in the arguments:** it asked nothing and wrote `POC.md`, `LOG.md`, `verify.sh` and `CLAUDE.md` in 7 turns for an estimated $0.176. Checked by script afterwards: `POC.md` is 24 lines, has exactly the template headings, a `Started:` line with date and time, no `<...>` placeholders and no em dashes. `verify.sh` is executable and exits 1 as an unedited stub. `LOG.md` has the template plus a first "PoC started" entry. `CLAUDE.md` has the wiring section with all four required points. Nothing was staged or committed. `verify.sh` was left as the stub although the success check was written as "running `./verify.sh` exits 0", which is circular with no code yet, so that was reasonable. Whether a scriptable check would be written in is not tested.
- **No arguments:** it asked its interview questions as one plain-text message (setup, deal, question and so on), wrote no files, and stopped, in 2 turns for $0.092. It had checked first that no `POC.md`, `LOG.md`, `verify.sh` or `CLAUDE.md` existed.
- **Consequences:** the "did not re-ask" check works on text questions only. Compare the question text before the first file write with the scripted answers by keyword. An `AskUserQuestion` count is meaningless headlessly and is dropped from the spec. The "no `<...>` placeholders" check applies to `POC.md` only, because the `LOG.md` template header legitimately contains `<YYYY-MM-DD HH:MM>` style lines (3 matches in a correct run).
- **Not tested here:** tier 0, a public repo, an existing `POC.md`, no git repo, and a vague-but-partial set of answers. These are Phase 2 cases.

## 0.7 `claude plugin eval` (done)

Docs read: https://code.claude.com/docs/en/plugin-evals, 2026-11-25. Ran one case against a copy of the plugin, with `--trust-plugin --scaffold --no-publish --ablation none --runs 1 -j 1 --keep-temp`, under the same clean environment and token as the other probes.

**What works**
- It authenticated with the token and ran the case in about 8 seconds for about $0.004. The run's own `system/init` shows `apiKeySource: "none"`, the `spike-loop` plugin and 12 skills loaded, and only the built-in `cc-plugin-*` plugins besides it.
- The case prompt can be a slash command (`/spike-loop:poc-log ...`), and the skill ran.
- A case is a directory under `evals/` with a `case.yaml` (`schema_version: "1.1"`, `name`, `context.scaffold_script`, `execution`, `graders`). A scaffold script builds the fixture in an empty workspace, including `git init`, but only runs with `--scaffold`.
- Isolation is built in: each run gets a temporary home, working directory and config, and the eval directory is hidden from the agent. This covers the leakage rule in the spec without us copying the plugin tree.
- Retained with `--keep-temp`: a full stream-json event log at the `tracePath` given in the result JSON (init, tool calls, a `system permission_denied` event, result), and the final workspace including `.git`, under `<kept dir>/sealed/home/cwd`. The workspace is sealed (mode 000) until `chmod 700` is run on the kept directory and `sealed`. There is no snapshot of the starting state, so a diff needs the scaffold re-run.
- The result JSON has per-run `score`, `turns`, `costUsd`, `tracePath`, per-grader `passed` and `explanation`, plus `claudeVersion` and the plugin version.

**What does not, or is unresolved**
- Graders are `regex`, `file_exists`, `tool_used`, `tool_order`, `llm` and `baseline`. The docs say "There are no custom-code graders", so recall, the matcher, byte-identical and exit-code checks cannot run inside it.
- Runs use permission mode `dontAsk` and remove built-in tools that are not granted (the init event lists 9 tools). With `--allow-tools Edit Write 'Bash(date *)'` the skill's compound `cd ... && ... ; date ...` command was denied and the skill gave up, scoring 0, where the same skill recovered under the default mode earlier. With `--allow-tools Edit Write Bash` it succeeded. The `Bash` grant is OS-sandboxed by the tool, per its help text.
- `execution.runs: 1` in `case.yaml` was not honoured (the result reports `runsPerCase: 3`). The `--runs` flag worked.
- The `file_exists` grader reported "LOG.md missing (expected present)" while the file existed and a `regex` grader read it. Cause not found. It may only count files the run created. Not relied on.
- The kept directory is under `/private/tmp`, outside `TMPDIR`. The layout (`out/trace.jsonl`, `sealed/home/cwd`) was observed, and only the `tracePath` field is in the result JSON, so the workspace location is not a documented interface.
- By default the HTML report is published to claude.ai as a private artifact when signed in with a subscription and artifacts are available. The docs say runs started from a Claude Code session stay local. `--no-publish` must always be passed.
- The first run in an untrusted plugin directory prompts, so `--trust-plugin` is needed headlessly. It trusts the plugin's code and eval suite, which is acceptable only for this repo's own plugin.

**Reading for Gate 0.** A hybrid is possible: the built-in command runs and isolates the sessions, and our graders read `trace.jsonl` and the kept workspace afterwards. It depends on an undocumented kept-directory layout, on `chmod` of a sealed directory, and on re-running scaffolds for diffs. The custom runner used for 0.2 and 0.3 already captures the same event log, the final tree and permission denials, with full control of the fixture and the tool grants, and needs our graders either way. The decision is recorded at Gate 0, once the remaining tasks are done. Current lean: custom runner, with `claude plugin eval` kept as an optional way to run `llm` graders.

## 0.9 `isolation: worktree` (done)

Two paths, each on a fresh fixture git repo with one commit, same isolated setup as the other probes.

- **Via the Agent tool** (`subagent_type: spike-loop:implementer`): a worktree is created at `<repo>/.claude/worktrees/agent-<id>` on branch `worktree-agent-<id>`, from the repo's HEAD. The change is made there (`hello.txt` untracked in the worktree) and the main tree has only an untracked `.claude/`. The worktree is kept because it has changes.
- **Via the forked skill** (`/spike-loop:poc-build`, `context: fork`, `agent: spike-loop:implementer`): **no worktree.** The implementer worked in the main tree. See `docs/evals/findings.md`, F1.
- **How a grader finds the worktree:** run `git worktree list --porcelain` in the fixture after the run, take any worktree path under `.claude/worktrees/`, and read its files and `git status`. The path also appears in the child `Write` and `Edit` tool inputs in the event log. The branch name is `worktree-agent-<id>`.
- **Consequences for the evals:** the build and debug cases must call the implementer the way the plugin actually does, so the F1 behaviour is itself something the evals report. "No tracked file modified" checks must read the main tree, and "diff touches only the named files" checks must read the worktree when one exists and the main tree otherwise. The main tree will always show an untracked `.claude/` after a worktree run, so untracked-file checks must ignore it.

## 0.10 `skills:` preloading in the agents (done)

Four agents list `spike-loop:research-protocol` under `skills:` (`researcher`, `reviewer`, `reviewer-lite`, `debugger`). The skill has no `disable-model-invocation`.

- **Method:** each agent was called through the Agent tool with a brief that said not to use tools and asked it to quote, from "the research guidance already in your context", the heading of the first numbered section and the last sentence of the first bullet under it. The brief did not contain either text. A `general-purpose` agent, which does not list the skill, got the same brief as a control.
- **Result:** all four agents quoted both lines verbatim (`1. Choose the source class first`, and the "Skipping Context7 ..." sentence). The control replied `NONE`. The debugger run's `modelUsage` includes `claude-opus-5-5`, so the agent ran as defined.
- **No tool use by the agents:** each of the four runs has exactly one child `user` event (the brief) and no child tool results, whereas the earlier research run showed child tool calls when there were some. The top-level session only called the Agent tool, so it could not have supplied the text.
- **Limits:** tested through the Agent tool only. The `context: fork` skills (`poc-review`, `poc-debug`, `poc-verify`) use these agents too, and preloading there was not tested. Tested in an isolated headless run, not an interactive one.
- **Event log quirk:** for a foreground subagent that makes no tool calls, the log has no child `assistant` event. The agent's answer is only in the Agent call's `tool_result`, a top-level `user` event. A grader should read the final answer from the last `result` event, or from that tool result, and not assume child assistant messages exist. The control ran in the background (two `init` and two `result` events, as in 0.3), the four agents did not, and nothing was set to choose between them.

## 0.5 Budget flag and result fields (done)

`claude -p ... --max-budget-usd <n>`, Sonnet, isolated, on a three-Bash-call task and on the `poc-research` subagent case. Four runs, so the overshoot figures are indicative only.

| Run | Cap | Outcome | Reported cost | Over cap |
|---|---|---|---|---|
| Three Bash calls, no cap | none | `success`, 4 turns | $0.0382 | n/a |
| Same task | $0.02 | stopped after 1 turn, 1 of 3 Bash calls made | $0.0297 | $0.0097 (48%) |
| Same task | $0.05 | `success`, cap not reached | $0.0387 | none |
| `poc-research` with a subagent | $0.04 | stopped after 3 turns | $0.0459 | $0.0059 (15%) |

- **The cap works but is a soft limit.** A run that hit it ended with `is_error: true`, `subtype: "error_max_budget_usd"`, `terminal_reason: "budget_exhausted"`, `errors: ["Reached maximum budget ($0.02)"]`, and an empty `result` text. The overshoot is the cost of the turn in flight, and a first turn alone costs about $0.03 on Sonnet here, so caps below roughly $0.05 are not meaningful for a single run.
- **A budget stop loses the work in flight.** In the subagent case the researcher was started, then killed (`subagent_stats.killed.system: 1`, `completed: 0`) and no answer came back. A grader must treat `budget_exhausted` as a harness failure, not a stage failure.
- **Whether the subagent's own spend counted toward the cap is not established.** All of the reported $0.0459 is attributed to the top-level Sonnet, and the subagent was killed early.
- **Result event fields that help graders.**
  - `result_index` numbers the result events (0, 1, ...), so the final answer is the highest index. This confirms the stale-first-result behaviour from 0.3.
  - `subagent_stats` gives `spawned`, `completed`, `failed`, `killed`, `started_in_background` and `by_type` (for example `{"spike-loop:researcher": 1}`). This counts agent calls without parsing tool calls, which is what the `poc-harden` call-count check needs.
  - `subagent_stats.requested.unset: 1` with `started_in_background: 1` means a subagent with no explicit setting was started in the background. That is the likely source of the two-`result` pattern.
  - Others seen: `num_turns`, `stop_reason`, `terminal_reason`, `total_cost_usd`, `modelUsage`, `model_usage_since_last_result`, `permission_denials`, `safety_stops`, `duration_ms`, `duration_api_ms`, `session_id`.
- **Consequence for the harness.** Per-run caps are set at least twice the expected cost of a case and never below $0.10. The suite cap leaves headroom of at least 50 percent of the largest single-run cap. Both are provisional until Phase 1 measures real case costs.

## 0.8 Does `evals/` ship to users (done)

Docs read: https://code.claude.com/docs/en/plugin-marketplaces, `plugins-reference`, `plugins/marketplace-reference` and `plugins/loading`, 2026-11-25. Then measured by installing from two layouts into an isolated config and listing the cache.

- **Docs:** the plugin's own directory (its source path) is copied into `cache/<marketplace>/<plugin>/<version>/`, and "files outside the plugin directory aren't copied". No ignore file, `files` allowlist, exclude glob or `export-ignore` is documented. A relative-path plugin in a marketplace added from a local path loads in place and is not copied. Size limits for ordinary plugins are not stated.
- **`claude plugin marketplace add file://...` is rejected.** Accepted forms are `owner/repo`, `https://...` or `./path`. The tests therefore used a local marketplace directory whose plugin entry pointed at a `file://` git repo, as a stand-in for a GitHub-hosted marketplace. A real `owner/repo` install was not tested.
- **Layout A, plugin at the repo root** (the current layout, source `url`): the installed copy held `agents`, `skills`, `.claude-plugin`, `assets`, `docs`, `tests`, `evals`, `.envrc`, `.env.example`, `.gitignore`, `.gitleaks.toml`, `_typos.toml`, `CHANGELOG.md`, `CLAUDE.md`, `LICENSE`, `README.md`. So the whole repo except `.git` ships, and `evals/` would too.
- **Layout B, plugin in `plugins/spike-loop/` with `evals/` at the repo root** (source `git-subdir`): the installed copy held only the subdirectory's contents. `evals/` was absent.
- **Decision:** keep the current layout and accept that `evals/` ships under the size budget in the spec, because `tests/`, `docs/`, `.envrc` and `CLAUDE.md` already ship and moving the plugin changes the install path and the clone instructions. Revisit if `evals/` grows.

## Not yet run

0.1 (doc reading, mostly covered by the 0.7 and 0.8 docs pages). Also open inside 0.4: Anthropic's terms on scripted use of a subscription and plan usage over a larger run.
