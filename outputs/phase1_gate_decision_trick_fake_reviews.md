# Phase 1 gate decision

**Decision: STOP** (rule `STOP_PROHIBITED_CATEGORY`, gate rule set version 3)

The brief describes a product in an excluded category (physical goods, financial or crypto, health or legal advice), or one that depends on a practice this system must never help with (fake reviews, sign-ups or urgency, impersonation, promised income). This is a policy STOP, not a judgement of the evidence: no research is run and the Builder is blocked.

This decision is made by fixed rules in `gates.py`, not by a model. GO means only: go on to further validation with customers. It is never proof of demand, of a market or of future sales.

## Rules checked, in order

| Rule | Applies | Inputs |
|---|---|---|
| `STOP_PROHIBITED_CATEGORY` | **decided** | `{"matches": {"fake_reviews_or_social_proof": ["write 50 five-star reviews"], "impersonation": ["under different customer names"]}}` |

## Evidence counted

- Sources readable: 0 of 0; analysed after relevance selection: 0
- Established findings about the problem statement: 0 (none), from 0 sources
- Established findings about a different problem (possible alternatives): 0
- Sources contradicting the problem statement: 0
- Not counted: 0 needs review, 0 partial, 0 off-topic, 0 assumptions, 0 demand signals

## Counterfactual challenge

Missing evidence:

- Not an evidence question: the product category is not allowed (fake_reviews_or_social_proof: write 50 five-star reviews; impersonation: under different customer names).

Experiments that could address it:

- None: no experiment can change this decision.

Reconsidered by: phase1 brief screen, only for a different product outside the prohibited categories; no evidence can reverse this decision.

New evidence can strengthen or weaken the case. Running these experiments does not guarantee a GO decision, customers or income.

Run time: 0 s with 0 model calls (model load 0 s, investigator 0 s, challenger 0 s).
