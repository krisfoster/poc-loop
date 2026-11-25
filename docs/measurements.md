# Measurements

## How to read this

One run per variant, on one small task. The dollar figures are indicative of how the variants compare on that task, not a benchmark, and differences under about 30% are noise. The case for the loop on this evidence is independent verification and review plus repo hygiene, not a token saving.

Question: does the loop give better quality and lower token use than one plain Opus session? Short answer from one small task: it did not lower cost until harden was trimmed, and then it only came close. Treat everything here as one run per variant on one task, not as a benchmark.

## Method

A standard-library Python webhook receiver (HMAC check, replay window, size limit, a dozen specified status codes), the same spec text for every arm. Quality is a hidden 23-check suite plus an independent Opus review of each result. Usage comes from the `result` event of `claude -p --output-format stream-json`, which includes subagent models. Two bugs in my own hidden test surfaced on the first arm and were fixed, then every arm was scored with the fixed version. Some edge probes were written after I saw the reviewer's findings.

- **A**: one Opus session, no subagents, then a review.
- **B**: separate fresh sessions: start (Opus), build (Sonnet), verify (Haiku), log (Haiku), harden (Sonnet main, Opus reviewer), package (Sonnet).
- **B2**: start, build and log merged into one Sonnet session at low effort, a Sonnet reviewer without connector tools.
- **B3**: B2 plus a trimmed harden: one low-effort reviewer call capped at 12 tool calls, one packager call, no audit loop. This became the lean path.

## Results

| | A + review | B | B2 | B3 |
|---|---|---|---|---|
| Total cost | $1.17 | $3.16 | $2.56 | $1.38 |
| Output tokens | 19.8k | 67.5k | 66.6k | 24.6k |
| Cache write / read | 100k / 395k | 417k / 2.93M | 492k / 3.32M | 290k / 1.40M |
| Hidden suite | 23/23 | 23/23 | 23/23 | 23/23 |
| Two crash inputs handled | no (1 of 2) | yes | yes | yes |
| `Allow` header on 405 | no | yes | yes | no |

## What drove the cost

- Every fresh session re-pays the baseline context (tools, skills, agent lists): 55k to 90k cache-write tokens, even for a step that appends five lines.
- Harden was about 60% of B's cost. Most of the spend was output and cache writes inside the reviewer and packager subagents, not the model choice.
- The first Opus start session cost nearly as much as all of A's build.

## Caveats

- One run each, on a small task where a plain session finishes in seven turns, so there was no long context for subagents to protect.
- Build cost varied about 30% between runs, so smaller differences are noise.
- B3 stopped at the review gate on a finding that also applies to A and B. It was packaged afterwards, so add about $0.05 for a like-for-like total.
- The cheaper reviewer had no web tools and low effort, and it reviewed different code, so its recall against the other arms is unknown.

The argument for the loop on this evidence is independent verification and review, and repo hygiene, not a token saving. A longer task is the next test.
