# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `full`. Searches: release notes automation, changelog writing time, small team release notes (model). Model calls: 3. Time: 79 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 10 | https://hn.algolia.com/api/v1/search?query=release+notes+automation&tags=comment&hitsPerPage=10 |
| hn_comments | available | 10 | https://hn.algolia.com/api/v1/search?query=changelog+writing+time&tags=comment&hitsPerPage=10 |
| hn_comments | available | 7 | https://hn.algolia.com/api/v1/search?query=small+team+release+notes&tags=comment&hitsPerPage=10 |

Relevance selection: 27 comments retrieved, 1 set aside as off-topic (fewer than two key words shared with the brief), 8 analysed. Key words: app, changelog, companie, customer, developer, draft, edit, facing, manager, merged, note, product, publish, pull, release, request, saa, software, team, web, writing.

## Customer problem and segment findings

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F1** [customer_problem, statement] One user says they spend time writing release notes and changel: hand write the release notes, copy and paste the version number, and select date for each release
  - Needs review: wording goes beyond the quoted text: spend, time, writing, changel
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > I hand write the release notes, copy and paste the version number, and select date for each release (sometimes I'll batch add them if I get behind).  
  > Source: https://news.ycombinator.com/item?id=46279042
- **F2** [customer_problem, statement] One user says they spend time writing release notes and changelogs: hand write the release notes, copy and paste the version number, and select date for each release
  - Needs review: wording goes beyond the quoted text: spend, time, writing, changelogs
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > I hand write the release notes, copy and paste the version number, and select date for each release (sometimes I'll batch add them if I get behind).  
  > Source: https://news.ycombinator.com/item?id=46279042
- **F3** [segment, statement] One user says they hand write release notes for their dev team
  - Needs review: wording goes beyond the quoted text: dev, team
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > I hand write the release notes, copy and paste the version number, and select date for each release (sometimes I'll batch add them if I get behind).  
  > Source: https://news.ycombinator.com/item?id=46279042


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
