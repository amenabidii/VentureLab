# Phase 1 gate decision

**Decision: GO** (rule `GO_TO_FURTHER_VALIDATION`)

At least 2 independent sources support the problem statement (established findings, or people describing it in their own verified words), and nothing contradicts it. This justifies experiments with customers; it is not proof of demand or of a market.

This decision is made by fixed rules in `gates.py`, not by a model. GO means only: go on to further validation with customers. It is never proof of demand, of a market or of future sales.

## Rules checked, in order

| Rule | Applies | Inputs |
|---|---|---|
| `STOP_PROHIBITED_CATEGORY` | no | `{"matches": {}}` |
| `STOP_FAILED_VALIDATION_CONDITION` | no | `{"failed": []}` |
| `STOP_CONTRADICTED` | no | `{"supporting_findings": 0, "corroborating_checks": 2, "supporting_sources": 2, "contradicting_sources": 0, "alternatives": 0}` |
| `PIVOT_ALTERNATIVE_SUPPORTED` | no | `{"supporting_findings": 0, "corroborating_checks": 2, "supporting_sources": 2, "contradicting_sources": 0, "alternatives": 0, "alternative_findings": []}` |
| `REPEAT_MIXED_EVIDENCE` | no | `{"supporting_findings": 0, "corroborating_checks": 2, "supporting_sources": 2, "contradicting_sources": 0, "alternatives": 0}` |
| `REPEAT_NO_READABLE_SOURCES` | no | `{"sources_total": 3, "sources_readable": 3, "sources_analysed": 1}` |
| `REPEAT_CLARIFY_AVAILABILITY` | no | `{"hours_per_week": 10.0}` |
| `GO_TO_FURTHER_VALIDATION` | **decided** | `{"supporting_findings": 0, "corroborating_checks": 2, "supporting_sources": 2, "contradicting_sources": 0, "alternatives": 0, "not_counted": {"needs_review": 3, "partial": 0, "off_topic": 1, "assumptions": 0}}` |

## Evidence counted

- Sources readable: 3 of 3; analysed after relevance selection: 1
- Established findings about the problem statement: 0 (none), from 0 sources
- Established findings about a different problem (possible alternatives): 0
- Sources contradicting the problem statement: 0
- Not counted: 3 needs review, 0 partial, 1 off-topic, 0 assumptions, 0 demand signals

## Counterfactual challenge

Missing evidence:

- Demand and willingness to pay (A6): Desk research cannot establish demand or willingness to pay; only experiments with target customers can.
- Validation conditions: none set. Set pass marks before running any experiment.

Experiments that could address it:

- **Test tool effectiveness** (challenger, tests A3): Run the tool on 10 inaccessible PDFs and measure screen reader success rate
  - Would support the hypothesis if: Screen reader success rate > 80%
  - Would weaken it if: Screen reader success rate < 50%
- **Pilot pricing survey** (challenger, tests A6): Ask 50 target users about willingness to pay for the tool
  - Would support the hypothesis if: At least 30 users indicate willingness to pay > 5 EUR
  - Would weaken it if: All users indicate willingness to pay < 1 EUR
- **Problem interviews** (default, tests A1): Talk to people who match 'blind and low-vision people who use screen readers' about the last time they dealt with this problem. Ask what happened and what they did; do not pitch the idea.
  - Would support the hypothesis if: Most interviewees describe a recent, specific occurrence without being prompted. Write down the pass mark before you start, as a validation condition in the brief.
  - Would weaken it if: Most cannot recall a recent occurrence, or say it is minor or already solved.
- **Honest interest test (Validate phase)** (default, tests A6): A plain page that describes the planned product as not yet built and invites people to join a waitlist. No payment, no countdowns, no testimonials.
  - Would support the hypothesis if: Visitors from the target group join at a rate above the pass mark you set. Write down the pass mark before you start, as a validation condition in the brief.
  - Would weaken it if: Few visitors join, or those who join are not in the target group.

Reconsidered by: phase2 validation gate, against the founder's predefined validation conditions.

New evidence can strengthen or weaken the case. Running these experiments does not guarantee a GO decision, customers or income.

Run time: 247 s with 8 model calls (model load 0 s, investigator 138 s, challenger 108 s).
