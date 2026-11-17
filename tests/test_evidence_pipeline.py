"""End-to-end safety of the evidence pipeline, through the application code.

Each test runs `extract_claims` and `assess_item` from `evidence.py` on the
SYNTHETIC invoice thread, with the STUBBED Ollama playing a model that makes a
specific mistake and then over-confidently says `supports` and passes its own
second check. The deterministic safeguards must stop every one of these from
becoming an ESTABLISHED finding, while keeping the claim visible for review.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import evidence as ev

SOURCE = (Path(__file__).resolve().parent.parent / "bench" / "fixtures" / "synthetic_source.txt").read_text(
    encoding="utf-8"
)
PASSAGES = ev.split_passages(SOURCE)
TOPIC = "freelancers tracking unpaid invoices"


def pid(fragment: str) -> int:
    return next(p.id for p in PASSAGES if fragment in p.text)


BOOKKEEPER = pid("most common reason they call me")
LOSE_HOURS = pid("Every month I lose at least two hours")
SUPPORTS = json.dumps({"reason": "The quote states this.", "limitations": "none", "verdict": "supports"})
CONFIRMED = json.dumps({"problems": "none", "fully_supported": True})


def run_pipeline(fake_ollama, claim: str, passages: list[int], replies: list[str]) -> list[ev.EvidenceItem]:
    extraction = json.dumps({"claims": [{"type": "customer_problem", "claim": claim, "passages": passages}]})
    fake = fake_ollama(chat_replies=[extraction, *replies])
    client = fake.client()
    items, _ = ev.extract_claims(client, "qwen3:4b", SOURCE, topic=TOPIC, source_url="https://example.test/thread")
    for item in items:
        ev.assess_item(client, "qwen3:4b", item, SOURCE)
    return items


@pytest.mark.parametrize(
    ("case", "claim", "passage", "words"),
    [
        ("wrong speaker",
         "A freelance translator says matching payments to invoices is the most common reason they call.",
         BOOKKEEPER, ["freelance", "translator"]),
        ("invented group size",
         "Two bookkeepers say matching payments to invoices is the most common reason they call.",
         BOOKKEEPER, ["two"]),
        ("one person made into most of a group",
         "Most freelance translators lose at least two hours a month checking invoices.",
         LOSE_HOURS, ["most"]),
        ("unsupported paraphrase adding a cause",
         "One translator loses two hours a month because invoicing apps are too expensive.",
         LOSE_HOURS, ["apps", "too", "expensive"]),
    ],
)
def test_overconfident_model_cannot_establish_changed_wording(fake_ollama, case, claim, passage, words):
    items = run_pipeline(fake_ollama, claim, [passage], [SUPPORTS, CONFIRMED])
    assert len(items) == 1, case
    item = items[0]
    assert item.verified and item.verdict == "supports" and item.confirmed is True
    assert set(words) <= set(item.unsourced), (case, item.unsourced)
    # Kept and visible for a person, never a finding.
    assert item.standing is ev.Standing.NEEDS_REVIEW
    assert ev.established(items) == []
    assert any("wording goes beyond the quoted text" in r for r in item.review)
    # The verified quotation itself is still available to the reviewer.
    assert all(q.verified and q.text in SOURCE for q in item.quotes)


@pytest.mark.parametrize(
    "claim",
    [
        "Bookkeepers say matching payments to invoices is the most common reason they call.",
        "Sole traders call their bookkeeper most often about matching payments to invoices.",
    ],
)
def test_one_persons_words_cannot_become_a_groups_finding(fake_ollama, claim):
    # Every word is in the text (plurals match singulars), so only the attribution rule catches this.
    items = run_pipeline(fake_ollama, claim, [BOOKKEEPER], [SUPPORTS, CONFIRMED])
    item = items[0]
    assert item.attributed is False
    assert item.standing is ev.Standing.NEEDS_REVIEW and ev.established(items) == []
    assert any("attributed to one person" in r for r in item.review)


def test_faithful_attributed_claim_is_established(fake_ollama):
    claim = "One bookkeeper says matching payments to invoices is the most common reason sole traders call."
    items = run_pipeline(fake_ollama, claim, [BOOKKEEPER], [SUPPORTS, CONFIRMED])
    assert items[0].unsourced == [] and items[0].attributed is True and items[0].review == []
    assert ev.established(items) == items


def test_altered_quotation_is_unverified_and_never_assessed():
    # The legacy path where a model writes the quote: "600 euro" altered to "6.000 euro".
    quote = ev.verify_excerpt(SOURCE, "I only noticed a 6.000 euro invoice was unpaid after four months.")
    item = ev.EvidenceItem("One illustrator missed an unpaid 6.000 euro invoice.", "customer_problem", [quote])
    assert not quote.verified and "UNVERIFIED" in quote.display()
    # Even if something later wrote a confident verdict onto it, it cannot be promoted.
    item.verdict, item.confirmed, item.unsourced = "supports", True, []
    assert item.standing is ev.Standing.ASSUMPTION


def test_passage_the_model_was_not_shown_gives_an_unverified_assumption(fake_ollama):
    items = run_pipeline(fake_ollama, "One user says invoices are late.", [999], [])
    item = items[0]
    assert not item.verified and item.standing is ev.Standing.ASSUMPTION
    assert any("not verified" in n for n in item.notes)
    assert len(items) == 1  # kept, labelled, not dropped


def test_contradiction_in_reason_with_weaker_verdict_is_flagged_not_changed(fake_ollama):
    reply = json.dumps({"reason": "The context contradicts the claim: he says a spreadsheet is fine.",
                        "limitations": "one person", "verdict": "does_not_support"})
    items = run_pipeline(fake_ollama, "One user says spreadsheets do not work for invoices.",
                         [pid("I just use a spreadsheet")], [reply])
    item = items[0]
    assert item.verdict == "does_not_support" and item.standing is ev.Standing.UNSUPPORTED
    assert any("reason mentions a contradiction" in r for r in item.review)


def test_contradicts_verdict_is_kept_as_contradicted(fake_ollama):
    reply = json.dumps({"reason": "The context contradicts the claim.", "limitations": "",
                        "verdict": "contradicts"})
    items = run_pipeline(fake_ollama, "One user says spreadsheets do not work for invoices.",
                         [pid("I just use a spreadsheet")], [reply])
    assert items[0].standing is ev.Standing.CONTRADICTED
    assert not any("contradiction" in r for r in items[0].review)
