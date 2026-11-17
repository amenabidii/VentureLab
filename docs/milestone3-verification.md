# Milestone 3 verification — 2026-11-17

## Implemented and exercised

- Typed input/output contracts, deterministic experiment-kit generation, JSON/Markdown
  reports, and a fixed responsive landing-page renderer.
- Persistent founder approval, exact-content SHA-256 binding, one-use execution,
  rejection, blocked attempts, changed-artifact rejection and compatible audit events.
- A founder-operated CLI independent of Milestone 2 and the Milestone 1 web entry point.
- Real desktop/mobile rendering in installed Microsoft Edge, including the local CTA,
  no horizontal overflow and no external HTTP(S) requests.

## Tests on Jad's machine

Environment: Windows 11 Enterprise, Python 3.11.9, Git 2.56.0, about 15.7 GiB total
RAM and Intel Iris Xe integrated graphics. Installed the repository's pinned runtime
dependencies into `.venv` and Playwright 1.58.0 as an optional development dependency.
Docker Desktop, Docker CLI 29.9.3, Compose 5.7.0 and WSL were installed; no reboot was
performed and no unrelated user applications were closed.

Offline suite: **163 passed, 10 skipped**, one upstream Starlette/AnyIO deprecation
warning. This includes all existing Milestone 1 offline tests. Eight skipped tests
require real Ollama inference; two require the browser-test opt-in.

Separate real-browser suite: **2 passed**, at 1280×900 and 390×844. These tests use a
clearly labelled synthetic fixture under `tests/fixtures/`; generated test artifacts
and screenshots remain in ignored temporary state, not in the demo outputs.

Live model: **not executed on Jad's machine**. Free physical RAM fell below 0.5 GiB
after Docker startup. No Qwen model was loaded under those conditions. The optional
Ollama path has MOCKED offline tests and an opt-in live test; it must not be described
as live-verified by Milestone 3. Milestone 1's archived model benchmarks are separate.

Docker: `docker compose up -d --build app` built successfully and started the app
and its Ollama dependency. Both containers became healthy, and the host request to
`http://localhost:8000/health` returned status `ok`. `docker compose exec -T app
pytest -q` also returned **163 passed, 10 skipped** inside Linux. Verified that local
approval state was excluded from the image. The default all-services `docker compose
up` model-download/inference path was not exercised because of the available-RAM
limit; the existing Compose configuration remains unchanged.

## Actual approved pipeline run

The input is `inputs/venturelab.json`, based on the actual VentureLab project concept
provided by Jad. No supporting market evidence was supplied. All market statements
are assumptions, and no interviews or experiments have been performed.

- Run: `venturelab-m3`
- Action: `a7f1ac1da4474fe5ac845c3c1b64e023`
- Generator: `deterministic-template`; model: null; service cost: $0.00
- Fingerprint: `0dddf857b814358fba5c5eace009b995447e1a360edd506b2fad9169f3655bb4`
- Jad explicitly approved this exact artifact fingerprint and the proposed 3-of-5
  criterion in the conversation before the decision and execution commands ran.
- Execution succeeded once through `ApprovalStore.execute`.
- Verified all four files byte-for-byte against the approved bundle; rendered the
  actual demo in Edge at desktop/mobile widths and inspected the desktop screenshot.

The four actual output files are under
`outputs/venturelab-m3/a7f1ac1da4474fe5ac845c3c1b64e023/`. The founder-gate receipt is
`outputs/phase3_gate_founder-approval.json`; `decision_log.json` contains the recorded
events from this run. Neither file was populated with hand-authored sample events.
This is an approval gate, not a business GO/REPEAT/PIVOT/STOP verdict.

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
`tests/test_builder_cli.py`, `tests/test_builder_browser.py`,
`tests/test_builder_live.py`, `tests/fixtures/builder_input.json`, and
`tests/fixtures/README.md`.

Generated by the actual run: the four phase/step files listed above,
`outputs/phase3_gate_founder-approval.json`, and `decision_log.json`.

Modified only `.dockerignore` (exclude local approval state and generated outputs
from images), `.gitignore` (ignore operational state and ordinary run directories),
and `pytest.ini` (declare the opt-in browser marker). Explicitly staged the approved
demo files; no synthetic output, database, screenshot, virtual environment or secret
belongs in the commit. `CLAUDE.md`, `evidence.py`, `llm.py`, `config.py`, `app/main.py`,
`docker-compose.yml`, `Dockerfile`, and runtime `requirements.txt` are unchanged.
