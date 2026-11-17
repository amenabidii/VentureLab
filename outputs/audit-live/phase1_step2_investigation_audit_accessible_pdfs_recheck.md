# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `full`. Searches: pdf accessibility screen reader, inaccessible pdfs blind users, pdf to html screen reader friendly (model). Model calls: 2. Time: 45 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 10 | https://hn.algolia.com/api/v1/search?query=pdf+accessibility+screen+reader&tags=comment&hitsPerPage=10 |
| hn_comments | empty (no comments matched the query) | 0 | https://hn.algolia.com/api/v1/search?query=inaccessible+pdfs+blind+users&tags=comment&hitsPerPage=10 |
| hn_comments | available | 2 | https://hn.algolia.com/api/v1/search?query=pdf+to+html+screen+reader+friendly&tags=comment&hitsPerPage=10 |

Relevance selection: 12 comments retrieved, 1 set aside as off-topic (fewer than two key words shared with the brief), 8 analysed. Key words: blind, convert, document, friendly, html, inaccessibl, into, low, pdf, read, reader, screen, struggl, tool, user, vision, web, who.

## Customer problem and segment findings

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F1** [customer_problem, statement] One user says they flip between PDF pages to read text and check figures
  - Needs review: wording goes beyond the quoted text: flip, check
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > Think of the number of times you've flipped between pages of a PDF to read text and look at the figure described.  
  > Source: https://news.ycombinator.com/item?id=4610922
- **F2** [customer_problem, off-topic] One user says they open the same document twice to compare side-by-side
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > Sometimes I end up opening the same document twice and putting them on my screen side-by-side.  
  > Source: https://news.ycombinator.com/item?id=4610922
- **F3** [segment, off-topic] Screen readers for the blind should extract text for accessibility
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > Screen readers for the blind should be able to extract the text.  
  > Source: https://news.ycombinator.com/item?id=17549787
- **F4** [segment, off-topic] Screen reader users need accessibility for PDF documents
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > That's important for accessibility, particularly for screen reader users.  
  > Source: https://news.ycombinator.com/item?id=34431828


## Competitor findings (existing products; not evidence of demand)

None found.

## Demand signals (desk research can never establish demand)

None found.

## Founder's problem statement checked against the sources

No passage shared two key words with the problem statement.
