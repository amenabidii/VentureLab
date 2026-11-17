# Phase 2, step 3: Advisor proposals for this idea

Source: **model** (qwen3:4b). Label for every item: ASSUMPTION (proposed by qwen3:4b; not evidence).
These are specific proposals to test, not evidence. Items that failed VentureLab's content
or non-leading rules were dropped by code: price_anchor.

- Riskiest assumption: Remote engineers and product managers spend significant time reviewing missed Slack messages
- Proposed stop rule (decide before testing): Stop if fewer than 3 of 10 interviewees reported spending more than 30 minutes per week reviewing missed Slack messages
- Value proposition: Get important Slack messages without missing them when you're not looking at the channel.
- Key metric: Time spent reviewing missed Slack messages per week
- Price anchor: None; test prices per month: €5, €10, €20. Anchor to the cost of manual message scanning in Slack (5 EUR) and third-party Slack apps (10-20 EUR) that users currently pay for
- Launch angle: Focus on reducing time spent reviewing missed Slack messages for remote engineers and product managers

## What these customers likely use today (verify in interviews)

- Manual message scanning in Slack
- Using Slack's built-in search to find missed messages
- Third-party Slack apps that summarize threads

## Channels to recruit interviewees and launch

- **r/remoteengineering**: Active community of remote engineers who use Slack daily and have experienced message overload
- **Slack Dev Community**: Dedicated Slack ecosystem users who discuss tooling and workflow improvements
- **Product Manager Slack**: Specialized group for product managers on distributed teams who face similar communication challenges

## Interview questions (past behaviour, checked for leading wording)

1. Tell me about the last time you missed an important Slack message and had to go back through the thread to find it?
2. How much time did you spend reviewing Slack messages you missed last week?
3. What did you do when you realized you missed a Slack message?
4. How often do you check Slack messages outside of work hours?
5. What tools do you use to track missed Slack messages?
