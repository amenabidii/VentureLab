"""Deterministic gate decisions and the counterfactual challenge."""

from __future__ import annotations

import pytest

import evidence as ev
from agents.challenger import Challenge
from agents.investigator import Finding, Investigation
from brief import FounderBrief, screen_brief
from counterfactual import NO_GUARANTEE, explain
from gates import RULES, Decision, decide
from sources import Segment, Source

BRIEF = {
    "idea": "A web app that drafts release notes from merged pull requests.",
    "problem_statement": "Small software teams spend too much time writing release notes.",
    "target_customer": "developers at small SaaS companies",
    "market": "online",
    "founder_skills": ["Python"],
    "hours_per_week": 10,
    "budget_eur": 0,
}
TEXT = "One developer says writing release notes takes an hour every week."
E = ev.Standing


def brief(**change) -> FounderBrief:
    return FounderBrief.model_validate(BRIEF | change)


def finding(fid: str, standing: ev.Standing, url: str, *, origin="extracted", claim_type="customer_problem",
            relevance="statement") -> Finding:
    """A finding whose fields produce `standing` through the real promotion rule."""
    quote = ev.verify_span(TEXT, 0, len(TEXT), url)
    item = ev.EvidenceItem(TEXT if origin == "extracted" else BRIEF["problem_statement"], claim_type, [quote])
    if standing is E.ASSUMPTION:
        item.quotes = [ev.verify_excerpt(TEXT, "invented text", url)]
    else:
        item.verdict = {E.ESTABLISHED: "supports", E.NEEDS_REVIEW: "supports", E.PARTIAL: "partially_supports",
                        E.UNSUPPORTED: "does_not_support", E.CONTRADICTED: "contradicts"}[standing]
        item.confirmed = True if item.verdict == "supports" else None
        item.unsourced = [] if standing is E.ESTABLISHED else ["teams"]
        item.attributed = standing is E.ESTABLISHED
    f = Finding(fid, origin, "hn_comments", item, relevance=relevance)
    assert f.standing is standing
    return f


def investigation(*findings, readable=True) -> Investigation:
    src = Source("hn_comments", "https://hn.test/search", "s", text=TEXT, segments=[Segment(0, len(TEXT), "u")],
                 status="available" if readable else "unavailable")
    return Investigation(queries=["q"], query_origin="model", sources=[src], analysed=[src] if readable else [],
                         findings=list(findings))


def run(b: FounderBrief, inv: Investigation | None):
    return decide(b, screen_brief(b), inv)


def contra(fid: str, url: str) -> Finding:
    return finding(fid, E.CONTRADICTED, url, origin="hypothesis_check")


# --- GO -------------------------------------------------------------------------------------------

def test_go_to_further_validation_needs_two_relevant_findings_from_two_sources():
    g = run(brief(), investigation(finding("F1", E.ESTABLISHED, "u1"), finding("F2", E.ESTABLISHED, "u2")))
    assert g.decision is Decision.GO and g.rule.id == "GO_TO_FURTHER_VALIDATION"
    assert "not proof of demand" in g.rule.meaning


def test_go_is_never_described_as_proof_of_demand():
    for rule in RULES.values():
        text = rule.meaning.lower()
        assert "proves demand" not in text and "proof of demand" not in text.replace("not proof of demand", "")


def test_two_findings_from_one_source_are_not_enough():
    g = run(brief(), investigation(finding("F1", E.ESTABLISHED, "u1"), finding("F2", E.ESTABLISHED, "u1")))
    assert g.decision is Decision.REPEAT and g.rule.id == "REPEAT_INSUFFICIENT_EVIDENCE"


@pytest.mark.parametrize("weak", [E.NEEDS_REVIEW, E.PARTIAL, E.UNSUPPORTED, E.ASSUMPTION])
def test_unconfirmed_findings_never_satisfy_the_evidence_requirement(weak):
    many = [finding(f"F{i}", weak, f"u{i}") for i in range(6)]
    g = run(brief(), investigation(*many))
    assert g.decision is Decision.REPEAT and g.evidence.supporting == []


