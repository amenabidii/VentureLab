# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `full`. Searches: design feedback collection, client feedback for design drafts, freelance design feedback (model). Model calls: 6. Time: 107 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 7 | https://hn.algolia.com/api/v1/search?query=design+feedback+collection&tags=comment&hitsPerPage=10 |
| hn_comments | available | 5 | https://hn.algolia.com/api/v1/search?query=client+feedback+for+design+drafts&tags=comment&hitsPerPage=10 |
| hn_comments | available | 9 | https://hn.algolia.com/api/v1/search?query=freelance+design+feedback&tags=comment&hitsPerPage=10 |

Relevance selection: 21 comments retrieved, 0 set aside as off-topic (fewer than two key words shared with the brief), 8 analysed. Key words: app, collect, customer, design, designer, draft, feedback, freelanc, graphic, pinn, plac, scatter, shar, wast, web, wher.

## Customer problem and segment findings

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F1** [customer_problem, statement] One freelance web designer says they lose 2-3 days of time to design the initial draft
  - Needs review: wording goes beyond the quoted text: freelance, web, designer, days, initial
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > They lose nothing but time (the 2-3days I take to design the draft).  
  > Source: https://news.ycombinator.com/item?id=2138845
- **F2** [segment, statement] One freelance web designer says they work on client projects that require detailed specifications
  - Needs review: wording goes beyond the quoted text: freelance, web, designer, work, projects, require
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > The client generally gives me a detailed specification of their app or website, which details the number of screens/pages I need to design.  
  > Source: https://news.ycombinator.com/item?id=2138845


## Competitor findings (existing products; not evidence of demand)

None found.

## Demand signals (desk research can never establish demand)

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F3** [demand, statement] One freelance graphic designer says they need a tool to clear and organise feedback on design drafts
  - Needs review: wording goes beyond the quoted text: graphic, need
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > Draft is a Design Feedback tool for Freelance Designers & Small Teams that helps you clear and organise your feedback.  
  > Source: https://news.ycombinator.com/item?id=5096574


## Founder's problem statement checked against the sources

- **H1** standing: partial_evidence
  - Verdict: partially_supports; second check: not run. The quote describes Draft's purpose as a tool to help freelance designers organize feedback, which addresses the problem of scattered client feedback but doesn't explicitly confirm that users experience this problem.
  - Needs review: wording goes beyond the quoted text: experience, problem, waste, time, collecting, scattered, client
  > Draft is a Design Feedback tool for Freelance Designers & Small Teams that helps you clear and organise your feedback.  
  > Source: https://news.ycombinator.com/item?id=5096574
- **H2** standing: partial_evidence
  - Verdict: partially_supports; second check: not run. The quote describes a specific experience of the speaker as a freelance designer, but the claim states a general problem experienced by 'one commenter'. The context shows the speaker's personal experience, not a representative sample.
  - Needs review: wording goes beyond the quoted text: experience, problem, waste, time, collecting, scattered, feedback, drafts
  > After years as a freelance graphic designer, I noticed that most of my clients couldn't distinguish a good design from a better one!  
  > Source: https://news.ycombinator.com/item?id=33064987
- **H3** standing: contradicted
  - Verdict: contradicts; second check: not run. The quote states that the initial design draft shows quality work and refunds if sub-par, which contradicts the claim that freelance designers waste time collecting scattered client feedback.
  - Needs review: wording goes beyond the quoted text: experience, problem, freelance, designers, waste, time, collecting, scattered
  > The initial design draft shows the client my quality of work.  
  > Source: https://news.ycombinator.com/item?id=2138845
- **H4** standing: unsupported
  - Verdict: does_not_support; second check: not run. The context describes the founder-led process for logo design, not freelance designers' feedback collection issues.
  - Needs review: wording goes beyond the quoted text: problem, freelance, designers, waste, time, collecting, scattered, client, feedback
  > The logo design itself is almost always outsourced, but the concept and sketch are either conceived by the founders or edited by them (choosing among various draft designs).  
  > Source: https://news.ycombinator.com/item?id=20873714
