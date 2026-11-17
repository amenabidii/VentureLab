# Milestone 3: Builder and founder approvals

This component is independent of Milestone 2. It does not implement an Investigator,
Challenger, Judge, decision gate, workflow orchestrator, or full application UI.

## Run locally

Use Python 3.11, the same minor version as the existing Docker image:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m builder_cli prepare inputs/venturelab.json
```

On Linux/macOS use `python` from an activated virtual environment in place of the
Windows executable above. `inputs/venturelab.json` describes this repository's actual
project concept using the supplied project brief; its hypotheses are unvalidated
assumptions, not collected evidence. Synthetic unit inputs live only under tests.

`prepare` stores a pending draft in `.venturelab/builder-v2.sqlite3`. It does not write
final artifacts to `outputs/`. The deterministic mode constructs an experiment kit
from the brief; this is real template-based functionality, not a mocked model call.
Add `--model` to let the local Ollama model choose which supplied assumption to test.
The model returns only an index, which is range-checked; with one assumption the model
is not called and provenance stays `deterministic-template`. The hypothesis, interview
protocol, ethical method and proposed threshold remain deterministic.

To run with the Compose Ollama service, mount the repository into the app container:

```bash
docker compose run --rm --no-deps -v "$PWD:/srv" -e VENTURELAB_MODEL=qwen3:0.6b app \n  python -m builder_cli --state .venturelab/demo-run.sqlite3 prepare inputs/venturelab.json --model
```

Use the same `--state` (and container) for `inspect`, `decide` and `execute`: the store
records its absolute output root and refuses a different one.
There is no silent fallback if the model fails. The model never writes HTML.

For host Ollama, set `OLLAMA_BASE_URL=http://localhost:11434` in the process environment.
For container execution the existing Compose environment points to the Ollama service.
The preferred model is `qwen3:4b`; `qwen3:1.7b` is an explicit lower-resource choice.
Do not load a model without enough available RAM. No paid API is used.

## Review, approve or reject, then generate

The founder runs these commands, substituting the action ID and SHA-256 returned by
`prepare`. Inspection includes all exact HTML/JSON/Markdown content and destination:

```text
python -m builder_cli inspect ACTION_ID
python -m builder_cli decide ACTION_ID approve --sha256 SHA256 --reason "Reviewed concept, copy and proposed experiment criteria"
python -m builder_cli execute ACTION_ID
```

To reject, use `reject` instead of `approve`. A rejected request cannot be reversed;
prepare a new request after revisions. To revise thresholds before approval, use the
typed Python interface to replace `Criterion` in the bundle, then create a new request.
The numerical thresholds remain labelled PROPOSED ASSUMPTION in the immutable kit;
the approval record is the authoritative record of founder acceptance. Approval does
not turn a threshold, concept or market claim into evidence.

The result identifies the local directory and four generated files:

- `phase2_step1_validation-kit.json`
- `phase2_step1_validation-kit.md`
- `phase3_step1_landing-spec.json`
- `phase3_step1_landing-page.html`

Each action has a separate directory under `outputs/RUN_ID/ACTION_ID/`; filenames
follow the official phase/step convention. Open the HTML file directly in a browser.
There is no build step, external asset, script, form or network call. The CTA moves
to the concept section only. Product copy is HTML-escaped and labelled ASSUMPTION.
The page is a local validation artifact, not a functioning SaaS or validated business.

`--state PATH` and `--outputs DIRECTORY` are global options placed before the command.
Use the same paths for every command in a run. The resolved destination is part of
the approval request and cannot change during execution.

## Data contracts

All models reject unknown fields. Text has length limits; run/action identifiers
exclude path separators. Input lists use immutable tuples. Schemas are available
through each model's `model_json_schema()` method.

