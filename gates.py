"""Phase 1 evidence gate: a deterministic GO / REPEAT / PIVOT / STOP decision.

No model is involved. The rules are checked in a fixed order and the first one
that applies decides; every rule's inputs and result are recorded, so the
decision can be traced to one named rule.

- GO: go on to FURTHER VALIDATION (experiments with customers). Two sourced
  problem reports are never treated as proof of demand or of a market.
- REPEAT: not enough evidence, mixed evidence, nothing readable, or something
  the founder must clarify. Missing evidence is never treated as failure.
- PIVOT: the founder's statement of the problem is contradicted, and an
  established, relevant finding points to a different problem to test instead.
- STOP: a prohibited category, a pass mark the founder set in advance that an
  experiment failed, or independent sources contradicting the problem with
  nothing supporting it or any alternative. Low availability is a feasibility
  constraint to adjust or clarify, not a reason to stop; infeasibility stops a
  run only through a condition the founder set and a result that failed it.

Support for the founder's problem comes from independent sources, each counted once:
- an ESTABLISHED customer-problem finding about the founder's statement, or
- a corroborating check: one commenter's exact, verified, first-person words (never
  quoted material), about the statement
  by the deterministic relevance rule, that the assessment judges to fully support
  "this person experiences the founder's problem" AND that the sceptical second check
  confirms (it rejects product descriptions, changed context and opposite meaning).
  Partial support never counts. This is one person's account, so it is never
  ESTABLISHED and never proof of a market; two independent people describing the
  problem in their own words justify customer interviews, nothing more. Each person and
  each wording counts once, whatever URL it appears under.
NEEDS_REVIEW, off-topic, segment, competitor and demand findings never satisfy an
evidence requirement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import evidence as ev
from agents.investigator import Investigation
from brief import CategoryScreen, FounderBrief

# Predefined thresholds. Changing one changes every future decision, so they live here.
# Version of the gate rules. Raise it whenever a change could alter a past decision: a run
# decided under another version is superseded and can no longer reach the Builder
# (builder_adapter.adapt, enforced again at approval and execution in app/api.py).
# 2: corroboration counts only a commenter's own first-person words, each person once.
# 3: the brief screen also stops deceptive practices (fake reviews, sign-ups or urgency,
#    impersonation, promised income), not only excluded product categories.
RULESET_VERSION = 3

MIN_SUPPORTING_FINDINGS = 2
MIN_SUPPORTING_SOURCES = 2  # distinct comment or page URLs
MIN_CONTRADICTING_SOURCES_FOR_STOP = 2
LOW_AVAILABILITY_HOURS = 2.0  # below this, a feasibility note asks the founder to adjust the plan
# Only claims that someone has the problem count. A `segment` claim says who is
# involved, not that the problem exists, so it is reported but not counted.
PROBLEM_TYPES = frozenset({"customer_problem"})

GATE_NAME = "phase1_evidence_gate"


class Decision(str, Enum):
    GO = "GO"
    REPEAT = "REPEAT"
    PIVOT = "PIVOT"
    STOP = "STOP"


@dataclass(frozen=True)
class Rule:
    id: str
    decision: Decision
    meaning: str


RULES: dict[str, Rule] = {r.id: r for r in [
    Rule("STOP_PROHIBITED_CATEGORY", Decision.STOP,
         "The brief describes a product in an excluded category (physical goods, financial or crypto, health "
         "or legal advice), or one that depends on a practice this system must never help with (fake reviews, "
         "sign-ups or urgency, impersonation, promised income). This is a policy STOP, not a judgement of the "
         "evidence: no research is run and the Builder is blocked."),
    Rule("STOP_FAILED_VALIDATION_CONDITION", Decision.STOP,
         "An experiment result is below a pass mark the founder set before testing."),
    Rule("STOP_CONTRADICTED", Decision.STOP,
         f"At least {MIN_CONTRADICTING_SOURCES_FOR_STOP} independent sources contradict the problem statement, "
         "and no established finding supports it or any alternative problem."),
    Rule("PIVOT_ALTERNATIVE_SUPPORTED", Decision.PIVOT,
         "Sources contradict the founder's statement of the problem, nothing established supports it, and an "
         "established finding about the same customers or idea points to a different problem to test."),
    Rule("REPEAT_MIXED_EVIDENCE", Decision.REPEAT,
         "Some established findings support the problem statement and some sources contradict it."),
    Rule("REPEAT_NO_READABLE_SOURCES", Decision.REPEAT,
         "No relevant source material could be read, so there is no evidence either way."),
    Rule("REPEAT_CLARIFY_AVAILABILITY", Decision.REPEAT,
         "The brief gives 0 hours a week. Validation needs some of the founder's time; clarify or adjust."),
    Rule("GO_TO_FURTHER_VALIDATION", Decision.GO,
         f"At least {MIN_SUPPORTING_SOURCES} independent sources support the problem statement (established "
         "findings, or people describing it in their own verified words), and nothing contradicts it. This "
         "justifies experiments with customers; it is not proof of demand or of a market."),
    Rule("REPEAT_INSUFFICIENT_EVIDENCE", Decision.REPEAT,
         "Nothing contradicts the idea strongly enough to stop or pivot, but there is not enough established, "
         "relevant evidence to go on."),
]}


@dataclass
class EvidenceSummary:
    sources_total: int = 0
    sources_readable: int = 0
    sources_analysed: int = 0
    supporting: list[str] = field(default_factory=list)  # established, about the founder's statement
    supporting_sources: list[str] = field(default_factory=list)
    corroborating_checks: list[str] = field(default_factory=list)  # one commenter's words support the statement
    corroborating_sources: list[str] = field(default_factory=list)
    # statement checks the model judged supportive that cannot count: not the person's own
    # first-person words, or the same person / the same words already counted
    not_counted_checks: list[dict[str, str]] = field(default_factory=list)
    support_sources: list[str] = field(default_factory=list)  # distinct sources of either kind
    alternatives: list[dict[str, Any]] = field(default_factory=list)  # established, about a different problem
    contradicting_checks: list[str] = field(default_factory=list)
    contradicting_sources: list[str] = field(default_factory=list)
    unsupported_checks: list[str] = field(default_factory=list)
    needs_review: list[str] = field(default_factory=list)
    partial: list[str] = field(default_factory=list)
    off_topic: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    established_other: list[str] = field(default_factory=list)  # established competitor or segment claims
    demand_signals: list[str] = field(default_factory=list)  # never established by desk research

    @classmethod
    def from_investigation(cls, inv: Investigation | None) -> EvidenceSummary:
        s = cls()
        if inv is None:
            return s
        s.sources_total = len(inv.sources)
        s.sources_readable = sum(1 for src in inv.sources if src.available)
        s.sources_analysed = len(inv.analysed)
        support_urls: set[str] = set()
        contra_urls: set[str] = set()
        corro_urls: set[str] = set()
        speakers: set[str] = set()
        texts: set[str] = set()
        for f in inv.findings:
            st = f.standing
            if f.origin == "hypothesis_check":
                if st is ev.Standing.CONTRADICTED and f.relevance == "statement":
                    s.contradicting_checks.append(f.id)
                    contra_urls.update(f.urls)
                elif (f.relevance == "statement" and f.item.verified and len(f.urls) == 1
                      and f.item.verdict == "supports" and f.item.confirmed is True):
                    text = " ".join(re.findall(r"[a-z0-9]+", " ".join(q.text for q in f.item.quotes).lower()))
                    who = (f.speaker or "").strip().lower() or f.urls[0]
                    if not all(ev.speaks_for_self(q.text) for q in f.item.quotes):
                        s.not_counted_checks.append({"check": f.id, "reason": "not in the first person"})
                    elif who in speakers or f.urls[0] in corro_urls:
                        s.not_counted_checks.append({"check": f.id, "reason": "same person already counted"})
                    elif text in texts:
                        s.not_counted_checks.append({"check": f.id, "reason": "same words already counted"})
                    else:
                        speakers.add(who)
                        texts.add(text)
                        s.corroborating_checks.append(f.id)
                        corro_urls.update(f.urls)
                elif st is ev.Standing.UNSUPPORTED:
                    s.unsupported_checks.append(f.id)
                elif st is ev.Standing.NEEDS_REVIEW:
                    s.needs_review.append(f.id)
                continue
            if f.claim_type == "demand":
                s.demand_signals.append(f.id)
            if f.relevance == "off_topic":
                s.off_topic.append(f.id)
            elif st is ev.Standing.ESTABLISHED:
                if f.claim_type in PROBLEM_TYPES and f.relevance == "statement":
                    s.supporting.append(f.id)
                    support_urls.update(f.urls)
                elif f.claim_type in PROBLEM_TYPES:
                    s.alternatives.append({"finding": f.id, "claim": f.item.claim, "sources": f.urls})
                else:
                    s.established_other.append(f.id)
            elif st is ev.Standing.NEEDS_REVIEW:
                s.needs_review.append(f.id)
            elif st is ev.Standing.PARTIAL:
                s.partial.append(f.id)
            elif st is ev.Standing.ASSUMPTION:
                s.assumptions.append(f.id)
        s.supporting_sources = sorted(support_urls)
        s.contradicting_sources = sorted(contra_urls)
        s.corroborating_sources = sorted(corro_urls)
        s.support_sources = sorted(support_urls | corro_urls)
        return s

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class GateResult:
    gate: str
    decision: Decision
    rule: Rule
    checks: list[dict[str, Any]]
    evidence: EvidenceSummary
    failed_conditions: list[dict[str, Any]]
    unmeasured_conditions: list[dict[str, Any]]
    feasibility_notes: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "gate": self.gate,
            "ruleset_version": RULESET_VERSION,
            "decision": self.decision.value,
            "rule": self.rule.id,
            "rule_meaning": self.rule.meaning,
            "checks": self.checks,
            "evidence": self.evidence.to_dict(),
            "failed_conditions": self.failed_conditions,
            "unmeasured_conditions": self.unmeasured_conditions,
            "feasibility_notes": self.feasibility_notes,
            "thresholds": {
                "min_supporting_findings": MIN_SUPPORTING_FINDINGS,
                "min_supporting_sources": MIN_SUPPORTING_SOURCES,
                "min_contradicting_sources_for_stop": MIN_CONTRADICTING_SOURCES_FOR_STOP,
                "low_availability_hours": LOW_AVAILABILITY_HOURS,
            },
        }


def conditions(brief: FounderBrief) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split the founder's predefined conditions into failed and not yet measured."""
    failed, unmeasured = [], []
    for c in brief.validation_conditions:
        if c.metric not in brief.experiment_results:
            unmeasured.append(c.model_dump())
        elif brief.experiment_results[c.metric] < c.minimum:
            failed.append(c.model_dump() | {"result": brief.experiment_results[c.metric]})
    return failed, unmeasured


