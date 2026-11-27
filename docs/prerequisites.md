# Prerequisites

What the Spike Loop commands need on your machine, how each is checked, and how to install it. The source of truth is the checker, `scripts/check-prereqs`; a test keeps this page in step with it. Design: `docs/prereqs/spec.md`.

Each command that needs a tool runs the checker as its first step. A missing **required** tool stops the command before it changes anything, with a message naming what to install and a `Next:` line. A missing **optional** tool skips only the step that uses it, and the command says so.

| Tool | Required? | Used by | For | Check | Install |
|---|---|---|---|---|---|
| `git` | required | every command except `poc-sources`, and every agent | finding the repo root and reading its state | `git --version` | macOS: `xcode-select --install` or `brew install git`; Debian or Ubuntu: `sudo apt install git`; Windows: install Git for Windows (https://git-scm.com/download/win) |
| `python3` | required for `poc-research` and `poc-sources`, optional for `poc-log` | `poc-research`, `poc-sources`, `poc-log` | the research sources helper; the `poc-log` time check (skipped without it) | `python3` runs and is 3.9 or later | macOS: `xcode-select --install` or `brew install python`; Debian or Ubuntu: `sudo apt install python3`; Windows: install Python 3 from https://www.python.org and make sure `python3` runs in Git Bash |
| `rsync` | required | `poc-package`, `poc-harden` and the `packager` agent | the clean-clone test | `rsync --version` | macOS: `brew install rsync`; Debian or Ubuntu: `sudo apt install rsync`; Windows: Git for Windows does not include it, so run Claude Code in WSL or install rsync for Git Bash |
| `gitleaks` | optional | `poc-harden` and the `packager` agent | the secret scan (skipped without it) | on `PATH` | macOS: `brew install gitleaks`; Debian or Ubuntu and Windows: see https://github.com/gitleaks/gitleaks#installing |
| `typos` | optional | `poc-harden` | the spell check (skipped without it) | on `PATH` | macOS: `brew install typos-cli`; Debian or Ubuntu and Windows: see https://github.com/crate-ci/typos#install |

## Baseline

These come with a POSIX shell, so they are listed and not checked one by one: `date`, `mktemp`, `chmod`, `grep`, `ls`, `tail`, `sed`, `sh`. Claude Code runs its Bash tool in a POSIX shell on macOS and Linux, and in Git Bash on Windows when it is installed. On Windows without Git Bash, Claude Code's shell is PowerShell, where the checker cannot run: the commands say so and continue, and a command that needs a missing tool fails with its own error. Windows is untested.

## Not checked

- Tools your project needs (`docker`, `make`, `npm` and the like). `/spike-loop:poc-verify` reports a missing one as a failure.
- The Claude Code version.
