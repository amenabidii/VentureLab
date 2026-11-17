# Phase 1 gate decision

**Decision: REPEAT** (rule `REPEAT_INSUFFICIENT_EVIDENCE`)

Nothing contradicts the idea strongly enough to stop or pivot, but there is not enough established, relevant evidence to go on.

This decision is made by fixed rules in `gates.py`, not by a model. GO means only: go on to further validation with customers. It is never proof of demand, of a market or of future sales.

## Rules checked, in order

| Rule | Applies | Inputs |
|---|---|---|
| `STOP_PROHIBITED_CATEGORY` | no | `{"matches": {}}` |
| `STOP_FAILED_VALIDATION_CONDITION` | no | `{"failed": []}` |
| `STOP_CONTRADICTED` | no | `{"supporting_findings": 0, "corroborating_checks": 0, "supporting_sources": 0, "contradicting_sources": 0, "alternatives": 0}` |
| `PIVOT_ALTERNATIVE_SUPPORTED` | no | `{"supporting_findings": 0, "corroborating_checks": 0, "supporting_sources": 0, "contradicting_sources": 0, "alternatives": 0, "alternative_findings": []}` |
| `REPEAT_MIXED_EVIDENCE` | no | `{"supporting_findings": 0, "corroborating_checks": 0, "supporting_sources": 0, "contradicting_sources": 0, "alternatives": 0}` |
| `REPEAT_NO_READABLE_SOURCES` | no | `{"sources_total": 3, "sources_readable": 3, "sources_analysed": 1}` |
| `REPEAT_CLARIFY_AVAILABILITY` | no | `{"hours_per_week": 10.0}` |
| `GO_TO_FURTHER_VALIDATION` | no | `{"supporting_findings": 0, "corroborating_checks": 0, "supporting_sources": 0, "contradicting_sources": 0, "alternatives": 0, "not_counted": {"needs_review": 3, "partial": 0, "off_topic": 1, "assumptions": 0}}` |
| `REPEAT_INSUFFICIENT_EVIDENCE` | **decided** | `{}` |

## Evidence counted

- Sources readable: 3 of 3; analysed after relevance selection: 1
- Established findings about the problem statement: 0 (none), from 0 sources
- Established findings about a different problem (possible alternatives): 0
- Sources contradicting the problem statement: 0
- Not counted: 3 needs review, 0 partial, 1 off-topic, 0 assumptions, 1 demand signals

## Counterfactual challenge

Missing evidence:

- Independent sources supporting the problem statement: 0 of 2 needed (0 established findings, 0 people describing it in their own words).
- 3 needs-review and 0 partial findings do not count. A person may check them against their quotes; they never count automatically.
- 1 findings were off-topic for this brief and were not counted.
- Demand and willingness to pay (A6): Desk research cannot establish demand or willingness to pay; only experiments with target customers can.
- Validation conditions: none set. Set pass marks before running any experiment.

Experiments that could address it:

- **Test if customers prefer Crew over a new** (challenger, tests A3): Ask 10 small restaurant managers if they would use Crew instead of building a new app
  - Would support the hypothesis if: More than 70% say they would use Crew
  - Would weaken it if: More than 30% say they would build their own app
- **Check willingness to pay** (challenger, tests A6): Survey 20 small restaurant managers about their willingness to pay for a shift coordination tool
  - Would support the hypothesis if: At least 50% say they would pay 5 EUR/month
  - Would weaken it if: Less than 20% say they would pay 5 EUR/month
- **Problem interviews** (default, tests A1): Talk to people who match 'managers of small independent restaurants' about the last time they dealt with this problem. Ask what happened and what they did; do not pitch the idea.
  - Would support the hypothesis if: Most interviewees describe a recent, specific occurrence without being prompted. Write down the pass mark before you start, as a validation condition in the brief.
  - Would weaken it if: Most cannot recall a recent occurrence, or say it is minor or already solved.
- **Wider desk research** (default, tests A1): Re-run the investigation with public pages where target customers discuss the problem (forums, communities, reviews of existing tools), added as source URLs in the brief.
  - Would support the hypothesis if: Several different people describe the problem in their own words; these become established, relevant findings.
  - Would weaken it if: Relevant sources exist but people describe the problem as rare, minor or solved.

Reconsidered by: phase1_evidence_gate (run again with the new evidence).

New evidence can strengthen or weaken the case. Running these experiments does not guarantee a GO decision, customers or income.

Run time: 191 s with 5 model calls (model load 0 s, investigator 87 s, challenger 104 s).
