# Spec: prerequisites, checked and explained, and a scripted time check for `poc-log`

Status: draft 2, 2026-11-27, revised after the independent review R.1 (`docs/prereqs/review.md`). Implemented on this branch with one deviation, recorded under Deviations. Branch: `prereqs`, off `evals-phase-2`.

Maintainer decisions (2026-11-27): the `poc-log` time check (finding F2 in `docs/evals/findings.md`) is computed by a Python script, and the skill guards it with a prerequisite check. Every skill and agent is audited so that each tool it needs is recorded, checked, and explained to the user with a message saying how to fix it.

How to read the evidence. **(docs)** marks a claim read from the Claude Code docs on 2026-11-27 (code.claude.com `skills`, `plugins-reference`, `plugins/components`, `plugins/dependencies` and `permissions` pages, none showing a last-updated date), **(probe)** a claim from a headless run recorded in this repo, **(read)** a claim from reading the plugin files. Everything else is design.

## Problem

1. **F2 is not fixed.** `poc-log` asks the model to print `Elapsed <x> of <timebox>, <n> entries.` exactly. After two wording changes the line still broke in 3 of 39 headless Haiku runs (a comment on the same line, or reworded), no better than before (**probe**, `docs/evals/findings.md` F2). The model also does the date arithmetic and counts entries itself, and nothing checks either: the eval spec asks for elapsed time "within one minute of truth", which no case grades, and a known bug has some runs count the log's template line as an entry.
2. **F3 rests on the same judgement.** The over-timebox `Next:` rule depends on the model deciding the timebox is exceeded. The F3 fix held in 18 of 18 runs (**probe**), but the decision is still the model's.
3. **Prerequisites are neither recorded nor checked.** The README names Python 3.9+ for the sources helper and `gitleaks` and `typos` as optional for `poc-harden` (**read**). Nothing else is written down, no skill checks for a tool before using it, and a missing tool shows up as whatever the failing command prints. The worst case is `git`: eleven skills and all seven agents run `git -C "<target>" rev-parse` to find the repo root (**read**), and the paths rule treats a failure as "outside a git repository", so a machine without `git` would get a plausible answer about the wrong root instead of an error.
4. **No manifest field declares binaries.** The plugin manifest's `dependencies` array names other plugins only (**docs**, `plugins/dependencies`). A check has to happen at run time. The manifest does have `engines` for a Claude Code version range (**docs**, `plugins-reference`, as read by the reviewer), which answers the version question separately.

## Goals

1. The `poc-log` time-check line is produced by a script, byte for byte, with elapsed time and the entry count computed, never estimated, and the over-timebox decision made by the script, not the model. When the script cannot run, no time line is printed rather than one the model made up.
2. Every external tool a skill or agent needs is listed in one registry, with whether it is required or optional for each command, how it is checked, and the message the user sees when it is missing, naming how to fix it.
3. Each skill that needs a tool checks for it before it changes anything. A missing required tool stops the skill with the registry message and a `Next:` line. A missing optional tool skips only the step that uses it, and says so.
4. A test fails when a skill or agent uses a listed tool the registry does not name for it, or when a registry entry has no check or no message.
5. The evals can test the guard live: a run with a required tool hidden stops with the message and writes nothing.
6. A user with everything installed sees no new permission prompt in a skill, and at most one extra Bash call per command.

## Non-goals

- Tools the user's project needs (`docker`, `make`, `npm` and the like). The verifier reports a missing project tool as a failure already.
- Installing anything. The message says how; the user does it.
- A Claude Code version check at run time. The `engines` manifest field is the right place; adding it is a separate change (open question 1).
- Moving the elapsed-time text in `poc-checkpoint` (summary) and `poc-help` (status) onto the script. Possible follow-up (open question 2).
- Replacing `rsync` in the packager with `git ... | tar`. Recorded as a requirement instead (open question 3).

## Audit (read 2026-11-27)

"Paths paragraph" is the shared paragraph in every skill and agent that tells the model how to run commands. It names `cd`, `chmod`, `tail` and `date` only as examples, so those are not counted for it.

