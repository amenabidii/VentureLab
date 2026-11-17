# Milestone 4: founder workspace

For the subsequent critical audit, fixes, measured performance and final verdict, see [Milestone 4 QA report](milestone4-qa.md).

## Scope and implementation status

The founder interface is available at `/` and `/workspace`. The existing foundation status page is retained at `/diagnostics`; `/health`, `/health/model` and `/health/inference` retain their original behavior. This branch is based on foundation commit `b72f907` and intentionally does not import uncommitted Milestone 2 or 3 work.

| Capability | Status on this branch |
| --- | --- |
| Navigation, responsive layouts, brief validation and review | Working |
| Model availability indicator via existing `/health/model` | Working; model availability is not proof of workflow readiness |
| Evidence filtering, finding references, output rendering | Working UI; live data connection STUBBED |
| Workflow, decisions, counterfactuals and audit views | Working UI; live data connection STUBBED |
| Artifact text / inert HTML preview | Working UI; Builder connection STUBBED |
| Approval review | Working UI; backend connection STUBBED; approval controls disabled |
| Run creation / authoritative brief validation | STUBBED, owned by Milestone 2 |
| Artifact generation / authorization / approval persistence | STUBBED, owned by Milestone 3 |
| Commercial Setup, Launch, Operate & Learn | Future architecture / STUBBED |
| Demo data | MOCKED synthetic UI fixtures; never execution results |
| Payments, external publishing, messaging and signing | Not implemented |

No production run, evidence, decision, audit entry or artifact is fabricated. An explicit **Explore demo** button opts into synthetic examples. A banner remains visible throughout demo navigation. Reloading restores the empty live workspace. Fixtures reside only in the UI module, not in `outputs/` or `decision_log.json`.

## Architecture and files

- `app/ui/router.py`: FastAPI router for the HTML shell and a fixed asset allowlist. It sets a restrictive CSP and serves no domain operations.
- `app/ui/static/index.html`: semantic application shell, skip link, navigation and mode/model status.
- `app/ui/static/styles.css`: responsive design system and reduced-motion support.
- `app/ui/static/app.js`: navigation, in-memory brief state, asynchronous loading, error/retry handling, mode switching, filtering, artifact preview, backend-bound submission/approval handlers.
- `app/ui/static/views.js`: pure, escaped renderers for eleven screens and shared presentation components.
- `app/ui/static/contracts.js`: provisional JSDoc types, local usability validation, safe external URL handling and filtering.
- `app/ui/static/service.js`: centralized asynchronous adapter boundary. No invented HTTP paths.
- `app/ui/static/normalize.js`: runtime presentation validation, payload limits, backend field-error mapping and approval display guards.
- `app/ui/static/preview.js`: passive HTML reconstruction inside an opaque sandbox.
- `app/ui/static/fixtures.js`: explicitly MOCKED examples for UI development.
- `tests/test_ui.py`: delivery, headers, assets and read-only route checks.
- `tests/ui/`: Node unit tests and actual Playwright browser interactions; dependencies are test-only.
- `app/main.py`: only the old root route moves to `/diagnostics` and the new router is registered. Coordinate those two edits when integrating other workstreams.

The interface uses native browser modules, CSS and system fonts. There are no runtime JavaScript packages, external font/icon services, paid services or frontend build steps. The existing Dockerfile copies and serves the assets without modification. Playwright, axe-core and Prettier are development-only dependencies pinned in `tests/ui/package-lock.json`; Node is unnecessary in the production image.

## Screens and navigation

Hash routes preserve a simple deployment and browser back/forward behavior:

| Route | Function |
| --- | --- |
| `#dashboard` | Entry point, empty run list, real run selector when supplied, phases, readiness and recent decision |
| `#brief` | Idea, market, customer, problem, skills, time, budget/currency, values, constraints and optional source URLs; validation and review |
| `#workflow` | Four agent statuses and task descriptions; optional polling for connected workflows |
| `#evidence` | Standing/type filters, source links, quotations, assessments, limitations and assumptions |
| `#evidence/<finding-id>` | Opens the referenced finding |
| `#challenger` | Concern basis, risks, evidence references, missing information and experiments |
| `#decision` | Returned gate outcome and exact rule, evidence, missing information, risks and next action |
| `#counterfactual` | Unmet requirement, evidence limitations, proposed experiment, strengthening/weakening signals and reconsideration gate |
| `#artifacts` | Read-only text and inert HTML previews with identity, fingerprint and approval status |
| `#approvals` | Precisely scoped request review; backend confirmation required |
| `#history` | Agent-filtered audit records with timestamp, model, sources, cost, approval and outcome |
| `#roadmap` | Six phases, purpose, outputs, gates and explicit availability |

