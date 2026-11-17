# Phase 1, step 3: Challenge

Each founder assumption has a fixed ID. The label on each review is set by code from the findings it cites: EVIDENCE (an established, relevant finding), CONTRADICTING EVIDENCE, UNCONFIRMED (only findings that are not established) or ASSUMPTION (no valid finding). A stance the cited findings do not back is reset to 'untested'. Grounded reviews: 3 of 6.

## The founder's assumptions, reviewed

- **A1** (stated) Freelance designers waste time collecting scattered client feedback on design drafts.
  - **CONTRADICTING EVIDENCE**, stance: weakened (findings H1, H2, H3, H4). H1, H2, H3, H4 all state the same problem but with contradictory standings, showing inconsistency in evidence
  - https://news.ycombinator.com/item?id=20873714
  - https://news.ycombinator.com/item?id=2138845
  - https://news.ycombinator.com/item?id=33064987
  - https://news.ycombinator.com/item?id=5096574
- **A2** (stated) freelance graphic and web designers have this problem.
  - **UNCONFIRMED (needs review)**, stance: weakened (findings F3). F1, F2, F3 are all from freelance designers but with needs_review standing, indicating unconfirmed claims
  - https://news.ycombinator.com/item?id=5096574
- **A3** (stated) This solves it: A web app where freelance designers share drafts and collect pinned client feedback in one place.
  - **UNCONFIRMED (needs review)**, stance: weakened (findings F3, H1, H2). F3 states a need for a tool but H1-H4 show the problem is not universally experienced
  - https://news.ycombinator.com/item?id=33064987
  - https://news.ycombinator.com/item?id=5096574
- **A4** (stated) These customers can be reached in: online, English-speaking freelancers.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A5** (stated) The founder can build and test it with: Python, web development; 10 hours a week; 200 EUR.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A6** (implied) Enough of these customers would pay for it.
  - **ASSUMPTION**, stance: untested. no findings speak to whether customers would pay for it

## New hypotheses raised by the Challenger (not the founder's claims)

- **UNCONFIRMED (needs review)**: Freelance designers need a tool to manage feedback but may prioritize other tools over this specific solution (findings F3)

## Market and feasibility risks

- **ASSUMPTION**: market risk to A2: Freelance designers may not have this problem as claimed
- **ASSUMPTION**: feasibility risk to A3: The solution might not address the actual pain point

## Contradicting evidence (listed by code)

- H3 (contradicted): One commenter says they experience this problem: Freelance designers waste time collecting scattered client feedback on design drafts. https://news.ycombinator.com/item?id=2138845

## Proposed experiments (not run)

- **Survey of freelance designers** (tests A1)
  - Method: Ask 50 freelance designers about time spent on feedback collection
  - Supports if: More than 20% say they spend 2+ days on feedback collection
  - Weakens if: More than 80% say they don't spend time on feedback collection
- **Check segment size** (tests A2)
  - Method: Find how many freelance designers work on projects requiring detailed specifications
  - Supports if: At least 500 designers work on such projects
  - Weakens if: Fewer than 100 designers work on such projects
