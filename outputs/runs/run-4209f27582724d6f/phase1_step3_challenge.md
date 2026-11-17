# Phase 1, step 3: Challenge

Each founder assumption has a fixed ID. The label on each review is set by code from the findings it cites: EVIDENCE (an established, relevant finding), CONTRADICTING EVIDENCE, UNCONFIRMED (only findings that are not established) or ASSUMPTION (no valid finding). A stance the cited findings do not back is reset to 'untested'. Grounded reviews: 3 of 6.

## The founder's assumptions, reviewed

- **A1** (stated) Screen reader users struggle to read inaccessible PDF documents.
  - **UNCONFIRMED (needs review)**, stance: untested (findings F1, H1, H2, H3). F1, H1, H2, H3 all describe screen reader users struggling with inaccessible PDFs
  - https://news.ycombinator.com/item?id=13809215
  - https://news.ycombinator.com/item?id=31272485
  - https://news.ycombinator.com/item?id=6671934
- **A2** (stated) blind and low-vision people who use screen readers have this problem.
  - **UNCONFIRMED (needs review)**, stance: untested (findings F4, H1, H2). F4 and H1, H2, H3 confirm blind and low-vision users with screen readers face PDF issues
  - https://news.ycombinator.com/item?id=13809215
  - https://news.ycombinator.com/item?id=6671934
- **A3** (stated) This solves it: A web tool that converts inaccessible PDF documents into screen-reader friendly HTML.
  - **UNCONFIRMED (needs review)**, stance: weakened (findings F3, H1, H2, H3). F3 suggests PDFs are less helpful than HTML for accessibility tools, but H1, H2, H3 show screen readers still 
  - https://news.ycombinator.com/item?id=13809215
  - https://news.ycombinator.com/item?id=31272485
  - https://news.ycombinator.com/item?id=41681398
  - https://news.ycombinator.com/item?id=6671934
- **A4** (stated) These customers can be reached in: online, worldwide.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A5** (stated) The founder can build and test it with: Python, web development; 10 hours a week; 200 EUR.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A6** (implied) Enough of these customers would pay for it.
  - **ASSUMPTION**, stance: untested. No findings address whether customers would pay for this solution

## New hypotheses raised by the Challenger (not the founder's claims)

- **UNCONFIRMED (needs review)**: Screen reader users might prefer PDFs with specific accessibility features over full HTML conversion (findings F3)

## Market and feasibility risks

- **ASSUMPTION**: market risk to A6: No evidence that customers would pay for this solution

## Contradicting evidence (listed by code)

No finding contradicts its claim.

## Proposed experiments (not run)

- **Pricing survey** (tests A6)
  - Method: Ask 10 screen reader users about willingness to pay for PDF conversion
  - Supports if: At least 3 users say they would pay 5 EUR or more
  - Weakens if: All users say they would not pay more than 1 EUR

## Corrected or removed by code

- A1: model said 'supported' but no cited finding can support it: F1 related but needs_review; H1 a check of the founder's statement that is needs_review, not established; H2 a check of the founder's statement that is needs_review, not established; H3 a check of the founder's statement that is unsupported, not established; stance set to 'untested'
- A2: model said 'supported' but no cited finding can support it: F4 related but needs_review; H1 related but needs_review; H2 related but needs_review; H3 the quote shares 0 key concept(s) with the assumption; stance set to 'untested'
