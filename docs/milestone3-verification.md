# Milestone 3 verification — 2026-11-17

> Historical record, kept unchanged below. It describes an earlier state of the project: phases 2–6
> now run through `workflow.py` (with a clickable Phase 3 prototype), and test counts have grown.
> The current status is in the [README](../README.md) and [ARCHITECTURE.md](../ARCHITECTURE.md).

## Implemented and exercised

- Typed input/output contracts, deterministic experiment-kit generation, JSON/Markdown
  reports, and a fixed responsive landing-page renderer.
- Persistent founder approval, exact-content SHA-256 binding, one-use execution,
  rejection, blocked attempts, changed-artifact rejection and compatible audit events.
- A founder-operated CLI independent of Milestone 2 and the Milestone 1 web entry point.
- Real desktop/mobile rendering in installed Microsoft Edge, including the local CTA,
  no horizontal overflow and no external HTTP(S) requests.

## Tests on Jad's machine

Environment: Windows 11 Enterprise, Python 3.11.9, about 15.7 GiB total RAM (under
2 GiB free during testing), Intel integrated graphics, Docker Desktop with the Compose
`app` and `ollama` services running.

- Offline host suite: **215 passed, 28 skipped** (skips are the opt-in live and browser
  tests), including all Milestone 1 tests.
- Real-browser suites (`VENTURELAB_BROWSER_TESTS=1`, installed Edge): **20 passed**,
  desktop 1280x900 and mobile 390x844, no horizontal overflow, no external requests.
- Linux container (`python:3.11-slim` app image, repository mounted) with
  `VENTURELAB_LIVE_TESTS=1`: **110 passed** across all Milestone 3 test files, including
  `tests/test_builder_live.py` against the Compose Ollama service.

Live model: **executed** with `qwen3:0.6b` through the Compose Ollama service. The
preferred `qwen3:4b` was not loaded because free RAM was below its requirement. The
model's only role is choosing which supplied assumption to test; its output is an
index that is range-checked, so it cannot introduce prose, findings or HTML.

## Actual approved pipeline run

The input is `inputs/venturelab.json`, based on the actual VentureLab project concept
provided by Jad, with three founder assumptions. No supporting market evidence was
supplied. All market statements are assumptions, and no interviews or experiments
have been performed.

- Run: `venturelab-m3`
- Action: `0b69ddacc62040058a1c106946667d95`
- Generator: `ollama`; model: `qwen3:0.6b` (live, in Docker); service cost: $0.00
- The model selected assumption index 0 of 3; the other two are listed as untested.
- Fingerprint: `0cefc7235291fd10ccf947919694764c4a7b855db64e9ebb344a4f3ec8dca3d0`
- Jad explicitly approved this exact fingerprint and the proposed 3-of-5 participants /
  30-day recall criterion in chat before the decide and execute commands ran.
- Execution succeeded once; a second execute of the same action was refused.

The four output files are under
`outputs/venturelab-m3/0b69ddacc62040058a1c106946667d95/`. The founder-gate receipt is
`outputs/phase3_gate_founder-approval.json`; `decision_log.json` is the exported audit
of this run. Neither was hand-authored. Exported paths are relative to the repository.
This is an approval gate, not a business GO/REPEAT/PIVOT/STOP verdict. The earlier
Codex demo (`a7f1ac1d...`) was produced by a superseded renderer and has been removed.

## Changes in the review pass

- Experiment kit: configurable `ExperimentDesign` (sample size, threshold, recall window,
  assumption index), explicit assumption under test and untested assumptions, and an
  interviewer brief naming the situation to listen for while withholding the pitch.
- Markdown report: inert but readable (no blanket backslash escaping), numbered guide.
- Model provenance is recorded as `ollama` only when the model was actually consulted.
- Approval store: HMAC-signed rows and audit chain, founder capability file, external
  spent-approval ledger, sanitized failure recording, `GateContext` blocking non-GO builds.
- CLI exports paths relative to the working directory, so receipts and the decision log
  carry no local account paths.

## Integration still required

Amen must map his real Milestone 2 outputs through `Milestone2Adapter`, integrate
approval presentation and authenticated founder decisions into the future UI, merge
real action logs, and resolve any phase-step naming overlap. No end-to-end Milestone 2
integration was tested. README and ARCHITECTURE were absent at the baseline and added
here; coordinate any overlapping documentation changes during integration.

The final submission still needs the integrated business gate output, including a
weak-idea STOP case, and the final demo video. These belong to the integrated workflow;
Milestone 3 does not fabricate them or implement a replacement Judge. Main is not
modified by this work; the feature branch is for Amen to integrate.

## File inventory

Created production modules: `agents/__init__.py`, `agents/builder.py`, `approval.py`,
`builder_models.py`, `builder_service.py`, `builder_cli.py`, `landing_page.py`, and
`prompts/builder.md`. Created real concept input: `inputs/venturelab.json`.

Created documentation: `README.md`, `ARCHITECTURE.md`, `docs/milestone3.md`, and this
verification report. Created optional test dependencies: `requirements-dev.txt`.

Created tests: `tests/test_builder.py`, `tests/test_approval.py`,
`tests/test_approval_security.py`, `tests/test_m3_audit.py`, `tests/test_builder_variety.py`,
`tests/test_builder_cli.py`, `tests/test_builder_browser.py`, `tests/test_builder_browser_audit.py`,
`tests/test_builder_live.py`, `tests/run_m3_audit.py`, the `tests/fixtures/audit_*.json` synthetic fixtures, `tests/fixtures/builder_input.json`, and
`tests/fixtures/README.md`.

Generated by the actual run: the four phase/step files listed above,
`outputs/phase3_gate_founder-approval.json`, and `decision_log.json`.

Modified only `.dockerignore` (exclude local approval state and generated outputs
from images), `.gitignore` (ignore operational state and ordinary run directories),
and `pytest.ini` (declare the opt-in browser marker). Explicitly staged the approved
demo files; no synthetic output, database, screenshot, virtual environment or secret
belongs in the commit. `CLAUDE.md`, `evidence.py`, `llm.py`, `config.py`, `app/main.py`,
`docker-compose.yml`, `Dockerfile`, and runtime `requirements.txt` are unchanged.
