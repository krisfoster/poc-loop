# Setting up and updating research sources

The researcher can read your internal documents (wiki, drive, chat, email, meeting notes, local repos), but only the ones you allow. Two things control that, and they are kept apart on purpose.

| What | Where | Who changes it | Effect |
|---|---|---|---|
| **Where documents live**: notes on which pages, folders, channels and repos to search first, and which source wins when two disagree | `~/.config/spike-loop/research-sources.md` (set `SPIKE_LOOP_CONFIG` to move it) | You, by hand or with `/spike-loop:poc-sources add`. Plain text. | Steers the search. Cannot grant access. |
| **Which connector tools the researcher may call** | The `tools:` line of `~/.claude/agents/researcher-internal.md` | Only `/spike-loop:poc-sources`, with your explicit yes per connector | Grants access. Read-only tools only. |

Both live outside the plugin and outside any repo, so nothing about your workspace is ever committed or shared.

## When does setup happen

There is no install step, because a plugin cannot run an interactive step at install and what to allow depends on the connectors you have connected. Setup happens the first time you need it:

1. Install the plugin. `/spike-loop:poc-research <question>` works straight away on public sources.
2. On first use it notices internal sources are not set up and offers to stop so you can run `/spike-loop:poc-sources`. About five minutes.
3. Or run `/spike-loop:poc-sources` right after installing, if you already know you want it.

## First-time setup

Run `/spike-loop:poc-sources`. It:

1. Creates the sources file from a template, if it does not exist. It never overwrites one.
2. Lists the MCP tools your session can see and sorts them by their names into three buckets: **read** (get, list, search, read, query, fetch and similar), **review** (generic "run" or "execute" tools, downloads, anything it cannot place) and **write** (create, update, delete, send, share and similar). Write tools are only counted, never offered.
3. Asks which connectors the researcher may read. Review-bucket tools are asked about one by one, with "no" recommended.
4. Asks where your documents live and writes your answers into the sources file under headings you can edit later.
5. Generates `~/.claude/agents/researcher-internal.md` with exactly the tools you approved, plus Read, Bash, WebFetch, WebSearch and ToolSearch. The agent has no Edit or Write tool.
6. Reminds you to **restart Claude Code**. Agents created while a session is running are not picked up until the next start.

After the restart, `/spike-loop:poc-research` uses `researcher-internal` automatically.

### Permission prompts on first use

Allowing a tool in the agent file makes it available to the researcher, but Claude Code still asks for permission the first time each connector tool is used, as for any tool. Allow the read tools when prompted, or add them to your own permission settings. Write tools are never in the agent, so there is nothing to approve for them.

## Updating later

| You want to | Run | Restart needed |
|---|---|---|
| Record a new place to search, or a moved or retired one | `/spike-loop:poc-sources add <note>`, or edit the sources file directly | No. The researcher reads the file at the start of every question. |
| See what is configured, and whether connectors changed | `/spike-loop:poc-sources status` | No |
| Add a newly connected tool, drop a disconnected one, or change what the researcher may call | `/spike-loop:poc-sources refresh` | Yes |
| Start again from scratch | Delete `research-sources.md` and `researcher-internal.md`, then run `/spike-loop:poc-sources` | Yes |

`refresh` compares the tools your session can see now against the ones in the generated agent, shows what is gone and what is new, asks you about the new ones, and regenerates the agent. Run it after you connect or disconnect a connector, or if a connector changes its tool names.

### The sources file

It is plain Markdown. Keep entries short and specific, for example a page title plus what it holds, a channel name plus what it is for, an absolute path plus what is in it. The last section, **Priority and freshness notes**, is where you say which source wins ("the handbook beats old chat threads", "this page is out of date"). The researcher always checks last-modified dates and prefers the newest source anyway, and flags anything over 90 days old.

Never put credentials, tokens or private customer data in it.

## Safety properties

- A write-class tool can never be added. `render-agent` refuses a list that contains one, even if you ask, and it only edits a file it generated itself (marked with a comment) unless you force it.
- The classifier works on tool names, so it is a safety net and not a guarantee. It errs towards excluding (a read tool whose name contains a write word is held back). You approve every tool.
- If a connector later renames or adds tools, nothing is granted automatically. `refresh` shows the difference.
- The sources file cannot grant access, so a typo or a pasted instruction in it changes only what the researcher searches.

## Troubleshooting

- **`researcher-internal` is unknown**: restart Claude Code after setup or refresh. `/spike-loop:poc-research` falls back to the public researcher and says so.
- **A connector's tools are not listed**: the connector may be disconnected or its tools deferred. Reconnect it, then run `/spike-loop:poc-sources refresh`.
- **The agent file was edited by hand or came from elsewhere**: the helper refuses to overwrite a file it did not generate. Move it aside or use `--force` when calling the helper directly.
- **See what is configured**: run `/spike-loop:poc-sources status`. When working in a clone of the repo you can also run `python3 skills/poc-sources/scripts/spike_sources.py status`, and the tests are in `tests/`.

## Limits of "read-only"

The generated agent cannot call any write-class connector tool and has no Edit or Write tool. It does keep `Bash`, `WebFetch` and `WebSearch`. Text it reads in an email, chat message or document could try to talk it into sending internal content to an outside URL or writing a local file, and only the agent's prompt rules stand in the way. Keep the connector list to sources you trust. If you want a stricter agent, remove `Bash`, `WebFetch` and `WebSearch` from the `tools:` line of a copy you maintain yourself (the helper will refuse to overwrite it).
