# Phase 2, step 3: Advisor proposals for this idea

Source: **model** (qwen3:4b). Label for every item: ASSUMPTION (proposed by qwen3:4b; not evidence).
These are specific proposals to test, not evidence. Items that failed VentureLab's content
or non-leading rules were dropped by code: interview question: What would you do if you could get a summary of a Slack thread without reading i.

- Riskiest assumption: Remote engineers and product managers on distributed teams miss important Slack messages in long threads
- Proposed stop rule (decide before testing): Stop if fewer than 5 of 10 interviewees missed at least one important Slack message in the last week
- Value proposition: Get important Slack messages without having to read long threads they missed.
- Key metric: Percentage of interviewees who missed at least one important Slack message in the last week
- Price anchor: Current time spent manually scanning Slack threads for missed messages; test prices per month: €5, €10, €15. The price points are anchored to the time spent by remote engineers and product managers manually scanning Slack threads for missed messages, which is a common workaround for this problem. These prices are low enough to test willingness to pay without committing to a full product launch.
- Launch angle: Focus on the immediate problem of missed messages in Slack threads for remote teams

## What these customers likely use today (verify in interviews)

- Manually scanning Slack threads for missed messages
- Using Slack's built-in search to find messages
- Relying on teammates to share summaries

## Channels to recruit interviewees and launch

- **r/remoteengineering**: Active community of remote engineers discussing Slack workflow challenges
- **Slack channel #product-managers**: Dedicated Slack space for product managers to share workflow tips and pain points
- **The Remote Work newsletter**: Monthly email for remote software teams on communication tools and productivity

## Interview questions (past behaviour, checked for leading wording)

1. Tell me about the last time you missed an important Slack message in a long thread?
2. How much time did you spend scanning Slack threads to find messages you missed?
3. What did you do after you realized you missed an important message?
4. How often do you miss important messages in Slack threads?
