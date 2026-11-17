# Usage

Detailed version of the README Quickstart.


Requirements: Docker with Compose, about 4 GB of free disk for the model, and roughly
4 GB of free RAM for `qwen3:4b` (use `qwen3:1.7b` on smaller machines, see below).

```bash
docker compose up
```

Then open <http://localhost:8000>. The first start also runs a one-shot `model-pull`
service that downloads the configured model (`qwen3:4b`, about 2.5 GB); until it
finishes the header says the model is not ready and `/health/model` returns HTTP 503.

To inspect genuine prior work immediately, choose **Recorded executions** in the
header. This read-only view needs neither the original local database nor a ready
model. It shows committed evidence, decisions, counterfactuals and audit entries;
older rule versions are clearly superseded and cannot authorize Builder actions.
This is separate from **Explore demo**, which contains labelled synthetic fixtures.
In the Decision dashboard, expand **Inspect the recorded rule checks and thresholds**
to see why the gate stopped at a particular rule. Quotations keep their own sources.

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

Later phases for a completed run (each step stops at a gate until the founder approves;
`approve` asks you to type `APPROVE <action>`):

```bash
docker compose run --rm app python workflow.py plan --run outputs/runs/<run-id>
```

then `approve`, `prepare-launch`, `approve`, `launch`, as printed by each step.

The command-line Discover workflow still works:
`docker compose run --rm -v "$PWD:/srv" app python orchestrator.py --brief briefs/indie_game_bug_reports.json --quick`.
Retrieval needs internet access. On a smaller machine set `VENTURELAB_MODEL=qwen3:1.7b`
in `.env` (copy `.env.example`).

Tests: `docker compose run --rm --no-deps app python -m pytest -q`. Live-model tests are
opt-in (`VENTURELAB_LIVE_TESTS=1`); UI tests are in `tests/ui` (`npm ci`, `npm test`,
`npm run test:browser`).

