# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `quick`. Searches: release notes automation (model). Model calls: 7. Time: 73 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 10 | https://hn.algolia.com/api/v1/search?query=release+notes+automation&tags=comment&hitsPerPage=10 |

Relevance selection: 10 comments retrieved, 1 set aside as off-topic (fewer than two key words shared with the brief), 4 analysed. Key words: app, changelog, companie, customer, developer, draft, edit, facing, manager, merged, note, product, publish, pull, release, request, saa, software, team, web, writing.

## Customer problem and segment findings

### Established (verified quote, supported, confirmed, wording checked)

- **F1** [customer_problem, statement] One commenter says release notes stop being a dev artifact and become a communication channel
  - Verdict: supports; second check: agreed. The quote directly states that release notes become a communication channel when talking to users, matching the claim exactly.
  > If you're talking to users, Release notes stop being a dev artifact and become a communication channel.  
  > Source: https://news.ycombinator.com/item?id=46597069
- **F2** [customer_problem, statement] One commenter says it's tricky to fully automate release notes as a person needs to sense check the release note
  - Verdict: supports; second check: agreed. The quote explains that automation requires human sense checking, directly matching the claim about it being tricky to fully automate release notes.
  > Because of this it's tricky to fully automate the process as at some level you usually need a person casting an eye over the release note just to sense check.  
  > Source: https://news.ycombinator.com/item?id=46597069


## Competitor findings (existing products; not evidence of demand)

None found.

## Demand signals (desk research can never establish demand)

None found.

## Founder's problem statement checked against the sources

- **H1** standing: partial_evidence
  - Verdict: partially_supports; second check: not run. The quotes indicate that release notes/changelogs are automated, not human-focused, but the context shows a person translating bug reports into release notes for customers, suggesting they are human-focused.
  - Needs review: wording goes beyond the quoted text: small, teams, spend, too, much, time, writing
  - Needs review: a claim about people must be attributed to one person ("One host says ...")
  > I have never once considered conventional commits to be about human understanding, but more about automation (release notes, changelogs, and workflows).  
  > Source: https://news.ycombinator.com/item?id=48417335
  > Now she translates software engineering bug fix reports into customer-appropriate release notes for a big process-automation company.  
  > Source: https://news.ycombinator.com/item?id=31602126