def test_off_topic_established_findings_do_not_count():
    g = run(brief(), investigation(finding("F1", E.ESTABLISHED, "u1", relevance="off_topic"),
                                   finding("F2", E.ESTABLISHED, "u2", relevance="off_topic")))
    assert g.decision is Decision.REPEAT and g.evidence.supporting == [] and g.evidence.off_topic == ["F1", "F2"]


@pytest.mark.parametrize("claim_type", ["competitor", "segment", "demand"])
def test_competitor_segment_and_demand_findings_do_not_count_as_problem_evidence(claim_type):
    g = run(brief(), investigation(finding("F1", E.ESTABLISHED if claim_type != "demand" else E.PARTIAL, "u1",
                                           claim_type=claim_type),
                                   finding("F2", E.ESTABLISHED if claim_type != "demand" else E.PARTIAL, "u2",
                                           claim_type=claim_type)))
    assert g.decision is Decision.REPEAT and g.evidence.supporting == []


# --- REPEAT ---------------------------------------------------------------------------------------

def test_missing_evidence_is_repeat_not_stop():
    g = run(brief(), investigation())
    assert g.decision is Decision.REPEAT and g.rule.id == "REPEAT_INSUFFICIENT_EVIDENCE"


def test_no_readable_source_is_repeat_with_its_own_rule():
    g = run(brief(), investigation(readable=False))
    assert g.decision is Decision.REPEAT and g.rule.id == "REPEAT_NO_READABLE_SOURCES"


def test_one_contradicting_source_alone_is_not_enough_to_stop():
    assert run(brief(), investigation(contra("H1", "u1"))).decision is Decision.REPEAT


def test_support_and_contradiction_together_is_mixed_evidence():
    g = run(brief(), investigation(finding("F1", E.ESTABLISHED, "u1"), contra("H1", "u2")))
    assert g.decision is Decision.REPEAT and g.rule.id == "REPEAT_MIXED_EVIDENCE"


@pytest.mark.parametrize("hours", [0.5, 1, 1.9])
def test_low_availability_is_a_feasibility_note_not_a_stop(hours):
    g = run(brief(hours_per_week=hours), investigation(finding("F1", E.ESTABLISHED, "u1"),
                                                       finding("F2", E.ESTABLISHED, "u2")))
    assert g.decision is Decision.GO
    assert any("Limited availability" in n for n in g.feasibility_notes)
    assert all(r.id != "STOP_INFEASIBLE_TIME" for r in RULES.values())


def test_zero_hours_asks_for_clarification():
    g = run(brief(hours_per_week=0), investigation(finding("F1", E.ESTABLISHED, "u1"),
                                                   finding("F2", E.ESTABLISHED, "u2")))
    assert g.decision is Decision.REPEAT and g.rule.id == "REPEAT_CLARIFY_AVAILABILITY"


# --- PIVOT ----------------------------------------------------------------------------------------

def test_pivot_needs_an_established_alternative():
    alt = finding("F3", E.ESTABLISHED, "u3", relevance="topic")
    g = run(brief(), investigation(alt, contra("H1", "u1")))
    assert g.decision is Decision.PIVOT and g.rule.id == "PIVOT_ALTERNATIVE_SUPPORTED"
    assert g.evidence.alternatives[0]["finding"] == "F3"


def test_contradiction_without_any_alternative_is_not_a_pivot():
    weak_alt = finding("F3", E.NEEDS_REVIEW, "u3", relevance="topic")
    assert run(brief(), investigation(weak_alt, contra("H1", "u1"))).decision is Decision.REPEAT


# --- STOP -----------------------------------------------------------------------------------------

def test_contradiction_from_two_sources_without_support_or_alternative_stops():
    g = run(brief(), investigation(contra("H1", "u1"), contra("H2", "u2")))
    assert g.decision is Decision.STOP and g.rule.id == "STOP_CONTRADICTED"


