"""Challenger agent: tests the founder's own assumptions against the Investigator's findings.

1. Python turns the brief into numbered founder assumptions (A1, A2 ...). IDs are
   stable: they follow the brief's fields, so the same brief gives the same IDs.
   Each says whether the founder stated it or it is implied by running a business.
2. Python lists, for every assumption, the findings that share key words with it.
3. One model call reviews each assumption. The JSON schema only allows existing
   assumption IDs and finding IDs (constrained output), and Python checks every
   reference again, so an invented reference cannot get through either way.
4. The model's stance and reason are advisory. Python classifies every cited
   finding (direct, indirect, irrelevant, contradictory; see classify_link) and
   recomputes the stance: "supported" needs a finding that is established,
   related, covers what the assumption asserts (time, money ...) and that one
   assessment call (the existing evidence-assessment prompt) judges to support
   the assumption as worded. A citation existing never establishes support.
   Labels: EVIDENCE, PARTIAL EVIDENCE, CONTRADICTING EVIDENCE, UNCONFIRMED, ASSUMPTION.
5. Criticism of the founder's assumptions is kept apart from new hypotheses the
   Challenger raises itself, which are labelled as the Challenger's own.
Experiments that would fake social proof, pose as someone or take money are removed.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field, create_model

import evidence as ev
import relevance as rel
from agents.investigator import Finding, record_calls
from audit import AuditLog
from brief import FounderBrief
from llm import LLMError, OllamaClient

AGENT = "challenger"

BASIS_ESTABLISHED = "EVIDENCE"
BASIS_PARTIAL = "PARTIAL EVIDENCE"
BASIS_CONTRADICTING = "CONTRADICTING EVIDENCE"
BASIS_UNCONFIRMED = "UNCONFIRMED (needs review)"
BASIS_ASSUMPTION = "ASSUMPTION"
GROUNDED = (BASIS_ESTABLISHED, BASIS_PARTIAL, BASIS_CONTRADICTING, BASIS_UNCONFIRMED)

Stance = Literal["supported", "weakened", "contradicted", "untested"]

_UNSAFE_EXPERIMENT = re.compile(
    r"\b(?:fake|fabricat\w*|invent\w*|testimonials?|reviews? (?:from|by) (?:us|ourselves)|countdown|"
    r"pretend\w*|pos(?:e|ing) as|impersonat\w*|pre-?orders?|deposits?|charg(?:e|ing) (?:a |their )?card|"
    r"collect (?:payment|money)|take (?:payment|money))\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Assumption:
    id: str
    field: str
    text: str
    stated: bool  # True: written in the brief; False: implied by running it as a business


def founder_assumptions(brief: FounderBrief) -> list[Assumption]:
    """The founder's assumptions, numbered in a fixed order of brief fields."""
    out = [
        ("problem_statement", brief.problem_statement, True),
        ("target_customer", f"{brief.target_customer} have this problem.", True),
        ("idea", f"This solves it: {brief.idea}", True),
        ("market", f"These customers can be reached in: {brief.market}.", True),
        ("feasibility", f"The founder can build and test it with: {', '.join(brief.founder_skills)}; "
                        f"{brief.hours_per_week:g} hours a week; {brief.budget_eur:g} {brief.budget_currency}.", True),
        ("willingness_to_pay", "Enough of these customers would pay for it.", False),
    ]
    return [Assumption(f"A{i}", f, t, s) for i, (f, t, s) in enumerate(out, start=1)]


def _ids_type(ids: list[str]) -> Any:
    return Literal[tuple(ids)] if ids else Literal["none"]


@dataclass(frozen=True)
class Limits:
    """How much the Challenger writes. Output length is the main cost on a CPU."""

    hypotheses: int = 1
    risks: int = 2
    experiments: int = 2


FULL_LIMITS = Limits()
QUICK_LIMITS = Limits(hypotheses=0, risks=1, experiments=1)