def feasibility_notes(brief: FounderBrief) -> list[str]:
    """Constraints to adjust or clarify. They never decide on their own."""
    notes = []
    if 0 < brief.hours_per_week < LOW_AVAILABILITY_HOURS:
        notes.append(f"Limited availability ({brief.hours_per_week:g} hours a week): plan validation over more "
                     "weeks, choose smaller experiments, or clarify whether more time is possible.")
    if brief.budget_eur == 0:
        notes.append("No budget: only free experiments (interviews, free tools) are possible.")
    return notes


def pre_research_stop(brief: FounderBrief, screen: CategoryScreen) -> bool:
    """True if a STOP rule applies before any research (no point spending model time)."""
    return not screen.allowed or bool(conditions(brief)[0])


def decide(brief: FounderBrief, screen: CategoryScreen, inv: Investigation | None) -> GateResult:
    e = EvidenceSummary.from_investigation(inv)
    failed, unmeasured = conditions(brief)
    n_sup = len(e.supporting) + len(e.corroborating_checks)
    n_sup_src = len(e.support_sources)
    n_contra, n_alt = len(e.contradicting_sources), len(e.alternatives)
    counts = {"supporting_findings": len(e.supporting), "corroborating_checks": len(e.corroborating_checks),
              "supporting_sources": n_sup_src, "contradicting_sources": n_contra, "alternatives": n_alt}
    tests: list[tuple[str, bool, dict[str, Any]]] = [
        ("STOP_PROHIBITED_CATEGORY", not screen.allowed, {"matches": screen.matches}),
        ("STOP_FAILED_VALIDATION_CONDITION", bool(failed), {"failed": [c["id"] for c in failed]}),
        ("STOP_CONTRADICTED", n_contra >= MIN_CONTRADICTING_SOURCES_FOR_STOP and n_sup == 0 and n_alt == 0,
         counts),
        ("PIVOT_ALTERNATIVE_SUPPORTED", n_contra >= 1 and n_sup == 0 and n_alt >= 1,
         counts | {"alternative_findings": [a["finding"] for a in e.alternatives]}),
        ("REPEAT_MIXED_EVIDENCE", n_contra >= 1 and n_sup >= 1, counts),
        ("REPEAT_NO_READABLE_SOURCES", inv is not None and e.sources_analysed == 0,
         {"sources_total": e.sources_total, "sources_readable": e.sources_readable,
          "sources_analysed": e.sources_analysed}),
        ("REPEAT_CLARIFY_AVAILABILITY", brief.hours_per_week == 0, {"hours_per_week": brief.hours_per_week}),
        ("GO_TO_FURTHER_VALIDATION",
         n_sup >= MIN_SUPPORTING_FINDINGS and n_sup_src >= MIN_SUPPORTING_SOURCES and n_contra == 0,
         counts | {"not_counted": {"needs_review": len(e.needs_review), "partial": len(e.partial),
                                   "off_topic": len(e.off_topic), "assumptions": len(e.assumptions)}}),
        ("REPEAT_INSUFFICIENT_EVIDENCE", True, {}),
    ]
    checks, chosen = [], None
    for rule_id, applies, inputs in tests:
        decided = chosen is None and applies
        if decided:
            chosen = RULES[rule_id]
        checks.append({"rule": rule_id, "applies": applies, "inputs": inputs, "decided": decided})
        if decided:
            break
    assert chosen is not None  # the last rule always applies
    return GateResult(GATE_NAME, chosen.decision, chosen, checks, e, failed, unmeasured, feasibility_notes(brief))
