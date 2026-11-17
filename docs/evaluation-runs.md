# Evaluation runs (2026-11-17)

Live runs used to check how the gate behaves on unfamiliar, permitted briefs. Every run
used `qwen3:4b` locally through Ollama and real Hacker News search results at the time
of the run. Outputs are committed; their audit entries are in `decision_log.json`.

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

## Results (stricter rule)

| Brief (`briefs/`) | Decision | Rule | Corroborating commenters | Time | Model calls |
|---|---|---|---|---|---|
| `audit_accessible_pdfs` (CLI) | GO | `GO_TO_FURTHER_VALIDATION` | 2 (H1, H2) | 247 s | 8 |
| `audit_design_feedback` (CLI) | REPEAT | `REPEAT_INSUFFICIENT_EVIDENCE` | 0 (one quote judged contradicting) | 216 s | 7 |
| `audit_student_flashcards` (CLI) | REPEAT | `REPEAT_INSUFFICIENT_EVIDENCE` | 0 (two genuine accounts judged only partial) | 210 s | 7 |
| `audit_restaurant_shifts` (CLI) | REPEAT | `REPEAT_INSUFFICIENT_EVIDENCE` | 0 | 191 s | 5 |
| `audit_slack_reference` (CLI, same brief as the earlier web run) | REPEAT | `REPEAT_INSUFFICIENT_EVIDENCE` | 0 | 204 s | 6 |
| Accessible PDFs, through the web workspace (`run-4209f27582724d6f`) | GO | `GO_TO_FURTHER_VALIDATION` | 2 | 219 s | 8 |

Command-line outputs are in `outputs/audit-live/` (file suffix = brief name); the web run
is in `outputs/runs/run-4209f27582724d6f/`. After the web GO, the Builder prepared a
request that includes the local landing page (kit only would have been prepared after
REPEAT). That request is **pending**: it has not been approved, so no files were written.

Limits: one live sample per brief; search results change over time; "two people
describe the problem" justifies interviews, not a market. The student-flashcards result
shows the remaining conservatism: two genuine first-person accounts were judged partial.