| Tool | Used by | How | Today |
|---|---|---|---|
| `git` | 11 skills (`poc-build`, `poc-checkpoint`, `poc-debug`, `poc-harden`, `poc-help`, `poc-log`, `poc-package`, `poc-research`, `poc-review`, `poc-start`, `poc-verify`) and all 7 agents | root finding (`rev-parse`), State, worktrees | not checked; a failure reads as "not a git repo" |
| `python3` 3.9+ | `poc-sources`, `poc-research` (required), `poc-log` after this change (optional) | `spike_sources.py`, `time_check.py` | named in the README, not checked |
| `rsync` | `packager` (so `poc-package`, `poc-harden`) | clean-clone copy (`agents/packager.md:28`) | not checked; not POSIX, absent from Git for Windows and minimal Debian or Ubuntu |
| `gitleaks` (optional) | `poc-harden`, `packager` | secret scan | `poc-harden` skips it with a note; `packager` does not say |
| `typos` (optional) | `poc-harden` | spell check | skipped with a note |
| `date` | `poc-start`, `poc-log`, `poc-checkpoint`, `poc-help` | timestamps, elapsed time | baseline |
| `mktemp` | `poc-sources` | temp file of tool names | baseline |
| `chmod` | `poc-start` | makes `verify.sh` executable | baseline |
| `grep`, `ls`, `tail`, `sed` | reviewers, packager, verifier | inspection | baseline |

**Baseline** tools are POSIX utilities. Claude Code's Bash tool runs them in a POSIX shell on macOS and Linux, and on Windows in Git Bash when it is installed; without Git Bash the default shell on Windows is PowerShell (**docs**, `plugins-reference`, as read by the reviewer), where neither the baseline tools nor a POSIX checker exist. Baseline tools are listed in the registry doc and not checked one by one. On a Windows machine without Git Bash the checker cannot run, and the "check cannot run" rule below applies. `git`, `python3` and `rsync` are not part of a POSIX shell and are checked. The contract test scans each skill and agent for uses of the registry's tools, so a file that starts using one without checking it fails. A tool outside the registry is not caught automatically: adding one means adding it to the registry and to the test's pattern list.

## Design

### 1. One checker, one registry: `scripts/check-prereqs`

A POSIX `sh` script at the plugin root, so it needs nothing the shell does not have. It is always run as `sh <path>`, so it does not depend on keeping its executable bit through a plugin install. It holds the registry as one `case` block per tool. Usage: `sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" <command> <tool>[:optional]...`, where `<command>` is the command name (`poc-log`) for the message, and `:optional` marks a tool the command can do without.

Output: one line per tool, in the order given, then a summary line.

```
ok: git 2.47.1
MISSING: python3 3.9 or later is needed by /spike-loop:poc-research for its setup check. Install it (macOS: `xcode-select --install` or `brew install python`; Debian or Ubuntu: `sudo apt install python3`; Windows: install Python 3 from python.org and make sure `python3` runs in Git Bash), then run the command again.
skipped: gitleaks is not installed, so /spike-loop:poc-harden leaves out the secret scan. To include it, install gitleaks (https://github.com/gitleaks/gitleaks#installing) and run the command again.
prereqs: missing python3
```

- `ok:` the tool is there, with its version when the check reads one.
- `MISSING:` a required tool is absent or too old. The text after the colon is the registry message, complete and safe to print as is.
- `skipped:` an optional tool is absent. The message names what is left out.
- The last line is `prereqs: ok` or `prereqs: missing <tools>`. Exit 0 when nothing required is missing, 1 when something required is missing, 2 on a usage error (an unknown tool or command, which is a plugin bug).
- Checks: `git --version`; `python3 -c 'import sys; print("%d.%d.%d" % sys.version_info[:3]); sys.exit(0 if sys.version_info >= (3, 9) else 1)'`; `rsync --version`; `command -v` for `gitleaks` and `typos`. No per-check timeout (POSIX `sh` has no timeout builtin, and a hand-made one would need a temp file or leave orphans); a hanging binary is caught by the Bash tool's own timeout. No network, no writes, no environment values or paths printed. Versions are the only data from the machine in the output.
- Registry entries hold: tool, check, the feature each command needs it for, and the install steps. Messages name the command and the feature, the install steps for macOS, Debian or Ubuntu and Windows, and end "then run the command again".

