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
On a project's **Analysis** page, open **Technical details** under the recommendation and
then **Inspect the recorded rule checks and thresholds** to see why the gate stopped at a
particular rule. Quotations keep their own sources.

State is kept in the checkout and survives restarts: `.venturelab/` (run records,
approval store, founder key; created on first start), `outputs/` and
`decision_log.json`. This works on Docker Desktop (Windows, macOS) and on Linux without
manual permission changes: the container checks these paths as root (symlinks are
refused), then runs the app as the owner of your checkout, never as root. Run it from a
checkout owned by your normal user; a root-owned checkout is refused with an explanation.

The workspace has four places, plus **New idea**:

| Place | Question it answers |
|---|---|
| **Projects** | Which ideas exist, where each one stands, and what to do next |
| **Analysis** | What VentureLab recommends and why, the evidence, the challenged assumptions, and what would change the result |
| **Build & validate** | Where the project stands in the six phases, decisions waiting for you, and the files for your validation |
| **History & details** | The audit trail, what each agent recorded, identifiers and diagnostics |

1. **New idea**: fill in the form, review it and submit. The backend validates it
   (errors appear next to the fields) and starts a real analysis in the background.
2. **Analysis** shows the run's progress (from the backend's records, refreshed every 5
   seconds). A brief submitted while the first model download is still running waits for
   it (up to 15 minutes, shown as such) instead of failing. A full run takes about two to
   four minutes on a CPU laptop; the "shorter demonstration run" option uses one search
   and fewer claims.
3. When it finishes, **Analysis** shows the recommendation in plain words with its main
   reason, what supports the idea, what concerns us, what is still unknown and what to do
   next; below, the evidence grouped by strength (each standing shown exactly as
   assigned), the challenged assumptions, and what could change the recommendation.
4. **Ask the Builder to prepare a validation kit** (on Analysis). This only creates a
   request; it appears under **Build & validate → Decisions waiting for you**, with the
   files it would create under **Files for your validation**.
5. **Approve**: paste the founder key from
   `.venturelab/approvals.sqlite3.founder` (created on first start, kept on your
   machine), approve or reject the exact request, then **Write the approved files
   locally**. Approving asks you to confirm in a dialog that says what will and will not
   happen. Requests expire after two hours.
   After you run the interviews, record the totals on the written kit (**Validation
   results**, founder key required). The validation gate compares them with the
   approved pass mark: it cannot be lowered, the sample cannot be enlarged after the
   fact, and a GO or STOP result is final. Results are labelled FOUNDER-REPORTED.
6. **History & details**: every recorded action for the run.

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