def test_prohibited_category_stops_before_anything_else():
    b = brief(idea="A newsletter with daily crypto trading signals for beginners.")
    g = run(b, None)
    assert g.decision is Decision.STOP and g.rule.id == "STOP_PROHIBITED_CATEGORY"
    assert len(g.checks) == 1 and g.checks[0]["decided"]


def test_failed_predefined_condition_stops_and_unmeasured_ones_do_not():
    cond = [{"id": "interviews", "description": "people confirming the problem", "metric": "confirmed",
             "minimum": 5}]
    failed = run(brief(validation_conditions=cond, experiment_results={"confirmed": 2}), investigation())
    assert failed.decision is Decision.STOP and failed.rule.id == "STOP_FAILED_VALIDATION_CONDITION"
    assert failed.failed_conditions[0]["result"] == 2
    assert run(brief(validation_conditions=cond, experiment_results={"confirmed": 6}),
               investigation()).decision is Decision.REPEAT
    pending = run(brief(validation_conditions=cond), investigation())
    assert pending.decision is Decision.REPEAT and pending.unmeasured_conditions[0]["id"] == "interviews"


def test_founder_defined_feasibility_condition_can_stop():
    cond = [{"id": "build_time", "description": "hours available for building per week", "metric": "build_hours",
             "minimum": 4}]
    g = run(brief(validation_conditions=cond, experiment_results={"build_hours": 1}), investigation())
    assert g.decision is Decision.STOP and g.rule.id == "STOP_FAILED_VALIDATION_CONDITION"


def test_every_rule_check_is_recorded_up_to_the_deciding_rule():
    g = run(brief(), investigation())
    assert g.checks[0]["rule"] == "STOP_PROHIBITED_CATEGORY"
    assert sum(c["decided"] for c in g.checks) == 1
    assert g.to_dict()["rule"] == g.checks[-1]["rule"]


# --- counterfactual challenge -----------------------------------------------------------------

CASES = {
    "GO_TO_FURTHER_VALIDATION": lambda: (brief(), investigation(finding("F1", E.ESTABLISHED, "u1"),
                                                                finding("F2", E.ESTABLISHED, "u2"))),
    "REPEAT_INSUFFICIENT_EVIDENCE": lambda: (brief(), investigation(finding("F1", E.NEEDS_REVIEW, "u1"))),
    "REPEAT_NO_READABLE_SOURCES": lambda: (brief(), investigation(readable=False)),
    "REPEAT_MIXED_EVIDENCE": lambda: (brief(), investigation(finding("F1", E.ESTABLISHED, "u1"),
                                                             contra("H1", "u2"))),
    "REPEAT_CLARIFY_AVAILABILITY": lambda: (brief(hours_per_week=0), investigation()),
    "PIVOT_ALTERNATIVE_SUPPORTED": lambda: (brief(), investigation(
        finding("F3", E.ESTABLISHED, "u3", relevance="topic"), contra("H1", "u1"))),
    "STOP_CONTRADICTED": lambda: (brief(), investigation(contra("H1", "u1"), contra("H2", "u2"))),
    "STOP_PROHIBITED_CATEGORY": lambda: (brief(idea="An app giving medical advice to patients online."), None),
    "STOP_FAILED_VALIDATION_CONDITION": lambda: (brief(
        validation_conditions=[{"id": "c", "description": "people confirming", "metric": "m", "minimum": 5}],
        experiment_results={"m": 1}), None),
}


def test_every_rule_has_a_counterfactual_case():
    assert set(CASES) == set(RULES)


