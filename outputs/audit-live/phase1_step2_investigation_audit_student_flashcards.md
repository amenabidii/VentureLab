# Phase 1, step 2: Investigation

Model: `qwen3:4b` (local, via Ollama), effort `full`. Searches: lecture slides exam review, university slides study help, exam prep slide review (model). Model calls: 6. Time: 106 s.
Every quotation below was copied from the retrieved source by code, not written by the model, and cites the comment or page it came from. Only established findings about the founder's problem statement count as evidence.

## Sources

| Kind | Status | Items | Source |
|---|---|---|---|
| hn_comments | available | 7 | https://hn.algolia.com/api/v1/search?query=lecture+slides+exam+review&tags=comment&hitsPerPage=10 |
| hn_comments | available | 3 | https://hn.algolia.com/api/v1/search?query=university+slides+study+help&tags=comment&hitsPerPage=10 |
| hn_comments | available | 5 | https://hn.algolia.com/api/v1/search?query=exam+prep+slide+review&tags=comment&hitsPerPage=10 |

Relevance selection: 14 comments retrieved, 1 set aside as off-topic (fewer than two key words shared with the brief), 8 analysed. Key words: app, befor, effectively, exam, flashcard, into, lectur, prepar, repetition, review, slid, spac, struggl, student, turn, university, web.

## Customer problem and segment findings

### Needs review (kept with its quote; wording, attribution or relevance is uncertain)

- **F1** [customer_problem, statement] One user says they spend hours watching long video lectures before finals to understand sparse PDF slides and decipher friends' notes.
  - Needs review: wording goes beyond the quoted text: understand
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > I was spending hours watching long video lectures before finals, trying to make sense of sparse PDF slides, or deciphering the ancient hieroglyphs in my friends' (or my own) notes.  
  > Source: https://news.ycombinator.com/item?id=45532727
- **F2** [customer_problem, statement] One user says they struggle to explain certain concepts during lectures because they didn't make the slides.
  - Needs review: wording goes beyond the quoted text: because
  - Note: not sent to the model: the wording or attribution checks already rule out establishing it
  > During the lectures, they struggle to explain certain concepts since they didn't make the slides.  
  > Source: https://news.ycombinator.com/item?id=43891053
- **F3** [customer_problem, off-topic] One user says they treat actual exams as practice exams and sometimes pass them on the 'retry' but usually don't pass them the next year.
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > I did end up finishing high school at the highest level, and then got a university bachelors, but the whole process took about 1.5x as many years as it's supposed to, because I treated actual exams as practice exams, and I'd sometimes pass them on the "retry" (usually I did not, but I'd pass them the next year).  
  > Source: https://news.ycombinator.com/item?id=43532827
- **F4** [customer_problem, off-topic] One user says they hate laptops in class but students will run to Accommodative Services to get them if they try to ban laptops.
  - Needs review: the quoted text does not share two key words with the brief, including one about the problem or idea rather than the customer, so it is not counted as evidence about it
  - Note: not sent to the model: off-topic for this brief
  > > I hate laptops in class, but if I try to ban them the students will just run to Accommodative Services and get them to tell me that the student must use a laptop or they will explode into tiny pieces.  
  > Source: https://news.ycombinator.com/item?id=43532827


## Competitor findings (existing products; not evidence of demand)

None found.

## Demand signals (desk research can never establish demand)

None found.

## Founder's problem statement checked against the sources

- **H1** standing: unsupported
  - Verdict: does_not_support; second check: not run. The quote compares two note-taking methods but doesn't directly address whether students struggle to review slides effectively before exams.
  - Needs review: wording goes beyond the quoted text: experience, problem, university, students, struggle, effectively
  > Or maybe you’re asking if there’s a difference between slow, intentional note taking which you can augment with drawings, versus crib notes of whatever the slide says and probably won’t be reviewed until the week before exams.  
  > Source: https://news.ycombinator.com/item?id=35181602
- **H2** standing: unsupported
  - Verdict: does_not_support; second check: not run. The quotes describe students struggling to explain concepts during lectures due to poor slide preparation, but the claim specifies 'review lecture slides effectively before exams', which the context does not address.
  - Needs review: wording goes beyond the quoted text: experience, problem, university, lecture, effectively
  > During the lectures, they struggle to explain certain concepts since they didn't make the slides.  
  > Source: https://news.ycombinator.com/item?id=43891053
- **H3** standing: partial_evidence
  - Verdict: partially_supports; second check: not run. The quote describes a specific student's experience with ineffective lecture slides, directly matching the claim's description of students struggling to review slides before exams.
  - Needs review: wording goes beyond the quoted text: experience, university, students, struggle, lecture, effectively, exams
  > I was spending hours watching long video lectures before finals, trying to make sense of sparse PDF slides, or deciphering the ancient hieroglyphs in my friends' (or my own) notes.  
  > Source: https://news.ycombinator.com/item?id=45532727
- **H4** standing: partial_evidence
  - Verdict: partially_supports; second check: not run. The quote shows time spent reviewing slides per lecture, but doesn't address whether students struggle to review effectively.
  - Needs review: wording goes beyond the quoted text: experience, university, students, struggle, effectively, exams
  > With a provided syllabus, I probably spent 3-4 hours reviewing material and slides per lecture.  
  > Source: https://news.ycombinator.com/item?id=17040466
