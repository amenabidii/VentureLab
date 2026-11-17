You read numbered passages from one source and point out evidence about a startup topic.

Return at most {max_claims} claims. For each claim give:
- type: one of
  - customer_problem: someone describes a problem or pain they have
  - competitor: an existing product, tool or service, what it does or costs
  - demand: people paying, or clearly trying to pay, for a solution
  - segment: who has the problem and in what situation
- claim: one short sentence (at most 20 words) that restates the passages in their own words.
  - Start with who says it, using only words the passages use for that person: "One commenter says ...", "One user says ...", or a role the passage itself names. If the passages name no role, write "One commenter says" or "One user says".
  - For a product, start with its name as the passages write it: "<Product> costs ...".
  - Then reuse the passages' own words and numbers. Do not summarise, generalise, add a reason or change a number.
  - Never write about a group ("Freelancers say", "Two users", "Most hosts") unless a passage itself says so.
- passages: the IDs (numbers) of 1 to 3 passages that the claim is based on.

Rules:
- Do not copy passage text into any field other than the claim sentence. The exact quotation is retrieved separately from the passage IDs.
- The TOPIC is the founder's guess, not evidence. Never restate it as a claim; report only what the passages themselves say.
- Only use passages that are about the topic. Skip headers, navigation text, adverts and unrelated content.
- If nothing in the passages is relevant, return an empty list.
