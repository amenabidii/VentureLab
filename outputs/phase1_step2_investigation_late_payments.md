# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `full`. Searches: late payments freelancers, unpaid invoices reminders, client payment delays freelancers (model). Model calls: 5. Time: 102 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 8 | https://hn.algolia.com/api/v1/search?query=late+payments+freelancers&tags=comment&hitsPerPage=10 |
| hn_comments | available | 5 | https://hn.algolia.com/api/v1/search?query=unpaid+invoices+reminders&tags=comment&hitsPerPage=10 |
| hn_comments | available | 5 | https://hn.algolia.com/api/v1/search?query=client+payment+delays+freelancers&tags=comment&hitsPerPage=10 |

Relevance selection: 18 comments retrieved, 0 set aside as off-topic (fewer than two key words shared with the brief), 8 analysed. Key words: app, customer, designer, developer, freelanc, freelancer, invoice, lat, pay, polit, reminder, schedul, send, show, softwar, struggl, unpaid, usually, web, which.

## Customer problem and segment findings

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F1** [customer_problem, statement] One user says freelancers often experience late payments for invoices.
  - Needs review: wording goes beyond the quoted text: freelancers, often, experience, invoices
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > I've experienced late payments multiple times myself, so a built-in solution with multiple payment options should be a no-brainer for the client.  
  > Source: https://news.ycombinator.com/item?id=42853373
- **F2** [customer_problem, off-topic] One user says it takes time and effort to align clients and designers on project scope and style.
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > It takes time and effort to get clients and designers on the same page regarding design style and project scope.  
  > Source: https://news.ycombinator.com/item?id=41748040
- **F3** [segment, statement] Freelancers and solopreneurs use PayPrompt to automate invoice creation and payment reminders.
  - Needs review: wording goes beyond the quoted text: use
  - Needs review: a claim about people must be attributed to one person ("One host says ...")
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > I’m building PayPrompt, a simple but powerful tool for freelancers and solopreneurs to automate invoice creation and payment reminders.  
  > Source: https://news.ycombinator.com/item?id=43381182


## Competitor findings (existing products; not evidence of demand)

### Established (verified quote, supported, confirmed, wording checked)

- **F4** [competitor, statement] dotbrand automates early client communication for designers and agencies to align project expectations.
  - Verdict: supports; second check: agreed. The quote describes dotbrand automating early client communication to align expectations, matching the claim exactly.
  > dotbrand solves this by automating the early stages of client communication (before the down payment), helping designers and agencies gather key information, align project expectations, and send reports to both the client and the design team before investing a lot of time.  
  > Source: https://news.ycombinator.com/item?id=41748040


## Demand signals (desk research can never establish demand)

None found.

## Founder's problem statement checked against the sources

- **H1** standing: partial_evidence
  - Verdict: partially_supports; second check: not run. The quotes describe a freelancer's experience with late payments and accepting lost billable time due to client bankruptcy, but the context shows this is a personal example of risk acceptance, not a general struggle with timely payments.
  - Needs review: wording goes beyond the quoted text: freelancers, struggle, get, invoices
  - Needs review: a claim about people must be attributed to one person ("One host says ...")
  > Click start on the timer at the beginning of the call, click stop when you've ended the call, create invoice, add time entry, send to client (via email through Harpoon).  
  > Source: https://news.ycombinator.com/item?id=19747211
  > I might hound Joe down the street for that $10 he never paid me back for the rest of my days, but I can accept losing a few days of billable time because my client went bankrupt and can't pay me.  
  > Source: https://news.ycombinator.com/item?id=5877610
