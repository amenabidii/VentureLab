# Phase 1, step 4: Opportunity scorecard

Discover gate: **REPEAT** (run `run-a9f21cd634924cca`). No option has established evidence; the ranking only orders what to test first.

Against what customers use today: The founder's idea scores 1; the 3 alternatives customers use today score 0, 0, 0. They are ASSUMPTIONS from the advisor: the idea is only worth building if interviewees describe real costs with these alternatives.

| # | Option | Origin | Evidence | Founder fit | Open risks | Score | Sources |
|---|---|---|---|---|---|---|---|
| 1 | A browser extension that summarises long Slack threads a remote team member missed, linking each point back to the original message. | founder's idea (FOUNDER-STATED) | 1 | 2 | 2 | **1** | https://news.ycombinator.com/item?id=36434999, https://news.ycombinator.com/item?id=20896857, https://news.ycombinator.com/item?id=25056920 |
| 2 | Remote teams might prefer solutions that reduce meeting time over summarizing Slack threads | raised by the Challenger (UNCONFIRMED (needs review)) | 1 | 1 | 2 | **0** | https://news.ycombinator.com/item?id=20896857 |
| 3 | Current alternative: Manually scanning Slack threads for missed messages | what customers use today, ASSUMPTION (proposed by qwen3:4b; not evidence) | 0 | 0 | 0 | **0** | — |
| 4 | Current alternative: Using Slack's built-in search to find messages | what customers use today, ASSUMPTION (proposed by qwen3:4b; not evidence) | 0 | 0 | 0 | **0** | — |
| 5 | Current alternative: Relying on teammates to share summaries | what customers use today, ASSUMPTION (proposed by qwen3:4b; not evidence) | 0 | 0 | 0 | **0** | — |
| 6 | Status quo: target customers keep their current workaround | baseline | 0 | 0 | 0 | **0** | — |

Test first: **A browser extension that summarises long Slack threads a remote team member missed, linking each point back to the original message.**

## Rubric (fixed, deterministic)

- `problem_evidence`: 2 = at least one ESTABLISHED finding cited; 1 = only NEEDS_REVIEW or partial findings with verified quotes; 0 = no sourced finding
- `founder_fit`: 2 = the founder's own idea built with the stated skills; 1 = plausible with the stated skills but unconfirmed (ASSUMPTION); 0 = no product to build
- `open_risks`: minus 1 for each unresolved Challenger market risk; market risks apply equally to every product option, not to the status quo or to what customers use today (total not below 0)
- `current_alternatives`: what the target customers use today, proposed by the advisor (ASSUMPTION): scored with the same rubric; founder fit 0 because the founder does not build it; evidence counts only if a verified finding cites it, otherwise 0

## Market definition

- Customer: remote engineers and product managers on distributed teams (FOUNDER-STATED)
- Market: Online, English-speaking remote software teams (FOUNDER-STATED)
- Size: UNKNOWN — no sourced market-size figure; none is estimated
