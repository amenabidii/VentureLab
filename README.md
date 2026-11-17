# VentureLab

**Challenge the idea. Verify the evidence. Build with confidence.**

VentureLab is an open-source, multi-agent AI co-founder for early digital-product
ideas. It does not cheer every idea on. An **Investigator** looks for real public
evidence of the founder's stated problem and keeps only exactly copied quotations, and
a **Challenger** questions the founder's assumptions, with code checking what each
criticism actually rests on. A deterministic Python **gate** (the Judge's rules) then
returns GO, REPEAT, PIVOT or STOP, together with a **Counterfactual Challenge**: what
evidence or experiment could change the decision. A **Builder** turns the result into
a validation experiment kit (and, after GO, a local landing-page prototype) that is
written only after the founder approves the exact artifact.
[Watch the 2:54 captioned demo (Google Drive)](https://drive.google.com/file/d/1D2DdEu9gWMbQyLhkSkQIUfdP_0CiDbu3/view?usp=sharing).

- **Prohibited request → STOP:** the demo's fake-review request is refused before research; the Builder is blocked.
- **Insufficient evidence → REPEAT:** the recorded Slack-thread run has **0 of 2 required independent supporting sources** ([gate record](outputs/phase1_gate_decision.md)).
- **Phases 2–6 → REHEARSAL:** founder-approved local outputs demonstrate the workflow; the gate still says **DO NOT LAUNCH**.

**All six phases run, each ending in a gate.** Status on `main`, from real runs:

| Phase | Core step (case brief) | What VentureLab does | Status |
|---|---|---|---|
| 1 Discover | **Find opportunities**: sharpen the idea, score it against alternatives, define the market, Mom Test customer interviews | Investigator retrieves and verifies quotes; Challenger; opportunity scorecard; past-behaviour interview questions and recruiting post; deterministic gate + Counterfactual Challenge | **Working** (live `qwen3:4b`, Hacker News retrieval); holding the interviews is manual (**STUBBED**) |
| 2 Validate | **Design the business**: Lean Canvas, landing-page demand test, waitlist-threshold gate | Lean Canvas with every entry sourced or labelled; validation kit; landing page after GO; fixed gate on a target set in advance (100 sign-ups in 14 days, 12 arrive → STOP or pivot) | **Working**; collecting real sign-ups **STUBBED** |
| 3 Build | **Build the product**: tested MVP and user docs | A **working MVP** for the supported product type (thread digest at `/mvp`: paste a discussion, get decisions, open questions and action items, each linked to its source message), plus a clickable prototype, MVP scope, draft user guide and executed checks that run the MVP on real input | **Working** for the supported type (tested); other ideas get the clickable prototype only; arbitrary app generation **STUBBED** |
| 4 Commercial setup | **Set the price and policies** | Price hypotheses (ASSUMPTION), price set only by founder approval, DRAFT terms/privacy/refund | **Working** (no payments of any kind) |
| 5 Launch | **Open the store; deliver automatically** | Store page and post drafts; signed payment events, idempotent delivery, refunds, reconciliation | Drafts **Working**; publishing and sale to cash **MOCKED** |
| 6 Operate and learn | None (Phase 6 work: support, metrics, persevere-or-pivot memo) | Real-request triage, metrics, memo by fixed rules | **Working**; rehearsal metrics **MOCKED**, never evidence |

Each core step, with its code file and output file: [ARCHITECTURE.md → Phases](ARCHITECTURE.md#phases).

Founder control is enforced in code: nothing is written, published or delivered without
an approval bound to the exact file's SHA-256, and STOP blocks everything downstream.
Latest genuine run (`run-a9f21cd634924cca`, current gate rules): a brief about missed Slack
threads ended **REPEAT** at the Discover gate; with the founder's approvals (bound to that run),
the local model proposed idea-specific channels, prices, interview questions and a stop rule,
and phases 2–6 ran as a labelled **REHEARSAL**
(`outputs/phase1_step4_*` … `outputs/phase6_*`, `outputs/payment_test_log.md`: 8/8
sale-to-cash checks passed), and the Phase 6 memo recommends **REPEAT**, not launch.

**Try a working product:** open `/mvp` after startup, paste a discussion and get a
source-linked catch-up brief. Inspect any point against its original message or
download a Markdown handoff. No model or account is needed, and input is not stored.
The included example is SYNTHETIC, not customer evidence. Fixed rules extract
candidates; all questions remain visible for review rather than being silently
closed by an unrelated decision. This demonstrates functionality, not validated demand.

## Quickstart

Requirements: Docker with Compose, about 4 GB of free disk and roughly 4 GB of free RAM for
`qwen3:4b` (`qwen3:1.7b` on smaller machines).

```bash
docker compose up
```

Then open <http://localhost:8000>. The first start downloads the model (about 2.5 GB);
until then `/health/model` returns HTTP 503. Submit a founder brief in the workspace
(a run takes about 2–5 minutes on a CPU laptop), or choose **Recorded executions** to
browse genuine past runs without a model. Try the working Phase 3 MVP at <http://localhost:8000/mvp> (no model needed). Then open **Phases 1–6** in the header, choose
your finished run and click through phases 2–6 (plan, approve, prepare launch, approve, launch);
each approval and execution asks for the founder key in `.venturelab/approvals.sqlite3.founder`. The same
steps run from the command line with `docker compose run --rm app python workflow.py plan --run
outputs/runs/<run-id>`. After running the interviews in an approved kit, record the totals on the written kit (**Founder approval → Validation results**); a fixed validation gate compares them with the pass mark approved beforehand. Tests: `docker compose run --rm --no-deps app python -m pytest -q`.
Full walkthrough, CLI options and platform notes: [docs/usage.md](docs/usage.md).

## What works and what is mocked

| Step | Status |
|---|---|
| Docker Compose stack: app, Ollama, one-shot model pull, health checks, persistent local state | **Working** |
| Founder web workspace: brief, workflow, evidence, Challenger, decision, counterfactual, artifacts, approvals, history | **Working**, connected to the backend |
| Genuine committed execution browser with file-integrity checks | **Working**, read-only; historical approvals never reactivate |
| Background runs: queued, running, completed, failed, blocked; duplicate submissions merged; queue bounded | **Working** (queue in memory; a run interrupted by a restart is reported as failed, not resumed) |
| Founder brief validation and policy screen: excluded categories, plus requests for fake reviews, sign-ups or urgency, impersonation or promised income (policy STOP, no research, Builder blocked) | **Working** |
| Investigator: search planning, Hacker News and founder-listed page retrieval, relevance selection, quote extraction | **Working** (needs internet) |
| Evidence verification: exact quotes, wording and attribution checks, standing ESTABLISHED / NEEDS_REVIEW / partial / unsupported / contradicted / assumption | **Working**; known quality limits in [ARCHITECTURE.md](ARCHITECTURE.md#built-vs-stubbed) |
| Challenger: founder assumptions with stable IDs, code-checked citations and stances, risks, experiments | **Working** |
| Gate (GO / REPEAT / PIVOT / STOP) and Counterfactual Challenge | **Working**, deterministic Python, no model; GO needs 2 independent supporting sources (established findings, or different commenters whose own first-person words, not quoted material, fully support the problem and pass a second check) |
| Untrusted retrieved text: comments containing instructions to an AI are never sent to the model | **Working** |
| Builder: experiment kit, interview guide and a Lean Canvas whose every box is labelled EVIDENCE, FOUNDER-STATED, PROPOSED or ASSUMPTION; local landing page only after GO; STOP blocks the Builder | **Working**, local files only |
| Founder approval bound to action, run, fingerprint and expiry, enforced in the backend | **Working** (single-founder local key, not multi-user accounts) |
| Audit log `decision_log.json` (pipeline actions plus mirrored approval-store events) | **Working** |
| Validate-phase results: the founder records observed counts against the threshold approved in the kit; a deterministic validation gate returns GO / REPEAT / STOP. Results are labelled FOUNDER-REPORTED and are not verified by VentureLab | **Working** (no real experiment results have been recorded) |
| Phase 2 run-level Lean Canvas (`workflow.py`), same labels as the kit's canvas: FOUNDER-STATED, EVIDENCE (ESTABLISHED only) or ASSUMPTION (quotes that are not established shown with URL and standing) | **Working** (`agents/strategist.py`) |
| Phase 4 pricing hypotheses (labelled ASSUMPTION) and draft terms, privacy and refund policies (DRAFT, not legal advice); price chosen only by founder approval | **Working** (`agents/commercial.py`) |
| Phase 5 store page and launch-post drafts; publishing and posting | Drafts **Working**; publishing **MOCKED** (local only, founder approval of the exact page) |
| Phase 5 sale to cash: payment events, automatic delivery, refunds revoke access, duplicate and forged events refused, reconciliation | **MOCKED** (`payments.py`, `delivery.py`, `refunds.py`, `reconcile.py`): simulated test orders only, no payments of any kind, not even sandbox; log in `outputs/payment_test_log.md` |
| Phase 6 support triage, metrics and persevere-or-pivot memo (fixed rules over real evidence only) | **Working** (`agents/operator.py`); metrics from the rehearsal are **MOCKED** and never counted as evidence; no real support requests exist yet |
| Phase 3 clickable prototype (`outputs/phase3_step1_prototype.html`) with executed user-journey checks: end reachable, no dead links, every result point linked to its source | **Working** (`agents/product.py`, `tests/test_prototype.py`); placeholders only |
| Phase 3 working MVP for the supported type: thread digest (`mvp/thread_digest.py`, web form at `/mvp`), local, no model, nothing stored or sent; acceptance checks run it on real input | **Working** (`tests/test_mvp.py`); ideas outside the type are labelled UNSUPPORTED |
| Phase 3 code generation for arbitrary product types | **STUBBED** |
| "Explore demo" data in the workspace | **MOCKED**, synthetic, labelled in the interface, never stored as results |
| Model transport and public sources in offline tests | **MOCKED** (tests only) |

Recorded genuine runs of the integrated application are in [`decision_log.json`](decision_log.json)
and `outputs/runs/`: a new brief (summaries of missed Slack threads) ended in **REPEAT**
in 174 s, and a prohibited brief ended in **STOP**. The founder approved the resulting
validation kit, which was written to `outputs/builder/`. Further live runs on unfamiliar
briefs are in [docs/evaluation-runs.md](docs/evaluation-runs.md): four ended in
**REPEAT**. Two **GO** results for accessible PDFs were later found to be wrong: the two
comments counted were a quoted government report and a developer's technical criticism,
not screen reader users' own experiences. The rule was corrected, and a rerun ended in
**REPEAT**. No run under the current gate rules (version 3) reaches GO; two GOs made under superseded rules are kept unchanged, marked superseded in the app, and refused by the Builder. The top-level
`outputs/phase1_*` files are copies of the demo run's own Phase 1 files; earlier command-line
runs keep a suffix (`_discord_bug_reports`, `_late_payments`, …) with their log archived in `docs/history/`. The later phases were run
on the Slack-thread run as a founder-approved REHEARSAL (the gate said REPEAT): outputs
`outputs/phase2_*`, `phase4_*`, `phase5_*`, `phase6_*` and `outputs/payment_test_log.md`
(all 8 sale-to-cash checks passed); the Phase 6 memo recommends **REPEAT**.

## Architecture

Ten agents cover the six phases behind a FastAPI backend: the Investigator gathers
and verifies public evidence, the Challenger questions the founder's assumptions, the
Judge applies fixed Python rules to decide GO, REPEAT, PIVOT or STOP with a
counterfactual, and the Strategist, Advisor, Builder, Product, Commercial, Launcher and
Operator agents carry the idea through Validate, Build, Commercial setup, Launch and
Operate and learn. Every phase ends in a gate (founder approval, a threshold set in
advance, or passing tests), and anything short of a real GO says DO NOT LAUNCH. Founder
approvals are bound to the exact file's SHA-256. A model never decides a gate, never
upgrades evidence and never approves anything. Everything runs
locally with an open-weight model through Ollama, and every agent action is appended to
an audit log. The full six-phase design, gates, data flow and the built-versus-stubbed
inventory are in [ARCHITECTURE.md](ARCHITECTURE.md); integration details are in
[docs/integration-verification.md](docs/integration-verification.md).

## Models and free resources

- **Models** (open-weight, run locally through Ollama, Apache-2.0 licensed Qwen3):
  `qwen3:4b` is the default and was used for the integrated runs, including the
  Builder's choice of which assumption to test; `qwen3:1.7b` is the configured
  lower-memory fallback; the earlier Milestone 3 Builder demo used `qwen3:0.6b`.
  Smaller models are faster but weaker (measurements in [docs/benchmarks.md](docs/benchmarks.md)).
- **Free public sources**: the Hacker News Algolia search API (`hn.algolia.com`, no key)
  and pages the founder lists in the brief. No paid API, account or key is needed.
- **Measured on a CPU-only laptop** with `qwen3:4b`: Discover web runs took 174 s
  (5 model calls) and 304 s (the demo run `run-a9f21cd634924cca`); a fresh-clone check
  took 279 s; earlier command-line runs took 104 to 182 s. Timing varies with
  the brief, the network and the hardware.
- **Offline**: the app, model and gate run offline, but retrieval needs internet; a
  failed source is recorded as unavailable and never filled in.
- **AI tools used to build VentureLab** (disclosed as the hackathon rules require):
  Claude Code (Anthropic's Claude models) and OpenAI Codex wrote and reviewed most of
  the code, tests and documentation under the team's direction. Their output was checked
  with the automated test suite, adversarial tests, real Docker runs and manual review of
  every generated output; the team made every founder approval decision. The running
  system itself uses only the local open-weight Qwen3 model above.

## Cost per run

About **$0.00 per run** (local `qwen3:4b`, ~4,800 tokens) in API or service charges: local
model, free public sources, no paid services. The demo run `run-a9f21cd634924cca` made 6
Discover model calls with 3,807 prompt and 948 output tokens (recorded per call in
`outputs/runs/<run>/phase1_step2_investigation.json` and `phase1_step3_challenge.json`); the
Advisor's one call in phases 2–6 is not token-counted. What it does cost: local CPU
time (about 2 to 5 minutes per run; 279 s in a fresh-clone check on 2026-11-17), the electricity for it, about 2.5 GB of disk and
one download for `qwen3:4b`, and a little bandwidth for retrieval.

## Demo video

[Watch the 3-minute demo (Google Drive)](https://drive.google.com/file/d/1D2DdEu9gWMbQyLhkSkQIUfdP_0CiDbu3/view?usp=sharing)
(2:54, no audio, captioned). A recording of the running app: the "write 50 five-star reviews" trick prompt ending
in a policy STOP, verified evidence and the REPEAT gate with its counterfactual, phases 1–6 with every gate saying
DO NOT LAUNCH, the clickable prototype, the MOCKED store page and sale-to-cash log, and founder approval.

## What our system will NOT do

- Promise income, demand or success. GO means "go on to experiments", never proof.
- Invent evidence, quotations, interviews, reviews, testimonials, sign-ups, customer
  counts or countdown timers. Missing evidence stays visible as missing.
- Count unverified (NEEDS_REVIEW) or model-written claims as established evidence.
- Pose as the founder, a customer or another brand.
- Publish, send, spend or sign anything. Builder files are written only after an
  explicit founder approval of the exact artifact, and that approval covers local files
  only.
- Process real or sandbox payments, hold, move or refund money, create accounts, or
  store passwords or card numbers.
- Support physical goods or financial, investment, crypto, health or legal advice
  products, or ideas that depend on fake reviews, sign-ups or urgency, impersonation or
  promised income. A keyword policy screen (`brief.py`, tested on more than 40 trick
  phrasings in `tests/test_trick_briefs.py`) ends these in a policy STOP before any
  research, with the matched words shown; it is re-applied before phases 2–6, and the
  Builder is blocked. A keyword screen can still miss a new phrasing.
- Invent or estimate experiment results. Validation results are only what the founder
  records, labelled FOUNDER-REPORTED.
- Hide core features behind a paywall.

## How the project stays alive after the hackathon

- **Maintainers**: Mohamed Amen Allah Abidi (research workflow, integration) and Jad
  (Builder, approvals, submission). Issues and pull requests on GitHub.
- **Roadmap**: record real experiment results against the pass marks the founder set;
  improve evidence quality (semantic relevance, attribution); a human review queue for
  NEEDS_REVIEW findings; then MVP production code and real sign-up collection, the parts still STUBBED.
- **Community**: MIT-licensed; contributions need tests and honest status labels.
- **Funding**: none assumed. Running costs stay at zero API spend by design.