Only the current selected run supplies output screens. Dashboard run buttons select the run. Recorded runs can carry `recordedAt`, displayed with their timestamp. Costs and severities are displayed only when supplied; no confidence percentages or startup success statistics are inferred.

## Design system and accessibility

The palette uses deep navy navigation, neutral page surfaces, teal primary actions, green established/success states, amber review states and red failed/contradictory states. Status text accompanies every color. System typography, restrained borders and consistent card spacing emphasize evidence over decoration.

Layouts adapt at 1150px and 760px. Mobile navigation scrolls horizontally; audit tables scroll within their own container. Controls have labels, visible focus states and native keyboard behavior. Form errors are associated with fields and focus moves to the first invalid input. Navigation updates the document title and focuses the main region. Details/summary elements support keyboard expansion. Loading and error messages use status/alert roles. Reduced motion disables the loading animation. Manual assistive-technology verification remains recommended; this is not a formal accessibility certification.

## Provisional contracts and adapter boundary

`contracts.js` defines presentation types for `FounderBrief`, `Run`, `AgentStatus`, `Finding`, `Challenge`, `Decision`, `Counterfactual`, `Artifact`, `Approval` and `AuditEntry`. These are provisional presentation types, not authoritative domain schemas. `normalize.js` now validates responses before rendering, rejects invalid critical classifications/identities and bounds payloads. Missing optional text is explicitly marked Not provided; missing lists become empty lists; missing costs remain null. Integrating adapters must map authoritative backend schemas into this boundary without inventing data.

Implement or replace the methods in `WorkspaceService`; keep endpoint choices centralized there:

| Method | Expected result / boundary |
| --- | --- |
| `listRuns()` | `Run[]` from actual persisted runs |
| `createRun(brief)` | Persisted `Run`; authoritative validation and durable job creation belong to Milestone 2 |
| `getRunStatus(runId)` | `AgentStatus[]`; actual task/status, never simulated progression |
| `getFindings(runId)` | `Finding[]`; standing and source relationship are separate fields |
| `getChallenges(runId)` | `Challenge[]`; preserve concern basis and finding IDs |
| `getDecision(runId)` | `Decision` or `null`; preserve the deterministic rule/outcome exactly |
| `getCounterfactual(runId)` | `Counterfactual` or `null`; hypothetical evidence must remain hypothetical |
| `listArtifacts(runId)` | `Artifact[]`; bounded content, no arbitrary local paths |
| `getApprovals(runId)` | `Approval[]`; server-owned status and exact identity/fingerprint |
| `decideApproval(request, choice)` | A complete confirmed Approval object with matching identity, action, fingerprint and terminal status; refetch authoritative request state before displaying the changed status |
| `getAudit(runId)` | `AuditEntry[]`; normalize authoritative Milestone 2 schema, preserving null/absent values |

Capabilities default to `false`: `createRun`, `workflow`, `approvals`. Enable each only after its backend implementation, authorization and error mapping have been verified. Demo mode must never enable approval or execution. The live fallback returns empty lists and null decisions, not fixtures. Both mutation methods throw `UnavailableError` on this branch even if called directly.

No workflow URL is proposed as an existing endpoint. The only fetched endpoint is the inspected `/health/model`, refreshed every 30 seconds with a 15-second status-check timeout. Actual inference is not subject to that timeout. Integrate long-running analysis as durable run creation followed by status retrieval; `workflow` enables polling five seconds after the preceding read completes while the workflow screen is visible. Navigation does not start overlapping reads. Do not hold a frontend request open expecting immediate model completion. Run creation and approval retries require server-side idempotency; the UI does not automatically retry mutations after ambiguous failures.

### Milestone 2 integration

1. Confirm the actual run, brief, evidence, decision, counterfactual and audit APIs/schemas. Map them in `service.js` to the runtime-validated presentation contracts in `normalize.js`; add tests against real responses, including malformed data.
2. Map presentation brief keys to the authoritative brief schema; map server field errors to `BriefValidationError` from `normalize.js`. The UI preserves input and focuses the invalid field; ambiguous transport failures lock resubmission to avoid blind duplicates. Preserve user-entered values rather than inventing missing details.
3. Supply persisted run IDs and real statuses. Preserve timestamps for recorded runs.
4. Preserve findings, classifications, quotations, limitations and source URLs without promoting assumptions to established evidence.
5. Enable run creation and workflow capabilities only once working. Add contract tests against the actual backend, including slow jobs, failures and stale responses.

### Milestone 3 integration

1. Return bounded artifact text/content through authorized API responses, not raw local file paths or unrestricted file-serving URLs.
2. Bind every approval to request ID, run ID, action, artifact ID and content fingerprint/version. Validate all of them on the backend.
3. Reject stale, altered, already-decided or unauthorized requests on the server. Add CSRF protection if cookie-based authentication is introduced.
4. Make only explicitly permitted local operations available. No external publishing, messaging, payment or signing paths belong in this interface.
5. Enable approval capability only after real confirmation/refetch behavior is covered by integration tests. The current buttons are intentionally disabled.

