# Stage 1 readiness review

> Historical record, kept unchanged below. It describes an earlier state of the project: phases 2–6
> now run through `workflow.py` (with a clickable Phase 3 prototype), and test counts have grown.
> The current status is in the [README](../README.md) and [ARCHITECTURE.md](../ARCHITECTURE.md).

Baseline: `origin/main` at `93df7bf`. Scope: application, repository and architecture;
Stage 2 pitch and three-minute video are excluded. This is a coverage assessment,
not an estimated competition score or a claim about placement.

| Criterion | Repository evidence and improvements | Remaining limitation |
|---|---|---|
| Prototype (25%) | Integrated founder brief → research → challenge → deterministic decision → approval-gated local kit. Genuine committed executions now open directly in the workspace without the original SQLite database. | Local model and internet needed for new research. No corrected-rule recorded GO. Later phases are not executable. |
| Architecture (20%) | `ARCHITECTURE.md` now details every phase: alternative scoring, market definition, behavioural interviews, Lean Canvas, demand test, tested MVP and docs, pricing/policies, store/posts/mock fulfillment, support/metrics/persevere-pivot loop. | Detailed designs are explicitly STUBBED; a passive landing page is not a fully generated MVP. |
| Evidence and honesty (15%) | Source-specific exact quotations; inspectable recorded gate checks, inputs and thresholds; historical decisions retain their original result and rule version. Nine genuine executions indexed with checksums and audit provenance. | Checksums establish file consistency, not factual truth. Source relevance and customer attribution still depend partly on model judgments. Superseded GO decisions cannot authorize new work. |
| Founder control and safety (15%) | Existing key/fingerprint/expiry/single-use enforcement retained. Read-only recordings cannot create runs, prepare artifacts, approve or execute. The approval form now preserves the founder's typed reason. | Single-machine founder capability, not multi-user authentication. Future publishing/sending/delivery remain unimplemented. |
| Reproducibility and cost (10%) | Existing pinned local open-weight stack, Compose quickstart and $0 paid API cost; read-only history works while the model is unavailable. Missing or modified recorded files produce explicit errors. | Hardware, electricity and retrieval connectivity remain requirements for new runs. Historical timings are not guaranteed. |
| Pitch (15%) | Excluded from this review. | No Stage 2 work performed. |

## Verification

- Full Python suite: 485 passed, 41 skipped (opt-in/environment-dependent checks).
- Added history tests: nine pass locally and in the Compose-mounted container, covering genuine records, superseded GO, tampering,
  missing files, unsafe paths, malformed index and unknown identity.
- Interface unit checks: 22 pass, including source pairing, hostile text, retry and
  refusal of mutations in recorded mode.
- Browser checks: 28 existing tests and two focused regressions pass, covering the
  typed approval reason and genuine history on a narrow screen with accessibility
  checks. Browser network/model substitutes remain test-only and explicitly mocked.
- No historical execution output or audit log was rewritten. The manifest is derived
  from tracked outputs and matching actual audit entries with
  `python tools/index_recordings.py`.

## Highest-value remaining product work

1. Record actual validation observations against pre-agreed criteria, with provenance
   and explicit denominators. This would close the learning loop rather than only
   generating experiment plans.
2. Add a versioned Lean Canvas linked to evidence and assumptions.
3. Demonstrate a complete narrow MVP with its own acceptance tests and user guide;
   do not count VentureLab's tests as tests of a generated product.
4. Implement local-only MOCKED fulfillment and reconciliation with duplicate-event
   and refund-revocation checks. No real or sandbox payments.

The default branch is the submission artifact. Improvements on a feature branch do
not count as submitted until integrated into `main` before the applicable freeze.
