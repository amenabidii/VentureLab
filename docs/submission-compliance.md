# Submission compliance matrix

Checked on 2026-11-17 against the repository's `CLAUDE.md` (the conventions file;
the hackathon case brief and slides are not in the repository and were not reviewed
here). Scope: first written on branch `feature/milestone5-submission`; statuses updated
on the integration branch `integration/venturelab-complete` after Milestones 2 to 5 were
merged and the integrated application was run end to end.
Statuses: PASS, FAIL, PENDING INTEGRATION, NOT VERIFIED, STUBBED, NOT APPLICABLE.
"Automated" means `tests/test_submission_compliance.py`.

## Mandatory repository items

| Requirement | Source | Where | Verification | Status |
|---|---|---|---|---|
| `README.md` with the 8 headings in order | CLAUDE.md | `README.md` | automated heading test | PASS (was missing on `main`) |
| Quickstart bash block with `docker compose up` | CLAUDE.md | README Quickstart | automated | PASS |
| Status table with Working / MOCKED / STUBBED | CLAUDE.md | README | automated label check, manual review against code | PASS |
| Cost per run with a `$` figure | CLAUDE.md | README | automated; figure is API cost only, local costs described | PASS |
| `LICENSE`, OSI-approved, full text | CLAUDE.md | `LICENSE` (MIT, © 2026 Mohamed Amen Allah Abidi) | automated full-text phrases; no conflicting license text found | PASS |
| `docker-compose.yml`, one-command setup | CLAUDE.md | `docker-compose.yml` | integrated stack built and started with `docker compose up`; health, model and API checked | PASS (warm Docker cache; a cold clean-clone build of the integrated tree was not repeated) |
| `decision_log.json`, required keys per entry | CLAUDE.md | `decision_log.json` (log of the integrated application's genuine runs; earlier milestone logs archived unchanged in `docs/history/`) | automated schema test | PASS |
| `outputs/` named by phase/step, text, small | CLAUDE.md | `outputs/` | automated name, type and size test | PASS |
| At least one gate decision | CLAUDE.md | `outputs/phase1_gate_decision*.json` | automated | PASS |
| STOP shown for a weak idea | CLAUDE.md | `phase1_gate_decision_prohibited_example.*` | the only recorded STOP is a prohibited-category STOP; all real ideas ended REPEAT | PASS for a STOP; evidence-based STOP is implemented and unit-tested but not demonstrated in a real run |
| Market claims cite a URL or say ASSUMPTION | CLAUDE.md | Investigator outputs | quotes are copied by Python from retrieved text; standing per claim | PASS on recorded outputs; quality limits remain (ARCHITECTURE) |
| `tests/` smoke tests, passing | CLAUDE.md | `tests/` | 418 Python tests pass (incl. 29 compliance and 21 API integration tests), 9 live-model, 20 Builder browser, 20 UI unit and 27 UI browser tests pass | PASS |
| `ARCHITECTURE.md` with 7 sections and a text diagram | CLAUDE.md | `ARCHITECTURE.md` | automated | PASS (was missing on `main`) |
| `.env.example`, placeholders only | CLAUDE.md | `.env.example` | automated; no keys needed at all | PASS |
| `prompts/`, one file per agent prompt | CLAUDE.md | `prompts/` (5 files) | automated: every prompt is used by code and every referenced prompt exists | PASS |
| Demo video link | CLAUDE.md (SHOULD) | README | not recorded | FAIL (record it with [demo-runbook.md](demo-runbook.md)) |

## Rules on models, money and approval

| Requirement | Where | Verification | Status |
|---|---|---|---|
| No paid service required; open-weight model works locally | `config.py`, compose, `llm.py` | automated scan for paid providers; recorded runs used `qwen3:4b` locally | PASS |
| Payments sandboxed or mocked | — | project policy forbids even sandbox payments; sale to cash is design only | STUBBED (stricter rule followed; no `payment_test_log.md`) |
| Nothing published, sent, spent or signed without founder approval, in code | `approval.py`, `app/api.py` | M3 tests; API tests (missing key, wrong run, fingerprint, expiry, replay); bypass attempts refused on the live server; a real founder approval through the UI | PASS (nothing can be published or sent at all; approval covers local files only) |
| Mocks labelled MOCKED/STUBBED in README and app | README, `app/main.py` FEATURES, workspace roadmap and demo banner | manual | PASS |
| Outputs come from real runs | `outputs/`, log | `outputs/runs/<run>` and `outputs/builder/<run>` match run IDs and fingerprints in `decision_log.json` | PASS (integrated runs `run-64fdee373f244b81`, `run-2978f51dd4c040b1`) |

## Never-do list

| Rule | Evidence | Status |
|---|---|---|
| No income or success promises | gate and counterfactual text; README | PASS |
| No fake reviews, testimonials, sign-ups, timers | Builder content rules and fixed template | PASS |
| No impersonation; no accounts, passwords, card numbers | no such code on any branch | PASS |
| Prohibited product categories rejected | `brief.screen_brief`, `gates.py` STOP rule, real STOP output | PASS (keyword screen can over-match; matched words are shown) |
| No text addressing reviewers | automated scan of README, ARCHITECTURE, docs | PASS |
| No secrets or local state tracked | automated `git ls-files` check; manual scan for paths/keys | PASS |

## Adversarial and negative cases

Existing tests already cover these, so they were not duplicated here.

| Case | Covered by | Branch |
|---|---|---|
| Crypto, health, legal, financial products | `tests/test_brief.py`, `tests/test_gates.py` (`STOP_PROHIBITED_CATEGORY`) | `main` |
| Inadequate or missing evidence → REPEAT, not GO/STOP | `test_gates.py::test_missing_evidence_is_repeat_not_stop` | `main` |
| Contradictory evidence | `test_gates.py` (one source is not enough; two stop; mixed → REPEAT) | `main` |
| Unavailable sources, network failure | `test_sources.py::test_unavailable_source_is_recorded_not_invented`, `test_orchestrator.py::test_all_sources_unavailable_is_repeat_not_stop` | `main` |
| Fabricated quotations, wrong attribution, NEEDS_REVIEW not counted | `test_evidence.py`, `test_evidence_pipeline.py`, `test_gates.py::test_unconfirmed_findings_never_satisfy_the_evidence_requirement` | `main` |
| Unavailable model | `test_llm.py`, `test_startup.py` (health returns 503) | `main` |
| Unsupported commercial claims, fake social proof | `tests/test_builder.py`, `test_m3_audit.py` | M3 |
| Missing, rejected, changed, replayed approvals; forged DB status | `tests/test_approval.py`, `tests/test_approval_security.py`, `test_m3_audit.py` | M3 |
| Unsafe HTML, injection, path traversal in run IDs | `tests/test_builder.py` | M3 |
| Unauthorized external communication | no send, publish or payment code exists on any branch | all |

## Reproducibility, as actually run

- **Fresh clone of `main`** into a scratch directory, `docker compose -p vlcleancheck up
  -d --build ollama app` on port 8010 (skipping model-pull to avoid a 2.5 GB download):
  containers started healthy; `/health` 200; `/health/model` and `/health/inference`
  503 with "model not found", and the start page said the model was still
  downloading; 209 tests passed inside the container. Docker's layer cache on this
  machine was warm, so this does not measure a cold build. The isolated containers
  and volume were removed afterwards.
- The model-pull path and a live Discover run from a clean machine were not repeated
  here; recorded live runs (103–182 s each with `qwen3:4b`) are in `decision_log.json`.
- **Merge rehearsal** of all branches: see
  [integration-handoff.md](integration-handoff.md).
- **Persistent state from an empty checkout** (2026-11-17, after the integration was
  merged): the app container starts as root only to prepare `.venturelab/`, then runs as
  the owner of the mounted `outputs/` folder (UID 1000 when the mount reports root),
  never as root. Isolated Compose projects with no `.venturelab/` were tested on Docker
  Desktop for Windows (real relative bind mounts) and with Linux bind-mount semantics
  (folders inside Docker Desktop's Linux VM, where Docker creates a missing mount source
  as root) for checkouts owned by UID 0, 1000 and 1001. In every case: the app became
  healthy; a run record and its outputs were written; the approval store and founder
  key were created; execution with a wrong key or before approval was refused; a
  SIMULATED approval on a synthetic fixture wrote the files once; run state survived a
  container restart; and a replay after the restart was refused. Before the fix, the
  Linux case crash-looped with `sqlite3.OperationalError: unable to open database file`.
  The Docker layer cache was warm and no model was pulled in these tests.

## Contradictions found and how they were handled

- `CLAUDE.md` allows payments in sandbox/test mode; the team's stricter rule forbids
  any transaction. The stricter rule is followed; sale to cash is STUBBED.
- `main` had no README or ARCHITECTURE although `CLAUDE.md` requires them; the M3
  branch has its own versions. This branch provides integrated versions; take them
  when resolving the add/add conflicts.
- The `main` start page listed "Founder approval" and "Builder" as STUBBED. The
  FEATURES list in `app/main.py` was updated during integration.

## Open items before final submission

1. No demo video yet (the README says so).
2. No real run has produced GO or an evidence-based STOP; REPEAT and a category STOP are
   demonstrated live, GO and PIVOT only with constructed test fixtures. The landing page
   is therefore exercised only by tests.
3. Startup from an empty checkout is verified (see above), but a fully cold build (no
   Docker layer cache) with a fresh model pull has not been repeated.

The integration is merged: on 2026-11-17 `main` and `integration/venturelab-complete`
both pointed to `ac59e35`, and the submission is read from `main`.
