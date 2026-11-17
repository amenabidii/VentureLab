"""Quotation verification and the promotion rule (offline; model calls use the STUBBED Ollama)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import evidence as ev
from llm import LLMError

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "bench" / "fixtures"
SOURCE = (
    "Post 1: I lose two hours a month.  It is boring!\n"
    "Post 2: I only noticed a 600 euro invoice was unpaid after four months. I use a spreadsheet."
)


def _reply(obj) -> str:
    return json.dumps(obj)


# --- passages ------------------------------------------------------------------


@pytest.mark.parametrize("name", ["synthetic_source.txt", "synthetic_forum_page.txt"])
def test_passage_offsets_are_exact(name):
    source = (FIXTURES / name).read_text(encoding="utf-8")
    passages = ev.split_passages(source)
    assert passages
    assert [p.id for p in passages] == list(range(1, len(passages) + 1))
    for p in passages:
        assert source[p.start : p.end] == p.text
        assert p.text == p.text.strip() and p.text


def test_long_unbroken_text_is_cut_without_losing_characters():
    source = "x" * 900 + ". Short one."
    passages = ev.split_passages(source, max_chars=400)
    assert all(source[p.start : p.end] == p.text for p in passages)
    assert "".join(p.text for p in passages if p.text.startswith("x")) == "x" * 900 + "."


def test_prefilter_keeps_relevant_passages_in_order():
    passages = ev.split_passages(SOURCE)
    kept = ev.rank_passages(passages, "unpaid invoices spreadsheet", k=2)
    assert [p.id for p in kept] == sorted(p.id for p in kept)
    assert any("600 euro invoice" in p.text for p in kept)


# --- quotations ------------------------------------------------------------------


def test_quote_from_ids_copies_source_text():
    passages = ev.split_passages(SOURCE)
    [quote] = ev.quotes_from_passages(SOURCE, passages, [3])
    assert quote.verified
    assert quote.text == SOURCE[quote.start : quote.end]
    assert "600 euro" in quote.text


def test_consecutive_ids_become_one_quote_and_gaps_become_separate_quotes():
    passages = ev.split_passages(SOURCE)
    joined = ev.quotes_from_passages(SOURCE, passages, [3, 4])
    assert len(joined) == 1 and joined[0].text == SOURCE[passages[2].start : passages[3].end]
    separate = ev.quotes_from_passages(SOURCE, passages, [1, 3])
    assert [q.text for q in separate] == [passages[0].text, passages[2].text]
    assert all(q.verified for q in separate)


@pytest.mark.parametrize("ids", [[], [99], [1, 99], [0]])
def test_bad_passage_ids_give_unverified_quote(ids):
    [quote] = ev.quotes_from_passages(SOURCE, ev.split_passages(SOURCE), ids)
    assert not quote.verified
    assert quote.text == ""


def test_changed_number_is_rejected():
    # Root cause of the Milestone 1 failures: the model turned "600 euro" into "6.000 euro".
    assert not ev.verify_excerpt(SOURCE, "I only noticed a 6.000 euro invoice was unpaid after four months.").verified


def test_paraphrase_is_rejected():
    assert not ev.verify_excerpt(SOURCE, "I noticed an unpaid 600 euro invoice after four months.").verified


def test_whitespace_and_curly_quotes_tolerated_but_source_text_returned():
    source = "She said “it’s fine”   twice."
    quote = ev.verify_excerpt(source, "said \"it's fine\" twice")
    assert quote.verified
    assert quote.text == "said “it’s fine”   twice"  # original characters, not the submitted ones


def test_empty_excerpt_is_rejected():
    assert not ev.verify_excerpt(SOURCE, "   ").verified


def test_unverified_quote_is_never_displayed_as_quotation():
    shown = ev.verify_excerpt(SOURCE, "made up words").display()
    assert shown.startswith("[UNVERIFIED")
    assert "“" not in shown


# --- promotion rule ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("verified", "verdict", "confirmed", "claim_type", "standing"),
    [
        (True, "supports", True, "customer_problem", ev.Standing.ESTABLISHED),
        (True, "supports", True, "competitor", ev.Standing.ESTABLISHED),
        (True, "supports", False, "customer_problem", ev.Standing.PARTIAL),  # second check disagreed
        (True, "supports", None, "customer_problem", ev.Standing.PARTIAL),  # second check not run
        (True, "supports", True, "demand", ev.Standing.PARTIAL),  # desk research cannot establish demand
        (True, "partially_supports", True, "segment", ev.Standing.PARTIAL),
        (True, "does_not_support", None, "segment", ev.Standing.UNSUPPORTED),
        (True, "contradicts", None, "segment", ev.Standing.CONTRADICTED),
        (True, None, None, "segment", ev.Standing.ASSUMPTION),
        (False, "supports", True, "customer_problem", ev.Standing.ASSUMPTION),
        (False, "partially_supports", None, "segment", ev.Standing.ASSUMPTION),
        (False, None, None, "segment", ev.Standing.ASSUMPTION),
    ],
)
def test_promotion_rule(verified, verdict, confirmed, claim_type, standing):
    assert ev.standing_for(verified, verdict, confirmed, claim_type, grounded=True) is standing


def test_ungrounded_or_unchecked_wording_is_never_established():
    review = ev.Standing.NEEDS_REVIEW
    assert ev.standing_for(True, "supports", True, "customer_problem", grounded=False) is review
    assert ev.standing_for(True, "supports", True, "customer_problem") is review  # check not run
    item = ev.EvidenceItem("c", "customer_problem", [ev.verify_span(SOURCE, 0, 10)], "supports", confirmed=True)
    assert item.unsourced is None and item.standing is review
    # Demand and unconfirmed support stay partial evidence whatever the wording.
    assert ev.standing_for(True, "supports", True, "demand", grounded=False) is ev.Standing.PARTIAL
    assert ev.standing_for(True, "supports", False, "segment", grounded=False) is ev.Standing.PARTIAL


@pytest.mark.parametrize(
    ("claim", "support", "missing"),
    [
        # wrong speaker
        ("A freelance translator says matching payments is the most common reason they call.",
         "As a bookkeeper I see this a lot. Matching payments is the most common reason they call me.",
         ["freelance", "translator"]),
        # one person turned into a group, and an invented count
        ("Two posters report AI tools cut breaths.", "The AI tools still cut breaths in strange places.",
         ["two", "posters"]),
        ("Freelance audio editors report significant limitations.", "I edit for nine shows as a freelancer.",
         ["freelance", "audio", "editors", "significant", "limitations"]),
        # changed number
        ("One poster lost a 6000 euro invoice.", "I only noticed a 600 euro invoice was unpaid.", ["lost", "6000"]),
        # conservative: a faithful paraphrase is still held for review
        ("PodTrim's Pro plan costs 29 dollars per seat.", "PodTrim's Pro plan is 29 dollars a month per seat.",
         ["costs"]),
        ("Most posters say editing is slow.", "Editing is slow for me.", ["most", "posters"]),
    ],
)
def test_wording_beyond_the_quote_is_found(claim, support, missing):
    assert ev.unsourced_words(claim, support) == missing


@pytest.mark.parametrize(
    ("claim", "support"),
    [
        ("One user says she checked invoices every month.", "I check invoices every month."),
        ("Someone loses two hours a month.", "I lose two hours a month."),
    ],
)
def test_faithful_wording_passes(claim, support):
    assert ev.unsourced_words(claim, support) == []


@pytest.mark.parametrize(
    "claim",
    [
        "Freelancers are willing to pay for invoice-matching software.",
        "One host says she would pay 15 dollars a month.",
        "Wedding planners will pay for a seating-chart app.",
        "PayMatch has 8,000 paying subscribers.",
        "Two clients paid for an AI tool for a month.",
        "Students buy the premium plan.",
        "There is demand for automatic transcripts.",
        "One poster cancelled two subscriptions.",
    ],
)
def test_payment_language_makes_a_demand_claim(claim):
    assert ev.effective_claim_type(claim, "customer_problem") == "demand"
    item = ev.EvidenceItem(claim, "customer_problem", [ev.verify_span(SOURCE, 0, 10)], "supports", confirmed=True)
    assert item.standing is ev.Standing.PARTIAL


@pytest.mark.parametrize(
    "claim",
    [
        "One translator says invoices are often paid late.",
        "Payments land in two different bank accounts.",
        "One freelancer says a 600 euro invoice was unpaid for four months.",
        "Restaurants want an AI menu-translation tool.",
    ],
)
def test_ordinary_payment_talk_is_not_demand(claim):
    assert ev.effective_claim_type(claim, "customer_problem") == "customer_problem"


def test_failed_assessment_leaves_claim_an_assumption(fake_ollama):
    cut_off = '{"reason": "a very long reason that never ends'
    fake = fake_ollama(chat_replies=[cut_off, cut_off])
    item = ev.EvidenceItem("c", "segment", ev.quotes_from_passages(SOURCE, ev.split_passages(SOURCE), [1]))
    assert ev.assess_item(fake.client(), "qwen3:4b", item, SOURCE) == []
    assert item.verdict is None
    assert item.standing is ev.Standing.ASSUMPTION
    assert any("assessment failed" in n for n in item.notes)


def test_item_with_any_unverified_quote_is_not_verified():
    good = ev.verify_span(SOURCE, 0, 10)
    bad = ev.verify_excerpt(SOURCE, "not in the source")
    item = ev.EvidenceItem("c", "customer_problem", [good, bad], "supports", confirmed=True)
    assert not item.verified
    assert item.standing is ev.Standing.ASSUMPTION
    assert ev.EvidenceItem("c", "customer_problem", [], "supports", confirmed=True).standing is ev.Standing.ASSUMPTION


def test_established_filter():
    good = [ev.verify_span(SOURCE, 0, 10)]
    items = [
        ev.EvidenceItem("a", "customer_problem", good, "supports", confirmed=True, unsourced=[], attributed=True),
        ev.EvidenceItem("b", "customer_problem", good, "supports", confirmed=False),
        ev.EvidenceItem("c", "demand", good, "supports", confirmed=True),
        ev.EvidenceItem("d", "customer_problem", good, "partially_supports"),
        ev.EvidenceItem("e", "customer_problem", good),
    ]
    assert [i.claim for i in ev.established(items)] == ["a"]


# --- model calls (STUBBED Ollama) ---------------------------------------------------------


def test_extraction_builds_quotes_from_ids(fake_ollama):
    reply = {"claims": [{"type": "customer_problem", "claim": "Invoice unpaid for months.", "passages": [3],
                         "quote": "INVENTED TEXT the model tried to add"}]}
    fake = fake_ollama(chat_replies=[_reply(reply)])
    items, _ = ev.extract_claims(fake.client(), "qwen3:4b", SOURCE, topic="unpaid invoices")
    assert len(items) == 1 and items[0].verified
    assert items[0].quotes[0].text == ev.split_passages(SOURCE)[2].text
    assert all("INVENTED" not in q.text for q in items[0].quotes)
    _, body = fake.requests[-1]
    assert "exact quotation is retrieved separately" in body["messages"][0]["content"]
    assert "Start with who says it" in body["messages"][0]["content"]
    assert "Never write about a group" in body["messages"][0]["content"]
    assert "at most 5 claims" in body["messages"][0]["content"]


def test_extraction_respects_claim_limit(fake_ollama):
    claim = {"type": "segment", "claim": "x", "passages": [1]}
    fake = fake_ollama(chat_replies=[_reply({"claims": [claim] * 5})])
    items, _ = ev.extract_claims(fake.client(), "qwen3:4b", SOURCE, topic="t", max_claims=3)
    assert len(items) == 3
    assert "at most 3 claims" in fake.requests[-1][1]["messages"][0]["content"]


def test_extraction_rejects_ids_that_were_not_shown(fake_ollama):
    fake = fake_ollama(chat_replies=[_reply({"claims": [{"type": "segment", "claim": "x", "passages": [1]}]})])
    items, _ = ev.extract_claims(fake.client(), "qwen3:4b", SOURCE, topic="spreadsheet invoice", max_passages=1)
    assert not items[0].verified
    assert items[0].standing is ev.Standing.ASSUMPTION


def test_unverified_items_are_never_sent_for_assessment(fake_ollama):
    fake = fake_ollama(chat_replies=[])
    item = ev.EvidenceItem("c", "segment", [ev.verify_excerpt(SOURCE, "invented")])
    assert ev.assess_item(fake.client(), "qwen3:4b", item, SOURCE) == []
    assert item.verdict is None and item.standing is ev.Standing.ASSUMPTION
    assert fake.requests == []


def test_supports_verdict_triggers_second_check_and_can_be_overruled(fake_ollama):
    fake = fake_ollama(chat_replies=[
        _reply({"reason": "r", "limitations": "l", "verdict": "supports"}),
        _reply({"problems": "scope: one person, claim says most", "fully_supported": False}),
    ])
    item = ev.EvidenceItem("Most people lose hours.", "customer_problem", ev.quotes_from_passages(
        SOURCE, ev.split_passages(SOURCE), [1]))
    ev.assess_item(fake.client(), "qwen3:4b", item, SOURCE)
    assert item.verdict == "supports" and item.confirmed is False
    assert item.standing is ev.Standing.PARTIAL
    assert len(fake.requests) == 2


def test_supports_confirmed_is_established(fake_ollama):
    fake = fake_ollama(chat_replies=[
        _reply({"reason": "r", "limitations": "l", "verdict": "supports"}),
        _reply({"problems": "none", "fully_supported": True}),
    ])
    item = ev.EvidenceItem("Someone loses two hours a month.", "customer_problem",
                           ev.quotes_from_passages(SOURCE, ev.split_passages(SOURCE), [1]))
    ev.assess_item(fake.client(), "qwen3:4b", item, SOURCE)
    assert item.unsourced == []
    assert item.standing is ev.Standing.ESTABLISHED


def test_confirmed_support_with_changed_wording_needs_review(fake_ollama):
    fake = fake_ollama(chat_replies=[
        _reply({"reason": "r", "limitations": "l", "verdict": "supports"}),
        _reply({"problems": "none", "fully_supported": True}),
    ])
    item = ev.EvidenceItem("Two freelancers lose two hours a month.", "customer_problem",
                           ev.quotes_from_passages(SOURCE, ev.split_passages(SOURCE), [1]))
    ev.assess_item(fake.client(), "qwen3:4b", item, SOURCE)
    assert item.confirmed is True and item.unsourced == ["freelancers"]
    assert item.standing is ev.Standing.NEEDS_REVIEW
    assert any("wording goes beyond" in r for r in item.review)


def test_other_verdicts_skip_second_check(fake_ollama):
    fake = fake_ollama(chat_replies=[_reply({"reason": "r", "limitations": "l", "verdict": "contradicts"})])
    item = ev.EvidenceItem("c", "segment", ev.quotes_from_passages(SOURCE, ev.split_passages(SOURCE), [2]))
    ev.assess_item(fake.client(), "qwen3:4b", item, SOURCE)
    assert item.confirmed is None and item.standing is ev.Standing.CONTRADICTED
    assert len(fake.requests) == 1


def test_assessment_writes_reason_before_verdict(fake_ollama):
    fake = fake_ollama(chat_replies=[_reply({"reason": "r", "limitations": "l", "verdict": "supports"})])
    ev.assess(fake.client(), "qwen3:4b", "claim", ["quote"], "context")
    schema = fake.requests[-1][1]["format"]
    assert list(schema["properties"]) == ["reason", "limitations", "verdict"]


def test_assessment_rejects_unknown_verdicts(fake_ollama):
    bad = _reply({"reason": "r", "limitations": "l", "verdict": "probably"})
    fake = fake_ollama(chat_replies=[bad, bad])
    with pytest.raises(LLMError):
        ev.assess(fake.client(), "qwen3:4b", "claim", ["quote"], "context")


def test_context_includes_neighbouring_passages():
    passages = ev.split_passages(SOURCE)
    quotes = ev.quotes_from_passages(SOURCE, passages, [3])
    context = ev.context_for(SOURCE, quotes)
    assert passages[1].text in context and passages[3].text in context
    assert ev.context_for(SOURCE, [ev.verify_excerpt(SOURCE, "invented")]) == ""


def test_prompts_exist():
    for name in ("investigator_assess", "investigator_confirm"):
        assert ev.load_prompt(name)
    assert "at most 4 claims" in ev.load_prompt("investigator_extract", max_claims=4)
