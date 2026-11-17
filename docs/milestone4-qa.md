# Milestone 4 final QA and usability audit

Date: 2026-11-17. Audited foundation: `2aafd7f8c120aa14366d0d49d84d790f3c519c14`. Scope: the existing isolated `feature/milestone4-ui` worktree only. No M2/M3 integration was started.

## Verdict: CONDITIONAL PASS

The founder interface passes the local functional, security-regression, responsive and automated accessibility checks described below. It is ready for controlled backend integration work. It is **not a verified end-to-end venture system or a production-readiness certification**. Actual research, gate evaluation, Builder generation and approval authorization remain STUBBED on this branch. Their authoritative contracts, security enforcement and live integration tests are still required.

## Defects found and corrected

| Finding | Impact | Correction |
| --- | --- | --- |
| Prototype-property hash routes such as `#constructor` passed a truthiness lookup | Navigation could crash | Own-property route allowlist; malformed and unknown hashes fall back safely |
| Skip link changed the hash to an unknown route | Skipping navigation reset the current screen | Explicit main-region focus without changing the route |
| Mode/run transitions retained old data while requests were pending | Navigating during a slow transition could expose demo data under live labeling | Clear data on mode/run changes, persistent loading/error state and stale-response epochs |
| Partial response failures were lost when navigating away and back | Failed reads could appear as empty records or stale outputs | Per-section errors persist; unaffected sections remain usable |
| A selected/new run absent from the list fell back to the first run | Another venture's outputs could be shown after creation | Preserve selected identity; show an unavailable-run error and never substitute another run |
| Agent output links used array indices | Reordered backend roles linked to incorrect outputs | Role-keyed destinations |
| Missing fields and wrong types were not validated at runtime | Render exceptions; unknown outcomes/classifications could be displayed | Central presentation normalizer with strict critical fields, explicit absent values and payload limits |
| Null/whitespace/coercible numeric inputs and missing source arrays were mishandled | Malformed briefs could pass validation or throw | Type-aware numeric checks, precision bound and optional-source handling |
| All submission errors were generic; successful review could be resubmitted | Backend corrections were unusable; duplicate-run risk | Backend field-error mapping, retained input, confirmed-submission state and ambiguous-failure retry lock |
| Approval handling lacked expiry/version/run checks and acknowledgment validation | Future integration could expose stale controls or accept mismatched confirmation | UI checks exact scope and terminal state, locks duplicate/uncertain actions, verifies response identity, and refetches authoritative records |
| Missing finding IDs produced dead navigation links | Founder could not distinguish missing evidence | Explicit unavailable-reference labels and direct-reference missing states |
| Source labels hid missing or malformed URLs | Attribution appeared inspectable when no safe link existed | Explicit missing/disabled source labels; strict HTTP/HTTPS URLs without credentials/control characters |
| Preview parsing used DOMParser before stripping active content | Some parsed resource-bearing nodes can load before sanitization | Inert template parsing and reconstruction of passive tags with no attributes, plus deny-all sandbox CSP |
| Closing a preview focused the first artifact button | Keyboard users lost their position | Return focus to the actual triggering artifact |
| Evidence rendering built every finding's DOM and long strings could expand cards | Large result sets and mobile content degraded usability | 50-row evidence pages, direct-reference page selection and long-text wrapping |
| Failed model refresh left the ready CSS class | Stale visual readiness cue | Validate health shape and clear readiness styling on errors |
| Status scheduling could overlap a slow read after navigation | Unnecessary requests and discarded progress | Read-count guard and completion-based polling; stops outside the visible workflow view |
| Diagnostics link relied only on color | Automated WCAG link differentiation violation | Persistent underline; automated scan now passes |
| Discover roadmap label said In progress without an actual run | Could imply execution | Explicit Intake working / Research STUBBED capability label |

No backend decision, approval, artifact-generation or evidence-retrieval logic was recreated. UI approval checks are defense in depth and cannot replace server authorization.

## Functional coverage

All ten screens and the roadmap were exercised in a real Microsoft Edge browser. Navigation, live empty states and unmistakable demo labeling were checked. Brief tests include missing fields, invalid numeric values, a 4,000-character boundary, Unicode, HTML-shaped text, review/edit, backend validation, refresh clearing, and slow-read preservation. Submission and approval scenarios use **test-only synthetic transports**, never production backend claims.

Evidence tests cover every standing, independent relationships including contradiction, type/standing filters, source targets and `noopener noreferrer`, absent/unsafe URLs, missing references, direct references across pages and 100,000-character quotations. All four gate outcomes are rendered with explicitly synthetic rule identifiers. Counterfactual language does not promise GO.

Artifact tests cover text experiment/interview content, HTML previews, hostile scripts, external-resource URLs, frames, forms, SVG, refresh redirects and local-file URLs. A 400,000-character text preview and a 5,000-finding list fit a 390px viewport. Approval tests cover pending, approved, rejected, expired, invalid, missing backend/artifact, changed fingerprints, wrong run, network failure, mismatched confirmation and repeated clicks. No success is fabricated locally.

## Test results

- Python suite: **116 passed, 7 skipped**. Includes all existing M1 tests plus UI delivery, security headers, configuration denial and encoded traversal cases. Skipped cases require opt-in live Ollama inference. One upstream deprecation warning remains.
- Node adapter/rendering suite: **20 passed**.
- Browser suite: **27 passed**: existing eight interactions plus nineteen audit regressions, including a completion-based polling test.
- Automated axe WCAG 2 A/AA and 2.1 AA scan: zero violations across all eleven demo views after fixing the diagnostics link. Text contrast and programmatically associated labels passed the automated checks.
- Docker Compose configuration, image build, startup and real browser smoke checks pass. Root and `/health` return 200; new module assets return 200; non-allowlisted `package.json` returns 404. The actual model health endpoint reports `qwen3:4b · Not ready` in the isolated smoke container. No JavaScript page errors were observed. Test-only Node dependencies are absent from the image.