def output_model(assumption_ids: list[str], finding_ids: list[str], strict: bool = True,
                 review_ids: list[str] | None = None, limits: Limits = FULL_LIMITS) -> type[BaseModel]:
    """The reply schema. Strict: ID fields only accept IDs that exist in this run
    (sent to the model server to constrain its output), reviews only cover
    `review_ids` (assumptions some finding speaks to, plus willingness to pay),
    and every text field has a length cap. Lenient: any string and length, so
    Python can check each value itself and report the ones that are invalid."""
    review_ids = review_ids or assumption_ids
    a_id, f_id = (_ids_type(assumption_ids), _ids_type(finding_ids)) if strict else (str, str)
    max_refs = (3 if finding_ids else 0) if strict else 10

    def text(limit: int) -> Any:
        # Strict: the length cap goes into the grammar, so the reply always fits the
        # output budget and is never cut off mid-JSON. Lenient parsing accepts any length.
        return (str, Field(max_length=limit)) if strict else (str, ...)

    def most(n: int) -> int:
        return n if strict else 20

    refs = (list[f_id], Field(default_factory=list, max_length=max_refs))
    body = create_model("Review", stance=(Stance if strict else str, ...), reason=text(110), evidence=refs)
    # Strict: one required key per reviewable assumption, so the model writes exactly
    # one review for each, never a duplicate and never one for an invented assumption.
    reviews_type: Any = (create_model("Reviews", **{rid: (body, ...) for rid in review_ids})
                         if strict else dict[str, body])
    hypo = create_model("NewHypothesis", text=text(110), evidence=refs)
    risk = create_model("Risk", assumption=(a_id, ...),
                        kind=(Literal["market", "feasibility"] if strict else str, ...), text=text(100),
                        evidence=refs)
    exp = create_model("Experiment", assumption=(a_id, ...), name=text(40), method=text(120),
                       support_if=text(80), weaken_if=text(80))
    return create_model(
        "ChallengerOutput",
        reviews=(reviews_type, ...),
        new_hypotheses=(list[hypo], Field(default_factory=list, max_length=most(limits.hypotheses))),
        risks=(list[risk], Field(default_factory=list, max_length=most(limits.risks))),
        experiments=(list[exp], Field(default_factory=list, max_length=most(limits.experiments))),
    )


@dataclass
class Challenge:
    assumptions: list[dict[str, Any]] = field(default_factory=list)
    reviews: list[dict[str, Any]] = field(default_factory=list)
    new_hypotheses: list[dict[str, Any]] = field(default_factory=list)
    risks: list[dict[str, Any]] = field(default_factory=list)
    experiments: list[dict[str, Any]] = field(default_factory=list)
    contradictions: list[dict[str, Any]] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # "ok" or "failed"
    error: str = ""
    elapsed_s: float = 0.0

    @property
    def grounded_reviews(self) -> int:
        return sum(1 for r in self.reviews if r["basis"] in GROUNDED)

    def to_dict(self) -> dict[str, Any]:
        keys = ("assumptions", "reviews", "new_hypotheses", "risks", "experiments", "contradictions",
                "removed", "calls", "status", "error")
        return {k: getattr(self, k) for k in keys} | {
            "grounded_reviews": self.grounded_reviews, "elapsed_s": round(self.elapsed_s, 1)}


# --- what a cited finding can do for an assumption -------------------------------------------
#
# A citation existing never establishes support. Code first classifies each link:
#   irrelevant     no verified quote, off-topic, or the quote shares fewer than two key
#                  concepts with the assumption;
#   contradictory  a check of the founder's own statement (A1) whose quote contradicts it;
#   indirect       related, but not established, or the quote never mentions an aspect the
#                  assumption asserts (time, money, frequency, difficulty);
#   candidate      established, related and covering every asserted aspect.
# Only a candidate can support an assumption, and only if one assessment call with the
# existing evidence-assessment prompt (evidence.assess) says the quotes support the
# assumption as worded; "partially_supports" gives "partly supported". The model's own
# stance is advisory: code recomputes the stance from these links.

DIRECT, INDIRECT, IRRELEVANT, CONTRADICTORY, CANDIDATE, PARTIAL = (
    "direct", "indirect", "irrelevant", "contradictory", "candidate", "partial")

