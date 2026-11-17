# Shared approval store and legacy migration

Builder and workflow approvals use `approval.py:ApprovalStore`, the same SQLite
database, signing key and founder capability. Workflow decisions are immutable
events in its HMAC-chained audit journal; there is no second approval authority.
The old JSON list is never consulted during normal execution.

Every workflow request binds an action ID, action type (including price option),
run ID, artifact filename, absolute file location and exact SHA-256. A newer
request supersedes the older request even when pending or rejected. Selecting a
different price supersedes the previous price choice. A changed file does not
inherit authorization. The founder key is required for CLI decisions and steps,
and for every web approve/execute POST; origin checks are additional protection.
The CLI prompts with hidden input; never pass keys in command-line arguments.

## Lifetime and execution

- Pending requests must be decided within two hours (configured store TTL).
- Approved `set_price:*` and `rehearse_*` choices persist while their bound file
  remains unchanged, until superseded. They authorize choices, not execution.
- `publish_store_page` and `enable_mock_delivery` expire after two hours and must
  be claimed together for one launch. `BEGIN IMMEDIATE` serializes claims.
- A completed identical launch returns its recorded result without delivering or
  writing again. Replay still requires the founder key and unchanged artifacts.
- A failed or interrupted launch remains consumed; it is never automatically
  retried. Review partial local outputs and obtain new approvals before a new
  attempt. All publishing and delivery remain **MOCKED**.
- Rejections, claims, failures and results persist across restarts. Edited or
  deleted journal entries fail authentication rather than revealing old authority.
- SQLite is authoritative. `decision_log.json` is a rebuildable display mirror,
  not authorization state; its filesystem persistence is not atomic with SQLite.

## Explicit legacy import

Do not run import automatically on an existing founder state directory. Back up
the state first. Both commands prompt for the current ApprovalStore founder key:

```bash
docker compose run --rm app python workflow.py --out outputs --state .venturelab import-legacy --run outputs/runs/<run-id>
docker compose run --rm app python workflow.py --out outputs --state .venturelab import-legacy --run outputs/runs/<run-id> --apply
```

The first command only previews and audits eligibility. Jad reviews the result
and decides whether to run the second. Choose `--out` matching the actual artifact
location (web outputs use `outputs/phases/<run-id>`). Import verifies every MAC in
each action's legacy history with `workflow.founder`, considers its latest
decision, and checks the current artifact fingerprint and supported action.
Invalid MACs, rejections, stale fingerprints and expired execution approvals are
refused. Execution approvals retain the original expiry; persistent choices can
be imported without renewing execution authority. Import is allowed once per run
and legacy path, only before new workflow requests exist. An interrupted import
is not retried automatically; prepare fresh requests for any missing decisions.

Legacy signatures do **not** prove that a later record was never deleted, nor do
they establish prior consumption. Import therefore requires the founder's explicit
decision to trust the surviving history and, for eligible execution approvals,
authorize one new local MOCKED launch. If uncertain, do not import: request fresh
approvals. Original legacy files are preserved. Import reports record imported and
refused actions without exposing keys.

## Trust boundary

This protects against accidental misuse and edits by processes or users without
the signing/founder keys. It does not protect against a fully privileged local
attacker holding those keys, arbitrary Python execution, or rollback of the whole
database and all trusted state together. Artifact bytes are checked at approval
and execution; the local OS account and filesystem remain trusted.