@pytest.mark.parametrize("rule", list(CASES))
def test_counterfactual_explains_every_decision(rule):
    b, inv = CASES[rule]()
    g = run(b, inv)
    assert g.rule.id == rule
    cf = explain(g, b, Challenge())
    assert cf["decision"] == g.decision.value and cf["rule"] == rule
    assert cf["missing_evidence"], "must name what is missing"
    assert cf["reconsidered_by"]
    assert cf["no_guarantee"] == NO_GUARANTEE and "does not guarantee" in NO_GUARANTEE
    for x in cf["experiments"]:
        assert x["support_if"] and x["weaken_if"] and x["method"]
    if rule == "STOP_PROHIBITED_CATEGORY":
        assert cf["experiments"] == [] and "no evidence can reverse" in cf["reconsidered_by"]
    if rule in ("REPEAT_INSUFFICIENT_EVIDENCE", "GO_TO_FURTHER_VALIDATION"):
        assert any("Demand" in m for m in cf["missing_evidence"])
    if rule == "PIVOT_ALTERNATIVE_SUPPORTED":
        assert cf["alternative_hypothesis"]["based_on"] == ["F3"]
    text = str(cf).lower()
    for promise in ("will succeed", "guaranteed", "will make money", "will lead to go", "proves demand"):
        assert promise not in text


def test_counterfactual_uses_challenger_experiments_first():
    b, inv = CASES["REPEAT_INSUFFICIENT_EVIDENCE"]()
    chal = Challenge(experiments=[{"name": "Changelog survey", "assumption": "A1", "method": "m",
                                   "support_if": "s", "weaken_if": "w", "status": "proposed, not run"}])
    cf = explain(run(b, inv), b, chal)
    assert cf["experiments"][0]["name"] == "Changelog survey"
    assert cf["experiments"][0]["origin"] == "challenger"


# --- reachability: each outcome follows from its conditions, and only from them ---------------------
# Fixtures are constructed by hand (SYNTHETIC). They show the rules are reachable and tight;
# they are not real-world validation.

GO_BASE = [lambda: finding("F1", E.ESTABLISHED, "u1"), lambda: finding("F2", E.ESTABLISHED, "u2")]


@pytest.mark.parametrize(
    ("label", "findings"),
    [
        ("second finding only needs review", [GO_BASE[0], lambda: finding("F2", E.NEEDS_REVIEW, "u2")]),
        ("second finding from the same source", [GO_BASE[0], lambda: finding("F2", E.ESTABLISHED, "u1")]),
        ("second finding is about a different problem",
         [GO_BASE[0], lambda: finding("F2", E.ESTABLISHED, "u2", relevance="topic")]),
        ("second finding is off-topic", [GO_BASE[0], lambda: finding("F2", E.ESTABLISHED, "u2", relevance="off_topic")]),
        ("second finding is a competitor", [GO_BASE[0], lambda: finding("F2", E.ESTABLISHED, "u2", claim_type="competitor")]),
        ("a source contradicts the statement", [*GO_BASE, lambda: contra("H1", "u3")]),
    ],
)
def test_go_near_misses_are_not_go(label, findings):
    g = run(brief(), investigation(*(f() for f in findings)))
    assert g.decision is not Decision.GO, label


def test_go_reached_exactly_when_its_conditions_hold():
    g = run(brief(), investigation(*(f() for f in GO_BASE)))
    assert g.rule.id == "GO_TO_FURTHER_VALIDATION"


@pytest.mark.parametrize(
    ("label", "findings", "expected"),
    [
        ("alternative only needs review",
         [lambda: finding("F3", E.NEEDS_REVIEW, "u3", relevance="topic"), lambda: contra("H1", "u1")],
         "REPEAT_INSUFFICIENT_EVIDENCE"),
        ("alternative but no contradiction",
         [lambda: finding("F3", E.ESTABLISHED, "u3", relevance="topic")], "REPEAT_INSUFFICIENT_EVIDENCE"),
        ("alternative, contradiction, but the statement is also supported",
         [lambda: finding("F3", E.ESTABLISHED, "u3", relevance="topic"), lambda: contra("H1", "u1"),
          lambda: finding("F1", E.ESTABLISHED, "u4")], "REPEAT_MIXED_EVIDENCE"),
        ("off-topic 'alternative'",
         [lambda: finding("F3", E.ESTABLISHED, "u3", relevance="off_topic"), lambda: contra("H1", "u1")],
         "REPEAT_INSUFFICIENT_EVIDENCE"),
    ],
)
def test_pivot_near_misses_are_not_pivot(label, findings, expected):
    g = run(brief(), investigation(*(f() for f in findings)))
    assert g.rule.id == expected, label