| Contract | Main fields |
|---|---|
| `BuilderInput` | run_id, business_idea, target_customer, core_problem, main_assumptions, supporting_evidence, founder_constraints, product_category=digital_product, experiment_design, optional gate_context |
| `ExperimentDesign` | sample_size, success_minimum, recall_days, assumption_index (all proposed assumptions until approved) |
| `GateContext` | decision_id, outcome GO/REPEAT/PIVOT/STOP from Milestone 2; any outcome other than GO blocks the landing-page build |
| `EvidenceReference` | statement, HTTP(S) source_url, standing=UNVERIFIED_CONTEXT |
| `ExperimentKit` | hypothesis, assumption_index, assumption_under_test, untested_assumptions, target_audience, interviewer_brief, interview_questions, validation_experiment, success_criteria, failure_criteria, recommended_next_steps, constraints, evidence, results_status |
| `Criterion` | metric, threshold, sample_size, explicit proposed-assumption label |
| `LandingPageSpec` | product_name, headline, value_proposition, target_audience, problem, proposed_solution, features, fixed local CTA |
| `ArtifactBundle` | run_id, artifact_identity, brief, kit, landing_page, model, generator; deterministic files() and fingerprint() |
| `ApprovalRequest` | action_id, action_type, run_id, artifact_identity, artifact_sha256, description, status, destination |
| `ApprovalDecision` | action_id, artifact_sha256, approve/reject decision, actor=founder, reason |
| `BuilderResult` | action_id, run_id, artifact_sha256, output_directory, files, executed status |
| `AuditEvent` | timestamp, agent, action, sources, model, cost=0, approved_by, action_id, run_id, artifact_sha256, artifact_identity, action_type, destination, outcome |

## Approval enforcement and limits

Only `generate_local_artifacts` exists. Export, sending and publishing are not stubbed
actions and have no executable implementation. A generation approval authorizes none
of those actions. The SHA-256 covers inputs, model metadata, filenames and exact rendered
bytes, so changes to either content or renderer require a new approval.

SQLite uses transactions to serialize decisions and atomically consume execution
authority before file I/O. Pending, rejected, missing, changed, consumed or mismatched
requests cannot execute. Terminal outcomes are executed or failed_execution, with
executing recording an in-progress attempt. A process crash after consumption leaves
the request consumed/executing; never retry it automatically. Inspect any partial
files and create a new reviewed request. Failures never delete or overwrite files.

Output uses exclusive file creation and rejects symlink/junction escapes under the
configured root. Keep the database and output directory owned by the trusted local
user; this is not protection against a malicious process with filesystem access or
an administrator racing path changes. Do not put approval storage on a network share.

Decisions additionally require the founder capability file (`<state>.founder`, created
with the store); the `actor` text alone never authorizes. Approval rows and the audit
chain are HMAC-signed with `<state>.key`, and consumed approvals are recorded in
`<state>.spent/`, so editing the database cannot forge, replay or truncate approvals.
The local OS user is the founder identity boundary. There is deliberately no HTTP
approval endpoint and no claim of multi-user authentication. Agents must not be given
the decision method/CLI as a tool. A future UI must authenticate the founder and call
`decide` server-side; never trust an `actor` field supplied by a remote caller.

Conservative content rules reject common prohibited claims and product categories.
They are not semantic truth verification: euphemisms, novel wording, sensitive content
and misrepresented identities still require founder review. Supplied sources are
retained as unverified context; Builder never promotes evidence standing. Interview
results are never synthesized, and this module makes no GO/REPEAT/PIVOT/STOP decision.

## Audit and integration with Amen

`python -m builder_cli audit` prints real persisted events using the official
decision-log keys. Do not replace Amen's decision log or commit test logs as demo evidence.
`python -m builder_cli receipt ACTION_ID` prints the actual founder-gate record and
its related audit events; this is an operational receipt, not a business gate verdict.
Merge those events into the real run's log through the eventual orchestration owner.
The database contains local operational state and is ignored by Git.

Amen must implement `Milestone2Adapter.to_builder_input()` against his actual schemas,
preserving source URLs and keeping evidence standing owned by Milestone 2. He must
select the correct workflow moment for `prepare`, present the exact request to the
founder, call the protected decision path, and then execute the same action. Namespace
the phase/step filenames if his outputs use the same step numbers. Integrate audit
events without overwriting other agent actions. The existing FastAPI entry point is
unchanged, including its Milestone 1 feature-status display; update it when integration
is real. No Milestone 2 integration has been tested here.

## Tests

```text
python -m pytest -q
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

Set `VENTURELAB_BROWSER_TESTS=1` to enable real desktop/mobile rendering tests. Set
`VENTURELAB_BROWSER_CHANNEL=msedge` to use installed Edge instead of downloading Chromium.
Set `VENTURELAB_LIVE_TESTS=1` to enable actual Ollama tests. The isolated Builder live
test is `tests/test_builder_live.py`. Live tests use labelled synthetic inputs and
are not demo evidence. Offline model tests use the existing explicitly MOCKED transport.

On Windows sandbox paths that exceed filesystem path limits, create `.venturelab`
and run pytest with `--basetemp .venturelab/test-temp` (a dedicated disposable test
directory). Browser and Docker tests may require normal host execution outside an
OS application sandbox.