## Startup

From this worktree:

```sh
docker compose up
```

Open `http://localhost:8000/` (or `/workspace`). The existing stack downloads its configured free open-weight model through Ollama. The UI loads without waiting for model readiness. The default model remains `qwen3:4b`; no model configuration changed.

Do not start the default Compose project over another developer's running stack. For an isolated complete stack, choose another project and port, for example in PowerShell:

```powershell
$env:APP_PORT = '8766'
docker compose -p venturelab-m4 up --build
```

For frontend development without Docker:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

A missing Ollama service produces an honest unavailable status; it does not prevent the UI from loading. Brief drafts remain in memory in the current tab only. Reloading clears them; no credentials or founder data are persisted in browser storage.

## Testing

```powershell
.\.venv\Scripts\python -m pytest -q
cd tests/ui
npm ci
npm test
npm run test:browser
```

Node 22.7+ is required for the test tools (verified with Node 26). Browser tests start their own local server on port 8765 using the worktree `.venv`. They default to installed Microsoft Edge on Windows. Set `UI_BROWSER=chrome` to use installed Chrome. On other platforms adapt the Python executable in `playwright.config.mjs` and install/select a supported browser. Browser test outputs and screenshots live under ignored `.pytest_cache/`.

The browser suite uses an explicitly mocked health response, synthetic fixtures and injected test-only service failures. It does not claim to test actual model inference or domain approval enforcement. Python's existing live-model tests are opt-in and require a running Ollama model.

Coverage includes startup and headers, every navigation view, required brief fields and numeric bounds, review and draft retention, empty states, loading/error/retry, evidence standing/type filters, source safety, finding references, all four decision renderings, counterfactual copy, inert artifact previews, disabled approval, audit filtering, HTML injection, keyboard focus and responsive overflow checks.

## Security and safety

- Text is escaped at render boundaries; text previews use `textContent`.
- External source links permit only HTTP/HTTPS without embedded credentials and use `noopener noreferrer` plus a no-referrer document policy. The frontend never fetches user source URLs.
- HTML previews use an opaque sandboxed iframe, reconstruct only an allowlisted passive HTML vocabulary with no copied attributes from inert template content, and add a deny-all CSP. Scripts, forms, external assets and navigation links are disabled. Styling is intentionally stripped; this is a content preview, not a full-fidelity landing-page renderer.
- Assets are served from a fixed allowlist. No local artifact paths, private configuration or arbitrary filenames are exposed.
- Approval cannot be granted locally; disabled controls and throwing adapters are not a substitute for future backend authorization.
- No external side effects, payments, credentials, telemetry, persistent browser storage or paid APIs are introduced.
- Demo material is explicitly synthetic and separate from live data. No execution outputs or decision logs were fabricated.

## Known limitations and handoff

Live M2/M3 integrations are unavailable on the inspected foundation and remain STUBBED. Their exact contracts must be agreed during integration. The UI supplies provisional types and rendering, not a backend orchestration or approval implementation. It does not persist drafts across reloads or provide accounts/multi-user access control. The six-phase view expresses planned architecture; it cannot infer real phase completion without backend data. HTML previews deliberately sacrifice visual fidelity for a safe content review.

Project-wide README/ARCHITECTURE, official CLAUDE.md, model settings, Dockerfile/Compose definitions and all M2/M3-owned modules are unchanged. The only packaging adjustment adds `**/node_modules` to `.dockerignore` so nested test dependencies are excluded from the production image. The integrating maintainer should coordinate the required project-wide capability table and final submission documentation; this isolated workstream does not rewrite those files.


## Original implementation verification (2026-11-17)

- Python suite, including all existing Milestone 1 tests: **109 passed, 7 skipped**. Seven opt-in live Ollama tests were skipped; no actual model inference was claimed. One dependency deprecation warning was reported.
- Node adapter/rendering tests: **10 passed**.
- Real Microsoft Edge browser tests: **8 passed**. Includes desktop/mobile overflow, keyboard focus, brief review, filters, references, source links, disabled approval, audit, error/retry and malicious HTML handling.
- `docker compose config --quiet`: passed.
- Final isolated Docker app image: built successfully with unchanged Dockerfile and Compose definitions. Confirmed nested test `node_modules` is absent from the image.
- Container smoke check on localhost:8766: root and health return HTTP 200; no browser JavaScript errors. Dashboard, evidence and counterfactual screenshots were visually inspected. The full Ollama/model-pull stack was not started for this UI smoke check.
- `git diff --check`: passed before staging.

The UI tests use clearly synthetic data and do not establish correctness of future M2/M3 backend integrations. Manual screen-reader testing and live integrated workflow/approval tests remain integration responsibilities.
