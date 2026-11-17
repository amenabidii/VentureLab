# Phase 1, step 3: Challenge

Each founder assumption has a fixed ID. The label on each review is set by code from the findings it cites: EVIDENCE (an established, relevant finding), CONTRADICTING EVIDENCE, UNCONFIRMED (only findings that are not established) or ASSUMPTION (no valid finding). A stance the cited findings do not back is reset to 'untested'. Grounded reviews: 2 of 6.

## The founder's assumptions, reviewed

- **A1** (stated) Small software teams spend too much time writing release notes and changelogs.
  - **UNCONFIRMED (needs review)**, stance: untested (findings F1). F1 shows a user hands writes release notes and copies version numbers, indicating time spent on this task.
  - https://news.ycombinator.com/item?id=46279042
- **A2** (stated) developers and product managers at small SaaS companies have this problem.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A3** (stated) This solves it: A web app that drafts customer-facing release notes from a small software team's merged pull requests, for a person to edit and publish.
  - **UNCONFIRMED (needs review)**, stance: weakened (findings F3). F3 shows users already use GitHub-generated release notes from PR bodies, which may reduce the need for manual
  - https://news.ycombinator.com/item?id=46279042
- **A4** (stated) These customers can be reached in: English-speaking small SaaS companies, online.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A5** (stated) The founder can build and test it with: Python and web development, technical writing; 10 hours a week; 300 EUR.
  - **ASSUMPTION**, stance: untested. no finding relates to it, so the Challenger did not review it
- **A6** (implied) Enough of these customers would pay for it.
  - **ASSUMPTION**, stance: untested. No findings address whether customers would pay for this solution.

## New hypotheses raised by the Challenger (not the founder's claims)

- **UNCONFIRMED (needs review)**: Small software teams might prefer automated release notes that integrate with their existing CI/CD pipelines. (findings F3)

## Market and feasibility risks

- **ASSUMPTION**: market risk to A3: Existing GitHub-generated release notes may already meet the need, reducing adoption.

## Contradicting evidence (listed by code)

No finding contradicts its claim.

## Proposed experiments (not run)

- **Test GitHub-generated release notes** (tests A3)
  - Method: Ask users if they currently use GitHub-generated release notes for their release notes
  - Supports if: Users say they use GitHub-generated release notes
  - Weakens if: Users say they don't use GitHub-generated release notes

## Corrected or removed by code

- A1: model said 'supported' but no cited finding can support it: F1 the quote does not mention time, which the assumption asserts; stance set to 'untested'
