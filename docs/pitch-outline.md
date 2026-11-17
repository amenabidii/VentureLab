# Architecture pitch outline (5 minutes)

**1. Problem (0:00–0:40).** AI startup assistants agree with the founder. They write
confident plans from no evidence, invent market numbers and never say stop. A founder
needs the opposite: something that looks for evidence, shows what is missing and is
allowed to say no.

**2. What VentureLab does (0:40–1:20).** Brief in; real public evidence out with exact
quotes and links; assumptions challenged; a GO / REPEAT / PIVOT / STOP decision from
fixed rules; a counterfactual saying what would change it; validation artifacts built
only with founder approval. Tagline: *Challenge the idea. Verify the evidence. Build
with confidence.*

**3. Four agents, one rule (1:20–2:10).** Investigator (retrieve, extract, verify),
Challenger (question assumptions using findings), Judge (Python rules, no model),
Builder (experiment kit, landing page). The rule that binds them: a model may propose,
but code verifies. Quotes are copied by Python from retrieved text, standing is set by
code, and gate decisions are made by code.

**4. Six phases (2:10–2:50).** Show the ARCHITECTURE diagram. Discover works end to end
in the web workspace. Validate (experiment kit) works; Build (landing page) works after a
GO decision and has been exercised only in tests so far.
Commercial Setup, Launch and Operate & Learn are designed and labelled STUBBED.
Payments are deliberately not implemented.

**5. Gates and the counterfactual (2:50–3:30).** Rule order on screen. Only
ESTABLISHED, relevant problem findings from 2+ sources count. Missing evidence →
REPEAT, never a silent GO. STOP for prohibited categories, failed pre-set pass marks
or independent contradiction. Real example: 2 established findings from 1 source →
REPEAT, and the counterfactual names the missing second source and the interview
experiment.

**6. Founder control (3:30–4:00).** An approval is bound to one action, run and
artifact SHA-256. Missing, rejected, changed or replayed approvals are refused in
backend code, and the audit chain is signed. Generating a file never authorizes
publishing it.

**7. Open and reproducible (4:00–4:30).** MIT license, `docker compose up`, Qwen3
open weights through Ollama, no API keys, about $0.00 in service cost per run
(2–3 minutes of local CPU), and one audit entry per agent action. Measured numbers
only: Discover runs took 103–182 s with `qwen3:4b`; the benchmarks are in
`docs/benchmarks.md`.

**8. Honest limits and next steps (4:30–5:00).** Not yet integrated (UI, workflow
and Builder are separate branches). Evidence quality limits: keyword relevance,
attribution errors, conservative standing. No real run has reached GO yet. Next:
integrate, add a human review queue for NEEDS_REVIEW findings, and feed real experiment
results back into the pass marks.
