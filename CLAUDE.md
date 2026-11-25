# CLAUDE.md

This repo is a public Claude Code plugin and one-plugin marketplace holding the Spike Loop PoC workflow: skills under `skills/`, subagents under `agents/`.

## Repo rules

- Before any `git push`, `gh pr create` or `gh repo create --push`, review the outgoing changes for secrets and confidential information: customer names, internal hostnames and URLs, CRM or deal data, personal data, connector or workspace IDs. Scanners match patterns, not meaning. Never use `--no-verify`.
- This repo is public. Nothing from a user's own research-sources file, notes or connector list may be committed. User configuration lives outside the repo, in `~/.config/spike-loop/`.
- Spell check: run `typos` on changed files before committing. Add intentional words to `_typos.toml`.
- Config lives in `.env` (gitignored), loaded by `.envrc`. Secrets are 1Password references run with `op run`. Never print, cat or commit `.env`.
- Never use em dashes in skills, agents or docs.
