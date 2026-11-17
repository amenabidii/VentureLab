# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `quick`. Searches: release notes automation (model). Model calls: 4. Time: 51 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 10 | https://hn.algolia.com/api/v1/search?query=release+notes+automation&tags=comment&hitsPerPage=10 |

Relevance selection: 10 comments retrieved, 3 set aside as off-topic (fewer than two key words shared with the brief), 4 analysed. Key words: app, compani, customer, developer, draft, edit, fac, manager, merg, product, publish, pull_request, release_notes, saa, softwar, team, web, writ.

## Customer problem and segment findings

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F1** [customer_problem, off-topic] One user says release notes stop being a dev artifact and become a communication channel
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > If you're talking to users, Release notes stop being a dev artifact and become a communication channel.  
  > Source: https://news.ycombinator.com/item?id=46597069


## Competitor findings (existing products; not evidence of demand)

### Partial evidence (not counted by the gate)

- **F2** [competitor, topic] One user says an AI agent could spend a lot of time writing v1 code, having it fail and iterate to v2 and then to v3
  - Verdict: partially_supports; second check: not run. The quote directly states that an AI agent could spend time writing v1 code, failing, and iterating to v2 and v3 due to unclear version boundaries.
  > If anyone wants to use an AI agent to try out PyInfra - One issue I've faced is that PyInfra was rearchitected in v2 (and some more in v3?) but what belongs in v1 vs v2 vs v3 isn't very clear, so an AI agent could spend a lot of time writing v1 code, having it fail and iterate to v2 and then to v3.  
  > Source: https://news.ycombinator.com/item?id=48009158


## Demand signals (desk research can never establish demand)

None found.

## Founder's problem statement checked against the sources

- **H1** standing: partial_evidence
  - Verdict: partially_supports; second check: not run. The quote shows one person's experience with writing release notes, but the claim is about small software teams generally.
  - Needs review: wording goes beyond the quoted text: small, teams, spend, too, much, time, writing, changelogs
  - Needs review: a claim about people must be attributed to one person ("One host says ...")
  > Now she translates software engineering bug fix reports into customer-appropriate release notes for a big process-automation company.  
  > Source: https://news.ycombinator.com/item?id=31602126
