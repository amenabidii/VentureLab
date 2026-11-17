# Integration handoff

For the engineer who merges the workstreams. Branch heads were observed with
`git fetch` on 2026-11-17 at about 19:20 UTC. Re-check them before merging, since
they may have moved.

## Branches

| Branch | Head | Based on | Contents |
|---|---|---|---|
| `main` | `551a9e8` | — | M1 foundation and M2 Discover workflow (brief, Investigator, Challenger, gate, counterfactual, orchestrator CLI, audit log, outputs) |
| `fix/milestone2-evidence-quality` | `ac7afd5` | `551a9e8` | Challenger grounding, relevance and provenance fixes; regenerated M2 outputs and log (5 runs) |
| `feature/milestone3-builder` | `b2a2f26` | `b72f907` | Builder, approval store, founder CLI, approved demo artifacts, own README/ARCHITECTURE/log |
| `feature/milestone4-ui` | `60281e1` | `b72f907` | Founder web UI under `/` and `/workspace`; old status page moved to `/diagnostics`; backend calls STUBBED |
| `feature/milestone5-submission` | this branch | `551a9e8` | README, ARCHITECTURE, compliance tests, submission docs |

## Merge rehearsal (not committed anywhere)

In a throwaway detached worktree from `origin/main`, the M5 files were committed, then
these were merged in order: the quality fix, then M3, then M4.

| Step | Conflicts | Resolution used |
|---|---|---|
| + `fix/milestone2-evidence-quality` | none | — |
| + `feature/milestone3-builder` | `README.md`, `ARCHITECTURE.md` (add/add) | take the M5 versions; they already describe M3. Keep `docs/milestone3*.md` |
| | `decision_log.json` (add/add) | interim: union of both arrays sorted by timestamp (63 + 5 = 68 entries, distinct `run_id`s); final: regenerate, see below |
| + `feature/milestone4-ui` | `.dockerignore` | keep both sides (`.venturelab`, `outputs`, `**/node_modules`) |

Result: the combined Python suite passed (397 passed, 29 skipped; the skips are
opt-in live-model and browser tests). M4's Node/Playwright UI tests under `tests/ui/`
were not run in the rehearsal. The merged tree was also built and started in an
isolated Compose project (port 8011, no model pulled): `/health` 200, `/` and
`/workspace` served the founder UI, `/diagnostics` said the model was still
downloading, `/health/model` returned 503, and `builder_cli`, `orchestrator` and
`approval` imported inside the image. The isolated stack was removed afterwards.
A merge that compiles is not an integrated system: no
code connects the UI, the workflow and the Builder yet.

## Interfaces still to build

1. **HTTP endpoints for the workflow** (none exist on any branch). M4's
   `app/ui/static/service.js` is the single adapter boundary and invents no paths, so
   the endpoints and the adapter must be written together. Minimum: create a run from a
   brief (validate with `brief.FounderBrief`, screen with `screen_brief`), run status,
   and read investigation, challenge, gate decision and counterfactual JSON. A live run
   takes 2–3 minutes on CPU, so it must run in the background with polling, not inside
   one request.
2. **Builder input adapter**: implement `builder_service.Milestone2Adapter.to_builder_input()`
   from the real `FounderBrief` + gate decision. Map `customer`, `problem`, assumptions
   and the gate outcome into `BuilderInput.gate_context` (any outcome other than GO
   blocks the build). Keep source URLs; Builder must not change evidence standing.
3. **Approval endpoints**: wrap `ApprovalStore.create / inspect / decide / execute`.
   The decision must authenticate the founder on the server (the current CLI reads the
   `<state>.founder` capability file); never trust an `actor` field from the browser,
   and never expose `decide` to an agent. The UI must show the backend's result, not
   its own state.
4. **One audit log**: the orchestrator appends to `decision_log.json` (`audit.py`); the
   Builder records events in its signed SQLite store and exports them with
   `builder_cli audit`. After integration, write Builder events to the same log through
   `audit.AuditLog` (same required keys) while keeping the signed store as the
   authority for approvals.

## Logs and outputs after integration

- Do not hand-merge logs for the final submission. Run the integrated demo, then commit
  that run's real `decision_log.json` and `outputs/`. The union above is only a
  placeholder that keeps both milestones' genuine events with their `run_id`s.
- Keep genuine earlier outputs only if their generator is unchanged; otherwise
  regenerate. M3's outputs are bound by fingerprint to its renderer.
- Output names: M2 writes flat `outputs/phase1_*`; M3 writes
  `outputs/<run>/<action>/phase2_step1_*` and `phase3_step1_*`. No collisions today.
  M3's `.gitignore` ignores `outputs/*/` except `outputs/venturelab-m3/`, so add a
  negation for each new run directory you commit.
- `.dockerignore` excludes `outputs` after the M3 merge; the orchestrator command
  mounts the repository (`-v "$PWD:/srv"`), so outputs still land in the checkout.

## Acceptance checklist (run after integration; none of this is done yet)

Startup
- [ ] Fresh clone, `docker compose build` succeeds with no cache
- [ ] `docker compose up` starts ollama, model-pull, app; model download completes
- [ ] `/health` 200; `/health/model` 503 before download and 200 after; `/health/inference` ok
- [ ] `/` shows the founder UI, `/diagnostics` the status page

Founder journey
- [ ] A new brief submitted in the UI is validated by the backend (errors shown per field)
- [ ] Investigator retrieves real sources (URLs visible and reachable)
- [ ] Challenger output cites real finding IDs
- [ ] Gate decision and rule ID come from `gates.py`, shown unchanged in the UI
- [ ] Evidence Explorer and Counterfactual show the run's actual data, not fixtures
- [ ] A prohibited brief stops at the category screen

Builder and approval
- [ ] Builder input comes from the adapter, not a hand-written file
- [ ] Kit and landing page generated; filenames match `phase<N>_step<M>_*`
- [ ] Preview is sandboxed (no scripts, forms or external requests)
- [ ] Missing, rejected, changed-artifact and replayed approvals are refused by the backend, and the UI shows the refusal
- [ ] Approval is authenticated server-side; the browser cannot claim to be the founder

Audit
- [ ] Every agent action appears once in `decision_log.json` with the required keys
- [ ] Model names match what actually ran; `cost` is 0 for local models
- [ ] `approved_by: "founder"` only on actions the founder actually approved

Safety
- [ ] NEEDS_REVIEW findings never count toward GO
- [ ] No send, publish or payment path exists; no secrets in outputs or logs

Submission
- [ ] `python -m pytest -q` passes, including `tests/test_submission_compliance.py`
- [ ] Outputs and log are from the integrated run; README and ARCHITECTURE statuses updated to match
- [ ] Demo video recorded and linked in README
