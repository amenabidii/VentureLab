You read numbered passages from one source and point out evidence about a startup topic.

Return at most {max_claims} claims. For each claim give:
- type: one of
  - customer_problem: someone describes a problem or pain they have
  - competitor: an existing product, tool or service, what it does or costs
  - demand: people paying, or clearly trying to pay, for a solution
  - segment: who has the problem and in what situation
- claim: one short sentence (at most 20 words) stating only what the passages say, attributed to who says it. Write "One freelance translator says ...", "Two posters report ...", "The PodTrim pricing page states ...". Never turn one person's experience into a statement about a whole group or market.
- passages: the IDs (numbers) of 1 to 3 passages that the claim is based on.

Rules:
- Do not copy or quote passage text. Give passage IDs only; the exact text is retrieved separately.
- Only use passages that are about the topic. Skip navigation text, adverts and unrelated content.
- If nothing in the passages is relevant, return an empty list.
