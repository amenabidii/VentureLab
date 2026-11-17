# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `full`. Searches: slack missed messages summary, remote team slack thread catchup, distributed team slack messages missed (model). Model calls: 5. Time: 118 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 5 | https://hn.algolia.com/api/v1/search?query=slack+missed+messages+summary&tags=comment&hitsPerPage=10 |
| hn_comments | available | 1 | https://hn.algolia.com/api/v1/search?query=remote+team+slack+thread+catchup&tags=comment&hitsPerPage=10 |
| hn_comments | empty (no comments matched the query) | 0 | https://hn.algolia.com/api/v1/search?query=distributed+team+slack+messages+missed&tags=comment&hitsPerPage=10 |

Relevance selection: 6 comments retrieved, 0 set aside as off-topic (fewer than two key words shared with the brief), 6 analysed. Key words: back, browser, catch, distribut, each, engineer, extension, link, long, manager, member, messag, miss, original, point, product, remot, slack, summaris, team, thread, wast, worker.

## Customer problem and segment findings

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F1** [customer_problem, topic] One user says Slack threads are too long to read and they miss important messages.
  - Needs review: wording goes beyond the quoted text: slack, too, long, miss, important, messages
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > Must read each message to understand if it's relevant.  
  > Source: https://news.ycombinator.com/item?id=36434999

### Partial evidence (not counted by the gate)

- **F2** [customer_problem, topic] One user says Slack messages go unanswered more often than in Teams.
  - Verdict: partially_supports; second check: not run. The quote describes personal experience with Slack messages going unanswered more than in Teams, matching the claim's specific user perspective.
  > Unfortunately, I have no such insight into Slack's back-end, but anecdotally, I am interrupted far more through Slack than I was in Teams and my messages go unanswered far more often to the point that in Teams where I positively relied on status before sending a message, I don't even look at it in Slack because it doesn't help me to decide whether or not I'll be better off picking up the phone or  
  > Source: https://news.ycombinator.com/item?id=20896857

### ASSUMPTION (no verified quote, or not assessed)

- **F3** [segment, off-topic] Remote engineers and product managers on distributed teams miss Slack threads.
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not assessed: quotation not verified
  - [UNVERIFIED, not a quotation]  (passage not shown to the model: [1])


## Competitor findings (existing products; not evidence of demand)

None found.

## Demand signals (desk research can never establish demand)

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F4** [demand, statement] People pay for a solution to reduce time spent catching up on missed Slack threads.
  - Needs review: wording goes beyond the quoted text: pay, solution, reduce, spent, catching, missed, threads
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > As of now, HBR states 71% managers find meetings unproductive, CNBC told us 67% of team members spend way too much time in meetings.
With tools like Slack, Teams and "always-on" culture, staff are constantly bombarded with pings and FOMO prevents us from stepping away from our computer, leading to really long and stretched out work hours.
This lead to zoom fatigue, team disconnects, and people gen  
  > Source: https://news.ycombinator.com/item?id=25056920


## Founder's problem statement checked against the sources

- **H1** standing: partial_evidence
  - Verdict: partially_supports; second check: not run. The quote describes a problem with Slack threads but doesn't explicitly state that remote workers waste time catching up on missed threads.
  - Needs review: wording goes beyond the quoted text: experience, problem, remote, workers, waste, catching, long
  > (And just in case you think I missed it, I did read about "intelligently" forgetting threads but that feels so hand-wavy I don't even know how to address it, and part of having the history of something like Slack is that you can realise later on that you need information you previously said, even if you didn't think it important at the time).  
  > Source: https://news.ycombinator.com/item?id=36434999
- **H2** standing: unsupported
  - Verdict: does_not_support; second check: not run. The quote describes how remote workers are overwhelmed by notifications and FOMO, but doesn't specifically mention missing Slack threads causing wasted time.
  - Needs review: wording goes beyond the quoted text: experience, problem, remote, workers, waste, catching, threads, missed
  > With tools like Slack, Teams and "always-on" culture, staff are constantly bombarded with pings and FOMO prevents us from stepping away from our computer, leading to really long and stretched out work hours.  
  > Source: https://news.ycombinator.com/item?id=25056920
