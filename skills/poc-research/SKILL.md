---
name: poc-research
description: Answers a factual question from primary sources with dates and versions. Uses your approved internal connectors once /poc-sources has set them up, and public sources otherwise. Use when the user types /poc-research followed by the question.
disable-model-invocation: true
model: sonnet
effort: low
argument-hint: "<question>"
---
# poc-research

Question: "$ARGUMENTS". Never use em dashes. If the question is empty, reply only with `NEEDS INPUT: give me the question` and stop.

1. **Check the setup.** Run `python3 "${CLAUDE_SKILL_DIR}/../poc-sources/scripts/spike_sources.py" status` and read the two lines it prints (sources file, agent).
2. **First use, no internal sources yet** (the agent is MISSING). Tell the user in two lines: public research works now, and internal sources (wiki, drive, chat, email, meeting notes, local repos) need a one-time setup of about five minutes with `/spike-loop:poc-sources`. Ask with AskUserQuestion whether to research public sources only now or stop so they can run the setup first. If they stop, finish there. If they continue, do step 3 with `spike-loop:researcher`, and do not ask again in this session. If you cannot ask (a non-interactive run), continue with `spike-loop:researcher` and end your reply with one line: `Internal sources are not set up: run /spike-loop:poc-sources once.`
3. **Research.** Call the Agent tool once. Use subagent `researcher-internal` when the status shows it exists, otherwise `spike-loop:researcher`. If the call says `researcher-internal` is unknown, the user has not restarted since setup: say so and use `spike-loop:researcher` for this question. Pass the question verbatim, say it has no conversation history, and tell it to follow the research-protocol skill and its output contract. Remind it to keep customer names out of outbound queries.
4. **Report.** Show the agent's answer as returned. If it says internal sources are not configured, point at `/spike-loop:poc-sources`.