### 2. The guard in each skill

Every skill that uses a checked tool gets, in its frontmatter, the YAML list form of `allowed-tools` holding both spellings of the checker rule (the Bash rule matches the text before the first `*` as written, so quotes matter, **docs**, `permissions`):

```yaml
allowed-tools:
  - Bash(sh ${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs *)
  - Bash(sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" *)
```

and one paragraph, the same in every skill except the tool list:

> **Prerequisites.** Before anything else, run `sh "${CLAUDE_PLUGIN_ROOT}/scripts/check-prereqs" <command> <tools>` and read its output. If the last line is `prereqs: missing ...`, print each `MISSING:` line as it is, change nothing, and end with `Next: install what is missing, then run /spike-loop:<command> again`. Print any `skipped:` line and leave out the step that needs that tool. If the check cannot run (refused, not found, or no POSIX shell), say so in one line and continue: a command that needs a missing tool will fail with its own error. When you brief an agent, say "prerequisites checked".

Why a first step and not `` !`...` `` injection, with the trade-off stated in full: injection runs before the model sees the skill and saves a model round-trip on every invocation. With `allowed-tools` pre-approving the command, a non-allow permission result does not arise, auto mode does not abort, and `disableSkillShellExecution` swaps in placeholder text instead of failing; but a command that exits non-zero "aborts the entire skill invocation", and when the pre-approval does not apply (a policy setting, a plugin skill under `-p` if Probe 1 says so) a non-allow result aborts the invocation outside auto mode (**docs**, `skills`). An abort stops the whole command with Claude Code's error instead of the registry message, which is the failure this spec exists to remove. `|| true` would stop the non-zero abort but not the permission one. A first-step Bash call fails soft in every case, at the cost of one call. That the model runs the step is checked by the evals.

Why `allowed-tools`: "Using the same variable in both places lets a skill run a bundled script without a permission prompt", and the grant lasts for the turn that invokes the skill (**docs**, `skills`). It applies to a project skill in a `-p` run; plugin skills are not mentioned (Probe 1). No skill has `allowed-tools` today (**read**), so this adds the field.

**Agents.** `${CLAUDE_PLUGIN_ROOT}` is substituted in agent content (**docs**, `plugins-reference`). Each agent gets the paragraph with one more sentence: "Skip this if the command that started you, or your brief, says prerequisites were checked." A forked skill (`poc-debug`, `poc-package`, `poc-review`, `poc-verify`, all `context: fork`, **read**) puts its own body and the agent's in the same subagent, so the skill's paragraph runs the check and the agent's skips it. `poc-build` checks in the main session and says so in the brief. An agent called directly through the Agent tool runs the check itself. Agents have no `allowed-tools`, so a direct call may prompt once; whether a skill's grant reaches a forked subagent is Probe 2.

Which tools each file lists: `git` for every skill and agent that finds the root with it; `python3` for `poc-sources` and `poc-research` (required) and `poc-log` (`python3:optional`); `rsync` for `packager`, `poc-package` and `poc-harden`; `gitleaks:optional` for `poc-harden` and `packager`; `typos:optional` for `poc-harden`. `research-protocol` is preloaded, not a command, and lists nothing.

### 3. `poc-log` time check: `skills/poc-log/scripts/time_check.py`

Standard library only, Python 3.9+. Called after the entry is appended, as `python3 "${CLAUDE_SKILL_DIR}/scripts/time_check.py" --root "<root>" --docs <docs>`.

