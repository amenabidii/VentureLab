# Evaluation runs (2026-11-17)

Live runs used to check how the gate behaves on unfamiliar, permitted briefs. Every run
used `qwen3:4b` locally through Ollama and real Hacker News search results at the time
of the run. Outputs are committed; their audit entries are in `decision_log.json`.

## Correction: the two accessible-PDF GO results were wrong

Both GO results below rested on the same two comments, each judged "supports" by the
assessment and by the second check. Read independently, neither shows a screen reader
user describing their own difficulty with PDFs:

| Check | Comment | What it actually is |
|---|---|---|
| H1 | [item 13809215](https://news.ycombinator.com/item?id=13809215), user DanBC | A quoted excerpt (a `>` line) of a US Department of Justice finding about UC Berkeley's online course material, in a thread about the university removing it. The words are the report's, about other people, not the commenter's own experience. |
| H2 | [item 6671934](https://news.ycombinator.com/item?id=6671934), user chrismorgan | A developer, in a "Show HN" thread about a typesetting tool, objecting that its character substitution "makes the document inaccessible to things like screen readers". A builder's technical criticism, not a screen reader user's experience. |

The two commenters are different people, and no quote was counted twice, but neither one
counts as corroboration of "Screen reader users struggle to read inaccessible PDF documents".
The cause was that the model's judgement alone decided whether a quote was one person's own
account. The rule now also requires, in code:
- the quote is in the commenter's own first-person words (I, my, we, our ...), and is not
  quoted material (lines starting with `>` are never checked);
- each person (by author name) and each wording counts once, whatever URL it appears under;
- the claim names the target customer ("... personally, as one of the target customers (...),
  experience this problem"), and the second check asks whether the speaker is that customer
  rather than someone describing others, quoting a report, or speaking as a developer or
  vendor.

Regression tests in `tests/test_corroboration.py` replay excerpts of both comments with a
model that answers "supports" to everything, and the result is no longer GO. A live rerun
of the same brief with the corrected rule (`outputs/audit-live/*_audit_accessible_pdfs_recheck.*`,
86 s, 3 model calls) ended in **REPEAT** (`REPEAT_INSUFFICIENT_EVIDENCE`). That day's search
returned different comments, and none was a commenter's own first-person account matching
the statement.

What the code still cannot do: a first-person comment that the model misreads (for example,
a developer saying "my tool makes documents inaccessible to screen readers") passes the
deterministic checks and is stopped only by the two model judgements. This limit is
covered by a test of the prompt contents, not solved.

## Why most earlier runs ended in REPEAT

Across the five earlier recorded investigations, the model extracted 17 claims: 9 were
off-topic (2 of them without a verifiable quote), 3 were held for review because the
model's sentence went beyond the quote (for example, a commenter wrote *"I've experienced
late payments multiple times myself"* and the model wrote *"freelancers often experience
late payments"*), 3 were established, and 2 were partial evidence. GO needed two established claims, and at most four claims
were extracted per run. Meanwhile, the check of the founder's statement looked only at
the two best-matching passages, combined, and its result could only ever block.

## What changed

The founder's statement is now also checked against each relevant commenter separately,
in that person's exact verified words, as a claim about that one person ("One commenter
says they experience this problem: …"). Such a check counts toward GO only if the
assessment says it fully supports the claim **and** the sceptical second check agrees.
It is never ESTABLISHED and never evidence of a market. GO still needs two independent
sources and no contradiction.

A first version also counted "partially supports". On the briefs below it produced
three GOs, one of them wrong: a competitor's product description and a quote whose own
assessment reason argued against the problem were counted as support. That version was
discarded; the results below are from the stricter rule.

## Results (stricter rule, before the correction above)

The two GO rows are **superseded**: they came from the rule before the own-words
requirement and would not be GO today (see the correction above). The REPEAT rows are
unaffected, because tightening the rule cannot turn REPEAT into GO.

| Brief (`briefs/`) | Decision | Rule | Corroborating commenters | Time | Model calls |
|---|---|---|---|---|---|
| `audit_accessible_pdfs` (CLI) | GO (superseded) | `GO_TO_FURTHER_VALIDATION` | 2 (H1, H2), neither valid | 247 s | 8 |
| `audit_design_feedback` (CLI) | REPEAT | `REPEAT_INSUFFICIENT_EVIDENCE` | 0 (one quote judged contradicting) | 216 s | 7 |
| `audit_student_flashcards` (CLI) | REPEAT | `REPEAT_INSUFFICIENT_EVIDENCE` | 0 (two genuine accounts judged only partial) | 210 s | 7 |
| `audit_restaurant_shifts` (CLI) | REPEAT | `REPEAT_INSUFFICIENT_EVIDENCE` | 0 | 191 s | 5 |
| `audit_slack_reference` (CLI, same brief as the earlier web run) | REPEAT | `REPEAT_INSUFFICIENT_EVIDENCE` | 0 | 204 s | 6 |
| Accessible PDFs, through the web workspace (`run-4209f27582724d6f`) | GO (superseded) | `GO_TO_FURTHER_VALIDATION` | 2 (same H1, H2), neither valid | 219 s | 8 |
| `audit_accessible_pdfs`, rerun with the corrected rule (CLI) | REPEAT | `REPEAT_INSUFFICIENT_EVIDENCE` | 0 | 86 s | 3 |

Command-line outputs are in `outputs/audit-live/` (file suffix = brief name); the web run
is in `outputs/runs/run-4209f27582724d6f/`. After the web GO, the Builder prepared a
request that includes the local landing page. That request was never approved and no
files were written. The backend now refuses to approve or execute it: every gate decision
records the gate rule set version (`ruleset_version`, currently 2), and a run recorded
without the current version, like both GO runs above, is superseded. Such a run cannot
reach the Builder, either to prepare a request or to approve or execute one (rejecting
stays possible). The superseded output files and their `decision_log.json` entries are kept
unchanged as history. They can be identified by the missing `ruleset_version` field and by
this page.

Limits: one live sample per brief; search results change over time; "two people
describe the problem" justifies interviews, not a market. No recorded live run currently
reaches GO under the corrected rule.
