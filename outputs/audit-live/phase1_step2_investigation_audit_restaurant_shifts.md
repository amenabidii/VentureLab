# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `full`. Searches: restaurant shift coordination, staff schedule management, shift swap coordination (model). Model calls: 4. Time: 87 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 4 | https://hn.algolia.com/api/v1/search?query=restaurant+shift+coordination&tags=comment&hitsPerPage=10 |
| hn_comments | available | 6 | https://hn.algolia.com/api/v1/search?query=staff+schedule+management&tags=comment&hitsPerPage=10 |
| hn_comments | available | 4 | https://hn.algolia.com/api/v1/search?query=shift+swap+coordination&tags=comment&hitsPerPage=10 |

Relevance selection: 14 comments retrieved, 4 set aside as off-topic (fewer than two key words shared with the brief), 8 analysed. Key words: app, approv, chat, coordinat, group, independent, instead, manager, post, restaurant, shift, simpl, staff, swap, through, wast, web.

## Customer problem and segment findings

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F1** [customer_problem, statement] One user says coordinating staff shift swaps through group chats causes frustration
  - Needs review: wording goes beyond the quoted text: coordinating, staff, swaps, through, group, chats, causes, frustration
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > Crew currently consists of multiple “modules”: Messaging — Before using Crew, many of our users were using a mix of text messages and emails, with some using consumer messaging apps like WhatsApp and GroupMe.  
  > Source: https://news.ycombinator.com/item?id=9996454
  > Scheduling — Coordination around shifts is one of the top concerns in the businesses of many of our customers.  
  > Source: https://news.ycombinator.com/item?id=9996454
  > Crew makes it easy to post the shift schedule and then coordinate shift swapping when necessary.  
  > Source: https://news.ycombinator.com/item?id=9996454
- **F2** [customer_problem, off-topic] One user says using Excel for staff schedules and then emailing changes causes frustration
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > * Frustration using Excel for your staff's schedules and then emailing or texting them changes, or forgetting to email them changes?  
  > Source: https://news.ycombinator.com/item?id=24726501


## Competitor findings (existing products; not evidence of demand)

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F3** [competitor, statement] Crew costs nothing but allows users to post shift schedules and coordinate swaps
  - Needs review: wording goes beyond the quoted text: costs, nothing, allows, users, swaps
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > Crew makes it easy to post the shift schedule and then coordinate shift swapping when necessary.  
  > Source: https://news.ycombinator.com/item?id=9996454


## Demand signals (desk research can never establish demand)

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F4** [demand, topic] One user says they want to test the product and share feedback for free usage
  - Needs review: wording goes beyond the quoted text: want, free, usage
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > As such, we need a group of people from the community who are eager to test the product, share their feedback to help us make this app that best fits businesses’ and employees’ needs.  
  > Source: https://news.ycombinator.com/item?id=24726501


## Founder's problem statement checked against the sources

- **H1** standing: unsupported
  - Verdict: does_not_support; second check: not run. The quote describes Crew's feature for managing shifts, but the context shows it's a solution to the problem of wasted time coordinating shifts, not evidence that managers waste time.
  - Needs review: wording goes beyond the quoted text: experience, problem, small, managers, waste, time, coordinating, staff, swaps, through, group, chats
  > Crew makes it easy to post the shift schedule and then coordinate shift swapping when necessary.  
  > Source: https://news.ycombinator.com/item?id=9996454
- **H2** standing: unsupported
  - Verdict: does_not_support; second check: not run. The quotes describe keyboard layout issues with Windows, not restaurant staff coordination problems.
  - Needs review: wording goes beyond the quoted text: experience, problem, small, restaurant, managers, waste, time, coordinating, staff, through, group, chats
  > It doesn't help at all that Windows' default layout-switcher switches using Ctrl+Shift so any key combo that includes that pair (including select-by-word!) will swap your keyboard layout too.  
  > Source: https://news.ycombinator.com/item?id=29829125
