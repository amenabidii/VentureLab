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

**Status, stated plainly:** the founder web workspace runs the whole Discover workflow
on a real brief, shows the evidence, the Challenger's analysis, the gate decision and
the counterfactual, prepares Builder artifacts and enforces founder approval in the
backend before anything is written. Commercial Setup, Launch and Operate & Learn are
architecture only (STUBBED). Nothing is ever published, sent or paid.

## Quickstart

Requirements: Docker with Compose, about 4 GB of free disk for the model, and roughly
4 GB of free RAM for `qwen3:4b` (use `qwen3:1.7b` on smaller machines, see below).

```bash
docker compose up
```

Then open <http://localhost:8000>. The first start also runs a one-shot `model-pull`
service that downloads the configured model (`qwen3:4b`, about 2.5 GB); until it
finishes the header says the model is not ready and `/health/model` returns HTTP 503.

State is kept in the checkout and survives restarts: `.venturelab/` (run records,
approval store, founder key; created on first start), `outputs/` and
`decision_log.json`. This works on Docker Desktop (Windows, macOS) and on Linux without
manual permission changes: the container checks these paths as root (symlinks are
refused), then runs the app as the owner of your checkout, never as root. Run it from a
checkout owned by your normal user; a root-owned checkout is refused with an explanation.

1. **Founder brief**: fill in the form, review it and submit. The backend validates it
   (errors appear next to the fields) and starts a real analysis in the background.
2. **Agent workflow**: statuses come from the backend's progress records and refresh
   every 5 seconds. A brief submitted while the first model download is still running
   waits for it (up to 15 minutes, shown as such) instead of failing. A full run takes about two to four minutes on a CPU laptop; the
   "shorter demonstration run" option uses one search and fewer claims.
3. **Evidence explorer, Challenger analysis, Decision dashboard, Counterfactual
   challenge**: the run's recorded outputs, with every standing shown as assigned.
4. **Ask the Builder to prepare a validation kit** (Decision dashboard). This only
   creates a request; inspect it under **Builder artifacts**.
5. **Founder approval**: paste the founder key from
   `.venturelab/approvals.sqlite3.founder` (created on first start, kept on your
   machine), approve or reject the exact request, then **Write the approved files
   locally**. Requests expire after two hours.
6. **Decision history**: every recorded action for the run.

The command-line workflow still works:
`docker compose run --rm -v "$PWD:/srv" app python orchestrator.py --brief briefs/indie_game_bug_reports.json --quick`.
Retrieval needs internet access. On a smaller machine set `VENTURELAB_MODEL=qwen3:1.7b`
in `.env` (copy `.env.example`).

Tests: `docker compose run --rm --no-deps app python -m pytest -q`. Live-model tests are
opt-in (`VENTURELAB_LIVE_TESTS=1`); UI tests are in `tests/ui` (`npm ci`, `npm test`,
`npm run test:browser`).

## What works and what is mocked

| Step | Status |
|---|---|
| Docker Compose stack: app, Ollama, one-shot model pull, health checks, persistent local state | **Working** |
| Founder web workspace: brief, workflow, evidence, Challenger, decision, counterfactual, artifacts, approvals, history | **Working**, connected to the backend |
| Background runs: queued, running, completed, failed, blocked; duplicate submissions merged; queue bounded | **Working** (queue in memory; a run interrupted by a restart is reported as failed, not resumed) |
| Founder brief validation and prohibited-category screen | **Working** |
| Investigator: search planning, Hacker News and founder-listed page retrieval, relevance selection, quote extraction | **Working** (needs internet) |
| Evidence verification: exact quotes, wording and attribution checks, standing ESTABLISHED / NEEDS_REVIEW / partial / unsupported / contradicted / assumption | **Working**; known quality limits in [ARCHITECTURE.md](ARCHITECTURE.md#built-vs-stubbed) |
| Challenger: founder assumptions with stable IDs, code-checked citations and stances, risks, experiments | **Working** |
| Gate (GO / REPEAT / PIVOT / STOP) and Counterfactual Challenge | **Working**, deterministic Python, no model; GO needs 2 independent supporting sources (established findings, or commenters whose exact words fully support the problem and pass a second check) |
| Untrusted retrieved text: comments containing instructions to an AI are never sent to the model | **Working** |
| Builder: experiment kit and interview guide; local landing page only after GO; STOP blocks the Builder | **Working**, local files only |
| Founder approval bound to action, run, fingerprint and expiry, enforced in the backend | **Working** (single-founder local key, not multi-user accounts) |
| Audit log `decision_log.json` (pipeline actions plus mirrored approval-store events) | **Working** |
| Validate-phase results entry (recording real interview outcomes) | **STUBBED** |
| Commercial Setup, Launch, Operate & Learn | **STUBBED** (architecture only) |
| Payments, sale to cash | **STUBBED**, deliberately not implemented, no real or sandbox transactions |
| "Explore demo" data in the workspace | **MOCKED**, synthetic, labelled in the interface, never stored as results |
| Model transport and public sources in offline tests | **MOCKED** (tests only) |

Recorded genuine runs of the integrated application are in [`decision_log.json`](decision_log.json)
and `outputs/runs/`: a new brief (summaries of missed Slack threads) ended in **REPEAT**
in 174 s, and a prohibited brief ended in **STOP**. The founder approved the resulting
validation kit, which was written to `outputs/builder/`. Earlier command-line runs are in
`outputs/phase1_*` with their log archived in `docs/history/`. No real run has reached
GO yet; that is a result, not a fault.

## Architecture

Four logical agents work in sequence behind a FastAPI backend: the Investigator gathers
and verifies public evidence, the Challenger questions the founder's assumptions using
that evidence, the Judge applies fixed Python rules to produce a gate decision with a
counterfactual, and the Builder prepares validation artifacts that are written only
after founder approval bound to the artifact's SHA-256 fingerprint. Runs execute in a
background worker and the web workspace polls their real progress. A model never
decides a gate, never upgrades evidence and never approves anything. Everything runs
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
- **Measured on a CPU-only laptop** with `qwen3:4b`: the integrated web run took 174 s
  with 5 model calls; earlier command-line runs took 104 to 182 s. Timing varies with
  the brief, the network and the hardware.
- **Offline**: the app, model and gate run offline, but retrieval needs internet; a
  failed source is recorded as unavailable and never filled in.

## Cost per run

About **$0.00 per run** in API or service charges: local model, free public sources, no
paid services (5 model calls in the measured web run; token counts are recorded per run
in `outputs/runs/<run>/phase1_step2_investigation.json`). What it does cost: local CPU
time (about 2 to 4 minutes per run), the electricity for it, about 2.5 GB of disk and
one download for `qwen3:4b`, and a little bandwidth for retrieval.

## Demo video

Not yet recorded. It will be linked here ([docs/demo-runbook.md](docs/demo-runbook.md)).

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
  products (these stop at the category screen, and the Builder is blocked).
- Hide core features behind a paywall.

## How the project stays alive after the hackathon

- **Maintainers**: Mohamed Amen Allah Abidi (research workflow, integration) and Jad
  (Builder, approvals, submission). Issues and pull requests on GitHub.
- **Roadmap**: record real experiment results against the pass marks the founder set;
  improve evidence quality (semantic relevance, attribution); a human review queue for
  NEEDS_REVIEW findings; then the design-only phases one at a time.
- **Community**: MIT-licensed; contributions need tests and honest status labels.
- **Funding**: none assumed. Running costs stay at zero API spend by design.