- **Started:** the `Started:` field of `<docs>/POC.md`'s header line, `YYYY-MM-DD HH:MM` or `YYYY-MM-DD`. With no time, the timestamp of the first dated entry in `<docs>/LOG.md` (the rule the skill states today), and with no dated entry, 00:00 on that date.
- **Timebox:** the `Timebox (first pass):` field. Accepted: one or more parts, each a number (integer or decimal) followed by optional space and a unit (`minute(s)`, `min`, `m`, `hour(s)`, `hr(s)`, `h`, `day(s)`, `d`), case-insensitive, summed (`2 hours`, `90 min`, `1.5h`, `1h 30m`). Anything else is not parsed: the line shows the timebox as written and the state is `unknown`.
- **Entries:** lines matching `^## \d{4}-\d{2}-\d{2}( \d{2}:\d{2})?(\s|$)` in `<docs>/LOG.md`, including the one just appended. The template line `## <YYYY-MM-DD HH:MM> ...` does not match, which settles the template-counting bug.
- **Elapsed:** now minus Started, in local time, as `<h>h <m>m` (for example `47h 15m`), or `<m>m` under an hour. A Started in the future prints `0m` and the state `unknown`.
- **Output:** line 1 is `Elapsed <elapsed> of <timebox as written>, <n> entries.` (`1 entry.` for one), line 2 is `timebox: over`, `timebox: within` or `timebox: unknown`. Exit 0. A missing file or a missing `Started:` field prints one `time check: <reason>` line naming the file relative to the repo root (never an absolute path) and exits 3.
- Reads only the two files, writes nothing.

### 4. `poc-log` steps

- The Prerequisites paragraph for `git` and `python3:optional`, and `allowed-tools` holding the checker rules and both spellings of `Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/time_check.py *)`.
- Steps 1 to 3 as today (resolve, build, show and append).
- Step 4, "Time check", becomes: run the script. Print its first line exactly as the script printed it, on a line of its own, and put any comment on the next line. If line 2 is `timebox: over`, say so plainly and suggest deciding. If the script printed `time check: <reason>` or could not run (refused, `python3` skipped, any error), print `Time check: not run (<reason>)` and nothing else about time: never work out elapsed time or count entries yourself. Never write the reason or the time line into `<docs>/LOG.md`.
- Step 5's first rule keys on the script: "First, if the time check printed `timebox: over` and the Decision is `none yet`, the line is `Next: /spike-loop:poc-checkpoint <iterate | pivot | harden | stop | pause>` ...". With no time check, the Decision rule applies.
- Pins that change: `tests/test_skills_contract.py` `test_poc_log_time_check_line_is_printed_exactly` and `test_poc_log_over_timebox_next_is_its_own_rule` (rewritten for the new text), `docs/handoff/tools/mutate.py` rows that quote `poc-log` step text (checked, updated if stale), and `docs/evals/findings.md` F2 and F3 (a note that both move to the script, with the re-run result).

### 5. Registry doc and README

`docs/prerequisites.md`: the tools, required or optional per command, the feature, the check and the install steps, plus the baseline list and the Windows note. A test checks it against the script. The README's Requirements section points at it.

## Tests (free, no model)

1. `tests/test_check_prereqs.py`: the checker under a fake `PATH` (a temp directory of symlinks to the real tools, minus the hidden ones): all present gives `prereqs: ok` and exit 0; `python3` hidden gives the `MISSING:` line and exit 1; `python3:optional` hidden gives `skipped:` and exit 0; a fake `python3` reporting 3.8 counts as missing; an unknown tool or command gives exit 2; the output holds no path and no environment value; nothing is written.
2. `tests/test_time_check.py`: Started with and without time, every timebox form including `1h 30m`, an unparsed timebox, a heading with no title, the template line not counted, `1 entry`, a future Started, missing files with relative reasons, exit codes, and the exact first line. Time is injected (`--now`, for tests) so results are fixed.
3. Contract tests: every skill and agent that names a registry tool has the Prerequisites paragraph listing it with the right required or optional mark; every tool listed is in the registry; the paragraph is identical across skills (and across agents) except the tool list; every skill with the paragraph has both checker rules in `allowed-tools` in list form; every registry entry has a check and install steps; `docs/prerequisites.md` matches the registry; the new `poc-log` step 4 and 5 rules are pinned.
4. Mutation rows: drop the guard from `poc-log`; drop `python3` from its list; make the checker exit 0 on a missing required tool; make the time check count the template line; remove "never work out elapsed time ... yourself". Each must fail a test.

