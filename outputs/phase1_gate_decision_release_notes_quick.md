# Phase 1 gate decision

**Decision: REPEAT** (rule `REPEAT_INSUFFICIENT_EVIDENCE`)

Nothing contradicts the idea strongly enough to stop or pivot, but there is not enough established, relevant evidence to go on.

This decision is made by fixed rules in `gates.py`, not by a model. GO means only: go on to further validation with customers. It is never proof of demand, of a market or of future sales.

## Rules checked, in order

| Rule | Applies | Inputs |
|---|---|---|
| `STOP_PROHIBITED_CATEGORY` | no | `{"matches": {}}` |
| `STOP_FAILED_VALIDATION_CONDITION` | no | `{"failed": []}` |
| `STOP_CONTRADICTED` | no | `{"supporting_findings": 0, "supporting_sources": 0, "contradicting_sources": 0, "alternatives": 0}` |
| `PIVOT_ALTERNATIVE_SUPPORTED` | no | `{"supporting_findings": 0, "supporting_sources": 0, "contradicting_sources": 0, "alternatives": 0, "alternative_findings": []}` |
| `REPEAT_MIXED_EVIDENCE` | no | `{"supporting_findings": 0, "supporting_sources": 0, "contradicting_sources": 0, "alternatives": 0}` |
| `REPEAT_NO_READABLE_SOURCES` | no | `{"sources_total": 1, "sources_readable": 1, "sources_analysed": 1}` |
| `REPEAT_CLARIFY_AVAILABILITY` | no | `{"hours_per_week": 10.0}` |
| `GO_TO_FURTHER_VALIDATION` | no | `{"supporting_findings": 0, "supporting_sources": 0, "contradicting_sources": 0, "alternatives": 0, "not_counted": {"needs_review": 0, "partial": 1, "off_topic": 1, "assumptions": 0}}` |
| `REPEAT_INSUFFICIENT_EVIDENCE` | **decided** | `{}` |

## Evidence counted

- Sources readable: 1 of 1; analysed after relevance selection: 1
- Established findings about the problem statement: 0 (none), from 0 sources
- Established findings about a different problem (possible alternatives): 0
- Sources contradicting the problem statement: 0
- Not counted: 0 needs review, 1 partial, 1 off-topic, 0 assumptions, 0 demand signals

## Counterfactual challenge

Missing evidence:

- Established, relevant problem findings: 0 of 2 needed, from 0 of 2 sources needed.
- 0 needs-review and 1 partial findings do not count. A person may check them against their quotes; they never count automatically.
- 1 findings were off-topic for this brief and were not counted.
- Demand and willingness to pay (A6): Desk research cannot establish demand or willingness to pay; only experiments with target customers can.
- Condition 'problem_interviews' not yet measured (interviewees_confirming_problem >= 5).

Experiments that could address it:

- **Ask small SaaS teams about willingness** (challenger, tests A6): Survey 10 small SaaS teams about willingness to pay for a tool that drafts release notes from PRs
  - Would support the hypothesis if: At least 50% say they would pay 50 EUR/month
  - Would weaken it if: At least 50% say they would not pay for it
- **Problem interviews** (default, tests A1): Talk to people who match 'developers and product managers at small SaaS companies' about the last time they dealt with this problem. Ask what happened and what they did; do not pitch the idea.
  - Would support the hypothesis if: Most interviewees describe a recent, specific occurrence without being prompted. Write down the pass mark before you start, as a validation condition in the brief.
  - Would weaken it if: Most cannot recall a recent occurrence, or say it is minor or already solved.
- **Wider desk research** (default, tests A1): Re-run the investigation with public pages where target customers discuss the problem (forums, communities, reviews of existing tools), added as source URLs in the brief.
  - Would support the hypothesis if: Several different people describe the problem in their own words; these become established, relevant findings.
  - Would weaken it if: Relevant sources exist but people describe the problem as rare, minor or solved.

Reconsidered by: phase1_evidence_gate (run again with the new evidence).

New evidence can strengthen or weaken the case. Running these experiments does not guarantee a GO decision, customers or income.

Run time: 104 s with 5 model calls (model load 0 s, investigator 51 s, challenger 52 s).
