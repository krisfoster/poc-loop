# spike-loop

A small PoC workflow for [Claude Code](https://claude.com/claude-code), packaged as a plugin. Write down the question and the success check, build in a timeboxed loop, verify and review with cheap isolated subagents, then package for handoff.

Status: 0.2.0, early. The measurements are one run per variant on one small task, so read them as indicative only: see [how to read them](docs/measurements.md#how-to-read-this).

## What you get

| Command | Does |
|---|---|
| `/spike-loop:poc-help` | Lists the commands, explains one (`/spike-loop:poc-help verify`), and says where your PoC stands and what to run next |
| `/spike-loop:poc-start` | Interviews you, then writes `poc-spec/POC.md` (question, success check, ranked risks, scope), `poc-spec/LOG.md` and a failing `verify.sh` stub |
| `/spike-loop:poc-log` | Appends a short dated entry to `poc-spec/LOG.md` and shows time used against the timebox |
| `/spike-loop:poc-verify` | Runs `verify.sh` or the project's own check in a Haiku subagent, returns pass or fail with only the relevant errors |
| `/spike-loop:poc-research` | Answers a factual question from primary sources with dates and versions. Uses your internal documents once set up |
| `/spike-loop:poc-sources` | One-time setup and later updates of the internal sources the researcher may read, see [docs/updating-sources.md](docs/updating-sources.md) |
| `/spike-loop:poc-review` | Independent review of a diff or PoC (Opus) |
| `/spike-loop:poc-debug` | Root cause after a failed fix, in a read-only subagent |
| `/spike-loop:poc-build` | One bounded chunk of an approved plan, built in a separate git worktree (it branches from the default branch, and you merge the result) |
| `/spike-loop:poc-package` | README, run steps, `.env.example`, clean-clone test, secret scan |
| `/spike-loop:poc-harden` | Review, then package, then final gate. Lean path for small PoCs, full path with `full` |
| `/spike-loop:poc-checkpoint` | End-of-session summary, and `SUMMARY.md` on stop or harden |

Every command ends with a line starting `Next:` that names the command to run next, so you do not have to remember the flow. Run `/spike-loop:poc-help` any time to see the commands and where the current PoC stands.

Seven subagents back these (`verifier`, `reviewer`, `reviewer-lite`, `debugger`, `researcher`, `packager`, `implementer`). The research and review ones cannot edit files or write to a connector. They do keep `Bash` and web access, so their read-only rule is a prompt rule, not a sandbox: do not point them at untrusted content you would not paste into a chat. See [docs/workflow.md](docs/workflow.md) for how the pieces fit.

## Install

1. Add the marketplace, then install the plugin. The install is user scope by default, so the commands work from any repo.

   ```bash
   claude plugin marketplace add krisfoster/poc-loop
   claude plugin install spike-loop@spike-loop
   ```

2. Restart Claude Code.
3. In a git repo, start a PoC with `/spike-loop:poc-start`.

To try a clone without installing: `claude --plugin-dir /path/to/poc-loop`.

### Update

```bash
claude plugin marketplace update spike-loop
claude plugin update spike-loop@spike-loop
```

Restart Claude Code to apply it. Changes between versions are in [CHANGELOG.md](CHANGELOG.md).

### Uninstall

```bash
claude plugin uninstall spike-loop@spike-loop
claude plugin marketplace remove spike-loop
```

Add `--keep-data` to the first command to keep the plugin's data directory. Your sources file in `~/.config/spike-loop/` and the generated `researcher-internal` agent in `~/.claude/agents/` are yours and are not removed. Delete them by hand if you want them gone.

## Internal research sources (first use)

Public research works immediately. To let the researcher read your internal documents (wiki, drive, chat, email, meeting notes, local repos), run `/spike-loop:poc-sources` once, either right after install or when `/spike-loop:poc-research` offers it. It finds the read-only connector tools you have, asks you which to allow, records where your documents live, and generates a read-only `researcher-internal` agent. Restart Claude Code afterwards. Everything it writes stays on your machine, outside this repo. Full guide, including how to update later: [docs/updating-sources.md](docs/updating-sources.md).

## Design notes

- No framework. Three files carry the state: `poc-spec/POC.md` (written once), `poc-spec/LOG.md` (append only), `verify.sh` (exits non-zero on failure). A stub that fails on purpose cannot pass by accident.
- Working documents live in `poc-spec/`, so one folder can be left out of a public repo or a customer hand-off. `README.md`, `CLAUDE.md`, `verify.sh`, `.env.example` and `SUMMARY.md` stay at the repo root. The packager warns when `poc-spec/` would travel with a PoC that is public or tied to a deal.
- Older layout: a PoC started before 0.2.0 has `POC.md` and `LOG.md` at the repo root. It works as is. To move it, run `mkdir poc-spec && git mv POC.md LOG.md poc-spec/` (use `mv` if they are untracked) and update the paths in the `CLAUDE.md` section that `/spike-loop:poc-start` wrote. Nothing is moved for you.
- Commands find the repo root with git, so they are designed to work from a subdirectory as long as the session may use the root. If one is refused for that reason it says so: start the session at the repo root, or run `/add-dir` with the root. The shell snippets assume a POSIX shell, and Windows is untested.
- Subagents get no conversation history, so each slash command takes its target in the arguments.
- Auto-delegation by description proved unreliable in testing (delegated on 2 of 10 prompts that should), so every agent has an explicit slash command.
- Connectors are allowlisted by exact tool name, never by wildcard, because a plugin agent that omits `tools` inherits every tool including writes.

## Requirements

Claude Code with plugin support. Python 3.9+ standard library for the sources helper. `gitleaks` and `typos` are used by `/spike-loop:poc-harden` if installed, and skipped with a note if not.

## Development

```bash
python3 -m unittest discover -s tests
```

Contributions: keep prose free of em dashes, keep skill names equal to their folder names, and never commit a sources file, connector IDs or workspace names. See `CLAUDE.md`.

## License

MIT, see [LICENSE](LICENSE).
