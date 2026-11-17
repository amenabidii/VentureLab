"""Regression tests: a citation existing is not support, and relevance is by concept, not keyword.

Findings here are built by hand from SYNTHETIC quotes; their standings come from the
real promotion rule (verdict, second check, wording and attribution fields). The model
is the STUBBED Ollama from conftest. These tests check the code's safeguards; they are
not evidence about any real market.
"""

from __future__ import annotations

import json

import pytest

import evidence as ev
import relevance as rel
from agents.challenger import (
    BASIS_ASSUMPTION,
    BASIS_CONTRADICTING,
    BASIS_ESTABLISHED,
    BASIS_PARTIAL,
    BASIS_UNCONFIRMED,
    INDIRECT,
    IRRELEVANT,
    MAX_SUPPORT_CHECKS,
    challenge,
    classify_link,
    founder_assumptions,
)
from agents.investigator import Finding
from audit import AuditLog
from brief import FounderBrief
from tests.conftest import RoutedOllama

RELEASE_NOTES = FounderBrief.model_validate({
    "idea": "A web app that drafts customer-facing release notes from merged pull requests.",
    "problem_statement": "Small software teams spend too much time writing release notes and changelogs.",
    "target_customer": "developers and product managers at small SaaS companies",
    "market": "online",
    "founder_skills": ["Python"],
    "hours_per_week": 10,
    "budget_eur": 0,
})
A = {a.id: a for a in founder_assumptions(RELEASE_NOTES)}

# The exact quote from the live run that was wrongly accepted as support for A1.
COMMUNICATION_CHANNEL = ("If you're talking to users, Release notes stop being a dev artifact and become a "
                         "communication channel.")
TIME_BURDEN = "I spend about two hours writing the changelog for every release, and I dread it."
QUICK_JOB = "Writing our release notes takes five minutes, it is no burden at all."
COMPETITOR = "PodTrim has 8,000 users and a free plan for open-source projects."


def established(fid: str, quote: str, claim_type: str = "customer_problem", relevance: str = "statement",
                origin: str = "extracted", standing: ev.Standing = ev.Standing.ESTABLISHED) -> Finding:
    q = ev.verify_span(quote, 0, len(quote), f"https://news.ycombinator.com/item?id={fid}")
    item = ev.EvidenceItem(f"One commenter says {quote}", claim_type, [q])
    item.verdict = {ev.Standing.ESTABLISHED: "supports", ev.Standing.CONTRADICTED: "contradicts",
                    ev.Standing.PARTIAL: "partially_supports"}[standing]
    item.confirmed = True if item.verdict == "supports" else None
    item.unsourced, item.attributed = [], True
    f = Finding(fid, origin, "hn_comments", item, relevance=relevance)
    assert f.standing is standing
    return f


def run_challenge(tmp_path, findings, reviews, assess=None):
    reply = json.dumps({"reviews": reviews, "new_hypotheses": [], "risks": [], "experiments": []})
    model = RoutedOllama({"challenge": reply} | ({"assess": assess} if assess else {}))
    c = challenge(RELEASE_NOTES, findings, model.client(), "qwen3:4b", AuditLog(tmp_path / "l.json", "r"))
    return {r["assumption"]: r for r in c.reviews}, model, c


def verdict(v: str) -> str:
    return json.dumps({"reason": f"The quotes {v}.", "limitations": "", "verdict": v})


# --- the exact failure from the live run --------------------------------------------------------

def test_communication_channel_quote_cannot_support_a_time_burden(tmp_path):
    f1 = established("F1", COMMUNICATION_CHANNEL)
    relationship, why = classify_link(A["A1"], f1)
    assert relationship in (IRRELEVANT, INDIRECT), why
    r, model, c = run_challenge(tmp_path, [f1], {
        "A1": {"stance": "supported", "reason": "F1 shows teams spend too much time on release notes.",
               "evidence": ["F1"]}})
    assert r["A1"]["stance"] == "untested" and r["A1"]["basis"] in (BASIS_UNCONFIRMED, BASIS_ASSUMPTION)
    assert "assess" not in model.calls  # rejected by code, no model call needed
    assert any("A1: model said 'supported'" in x for x in c.removed)


def test_same_quote_is_not_even_relevant_by_concept():
    terms = rel.BriefTerms(RELEASE_NOTES.problem_statement, RELEASE_NOTES.idea, RELEASE_NOTES.target_customer)
    assert terms.statement_match(COMMUNICATION_CHANNEL) is None


def test_a_quote_about_the_topic_without_the_asserted_aspect_is_indirect():
    # Shares two concepts with A1 but says nothing about time.
    f = established("F2", "I write the release notes for our small team by hand.")
    relationship, why = classify_link(A["A1"], f)
    assert relationship == INDIRECT and "time" in why


@pytest.mark.parametrize(
    ("assumption", "quote"),
    [
        ("A6", COMPETITOR),  # a competitor existing is not willingness to pay
        ("A2", "Our developers love the new office coffee machine."),  # customer words only
        ("A3", "Pull requests are for humans, commit messages are for machines."),  # topic words, no claim
    ],
)
def test_misleading_citations_cannot_make_an_assumption_supported(tmp_path, assumption, quote):
    f = established("F1", quote, claim_type="competitor" if quote == COMPETITOR else "customer_problem")
    r, model, _ = run_challenge(tmp_path, [f], {
        "A1": {"stance": "untested", "reason": "-", "evidence": []},
        assumption: {"stance": "supported", "reason": "F1 proves it.", "evidence": ["F1"]}})
    assert r[assumption]["stance"] == "untested"
    assert r[assumption]["basis"] != BASIS_ESTABLISHED
    assert "assess" not in model.calls


