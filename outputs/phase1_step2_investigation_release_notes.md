# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `full`. Searches: release notes automation, changelog writing time, small team release notes (model). Model calls: 7. Time: 109 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 10 | https://hn.algolia.com/api/v1/search?query=release+notes+automation&tags=comment&hitsPerPage=10 |
| hn_comments | available | 10 | https://hn.algolia.com/api/v1/search?query=changelog+writing+time&tags=comment&hitsPerPage=10 |
| hn_comments | available | 6 | https://hn.algolia.com/api/v1/search?query=small+team+release+notes&tags=comment&hitsPerPage=10 |

Relevance selection: 26 comments retrieved, 3 set aside as off-topic (fewer than two key words shared with the brief), 8 analysed. Key words: app, compani, customer, developer, draft, edit, fac, manager, merg, product, publish, pull_request, release_notes, saa, softwar, team, web, writ.

## Customer problem and segment findings

### Established (verified quote, supported, confirmed, wording checked)

- **F1** [customer_problem, statement] One user says they hand write release notes and copy-paste version numbers for each release.
  - Verdict: supports; second check: agreed. The quote directly states the user hands writes release notes and copies version numbers, matching the claim exactly.
  > I hand write the release notes, copy and paste the version number, and select date for each release (sometimes I'll batch add them if I get behind).  
  > Source: https://news.ycombinator.com/item?id=46279042
- **F3** [segment, statement] One user says they use GitHub generated release notes from Pull Request bodies for their dev team.
  - Verdict: supports; second check: agreed. The quote directly states that the user uses GitHub generated release notes from Pull Request bodies for their dev team, matching the claim exactly.
  > I use Github generated release notes based on Pull Request bodies and this is more than sufficient for my dev team.  
  > Source: https://news.ycombinator.com/item?id=46279042

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F2** [customer_problem, off-topic] One user says they hand author release notes in a Django admin for a /release-notes/ page.
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > Clicking that takes the user to a /release-notes/ page that has a descending order list of the notes that I hand author in the Django admin.  
  > Source: https://news.ycombinator.com/item?id=46279042
- **F4** [customer_problem, off-topic] One user says they have to manually check release notes for accuracy before publishing.
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > Because of this it's tricky to fully automate the process as at some level you usually need a person casting an eye over the release note just to sense check.  
  > Source: https://news.ycombinator.com/item?id=46597069


## Competitor findings (existing products; not evidence of demand)

None found.

## Demand signals (desk research can never establish demand)

None found.

## Founder's problem statement checked against the sources

- **H1** standing: partial_evidence
  - Verdict: partially_supports; second check: not run. The quote states that using GitHub-generated release notes from PRs is sufficient for the speaker's small dev team, but the context specifies it's for internal apps, not public SaaS, so it doesn't directly address the claim about small software teams in general.
  - Needs review: wording goes beyond the quoted text: spend, too, much, time, writing, changelogs
  - Needs review: a claim about people must be attributed to one person ("One host says ...")
  > I use Github generated release notes based on Pull Request bodies and this is more than sufficient for my dev team.  
  > Source: https://news.ycombinator.com/item?id=46279042
