# Q&A preparation

Short, factual answers. If an answer depends on integration, say so.

**Why several agents instead of one model?** Each has a narrow job with its own check.
The Investigator's claims are verified by code before the Challenger may cite them, and
the decision is not a model at all. One prompt doing everything would grade its own
work.

**How is this different from a chatbot?** It produces a traceable record: quotes with
permalinks, a standing for every claim, the exact rule that decided the outcome, and
an audit entry per action. It can and does answer "not enough evidence".

**How do you avoid inventing evidence?** The model points at passages; Python copies the
quotation from the retrieved text and rejects anything not found there. A failed source
is recorded as unavailable and never filled in. Remaining risk: a real quote can be
attributed to the wrong claim. We have seen this, and fixes are on the quality branch.

**What happens when evidence is missing?** REPEAT, with the missing items listed and an
experiment proposed. Missing desk evidence is not treated as failure.

**Why so many REPEATs?** GO needs 2 established, relevant problem findings from 2
sources. Our recorded runs found less, for example 2 findings from 1 source. We prefer
a correct REPEAT to a flattering GO.

**How are GO and STOP decided?** By `gates.py`, a fixed rule order with no model. STOP
requires a prohibited category, a failed pass mark the founder set in advance, or 2
independent contradicting sources with no support.

**Can the founder override or reject?** The founder rejects any Builder action, and a
rejection is final for that request. Gate decisions are advice; the founder can change
the brief or run experiments and try again. Nothing the system does needs an override,
because it never acts externally.

**What works today?** In the integrated application, the founder web workspace runs
Discover end to end on a real brief (also available from the CLI), shows the evidence,
Challenger analysis, gate decision and counterfactual, and prepares a Builder request
whose files are written only after the founder approves it with the local founder key.
A real run ended in REPEAT and its validation kit was approved and written. No run
reaches GO under the current gate rules: two earlier accessible-PDF GO results were
withdrawn as superseded after review ([evaluation-runs.md](evaluation-runs.md)), and the
Builder refuses them. The landing page was prepared for one of them but never approved.

**Which phases are STUBBED?** None entirely. Phases 2–6 run through `workflow.py` behind
founder approvals, and Phase 3 writes a clickable prototype whose user journey is checked by
executed tests; what remains STUBBED is generating the MVP's production code and collecting
real sign-ups. Publishing and the sale-to-cash path are MOCKED (no payments of any kind).

**Why local open-weight models?** No API cost, no keys, founder briefs stay on the
machine, and anyone can reproduce the results. The trade-off is speed (2–5 minutes per
run on CPU) and smaller-model quality.

**What does a run cost?** About $0.00 in service fees, plus local CPU time and
electricity, a one-time 2.5 GB model download and some network traffic.

**Without internet?** The model and gate work; retrieval fails, sources are recorded as
unavailable, and the result is REPEAT for lack of readable sources.

**Can it guarantee success?** No. GO only means "worth running customer experiments",
and the output says so.

**How do you prevent unauthorized actions?** There is no send, publish or payment code.
Builder writes require an approval bound to the artifact hash, checked in the backend,
used once, and HMAC-signed in the store. UI approval is not yet wired to it.

**How can someone reproduce it?** Clone, `docker compose up`, then run the orchestrator
command in the README. The tests run with `python -m pytest -q`. We checked this
from a fresh clone on our machine with a warm Docker cache.