# --- support only through the assessment of the quote against the assumption --------------------

@pytest.mark.parametrize(
    ("assessment", "stance", "basis"),
    [
        ("supports", "supported", BASIS_ESTABLISHED),
        ("partially_supports", "partly_supported", BASIS_PARTIAL),
        ("does_not_support", "untested", BASIS_ASSUMPTION),
        ("contradicts", "weakened", BASIS_CONTRADICTING),
    ],
)
def test_a_real_candidate_is_judged_by_the_assessment_not_by_the_challenger(tmp_path, assessment, stance, basis):
    f = established("F1", TIME_BURDEN)
    r, model, _ = run_challenge(tmp_path, [f], {
        "A1": {"stance": "supported", "reason": "F1 says so.", "evidence": ["F1"]}}, assess=verdict(assessment))
    assert model.calls.count("assess") == 1
    assert (r["A1"]["stance"], r["A1"]["basis"]) == (stance, basis)
    assert r["A1"]["links"][0]["why"].endswith(assessment)


def test_no_support_check_unless_the_model_claims_support(tmp_path):
    f = established("F1", TIME_BURDEN)
    r, model, _ = run_challenge(tmp_path, [f], {"A1": {"stance": "weakened", "reason": "F1.", "evidence": ["F1"]}})
    assert "assess" not in model.calls
    assert r["A1"]["stance"] == "weakened" and r["A1"]["links"][0]["relationship"] == INDIRECT


def test_support_checks_are_bounded(tmp_path):
    fs = [established(f"F{i}", TIME_BURDEN) for i in range(1, 6)]
    reviews = {aid: {"stance": "supported", "reason": "F1.", "evidence": ["F1", "F2"]} for aid in A}
    _, model, _ = run_challenge(tmp_path, fs, reviews, assess=verdict("supports"))
    assert model.calls.count("assess") <= MAX_SUPPORT_CHECKS


def test_quote_saying_the_task_is_quick_is_contradiction_not_support(tmp_path):
    f = established("F1", QUICK_JOB)
    r, _, _ = run_challenge(tmp_path, [f], {"A1": {"stance": "supported", "reason": "F1.", "evidence": ["F1"]}},
                            assess=verdict("contradicts"))
    assert (r["A1"]["stance"], r["A1"]["basis"]) == ("weakened", BASIS_CONTRADICTING)


# --- contradiction comes only from evidence about the same assumption --------------------------------

def test_contradicted_needs_a_check_of_the_founder_statement(tmp_path):
    h1 = established("H1", QUICK_JOB, origin="hypothesis_check", standing=ev.Standing.CONTRADICTED)
    f2 = established("F2", QUICK_JOB, standing=ev.Standing.CONTRADICTED)  # the model's own claim was wrong
    r, _, _ = run_challenge(tmp_path, [h1, f2], {
        "A1": {"stance": "contradicted", "reason": "H1.", "evidence": ["H1"]},
        "A3": {"stance": "contradicted", "reason": "F2.", "evidence": ["F2"]}})
    assert (r["A1"]["stance"], r["A1"]["basis"]) == ("contradicted", BASIS_CONTRADICTING)
    assert r["A3"]["stance"] == "untested"


def test_low_relevance_is_not_contradiction(tmp_path):
    off = established("H1", "I like hiking on weekends.", origin="hypothesis_check",
                      standing=ev.Standing.CONTRADICTED, relevance="off_topic")
    r, _, _ = run_challenge(tmp_path, [off], {"A1": {"stance": "contradicted", "reason": "H1.", "evidence": ["H1"]}})
    assert r["A1"]["stance"] == "untested" and r["A1"]["links"][0]["relationship"] == IRRELEVANT


# --- concept relevance --------------------------------------------------------------------------------

TERMS = rel.BriefTerms(RELEASE_NOTES.problem_statement, RELEASE_NOTES.idea, RELEASE_NOTES.target_customer)


@pytest.mark.parametrize("text", [
    "I spend hours writing changelogs every release.",
    "I hand write the patch notes for each version.",
    "Writing the change log is the part of shipping I hate.",
    "As a product manager I write the release notes every Friday.",
])
def test_related_phrasings_match_the_statement(text):
    assert TERMS.statement_match(text)


@pytest.mark.parametrize("text", [
    "Our small team uses SaaS tools for everything.",  # customer words only
    "Developers at startups rarely take holidays.",  # customer words only
    "The release of the new console is delayed again.",  # 'release' alone is not release notes
    "I keep my notes in a paper notebook.",  # 'notes' alone is not release notes
    COMMUNICATION_CHANNEL,  # about release notes, but not about writing them
])
def test_superficially_similar_texts_do_not_match_the_statement(text):
    assert TERMS.statement_match(text) is None


def test_concept_list_is_small_and_documented():
    assert len(rel.PHRASES) + len(rel.WORDS) < 60
    assert "Limitations" in rel.__doc__
