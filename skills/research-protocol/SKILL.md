---
name: research-protocol
description: Rules for researching public and internal facts from primary sources with freshness checks, citations and privacy. Preloaded into the researcher, reviewer and debugger agents. Use when answering a factual question about a library, API, product, internal document, local repo or deal, or when asked to "research" or "check the latest".
---

# research-protocol

Follow these in order. Keep the final answer inside the calling agent's length cap.

## 1. Choose the source class first
- **Public** (libraries, APIs, CLIs, vendor products): if your tools include Context7 (`resolve-library-id`, then `query-docs`), your first tool calls MUST be those. Only after that returns, and only for what it lacks, use WebFetch or WebSearch, starting at the vendor's own docs. If Context7 has no entry for the library, say so in the answer. If you have no Context7 tools, start at the vendor's own docs. Skipping Context7 when you have it is a protocol failure even when the web answer is right.
- **Internal** (wiki, drive, chat, email, meeting notes): read the user's research-sources file first (`~/.config/spike-loop/research-sources.md`, or the path your agent prompt gives). It says where documents live and which source wins. Search those places with the connector tools you have. If you have no connector tools or the file is missing, say internal sources are not configured, point at `/spike-loop:poc-sources`, and do not answer an internal question from public docs.
- **Local code and notes**: the paths listed in the sources file, plus the repo at its root. Read and `grep`, plus read-only git.

## 2. Prefer primary sources
Vendor docs, release notes, source code and the original document beat blog posts, forum answers and summaries. State the version or date of everything you cite.

## 3. Freshness
- Internal documents: read the last-modified date before using one. If several documents cover the topic, prefer the newest and name the ones it supersedes.
- Check chat and email, if you have them, for a decision newer than the document.
- Local clone: run `git fetch` (read-only against the remote), then report commits behind and the last commit date before relying on it.
- Anything older than 90 days is `POSSIBLY STALE`. Never present stale information as current.

## 4. Privacy
Queries sent to external services (Context7, WebSearch, URLs given to WebFetch) must not contain customer names, internal project names, personal details or credentials. Generalise first: ask about the product behaviour, not the customer's setup.

## 5. Cite every claim
URL or path, plus a date or version. Anything you could not confirm from a source is `NOT STATED`. No half-theories: if you have not read it, do not assert it.

## 6. Answer first
Lead with the answer, then the snippet or syntax, then the source list. Stay inside the cap.

## Never
- Read `.env` files or quote secrets.
- Use any tool that writes to a wiki, drive, chat, email, meeting-notes tool, CRM or calendar. If a task needs one, return it as a proposed action instead.
