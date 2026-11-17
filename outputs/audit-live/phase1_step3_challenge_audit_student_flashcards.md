# Phase 1, step 3: Challenge

Each founder assumption has a fixed ID. The label on each review is set by code from the findings it cites: EVIDENCE (an established, relevant finding), CONTRADICTING EVIDENCE, UNCONFIRMED (only findings that are not established) or ASSUMPTION (no valid finding). A stance the cited findings do not back is reset to 'untested'. Grounded reviews: 2 of 6.

## The founder's assumptions, reviewed

- **A1** (stated) University students struggle to review lecture slides effectively before exams.
  - **UNCONFIRMED (needs review)**, stance: weakened (findings H1, H2, H3, H4). H1, H2, H3, H4 show the problem is stated by multiple commenters but not verified by students themselves.
  - https://news.ycombinator.com/item?id=17040466
  - https://news.ycombinator.com/item?id=35181602
  - https://news.ycombinator.com/item?id=43891053
  - https://news.ycombinator.com/item?id=45532727
- **A2** (stated) university students preparing for exams have this problem.
  - **ASSUMPTION**, stance: untested. No findings directly address whether students preparing for exams have this problem.
- **A3** (stated) This solves it: A web app that turns a student's lecture slides into spaced-repetition flashcards for exam review.
  - **UNCONFIRMED (needs review)**, stance: weakened (findings F1, F2). F1 and F2 suggest students struggle with lecture slides but not necessarily with spaced-repetition flashcards.
  - https://news.ycombinator.com/item?id=43891053
  - https://news.ycombinator.com/item?id=45532727
- **A4** (stated) These customers can be reached in: online, English-speaking universities.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A5** (stated) The founder can build and test it with: Python, web development; 10 hours a week; 200 EUR.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A6** (implied) Enough of these customers would pay for it.
  - **ASSUMPTION**, stance: untested. No findings address whether customers would pay for the product.

## New hypotheses raised by the Challenger (not the founder's claims)

- **UNCONFIRMED (needs review)**: Students might prefer to review lecture slides in real-time during lectures rather than before exams. (findings F1, F2)

## Market and feasibility risks

- **ASSUMPTION**: market risk to A1: Students may not actually struggle with lecture slides as described.
- **ASSUMPTION**: feasibility risk to A3: Spaced-repetition flashcards may not address the core issue of understanding sparse PDF slides.

## Contradicting evidence (listed by code)

No finding contradicts its claim.

## Proposed experiments (not run)

- **Ask students about slide review habits** (tests A1)
  - Method: Survey 50 students about their current slide review methods
  - Supports if: More than 60% say they spend hours watching lectures to understand slides
  - Weakens if: More than 30% say they review slides in real-time during lectures
- **Test flashcard effectiveness** (tests A3)
  - Method: Give 10 students a set of lecture slides and ask them to create spaced-repetition flashcards
  - Supports if: Students create flashcards in under 15 minutes
  - Weakens if: Students take more than 30 minutes to create flashcards
