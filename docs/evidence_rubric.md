# Evidence rubric

How VentureLab decides whether a quotation supports a claim. The assessment prompt (`prompts/investigator_assess.md`) states this rubric, and the labelled benchmark (`bench/fixtures/evidence_cases.json`) is labelled by it.

## Verdicts

| Verdict | Meaning |
|---|---|
| `supports` | The quote, read in its context, establishes the whole claim, including its scope (who, how many, how much). |
| `partially_supports` | The quote backs part of the claim, a narrower version of it, or gives only indirect evidence. |
| `does_not_support` | The quote is about something else, only mentions the topic, asks a question, or is irrelevant. It neither backs nor refutes the claim. |
| `contradicts` | The quote, read in context, states or shows the opposite of the claim. |

## Rules

1. **Context decides.** A quote is judged together with the surrounding text. A fragment that sounds supportive but is negated, hypothetical, reported from someone else or framed as a question is judged by what the context actually says.
2. **Scope matters.** One person's experience fully supports a claim about that person, and only partially supports a claim about "most" or "many" people.
3. **Interest is not payment.** "I'd love a tool that…" partially supports a claim that people want it, and does not establish that they will pay.
4. **Competitors are not demand.**
   - A product's own page fully supports claims about that product (its features, its price).
   - People paying a competitor partially supports a claim that there is demand for the job it does.
   - A product existing, being funded or being written about does not support a claim about demand.
5. **When in doubt, choose the weaker verdict.**

## Promotion rule (enforced in `evidence.py`)

A claim becomes an **established** finding only when all of these hold:

1. Every quotation is **verified**: copied from the source by Python at recorded offsets, never written by the model.
2. The assessment verdict is `supports`.
3. A second, sceptical check agrees the claim is fully supported.
4. **Wording rule:** every content word of the claim appears in the quoted text or its neighbouring passages. Function words and the vocabulary of attributing a statement to one person ("one user says") are exempt. This stops the model from changing the speaker, turning one person into a group, inventing a count or adding detail. It is deliberately strict, so a faithful paraphrase ("flashcards" for "decks", "costs" for "is") is held for review rather than established.
5. **Attribution rule:** a claim about people (type `customer_problem` or `segment`) starts with one person ("One host says", "A bookkeeper reports", "At least one user"). Because plurals match singulars in the wording rule, this is what stops "Bookkeepers say" being built from one bookkeeper's post.
6. It is not a demand claim. Any claim about paying, buying, subscribing or demand is one, whatever type the model gave it; desk research cannot establish demand.

A claim that passes everything except the wording or attribution rule becomes **needs review**: it is kept with its verified quote and the reason, for a person to check or reword, and is never treated as a finding. A `does_not_support` or `partially_supports` verdict whose own reason mentions a contradiction is also flagged for review; the verdict is not changed, because the reason may say "does not contradict".

Every other combination keeps the claim as partial evidence, unsupported, contradicted or an assumption. "Established" means "this source supports this attributed claim"; whether a finding holds across sources is decided by the gates.