ASPECTS = {
    "time": "time hour hours minute minutes day days week weeks month months long slow quick fast spend "
            "spent spending took take takes taking waste wasted weekend",
    "money": "pay paid paying price pricing cost costs costly expensive cheap budget fee fees dollar dollars "
             "euro euros subscription afford",
    "frequency": "often every daily weekly monthly always frequent frequently regularly recurring repeatedly",
    "difficulty": "hard difficult tedious painful pain annoying annoyed struggle struggling frustrating "
                  "frustrated tricky confusing chore",
}
_ASPECT_WORDS = {name: {rel.normalise(w) for w in words.split()} for name, words in ASPECTS.items()}
MAX_SUPPORT_CHECKS = 3  # bound on extra model calls per run


def aspects(text: str) -> set[str]:
    tokens = {rel.normalise(t) for t in re.findall(r"[a-z0-9]+", text.lower())}
    return {name for name, words in _ASPECT_WORDS.items() if tokens & words}


def quote_text(f: Finding) -> str:
    return " ".join(q.text for q in f.item.quotes if q.verified)


def classify_link(assumption: Assumption, f: Finding) -> tuple[str, str]:
    """Deterministic relationship between a cited finding and an assumption, with the reason."""
    text = quote_text(f)
    if not text:
        return IRRELEVANT, "no verified quotation"
    if f.relevance == "off_topic":
        return IRRELEVANT, "off-topic for this brief"
    if f.origin == "hypothesis_check" and assumption.field == "problem_statement":
        if f.standing is ev.Standing.CONTRADICTED:
            return CONTRADICTORY, "the quoted text contradicts the founder's statement"
        return INDIRECT, f"a check of the founder's statement that is {f.standing.value}, not established"
    shared_terms = rel.shared(rel.key_terms(assumption.text), text)
    if len(shared_terms) < rel.MIN_SHARED:
        return IRRELEVANT, f"the quote shares {len(shared_terms)} key concept(s) with the assumption"
    if f.standing is ev.Standing.CONTRADICTED:
        return IRRELEVANT, "the finding's own claim is contradicted by its quote; it says nothing about this"
    if f.standing is not ev.Standing.ESTABLISHED:
        return INDIRECT, f"related but {f.standing.value}"
    missing = aspects(assumption.text) - aspects(text)
    if missing:
        return INDIRECT, f"the quote does not mention {', '.join(sorted(missing))}, which the assumption asserts"
    return CANDIDATE, "established, related and covers what the assumption asserts"


def link_basis(links: list[dict[str, Any]]) -> str:
    kinds = {link["relationship"] for link in links}
    if CONTRADICTORY in kinds:
        return BASIS_CONTRADICTING
    if DIRECT in kinds:
        return BASIS_ESTABLISHED
    if PARTIAL in kinds:
        return BASIS_PARTIAL
    if kinds & {INDIRECT, CANDIDATE}:
        return BASIS_UNCONFIRMED
    return BASIS_ASSUMPTION


def _valid_refs(raw: list[str], findings: dict[str, Finding], removed: list[str], where: str) -> list[str]:
    valid = [i for i in dict.fromkeys(raw) if i in findings]
    for bad in dict.fromkeys(i for i in raw if i not in findings):
        removed.append(f"{where}: reference {bad!r} does not exist; dropped")
    return valid


_ID_IN_TEXT = re.compile(r"\b[FH]\d{1,3}\b")


def related_findings(a: Assumption, findings: list[Finding]) -> list[str]:
    """Findings sharing at least two key words with the assumption (off-topic ones excluded)."""
    terms = rel.key_terms(a.text)
    return [f.id for f in findings if f.relevance != "off_topic" and rel.is_about(
        terms, f.item.claim + " " + " ".join(q.text for q in f.item.quotes if q.verified))]


def findings_table(findings: list[Finding]) -> str:
    rows = [f"{f.id} | {f.claim_type} | {f.standing.value} | {f.relevance} | {f.item.claim[:160]}"
            for f in findings]
    return "\n".join(rows) or "(no findings: no relevant source material was found)"


def contradictions(findings: list[Finding]) -> list[dict[str, Any]]:
    out = []
    for f in findings:
        flagged = any("contradiction" in r for r in f.item.review)
        if f.standing is ev.Standing.CONTRADICTED or flagged:
            out.append({"finding": f.id, "claim": f.item.claim, "sources": f.urls,
                        "status": "contradicted" if f.standing is ev.Standing.CONTRADICTED
                        else "possible contradiction (needs review)", "reason": f.item.reason})
    return out


