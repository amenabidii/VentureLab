# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `full`. Searches: pdf accessibility screen reader, inaccessible pdfs screen reader, pdf to html accessibility screen reader (model). Model calls: 7. Time: 131 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 10 | https://hn.algolia.com/api/v1/search?query=pdf+accessibility+screen+reader&tags=comment&hitsPerPage=10 |
| hn_comments | available | 9 | https://hn.algolia.com/api/v1/search?query=inaccessible+pdfs+screen+reader&tags=comment&hitsPerPage=10 |
| hn_comments | available | 6 | https://hn.algolia.com/api/v1/search?query=pdf+to+html+accessibility+screen+reader&tags=comment&hitsPerPage=10 |

Relevance selection: 24 comments retrieved, 1 set aside as off-topic (fewer than two key words shared with the brief), 8 analysed. Key words: blind, convert, document, friendly, html, inaccessibl, into, low, pdf, read, reader, screen, struggl, tool, user, vision, web, who.

## Customer problem and segment findings

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F1** [customer_problem, statement] One user says PDFs are not formatted properly, making them inaccessible to screen reader users
  - Needs review: wording goes beyond the quoted text: making, users
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > Many documents were inaccessible to individuals with vision disabilities who use screen readers because the document was not formatted properly.  
  > Source: https://news.ycombinator.com/item?id=13809215
  > Individuals with vision disabilities who use screen readers would have a difficult time understanding and navigating the content.  
  > Source: https://news.ycombinator.com/item?id=13809215
- **F2** [customer_problem, off-topic] One user says screen readers have difficulty understanding and navigating content in inaccessible PDFs
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > Individuals with vision disabilities who use screen readers would have a difficult time understanding and navigating the content.  
  > Source: https://news.ycombinator.com/item?id=13809215
- **F3** [customer_problem, topic] One user says PDFs are generally not helpful to accessibility tools compared to HTML
  - Needs review: wording goes beyond the quoted text: compared
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > (It's been my experience that PDFs are generally not as helpful to accessibility tools as HTML or similar formats can be, as well.)  
  > Source: https://news.ycombinator.com/item?id=41681398
- **F4** [segment, statement] Individuals with vision disabilities who use screen readers struggle with inaccessible PDFs
  - Needs review: wording goes beyond the quoted text: struggle
  - Needs review: a claim about people must be attributed to one person ("One host says ...")
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > Many documents were inaccessible to individuals with vision disabilities who use screen readers because the document was not formatted properly.  
  > Source: https://news.ycombinator.com/item?id=13809215
  > Individuals with vision disabilities who use screen readers would have a difficult time understanding and navigating the content.  
  > Source: https://news.ycombinator.com/item?id=13809215
  > Some links were not keyboard accessible and did not indicate whether they were expandable or collapsible, so individuals with vision disabilities who use screen readers may not understand the purpose of the links and individuals with manual disabilities would not be able to use the links.  
  > Source: https://news.ycombinator.com/item?id=13809215


## Competitor findings (existing products; not evidence of demand)

None found.

## Demand signals (desk research can never establish demand)

None found.

## Founder's problem statement checked against the sources

- **H1** standing: needs_review
  - Verdict: supports; second check: agreed. The quote describes specific accessibility issues in PDFs that screen readers face, directly supporting the claim about screen reader users struggling with inaccessible PDFs.
  - Needs review: wording goes beyond the quoted text: experience, problem, users, struggle, read, pdf
  - Note: second check skipped: this claim cannot be established whatever it says
  > Many documents were inaccessible to individuals with vision disabilities who use screen readers because the document was not formatted properly.  
  > Source: https://news.ycombinator.com/item?id=13809215
- **H2** standing: needs_review
  - Verdict: supports; second check: agreed. The quote explicitly states that character substitution makes documents inaccessible to screen readers, directly supporting the claim about screen reader users struggling with inaccessible PDFs.
  - Needs review: wording goes beyond the quoted text: experience, problem, users, struggle, read
  - Note: second check skipped: this claim cannot be established whatever it says
  > (Another renderer is displaying it correctly.) Using character substitution as a standard technique is a really bad idea, and is the only thing that is preventing me from taking a deeper look at it with a view to using it as a backend for a play script/musical/opera libretti format that I wrote; it makes the document inaccessible to things like screen readers and prevents ready copying of text  
  > Source: https://news.ycombinator.com/item?id=6671934
- **H3** standing: unsupported
  - Verdict: does_not_support; second check: not run. The quote states there are many inaccessible PDFs needing remediation, but the claim is about screen reader users struggling with them, not the existence of such PDFs.
  - Needs review: wording goes beyond the quoted text: experience, problem, users, struggle, read
  > The web already has enough untagged, inaccessible PDFs to provide no shortage of work for multiple document remediation businesses, including my own.  
  > Source: https://news.ycombinator.com/item?id=31272485
