"""Challenger agent: tests the founder's own assumptions against the Investigator's findings.

1. Python turns the brief into numbered founder assumptions (A1, A2 ...). IDs are
   stable: they follow the brief's fields, so the same brief gives the same IDs.
   Each says whether the founder stated it or it is implied by running a business.
2. Python lists, for every assumption, the findings that share key words with it.
3. One model call reviews each assumption. The JSON schema only allows existing
   assumption IDs and finding IDs (constrained output), and Python checks every
   reference again, so an invented reference cannot get through either way.
4. Python decides what each point rests on:
   - EVIDENCE: cites an established finding that is relevant to the brief;
   - CONTRADICTING EVIDENCE: cites a finding whose quoted text contradicts it;
   - UNCONFIRMED: cites only findings that are not established;
   - ASSUMPTION: cites nothing valid.
   A stance the cited findings do not back ("supported" without an established
   finding, "contradicted" without contradicting evidence) is downgraded to
   "untested" and the change is recorded.
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
BASIS_CONTRADICTING = "CONTRADICTING EVIDENCE"
BASIS_UNCONFIRMED = "UNCONFIRMED (needs review)"
BASIS_ASSUMPTION = "ASSUMPTION"
GROUNDED = (BASIS_ESTABLISHED, BASIS_CONTRADICTING, BASIS_UNCONFIRMED)

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
                        f"{brief.hours_per_week:g} hours a week; {brief.budget_eur:g} EUR.", True),
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


def basis(ids: list[str], findings: dict[str, Finding]) -> str:
    cited = [findings[i] for i in ids if i in findings]
    if any(f.standing is ev.Standing.CONTRADICTED and f.relevance != "off_topic" for f in cited):
        return BASIS_CONTRADICTING
    if any(f.standing is ev.Standing.ESTABLISHED and f.relevance != "off_topic" for f in cited):
        return BASIS_ESTABLISHED
    if any(f.standing is not ev.Standing.ASSUMPTION for f in cited):
        return BASIS_UNCONFIRMED
    return BASIS_ASSUMPTION


def _valid_refs(raw: list[str], findings: dict[str, Finding], removed: list[str], where: str) -> list[str]:
    valid = [i for i in dict.fromkeys(raw) if i in findings]
    for bad in dict.fromkeys(i for i in raw if i not in findings):
        removed.append(f"{where}: reference {bad!r} does not exist; dropped")
    return valid


def _check_stance(stance: str, grounding: str) -> tuple[str, str]:
    """Keep the model's stance only if the cited evidence backs it."""
    if stance not in ("supported", "weakened", "contradicted", "untested"):
        return "untested", f"unknown stance {stance!r}"
    if stance == "supported" and grounding != BASIS_ESTABLISHED:
        return "untested", "model said 'supported' but cites no established finding"
    if stance == "contradicted" and grounding != BASIS_CONTRADICTING:
        return "untested", "model said 'contradicted' but cites no contradicting evidence"
    if stance == "weakened" and grounding == BASIS_ASSUMPTION:
        return "untested", "model said 'weakened' but cites no finding"
    return stance, ""


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
    for aid, r in reply.reviews.items():
        if aid not in a_ids:  # cannot happen with constrained output; checked anyway
            removed.append(f"review of unknown assumption {aid!r} dropped")
            continue
        # IDs written in the reason count as citations too, and are checked the same way.
        refs = _valid_refs(list(r.evidence) + _ID_IN_TEXT.findall(r.reason), by_id, removed, aid)
        grounding = basis(refs, by_id)
        stance, note = _check_stance(r.stance, grounding)
        if note:
            removed.append(f"{aid}: {note}; stance set to 'untested'")
        reviewed.add(aid)
        result.reviews.append({
            "assumption": aid, "assumption_text": a_ids[aid].text,
            "stated": a_ids[aid].stated, "stance": stance, "model_stance": r.stance,
            "reason": r.reason, "evidence": refs, "basis": grounding,
            "sources": sorted({u for i in refs for u in by_id[i].urls}),
        })
    for a in assumptions:  # every founder assumption is reported, reviewed or not
        if a.id not in reviewed:
            result.reviews.append({"assumption": a.id, "assumption_text": a.text, "stated": a.stated,
                                   "stance": "untested", "model_stance": None,
                                   "reason": "no finding relates to it, so the Challenger did not review it" if not next(x for x in result.assumptions if x["id"] == a.id)["related_findings"] else "not reviewed by the Challenger", "evidence": [],
                                   "basis": BASIS_ASSUMPTION, "sources": []})
    result.reviews.sort(key=lambda r: int(r["assumption"][1:]))
    for h in reply.new_hypotheses:
        refs = _valid_refs(list(h.evidence) + _ID_IN_TEXT.findall(h.text), by_id, removed, "new hypothesis")
        result.new_hypotheses.append({"text": h.text, "raised_by": "challenger", "evidence": refs,
                                      "basis": basis(refs, by_id),
                                      "sources": sorted({u for i in refs for u in by_id[i].urls})})
    for r in reply.risks:
        if r.assumption not in a_ids or r.kind not in ("market", "feasibility"):
            removed.append(f"risk tied to {r.assumption!r} ({r.kind!r}) dropped: unknown assumption or kind")
            continue
        refs = _valid_refs(list(r.evidence) + _ID_IN_TEXT.findall(r.text), by_id, removed, f"risk on {r.assumption}")
        result.risks.append({"assumption": r.assumption, "kind": r.kind, "text": r.text, "evidence": refs,
                             "basis": basis(refs, by_id)})
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