def challenge(
    brief: FounderBrief, findings: list[Finding], client: OllamaClient, model: str, log: AuditLog,
    limits: Limits = FULL_LIMITS,
) -> Challenge:
    started = time.perf_counter()
    by_id = {f.id: f for f in findings}
    assumptions = founder_assumptions(brief)
    a_ids = {a.id: a for a in assumptions}
    result = Challenge(contradictions=contradictions(findings))
    result.assumptions = [{"id": a.id, "field": a.field, "text": a.text, "stated": a.stated,
                           "related_findings": related_findings(a, findings)} for a in assumptions]
    lines = [f"{a['id']} ({'stated by the founder' if a['stated'] else 'implied'}): {a['text']} "
             f"| related findings: {', '.join(a['related_findings']) or 'none'}" for a in result.assumptions]
    messages = [
        {"role": "system", "content": ev.load_prompt("challenger")},
        {"role": "user", "content": "FOUNDER ASSUMPTIONS:\n" + "\n".join(lines)
         + "\n\nFINDINGS (id | type | standing | relevance | claim):\n" + findings_table(findings)},
    ]
    # Only assumptions some finding speaks to are reviewed by the model, plus willingness
    # to pay (always critical); the others are recorded as untested by code below.
    review_ids = [a["id"] for a in result.assumptions if a["related_findings"] or a["field"] == "willingness_to_pay"]
    strict = output_model(list(a_ids), list(by_id), review_ids=review_ids, limits=limits)
    lenient = output_model(list(a_ids), list(by_id), strict=False)
    try:
        res = client.chat_json(model, messages, strict, parse_as=lenient, num_predict=700)
        record_calls(result.calls, "challenge_assumptions", [res])
        reply = res.parsed
    except LLMError as exc:
        result.status, result.error = "failed", str(exc)[:300]
        result.elapsed_s = time.perf_counter() - started
        log.record(AGENT, "challenge_assumptions", model=model, outcome="failed", error=result.error)
        return result

    removed = result.removed
    reviewed: set[str] = set()
    support_checks = 0
    for aid, r in reply.reviews.items():
        if aid not in a_ids:  # cannot happen with constrained output; checked anyway
            removed.append(f"review of unknown assumption {aid!r} dropped")
            continue
        assumption = a_ids[aid]
        # IDs written in the reason count as citations too, and are checked the same way.
        refs = _valid_refs(list(r.evidence) + _ID_IN_TEXT.findall(r.reason), by_id, removed, aid)
        links = []
        for i in refs:
            relationship, why = classify_link(assumption, by_id[i])
            links.append({"finding": i, "relationship": relationship, "why": why})
        candidates = [link for link in links if link["relationship"] == CANDIDATE]
        stance, note = "untested", ""
        if r.stance == "supported":
            if not candidates:
                note = "model said 'supported' but no cited finding can support it: " + (
                    "; ".join(f"{link['finding']} {link['why']}" for link in links) or "nothing cited")
            elif support_checks >= MAX_SUPPORT_CHECKS:
                note = "model said 'supported'; support not checked (limit of checks per run reached)"
            else:
                support_checks += 1
                cited = [by_id[link["finding"]] for link in candidates]
                quotes = [q.text for f in cited for q in f.item.quotes if q.verified]
                answer = None
                try:
                    answer, res = ev.assess(client, model, assumption.text, quotes, "\n".join(quotes))
                    record_calls(result.calls, "check_support", [res])
                except LLMError as exc:
                    note = f"support check failed ({str(exc)[:80]})"
                outcome = {"supports": (DIRECT, "supported"), "partially_supports": (PARTIAL, "partly_supported"),
                           "does_not_support": (IRRELEVANT, "untested"),
                           "contradicts": (CONTRADICTORY, "weakened")}.get(answer.verdict if answer else "")
                if outcome:
                    for link in candidates:
                        link["relationship"] = outcome[0]
                        link["why"] = f"assessment of the quote against the assumption: {answer.verdict}"
                        link["assessment_reason"] = answer.reason
                    stance = outcome[1]
                    if stance != "supported":
                        note = f"model said 'supported'; the assessment of the cited quotes says {answer.verdict}"
        elif r.stance == "contradicted":
            if any(link["relationship"] == CONTRADICTORY for link in links):
                stance = "contradicted"
            else:
                note = "model said 'contradicted' but no cited finding contradicts this assumption"
        elif r.stance == "weakened":
            if any(link["relationship"] != IRRELEVANT for link in links):
                stance = "weakened"
            else:
                note = "model said 'weakened' but every cited finding is irrelevant to it"
        elif r.stance != "untested":
            note = f"unknown stance {r.stance!r}"
        for link in links:  # untried candidates are related and established, but support was not checked
            if link["relationship"] == CANDIDATE:
                link["relationship"] = INDIRECT
                link["why"] += "; support for this assumption was not checked"
        if note:
            removed.append(f"{aid}: {note}; stance set to '{stance}'")
        reviewed.add(aid)
        kept = [link["finding"] for link in links if link["relationship"] != IRRELEVANT]
        result.reviews.append({
            "assumption": aid, "assumption_text": assumption.text, "stated": assumption.stated,
            "stance": stance, "model_stance": r.stance, "reason": r.reason, "reason_is_advisory": True,
            "evidence": kept, "links": links, "basis": link_basis(links),
            "sources": sorted({u for i in kept for u in by_id[i].urls}),
        })
    for a in assumptions:  # every founder assumption is reported, reviewed or not
        if a.id not in reviewed:
            related = next(x for x in result.assumptions if x["id"] == a.id)["related_findings"]
            result.reviews.append({
                "assumption": a.id, "assumption_text": a.text, "stated": a.stated, "stance": "untested",
                "model_stance": None, "reason_is_advisory": True,
                "reason": "not reviewed by the Challenger" if related
                else "no finding relates to it, so the Challenger did not review it",
                "evidence": [], "links": [], "basis": BASIS_ASSUMPTION, "sources": []})
    result.reviews.sort(key=lambda r: int(r["assumption"][1:]))

    def side_note_basis(text: str, refs: list[str]) -> tuple[list[str], str]:
        # New hypotheses and risks are never checked for support, so they are at most UNCONFIRMED.
        kept = [i for i in refs if quote_text(by_id[i]) and by_id[i].relevance != "off_topic"
                and rel.is_about(rel.key_terms(text), quote_text(by_id[i]))]
        return kept, BASIS_UNCONFIRMED if kept else BASIS_ASSUMPTION

    for h in reply.new_hypotheses:
        refs = _valid_refs(list(h.evidence) + _ID_IN_TEXT.findall(h.text), by_id, removed, "new hypothesis")
        kept, grounding = side_note_basis(h.text, refs)
        result.new_hypotheses.append({"text": h.text, "raised_by": "challenger", "evidence": kept,
                                      "basis": grounding, "sources": sorted({u for i in kept for u in by_id[i].urls})})
    for r in reply.risks:
        if r.assumption not in a_ids or r.kind not in ("market", "feasibility"):
            removed.append(f"risk tied to {r.assumption!r} ({r.kind!r}) dropped: unknown assumption or kind")
            continue
        refs = _valid_refs(list(r.evidence) + _ID_IN_TEXT.findall(r.text), by_id, removed, f"risk on {r.assumption}")
        kept, grounding = side_note_basis(r.text, refs)
        result.risks.append({"assumption": r.assumption, "kind": r.kind, "text": r.text, "evidence": kept,
                             "basis": grounding})
    for e in reply.experiments:
        if e.assumption not in a_ids:
            removed.append(f"experiment {e.name!r} dropped: tests unknown assumption {e.assumption!r}")
            continue
        text = " ".join([e.name, e.method, e.support_if, e.weaken_if])
        unsafe = _UNSAFE_EXPERIMENT.search(text)
        if unsafe:
            removed.append(f"experiment {e.name!r} removed: uses {unsafe.group(0)!r}")
            continue
        result.experiments.append(e.model_dump() | {"status": "proposed, not run"})
    result.elapsed_s = time.perf_counter() - started
    cited = sorted({u for r in result.reviews for u in r["sources"]})
    log.record(AGENT, "challenge_assumptions", sources=cited, model=model, outcome="ok",
               reviews=len(result.reviews), grounded_reviews=result.grounded_reviews,
               new_hypotheses=len(result.new_hypotheses), risks=len(result.risks),
               experiments=len(result.experiments), contradictions=len(result.contradictions), removed=removed)
    return result
