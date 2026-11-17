# Phase 1, step 3: Challenge

Each founder assumption has a fixed ID. The label on each review is set by code from the findings it cites: EVIDENCE (an established, relevant finding), CONTRADICTING EVIDENCE, UNCONFIRMED (only findings that are not established) or ASSUMPTION (no valid finding). A stance the cited findings do not back is reset to 'untested'. Grounded reviews: 1 of 6.

## The founder's assumptions, reviewed

- **A1** (stated) Small software teams spend too much time writing release notes and changelogs.
  - **UNCONFIRMED (needs review)**, stance: weakened (findings F1, F2). F1 and F2 both describe a specific manual process for writing release notes but do not confirm that this is a 
  - https://news.ycombinator.com/item?id=46279042
- **A2** (stated) developers and product managers at small SaaS companies have this problem.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A3** (stated) This solves it: A web app that drafts customer-facing release notes from a small software team's merged pull requests, for a person to edit and publish.
  - **ASSUMPTION**, stance: untested. No findings directly test if the web app would solve the problem
- **A4** (stated) These customers can be reached in: English-speaking small SaaS companies, online.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A5** (stated) The founder can build and test it with: Python and web development, technical writing; 10 hours a week; 300 EUR.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A6** (implied) Enough of these customers would pay for it.
  - **ASSUMPTION**, stance: untested. No findings address whether customers would pay

## New hypotheses raised by the Challenger (not the founder's claims)

- **UNCONFIRMED (needs review)**: Small software teams might prefer manual release note creation over automated tools due to customization needs (findings F1, F2)

## Market and feasibility risks

- **ASSUMPTION**: market risk to A1: The problem might not be widespread enough to justify automation
- **ASSUMPTION**: feasibility risk to A1: Automated release notes might not be accurate without significant customization

## Contradicting evidence (listed by code)

No finding contradicts its claim.

## Proposed experiments (not run)

- **Test manual vs automated time** (tests A1)
  - Method: Ask 5 small software teams to write release notes manually and via the web app
  - Supports if: Manual takes longer than automated
  - Weakens if: Manual takes less time or automated is less accurate
- **Test problem severity** (tests A1)
  - Method: Survey 20 small software teams about time spent on release notes
  - Supports if: More than 50% spend over 1 hour per release
  - Weakens if: Less than 20% spend over 1 hour per release