Added regression coverage totals seven Python tests, ten Node tests and nineteen browser tests. Test-only Playwright/axe mocks are clearly confined to `tests/ui/`. Generated browser results and measurement JSON stay in ignored `.pytest_cache/`.

The immediate smoke attempt during container recreation raced startup; repeating after Docker reported the container healthy passed. The full Ollama/model-pull stack was not started for the UI smoke check. No live inference, live M2/M3 execution, backend authorization enforcement, cross-browser certification, manual screen-reader testing or prolonged soak test is claimed.

## Accessibility and security findings

Keyboard navigation, visible control focus, error association, skip behavior and preview focus restoration are checked. Native disclosure controls and semantic tables remain in use. Automated checks are practical evidence, not a substitute for manual NVDA/VoiceOver testing after integration. Disabled controls remain intentionally unavailable in production mode.

All untrusted text passes through escaping or textContent. HTML previews are an opaque sandbox with no scripts, forms, navigation attributes, external resources or local paths. Browser tests observe requests and dialogs, not just the presence of sandbox attributes. Fixed asset allowlisting rejects encoded traversal and configuration access. Source URLs are never fetched by the frontend. Unknown evidence standings and gate outcomes fail closed; no percentages, activity totals or approvals are invented. No credentials, persistent founder storage, paid runtime dependencies or external side effects were added.

## Performance measurements

Measured on this local Windows host with headless Microsoft Edge, no CPU throttling and a synthetic 5,000-finding response. The test transport is local; these numbers do not estimate backend inference or remote network latency.

| Measurement | Observed run |
| --- | ---: |
| Initial DOM ready, large synthetic response | 359.5 ms |
| Navigation median over 20 transitions | 33.7 ms |
| Navigation p95 over 20 transitions | 39.6 ms |
| Filtering 5,000 findings | 60.8 ms |
| Finding elements in the DOM | 50 |
| JS heap after forced GC, before transitions | 4.53 MiB |
| JS heap after forced GC, after transitions | 4.68 MiB |

The approximately 149 KiB retained-heap increase is a bounded observation over this short run, not proof of absence of leaks. Measurements vary between runs; the executable benchmark writes the most recent values to `.pytest_cache/audit-metrics.json`. There was one initial model-health request across normal navigation, no inference calls, and no external requests. Model health refreshes every 30 seconds while visible. Workflow polling waits for reads to complete and stops when its view is not active/visible.

## Exact integration dependencies

The adapter method map in [the development handoff](milestone4-ui.md#provisional-contracts-and-adapter-boundary) remains the integration entry point; no speculative URLs were introduced. `normalize.js` is a **presentation contract**, not an authoritative domain schema.

M2 must supply persisted run identity, real progress, founder-brief acceptance/field errors, findings with explicit standing, Challenger references, deterministic decisions with exact rule IDs, counterfactual explanations and audit events. Map backend field errors into `BriefValidationError`. Run creation must return the persisted run object; support eventual list visibility without substituting another run. Actual durable-job polling, retry/idempotency semantics and status freshness must be tested with the real backend.

M3 must supply authorized bounded artifact content, identity/fingerprint and approval requests. Approval requests need `id`, `runId`, `artifactId`, `fingerprint`, `action`, `status`, and optional timezone-qualified `expiresAt`. Known terminal states are Approved, Rejected, Expired and Invalid; missing status becomes Unknown and is non-actionable. `decideApproval` must return the complete confirmed request with matching scope and the expected terminal status; the UI then refetches authoritative records. The server must reject stale fingerprints, wrong-run requests, duplicate/conflicting decisions, expired requests and unauthorized callers. Cookie authentication requires CSRF protection. Backend ownership of these controls is unchanged.

Boundary limits are 5,000 rows per collection, 8 million serialized JSON characters per response, 20,000 characters per ordinary text field, 100,000 per quotation and 500,000 per artifact body. Oversized/invalid critical data produces an error rather than silently truncating evidence. Optional text displays Not provided; costs remain null when absent. Source URLs that cannot be safely linked remain visibly disabled. For datasets beyond these limits, agree server-side pagination before increasing limits. Evidence DOM pagination is already implemented.

Remaining STUBBED functionality: production run creation/research, agent execution, evidence retrieval, deterministic gate/counterfactual APIs, Builder generation, real approval persistence and audit APIs. Phases 4–6 remain future architecture. No final integration was attempted. Drafts still intentionally clear on reload, and HTML previews intentionally omit styling/active content.

## Reproduction

From this isolated worktree:

```powershell
.\.venv\Scripts\python -m pytest -q
npm --prefix tests/ui ci
npm --prefix tests/ui test
npm --prefix tests/ui run test:browser
docker compose -p venturelab-m4-qa config --quiet
docker compose -p venturelab-m4-qa build app
docker compose -p venturelab-m4-qa run --no-deps -d --name venturelab-m4-qa-ui -p 127.0.0.1:8767:8000 app
```

The smoke container name/port must be free before repeating the final command. The default `docker compose up` startup remains compatible and unchanged. The QA project/port isolates this test from other workstreams.