## Evals (paid)

- Runner: a case field `hide_tools: [<tool>, ...]` builds the run's `PATH` from a temp directory of symlinks to everything on the inherited `PATH` except the named tools and their versioned aliases (`python3` also hides `python3.*` and `python`). A grader fails a run that calls a hidden tool by absolute path (`tool_call_count` gains an `input_regex`). Claude Code's own use of `git` (for example the status in its system prompt) is not affected by what the Bash tool can find, so `missing-git` tests only what the skill does.
- Cases: `poc-log/missing-python` (appends the entry, prints the `skipped:` line and `Time check: not run`, no `Elapsed` line, no time arithmetic), `poc-sources/missing-python` (stops with the `MISSING:` message, writes nothing; it replaced a planned `poc-research/missing-python` after Deviation 1 made `python3` optional there, and the public-only path of `poc-research` has no eval case), `poc-start/missing-git` (stops, writes nothing, does not run `git init`), and the existing `poc-log` cases with the time-check graders tightened to the script's exact format and `tool_call_count` on the checker and the script.
- Re-run the `poc-log` cases at the F2 sample size (about 20 runs) to show whether the line now holds.

## Probes (paid, before building)

1. Does a plugin skill's `allowed-tools` pre-approve the checker in a headless `-p` run when `--allowedTools` does not grant it? Quoted and unquoted command, and a plugin directory path with a space. If not, eval cases grant it, and the README says only interactive users get the prompt-free path.
2. In a forked skill, does the skill's `allowed-tools` grant reach the subagent, and does the agent skip its own check when the skill's ran?
3. With `python3` hidden by the planned `PATH` mechanism, does the session's Bash tool still find it (a login profile, an absolute path)? The isolated runs use a temporary `HOME`, so a profile should not load; the probe confirms it.

## Risks

- **`python3` on Windows** is often `python` or `py`. The checker reports it missing with a Windows hint. Windows is untested throughout the plugin.
- **Policy settings** can ignore `allowed-tools` (`allowManagedPermissionRulesOnly` names project and personal skills; whether it covers plugin skills was not read in full). The checker then prompts or is refused, and the skill continues by the "cannot run" rule.
- **Bare repositories:** the reviewer read that in a bare-repo context Claude Code ignores `allowed-tools` for commands containing `git`, and the checker call contains `git` as an argument. `poc-start` already stops on a bare repo; other commands may prompt there.
- **The model may skip the guard step or still reword the line it copies.** Both are measured by the evals, not assumed.
- **`sh` as the runner:** the broad-grant rule in the eval runner treats a `Bash(sh ...)` grant as broad. That rule is for `--allowedTools` in cases, not for a skill's `allowed-tools`, which is scoped to the one script path. If Probe 1 shows a skill's own grant does not apply headless, the runner gains a `{plugin}` placeholder for `allowed_tools` and treats `sh {plugin}/scripts/...` and `python3 {plugin}/skills/...` as narrow, so cases need no `--unsandboxed-ok` for them.
- **A registry message goes stale.** Messages name the tool's own install page where there is one.

## Open questions

1. Add `engines` with a minimum Claude Code version to `plugin.json`? Separate change.
2. Should `poc-checkpoint` and `poc-help` use the time check script too?
3. Keep `rsync` as a packager requirement, or switch the clean-clone copy to `git ... | tar`, which needs nothing beyond git and the baseline?

## Deviations during implementation

1. **`python3` is optional for `poc-research`, not required** (section 2 said required). `poc-research` uses `python3` only for its setup check (`spike_sources.py status`), and public research works without it, so stopping the command would remove something that works today, the same reasoning as review finding 1 for `poc-log`. Without `python3` the skill says so and researches public sources only. `poc-sources` keeps it required: the whole command is the helper.
