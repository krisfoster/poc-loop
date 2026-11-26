---
name: poc-sources
description: Sets up or updates the internal document sources the researcher may use (wiki, drive, chat, email, meeting notes, local repos). Finds the read-only connector tools you have, asks which to allow, records where your documents live, and generates a read-only researcher-internal agent. Use when the user types /poc-sources for first-time setup, to add or remove a source, or after connectors change.
disable-model-invocation: true
model: sonnet
effort: medium
argument-hint: "[setup | status | refresh | add <note>]"
---
# poc-sources

Arguments: "$ARGUMENTS". Never use em dashes in anything you write. This skill changes only two things: the user's sources file and one generated agent file. It never edits any other file.

Helper (standard library Python): `python3 "${CLAUDE_SKILL_DIR}/scripts/spike_sources.py"`. Call it `HELPER` below. Where things live:
- Sources file: `~/.config/spike-loop/research-sources.md` (override with `SPIKE_LOOP_CONFIG`). Plain notes on where documents live. Outside every repo on purpose, so it is never committed.
- Agent file: `~/.claude/agents/researcher-internal.md`, generated. It holds the approved tool list. Never edit it by hand: re-run this skill.

Two rules that do not bend. You never approve a tool for the user: every connector and every ambiguous tool is the user's explicit yes. And write-class tools (create, update, delete, send, share and similar) are never offered, so the researcher cannot change anything in a connector.

## Choose the mode
- Empty, `setup`, or the sources file does not exist: **Setup**.
- `status`: run `HELPER status` and show it. Stop, ending with `Next:` set to `/spike-loop:poc-sources` when the agent is MISSING, otherwise `/spike-loop:poc-research <question>`.
- `refresh`: **Refresh**.
- `add <note>`: **Add a note**.

## Setup
1. `HELPER init-sources` (creates the template if absent, never overwrites). Tell the user the path.
2. **Discover tools.** Write every MCP tool name you can see, one per line, to a temp file (`mktemp`). Include names in the deferred-tools list as well as loaded ones. Never invent a name. If you see none, say there are no connectors, skip to step 5 and set up notes for local repos only.
3. `HELPER classify --file <tmp>`. For each server, name the product from its tool names (for example a server with `notion-fetch` is Notion; say "looks like" when unsure) and show the read tools and the review tools. For write tools show only the count.
4. **Ask which to allow.** Use AskUserQuestion, one question per batch of up to four servers, with multiSelect, so the user picks the connectors the researcher may read. Then show any review-bucket tool (dispatchers such as run or execute, downloads) of the chosen servers and ask about them one by one, with "no" as the recommended answer. Collect the approved names, exactly as printed, one per line, in a second temp file.
5. **Where documents live.** Ask the user, in one short round, for starting points per source type: wiki pages or databases, drive folders, chat channels, email labels or meeting series, local repos or notes folders (absolute paths), and which source wins when two disagree. Skip any type they have no connector for. Edit the sources file to add what they said under the matching headings, keeping the existing entries and the headings, and show the result. Never write a credential or token into it.
6. **Generate the agent.** Only after the user approved a tool list (it may be empty): `HELPER render-agent --approved <second tmp file>`. If it exits 2, report why and stop. Relay its output, including the restart note.
7. **Finish.** Say what was recorded, that the researcher can read but never write, that a restart of Claude Code is needed before `researcher-internal` appears, and that `/spike-loop:poc-research <question>` will then use it. Remove the temp files. End with `Next: restart Claude Code, then run /spike-loop:poc-research <question>`.

## Refresh (after connectors change, or sources moved)
1. Write the visible MCP tool names to a temp file as in Setup step 2, then `HELPER status --file <tmp>`.
2. Report approved tools that are gone and new read-class tools. Ask which new ones to add (same rules as Setup step 4) and whether to drop the gone ones.
3. Offer to update the sources file for moved or retired locations. Show the edit before making it.
4. Re-run `HELPER render-agent` with the full approved list (the old approved tools minus drops, plus additions). The old list is in the `tools:` line of the generated agent file, as names starting `mcp__`. Remind the user to restart, and end with `Next: restart Claude Code, then run /spike-loop:poc-research <question>`.

## Add a note
Append the note to the matching section of the sources file with Edit and show the line. No agent change and no restart is needed, because the researcher reads this file at the start of each question. If the note implies a new connector (for example "also search Slack"), say that this needs `/poc-sources refresh`. End with `Next: /spike-loop:poc-research <question>` (or `/spike-loop:poc-sources refresh` for a new connector).

## Never
- Approve, add or widen a tool without the user's explicit yes.
- Offer or include a write-class tool, or hand-edit the generated agent file.
- Put credentials, tokens, or private customer data in the sources file.
- Commit the sources file anywhere.
