# VentureLab

**Challenge the idea. Verify the evidence. Build with confidence.**

VentureLab is an open-source, multi-agent AI co-founder for early digital-product
ideas. It does not cheer every idea on. An **Investigator** looks for real public
evidence of the founder's stated problem and keeps only exactly copied quotations, and
a **Challenger** attacks unsupported assumptions. A deterministic Python **gate** (the
Judge's rules) then returns GO, REPEAT, PIVOT or STOP, together with a
**Counterfactual Challenge**: what evidence or experiment could change the decision.
A **Builder** turns an admitted idea into a validation experiment kit and a local
landing-page prototype, but only after the founder approves the exact artifact.

**Status, stated plainly:** the Discover workflow (brief → Investigator → Challenger →
gate → counterfactual) runs end to end on `main` from the command line. The Builder
with backend founder approval (Milestone 3) and the founder web interface (Milestone 4)
work on their own feature branches and are **not yet merged or connected**. Commercial
Setup, Launch and Operate & Learn are architecture only (STUBBED).

## Quickstart

Requirements: Docker with Compose, about 4 GB of free disk for the model, and roughly
4 GB of free RAM for `qwen3:4b` (use `qwen3:1.7b` on smaller machines, see below).

```bash
docker compose up
```

Then open <http://localhost:8000>. The first start also runs a one-shot `model-pull`
service that downloads the configured model (`qwen3:4b`, about 2.5 GB); until that
finishes the start page says the model is still downloading and `/health/model`
returns HTTP 503. Readiness checks:

- `/health`: the web app is up (does not touch the model).
- `/health/model`: Ollama is reachable and the configured model is downloaded.
- `/health/inference`: one tiny structured request actually runs on the model.

The web page on `main` is a status page. The research workflow runs from the command
line inside the same stack, with the repository mounted so outputs land in it:

```bash
docker compose run --rm -v "$PWD:/srv" app python orchestrator.py --brief briefs/indie_game_bug_reports.json --quick
```

It writes `outputs/phase1_*` files and appends one entry per agent action to
`decision_log.json`. Example briefs are in `briefs/`; `crypto_signals_newsletter.json`
is a prohibited category and demonstrates STOP. Retrieval needs internet access.
On a smaller machine set `VENTURELAB_MODEL=qwen3:1.7b` in `.env` (copy `.env.example`).

Tests: `docker compose run --rm --no-deps app python -m pytest -q`, or locally with
Python 3.11 and `pip install -r requirements.txt` then `python -m pytest -q`. Live-model
tests are opt-in (`VENTURELAB_LIVE_TESTS=1`).

## What works and what is mocked

Status is for the `main` branch unless the row says otherwise.

| Step | Status |
|---|---|
| Docker Compose stack: app, Ollama, one-shot model pull, health checks | **Working** (baseline; re-verify after integration) |
| Founder brief validation and prohibited-category screen | **Working** |
| Investigator: search planning, Hacker News and founder-listed page retrieval, quote extraction | **Working** (needs internet) |
| Evidence verification: quotes checked against retrieved text, standing ESTABLISHED / NEEDS_REVIEW / partial / assumption | **Working**; known quality limits listed in [ARCHITECTURE.md](ARCHITECTURE.md#built-vs-stubbed) |
| Challenger: grounded concerns, missing information, experiments | **Working** |
| Phase 1 gate (GO / REPEAT / PIVOT / STOP) and Counterfactual Challenge | **Working**, deterministic Python, no model |
| Audit log `decision_log.json` (one entry per agent action) | **Working** |
| Builder: experiment kit, local landing page, fingerprint-bound founder approval | **Working on branch `feature/milestone3-builder`**; not merged |
| Founder web interface (brief, evidence, decisions, artifacts, approvals) | **Working UI on branch `feature/milestone4-ui`**; backend connections **STUBBED**; its demo data is **MOCKED** and labelled in the UI |
| Web UI → research workflow → Builder → approval, end to end | **STUBBED** until integration |
| Commercial Setup, Launch, Operate & Learn | **STUBBED** (architecture only) |
| Payments, sale to cash | **STUBBED**, deliberately not implemented, no real or sandbox transactions |
| Offline model transport in unit tests | **MOCKED** (tests only) |

Recorded real runs on `main` ([outputs/](outputs/), [decision_log.json](decision_log.json))
ended in REPEAT (insufficient established evidence) for three briefs and STOP for the
prohibited-category brief. No run has produced GO; that is a result, not a fault.

## Architecture

Four logical agents work in sequence: the Investigator gathers and verifies public
evidence, the Challenger questions the founder's assumptions using that evidence, the
Judge applies fixed Python rules to produce a gate decision with a counterfactual, and
the Builder prepares validation artifacts that are written only after founder
approval bound to the artifact's SHA-256 fingerprint. A model never decides a gate and
never upgrades evidence on its own. Everything runs locally with an open-weight model
through Ollama, and every agent action is appended to an audit log. The full six-phase
design, gates, data flow and the built-versus-stubbed inventory are in
[ARCHITECTURE.md](ARCHITECTURE.md).

## Models and free resources

- **Models** (open-weight, run locally through Ollama, Apache-2.0 licensed Qwen3):
  `qwen3:4b` is the default and was used for every recorded Discover run;
  `qwen3:1.7b` is the configured lower-memory fallback; the Milestone 3 Builder demo
  used `qwen3:0.6b` because the machine had under 2 GB of free RAM. Smaller models
  are faster but weaker; they are not equivalent for evidence assessment
  (measurements in [docs/benchmarks.md](docs/benchmarks.md)).
- **Free public sources**: the Hacker News Algolia search API
  (`hn.algolia.com`, no key) and pages the founder lists in the brief. No paid API,
  account or key is needed anywhere.
- **Measured on a CPU-only laptop**: live Discover runs with `qwen3:4b` took 103 to
  182 seconds each (from the committed `decision_log.json` timestamps); timing varies
  with the brief, the network and the hardware.
- **Offline**: the app, model and gate run offline, but retrieval needs internet; a
  failed source is recorded as unavailable and never filled in.

## Cost per run

About **$0.00 per run** in API or service charges: local model, free public sources,
no paid services (token counts per run are not yet logged). What it does cost:
local CPU time (about 2 to 3 minutes per run, measured above), the electricity for it,
about 2.5 GB of disk and one download for `qwen3:4b`, and a little internet bandwidth
for retrieval. These local costs are not measured in dollars here.

## Demo video

Not yet recorded. It will be linked here after the integrated system passes its
acceptance checks ([docs/demo-runbook.md](docs/demo-runbook.md)).

## What our system will NOT do

- Promise income, demand or success. GO means "go on to experiments", never proof.
- Invent evidence, quotations, interviews, reviews, testimonials, sign-ups, customer
  counts or countdown timers. Missing evidence stays visible as missing.
- Count unverified (NEEDS_REVIEW) or model-written claims as established evidence.
- Pose as the founder, a customer or another brand.
- Publish, send, spend or sign anything, or write Builder artifacts, without an
  explicit founder approval tied to the exact artifact.
- Process real or sandbox payments, hold, move or refund money, create accounts, or
  store passwords or card numbers.
- Support physical goods or financial, investment, crypto, health or legal advice
  products (these stop at the category screen).
- Hide core features behind a paywall.

## How the project stays alive after the hackathon

- **Maintainers**: Mohamed Amen Allah Abidi (research workflow, integration) and Jad
  (Builder, approvals, submission). Issues and pull requests on GitHub.
- **Roadmap**: merge and test the Builder and founder interface against the research
  workflow; improve evidence quality (attribution, relevance, synonyms); add
  human review of NEEDS_REVIEW findings; then design-only phases one at a time.
- **Community**: MIT-licensed; contributions need tests and honest status labels.
- **Funding**: none assumed. Running costs stay at zero API spend by design.
