"""Live connectivity tests against the real Ollama server.

Skipped unless VENTURELAB_LIVE_TESTS=1. Run inside the compose stack:
    docker compose run --rm -e VENTURELAB_LIVE_TESTS=1 app pytest -m live
"""

from __future__ import annotations

import os

import pytest
from pydantic import BaseModel

from llm import OllamaClient

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("VENTURELAB_LIVE_TESTS") != "1", reason="set VENTURELAB_LIVE_TESTS=1"),
]


class Reply(BaseModel):
    status: str
    sum: int


@pytest.fixture(scope="module")
def client():
    c = OllamaClient()
    yield c
    c.close()


def test_server_reachable(client):
    assert client.version()


def test_configured_model_installed(client):
    assert client.has_model(client.settings.model), client.list_models()


def test_structured_json_inference(client):
    messages = [
        {"role": "system", "content": "Reply with JSON only."},
        {"role": "user", "content": 'Set "status" to "ok" and "sum" to 2 + 3.'},
    ]
    result = client.chat_json(client.settings.model, messages, Reply, num_predict=32)
    assert result.parsed == Reply(status="ok", sum=5)
    assert result.metrics.output_tokens > 0


def test_live_extraction_quotes_are_exact_source_text(client):
    import evidence as ev
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "bench" / "fixtures" / "synthetic_source.txt").read_text(
        encoding="utf-8"
    )
    items, result = ev.extract_claims(client, client.settings.model, source, topic="unpaid invoices")
    assert items, "the model found no claims"
    for item in items:
        for quote in item.quotes:
            if quote.verified:
                assert source[quote.start : quote.end] == quote.text
        if not item.verified:
            assert item.standing is ev.Standing.ASSUMPTION


def test_live_assessment_and_second_check_return_valid_output(client):
    import evidence as ev

    answer, check, results = ev.evaluate(
        client, client.settings.model,
        "PodTrim's Basic plan costs $12 per month.",
        ["The Basic plan is $12 per month, billed monthly."],
        "PodTrim pricing. The Basic plan is $12 per month, billed monthly.",
    )
    assert answer.verdict in {"supports", "partially_supports", "does_not_support", "contradicts"}
    assert answer.reason and answer.limitations
    assert (check is not None) == (answer.verdict == "supports")
    assert all(r.parsed is not None for r in results)


def test_live_wrong_speaker_is_never_established(client):
    """Real model, application code: a claim crediting a bookkeeper's words to a translator."""
    import evidence as ev
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "bench" / "fixtures" / "synthetic_source.txt").read_text(
        encoding="utf-8"
    )
    passages = ev.split_passages(source)
    target = next(p.id for p in passages if "most common reason they call me" in p.text)
    item = ev.EvidenceItem(
        "A freelance translator says matching payments to invoices is the most common reason they call.",
        "customer_problem", ev.quotes_from_passages(source, passages, [target]),
    )
    ev.assess_item(client, client.settings.model, item, source)
    assert item.verdict is not None, item.notes
    assert item.unsourced and "translator" in item.unsourced
    assert item.standing is not ev.Standing.ESTABLISHED


def test_live_pipeline_promotes_only_grounded_attributed_claims(client):
    """Real model, application code: extraction then assessment on the synthetic thread."""
    import evidence as ev
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "bench" / "fixtures" / "synthetic_source.txt").read_text(
        encoding="utf-8"
    )
    items, _ = ev.extract_claims(client, client.settings.model, source, topic="unpaid invoices",
                                 max_passages=16, max_claims=3, num_predict=250)
    for item in items:
        ev.assess_item(client, client.settings.model, item, source)
    assert items
    for item in ev.established(items):
        assert item.verified and item.confirmed is True
        assert item.unsourced == [] and item.attributed is True
    for item in items:
        if item.standing is ev.Standing.NEEDS_REVIEW:
            assert item.review  # the reason is kept for the person reviewing it


def test_live_challenger_output_is_grounded(client, tmp_path):
    """Real model: the Challenger's points are labelled by code, never by the model."""
    import evidence as ev
    from agents.challenger import BASIS_ASSUMPTION, challenge
    from agents.investigator import Finding
    from audit import AuditLog
    from brief import FounderBrief

    brief = FounderBrief.model_validate({
        "idea": "A web app that drafts release notes from merged pull requests.",
        "problem_statement": "Small software teams spend too much time writing release notes.",
        "target_customer": "developers at small SaaS companies", "market": "online",
        "founder_skills": ["Python"], "hours_per_week": 10, "budget_eur": 0,
    })
    text = "As a developer I spend two hours on the changelog for each release."
    item = ev.EvidenceItem("One developer says I spend two hours on the changelog for each release.",
                           "customer_problem", [ev.verify_span(text, 0, len(text), "https://example.test/c1")],
                           "supports", confirmed=True, unsourced=[], attributed=True)
    findings = [Finding("F1", "extracted", "hn_comments", item)]
    result = challenge(brief, findings, client, client.settings.model, AuditLog(tmp_path / "log.json", "live"))
    assert result.status == "ok", result.error
    assert [r["assumption"] for r in result.reviews] == ["A1", "A2", "A3", "A4", "A5", "A6"]
    for group in (result.reviews, result.new_hypotheses, result.risks):
        for p in group:
            assert set(p["evidence"]) <= {"F1"}  # constrained output: only IDs that exist
            assert p["evidence"] or p["basis"] == BASIS_ASSUMPTION
    for r in result.reviews:
        if r["stance"] == "supported":
            assert r["evidence"] == ["F1"]
    for e in result.experiments:
        assert e["assumption"] in {"A1", "A2", "A3", "A4", "A5", "A6"} and e["support_if"] and e["weaken_if"]
