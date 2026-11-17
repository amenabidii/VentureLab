# Phase 1, step 3: Challenge

Each founder assumption has a fixed ID. The label on each review is set by code from the findings it cites: EVIDENCE (an established, relevant finding), CONTRADICTING EVIDENCE, UNCONFIRMED (only findings that are not established) or ASSUMPTION (no valid finding). A stance the cited findings do not back is reset to 'untested'. Grounded reviews: 3 of 6.

## The founder's assumptions, reviewed

- **A1** (stated) Small restaurant managers waste time coordinating staff shift swaps through group chats.
  - **UNCONFIRMED (needs review)**, stance: untested (findings H1, H2). H1 and H2 both state that small restaurant managers waste time coordinating staff shift swaps through group ch
  - https://news.ycombinator.com/item?id=29829125
  - https://news.ycombinator.com/item?id=9996454
- **A2** (stated) managers of small independent restaurants have this problem.
  - **ASSUMPTION**, stance: untested. No findings directly address whether managers of small independent restaurants have this problem
- **A3** (stated) This solves it: A simple web app for small restaurants to post, swap and approve staff shifts instead of using group chats.
  - **UNCONFIRMED (needs review)**, stance: weakened (findings F3). F3 states that Crew costs nothing but allows users to post shift schedules and coordinate swaps, which is a 1:
  - https://news.ycombinator.com/item?id=9996454
- **A4** (stated) These customers can be reached in: online, English-speaking small businesses.
  - **UNCONFIRMED (needs review)**, stance: untested (findings F1). F1 only mentions one user's frustration but does not specify online or English-speaking small businesses
  - https://news.ycombinator.com/item?id=9996454
- **A5** (stated) The founder can build and test it with: Python, web development; 10 hours a week; 200 EUR.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A6** (implied) Enough of these customers would pay for it.
  - **ASSUMPTION**, stance: untested. No findings indicate whether enough customers would pay for this product

## New hypotheses raised by the Challenger (not the founder's claims)

- **ASSUMPTION**: Small restaurant managers might prefer using existing free tools like Crew over building a new app

## Market and feasibility risks

- **ASSUMPTION**: market risk to A3: Crew is a free tool that already solves the problem, so customers might not need a new app
- **ASSUMPTION**: market risk to A6: No evidence that customers would pay for a new solution when a free alternative exists

## Contradicting evidence (listed by code)

No finding contradicts its claim.

## Proposed experiments (not run)

- **Test if customers prefer Crew over a new** (tests A3)
  - Method: Ask 10 small restaurant managers if they would use Crew instead of building a new app
  - Supports if: More than 70% say they would use Crew
  - Weakens if: More than 30% say they would build their own app
- **Check willingness to pay** (tests A6)
  - Method: Survey 20 small restaurant managers about their willingness to pay for a shift coordination tool
  - Supports if: At least 50% say they would pay 5 EUR/month
  - Weakens if: Less than 20% say they would pay 5 EUR/month

## Corrected or removed by code

- A1: model said 'supported' but no cited finding can support it: H1 a check of the founder's statement that is unsupported, not established; H2 a check of the founder's statement that is unsupported, not established; stance set to 'untested'
