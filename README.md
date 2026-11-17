# VentureLab

An open-source AI co-founder for investigating digital-product ideas, challenging
unsupported assumptions, and preparing practical validation artifacts.

## Quickstart

```bash
docker compose up
```

Open [the local application](http://localhost:8000). The first model download takes
time and requires available RAM/disk space. The existing web page shows Milestone 1
health checks; Milestone 3 runs through the separate founder CLI, not the web UI.
See [Builder usage and approval instructions](docs/milestone3.md).

For host development, install Python 3.11 and `requirements.txt`, then run
`python -m builder_cli prepare inputs/venturelab.json`. Inspect, explicitly approve
or reject, and execute the resulting action as described in the guide.

## What works and what is mocked

| Step | Status |
|---|---|
| FastAPI health checks and Ollama client | **Working** — Milestone 1 foundation |
| Evidence verification primitives | **Working** — Milestone 1 tests; not the complete research workflow |
| Experiment-kit generator | **Working** — deterministic kit, JSON and Markdown; optional Ollama hypothesis drafting has MOCKED offline coverage, live test is opt-in |
| Local landing-page generator | **Working** — escaped template, responsive layout, actual desktop/mobile browser tests |
| Founder approval and local execution | **Working** — persistent, fingerprint-bound, one-use backend enforcement through the local CLI |
| Investigator, Challenger, Judge, orchestration and Counterfactual Challenge integration | **STUBBED** in this branch — Milestone 2 owned by Amen; no integration claim |
| Full founder web UI | **STUBBED** — future milestone |
| Commercial setup, external launch, delivery and learning workflows | **STUBBED** — architecture only |
| Payment processing | **STUBBED** — disabled by project policy; no real or sandbox transactions |
| Offline model transport used by unit tests | **MOCKED** — only under tests |

The generated landing page is a proposal, not evidence of demand. It has no signup
form or external communication. The [recorded demo](docs/milestone3-verification.md)
uses VentureLab's actual project brief and an explicit founder approval; it contains
no interview responses or market results.

## Architecture

VentureLab separates Investigator, Challenger, Builder and Judge responsibilities.
The full design covers Discover, Validate, Build, Commercial Setup, Launch, and
Operate and Learn. Milestone 3 adds an independent Builder contract and a local
approval service without guessing Milestone 2 interfaces. Evidence standing and
business decisions remain owned by the research workflow. See [architecture](ARCHITECTURE.md)
and the [integration boundary](docs/milestone3.md#data-contracts).

## Models and free resources

The preferred open-weight model is `qwen3:4b` through local Ollama; `qwen3:1.7b` is
the configured lower-resource fallback option. Compose includes Ollama and a one-shot
model pull service. No paid API is required. Builder's deterministic mode also works
without a model; it must not be described as a live AI inference run.

## Cost per run

About **$0.00 per run** in API/service charges using local templates or local models.
Electricity, hardware, download bandwidth and execution time are not included.

## Demo video

Not recorded yet. The team will add the final video after milestone integration.

## What our system will NOT do

VentureLab does not promise income or success, fabricate evidence or social proof,
impersonate people, collect passwords or payment details, or execute payments,
including sandbox payments. Builder produces only local digital-product artifacts
and rejects common prohibited claims/categories. It does not publish, send messages,
create accounts, or represent generated copy as validated market evidence.

## How the project stays alive after the hackathon

Jad owns Builder and approval work; Amen coordinates research workflow integration.
Next steps are real Milestone 2 integration, authenticated founder UI integration,
broader adversarial evaluations, and the final end-to-end demo. Contributions should
include reproducible tests and honest status labels. No funding or revenue outcome
is assumed; the project remains open source under the repository license.
