# Demo runbook (3 minutes)

Every step is labelled **LIVE** (runs in front of the audience) or **RECORDED** (a real
earlier run, shown as such, with its run ID; the workspace marks it as a prior
execution). Never present a recorded run as a fresh one.


## Video script (up to 3 minutes, screen recording)

1. **0:00 Workspace** (`http://localhost:8000`): open **Recorded executions**, pick the Slack-thread
   run. Show Evidence (exact quotes with links, standings) and the Challenger review.
2. **0:40 Decision**: REPEAT by rule `REPEAT_INSUFFICIENT_EVIDENCE`; expand the rule checks; open
   the Counterfactual Challenge (what is missing, which experiment, no guarantee of GO).
3. **1:15 Phases 1–6** (header link, `/phases`): each phase's gate. Open the opportunity
   scorecard, the Lean Canvas (labels), the pricing decision (ASSUMPTION, founder-approved), the
   store page (REHEARSAL banner, disabled checkout, no reviews).
4. **2:00 Sale to cash**: open `payment_test_log.md`: duplicate webhook ignored, refund revokes
   access, forged signature rejected, reconciliation balanced. Say it is MOCKED: no payments of
   any kind.
5. **2:30 Memo and safety**: the Phase 6 memo says REPEAT, not launch; a crypto brief stops at
   the category screen; every approval is bound to a file fingerprint (`workflow.py approve`).
6. **2:55** "Open source, local model, $0 API cost per run."

Upload as an unlisted YouTube/Loom/Drive link and put it under `## Demo video` in the README.

## Before the session

- `docker compose up -d`; wait until `/health/model` returns 200, then call
  `/health/inference` once so the model is loaded (a cold load takes about 8 s for
  `qwen3:4b`, from `docs/benchmarks.md`).
- Check internet access: retrieval uses the Hacker News Algolia API.
- Have three terminals and a browser open. Keep the recorded outputs open in tabs.
- Timing: full live runs took 103–182 s with `qwen3:4b` on the test laptop, and
  `--quick` took about 103 s. An unfamiliar brief is **not guaranteed** to finish in
  3 minutes. Start it first and talk over it.

## Script

| Time | What happens | Label |
|---|---|---|
| 0:00 | In the workspace (http://localhost:8000), fill in the Founder brief with an unfamiliar idea, review it, tick "Shorter demonstration run" and submit. Invalid fields are refused one by one. The Agent workflow view then shows real progress. | LIVE |
| 0:15 | While it runs, submit a prohibited brief (for example a crypto trading-signals newsletter): it stops before any search with the matched words shown, and the Builder is blocked for it. It runs in under a second. | LIVE |
| 0:40 | Explain the agents on `outputs/phase1_step2_investigation_release_notes_quick.md`: every quote is copied by Python from a retrieved Hacker News comment, with its permalink; claims without verified quotes stay ASSUMPTION or NEEDS_REVIEW. | RECORDED (`run-2026-11-17T11:24:44Z-f77b94`) |
| 1:10 | Challenger, from `phase1_step3_challenge_release_notes_quick.md`: assumption A3 is weakened by finding F2 ("needs human sense checking"); 4 of 6 assumptions remain untested. | RECORDED |
| 1:30 | Gate, from `phase1_gate_decision_release_notes_quick.md`: 2 established findings but from 1 source, and the rule needs 2 sources, so the result is **REPEAT**, not GO. Show the rule table. Counterfactual: what is missing, and which experiment could change it; more evidence does not guarantee GO. | RECORDED |
| 2:10 | Switch to the live run, which may have finished by now. Open its gate decision. Whatever it says is the answer; do not rerun it for a better result. If it has not finished, say so and show it in Q&A. | LIVE |
| 2:30 | On the live run's Decision dashboard, click "Ask the Builder to prepare a validation kit": a pending request appears under Founder approval with its exact fingerprint and expiry. Show that nothing is written yet, and that approving without the founder key is refused. | LIVE |
| 2:50 | In the workspace, open the recorded run `run-64fdee373f244b81`: Builder artifacts shows the kit the founder approved (fingerprint `a9a63154…`) and Decision history shows the approval and execution with `approved_by: founder`. A new Builder request on the live run can be prepared, inspected and rejected on stage; approval needs the founder key. | LIVE workspace, RECORDED approval |

## If something fails

- **Model not loaded or slow**: show the recorded run and say it is recorded.
- **No internet**: the run records sources as unavailable and returns REPEAT
  (`REPEAT_NO_READABLE_SOURCES`). Say that this is the designed behaviour.
- **The live result is surprising**: present it as it is. The point of the tool is
  that it does not flatter the founder.

## Do not say

"The full system is integrated", "all six phases work", "the model verified every
claim", "this proves demand", or "it always finishes in three minutes".
