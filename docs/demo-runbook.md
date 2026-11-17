# Demo runbook (3 minutes)

Every step is labelled **LIVE** (runs in front of the audience), **RECORDED** (a real
earlier run, shown as such, with its run ID), or **AFTER INTEGRATION** (needs the
integration work in [integration-handoff.md](integration-handoff.md); skip it until it
has passed the acceptance checklist). Never present a recorded run as a fresh one.

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
| 0:00 | Take the unfamiliar brief as JSON (copy `briefs/release_notes_tool.json` and edit idea, customer, problem). Run `docker compose run --rm -v "$PWD:/srv" app python orchestrator.py --brief briefs/<new>.json --quick`. It refuses invalid briefs field by field. | LIVE |
| 0:15 | While it runs, show the prohibited-category STOP: `briefs/crypto_signals_newsletter.json` stops before any search, with the matched words shown. It runs in under a second. | LIVE |
| 0:40 | Explain the agents on `outputs/phase1_step2_investigation_release_notes_quick.md`: every quote is copied by Python from a retrieved Hacker News comment, with its permalink; claims without verified quotes stay ASSUMPTION or NEEDS_REVIEW. | RECORDED (`run-2026-11-17T11:24:44Z-f77b94`) |
| 1:10 | Challenger, from `phase1_step3_challenge_release_notes_quick.md`: assumption A3 is weakened by finding F2 ("needs human sense checking"); 4 of 6 assumptions remain untested. | RECORDED |
| 1:30 | Gate, from `phase1_gate_decision_release_notes_quick.md`: 2 established findings but from 1 source, and the rule needs 2 sources, so the result is **REPEAT**, not GO. Show the rule table. Counterfactual: what is missing, and which experiment could change it; more evidence does not guarantee GO. | RECORDED |
| 2:10 | Switch to the live run, which may have finished by now. Open its gate decision. Whatever it says is the answer; do not rerun it for a better result. If it has not finished, say so and show it in Q&A. | LIVE |
| 2:30 | Builder and approval, from the M3 branch: `python -m builder_cli inspect <id>` shows the exact artifact and SHA-256; `execute` before `decide` is refused; after approval it writes once; a second `execute` is refused. Show the generated landing page (ASSUMPTION labels, no form). | LIVE on the M3 branch checkout, or RECORDED (action `0b69ddac…`) |
| 2:50 | Close on the founder UI only if integrated; otherwise one sentence: "The UI exists on its branch; the wiring is the next step." | AFTER INTEGRATION |

## If something fails

- **Model not loaded or slow**: show the recorded run and say it is recorded.
- **No internet**: the run records sources as unavailable and returns REPEAT
  (`REPEAT_NO_READABLE_SOURCES`). Say that this is the designed behaviour.
- **The live result is surprising**: present it as it is. The point of the tool is
  that it does not flatter the founder.

## Do not say

"The full system is integrated", "all six phases work", "the model verified every
claim", "this proves demand", or "it always finishes in three minutes".
