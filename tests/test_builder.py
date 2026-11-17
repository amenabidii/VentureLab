"""Offline unit tests. Any model response here is explicitly MOCKED."""
import json
from html.parser import HTMLParser
from pathlib import Path

import pytest
from pydantic import ValidationError

from agents.builder import generate_kit
from builder_models import BuilderInput, ExperimentKit, LandingPageSpec
from builder_service import prepare
from landing_page import render_landing_page


@pytest.fixture
def payload():
    return json.loads((Path(__file__).parent / "fixtures/builder_input.json").read_text())


def test_valid_contracts_and_complete_kit(payload):
    brief = BuilderInput.model_validate(payload["brief"])
    kit = generate_kit(brief)
    assert len(kit.interview_questions) >= 5
    assert kit.success_criteria.threshold <= kit.success_criteria.sample_size
    assert "PROPOSED ASSUMPTION" in kit.success_criteria.label
    assert "NOT RUN" in kit.results_status
    assert kit.hypothesis and kit.validation_experiment and kit.failure_criteria
    assert len(kit.recommended_next_steps) >= 3
    assert ExperimentKit.model_validate_json(kit.model_dump_json()) == kit


@pytest.mark.parametrize("field,value", [("run_id", "../escape"), ("main_assumptions", []),
    ("business_idea", " "), ("target_customer", 42), ("product_category", "physical_goods"),
    ("founder_constraints", []), ("supporting_evidence", [{"statement": "example", "source_url": "file:///secret"}])])
def test_malformed_input(payload, field, value):
    payload["brief"][field] = value
    with pytest.raises(ValidationError):
        BuilderInput.model_validate(payload["brief"])


def test_missing_input(payload):
    del payload["brief"]["core_problem"]
    with pytest.raises(ValidationError):
        BuilderInput.model_validate(payload["brief"])


def test_impossible_threshold_rejected():
    from builder_models import Criterion
    with pytest.raises(ValidationError, match="Threshold"):
        Criterion(metric="Participants with a concrete example", threshold=6, sample_size=5)


def test_founder_review_is_not_a_customer_review(payload):
    payload["landing_page"]["proposed_solution"] = "Prepare experiments for founder review."
    assert LandingPageSpec.model_validate(payload["landing_page"])


def test_unknown_fields_rejected(payload):
    payload["brief"]["approved"] = True
    with pytest.raises(ValidationError):
        BuilderInput.model_validate(payload["brief"])


@pytest.mark.parametrize("field", ["product_name", "headline", "value_proposition", "target_audience", "problem", "proposed_solution", "features"])
def test_every_landing_content_field_is_escaped(payload, field):
    injection = '<svg onload="alert(1)"> & text'
    payload["landing_page"][field] = [injection] if field == "features" else injection
    page = render_landing_page(LandingPageSpec.model_validate(payload["landing_page"]))
    assert "<svg" not in page and "&lt;svg" in page


def test_evidence_remains_unverified(payload):
    payload["brief"]["supporting_evidence"] = [{"statement": "Supplied context", "source_url": "https://example.org/source"}]
    kit = generate_kit(BuilderInput.model_validate(payload["brief"]))
    assert kit.evidence[0].standing == "UNVERIFIED_CONTEXT"
    assert str(kit.evidence[0].source_url) == "https://example.org/source"


@pytest.mark.parametrize("url", ["https://user:secret@example.org/", "https://example.org/?api_key=secret"])
def test_url_credentials_rejected_without_echoing_secret(payload, url):
    payload["brief"]["supporting_evidence"] = [{"statement": "Context", "source_url": url}]
    with pytest.raises(ValidationError) as error:
        BuilderInput.model_validate(payload["brief"])
    assert "secret" not in str(error.value).replace("secret parameters", "parameters")


@pytest.mark.parametrize("claim", ["Guaranteed success", "Trusted by 100 customers", "Fake testimonials",
    "Five star reviews", "Only 3 left", "Act now", "Proven demand", "Customers said they love it",
    "Surveys confirmed demand", "Store your password", "Investment advice", "Impersonate a founder"])
def test_unsafe_content_rejected(payload, claim):
    payload["landing_page"]["headline"] = claim
    with pytest.raises(ValidationError):
        LandingPageSpec.model_validate(payload["landing_page"])


def test_non_leading_questions(payload):
    kit = generate_kit(BuilderInput.model_validate(payload["brief"]))
    altered = kit.model_dump()
    altered["interview_questions"] = list(altered["interview_questions"])
    altered["interview_questions"][0] = "Wouldn't you love this app?"
    with pytest.raises(ValidationError):
        ExperimentKit.model_validate(altered)


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements = []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def test_valid_html_and_no_external_collection(payload):
    page = render_landing_page(LandingPageSpec.model_validate(payload["landing_page"]))
    parser = PageParser()
    parser.feed(page)
    assert page.startswith("<!doctype html>")
    assert "@media(max-width:720px)" in page
    assert "ASSUMPTION" in page
    assert "not evidence" in page
    assert not {"script", "iframe", "form", "input", "img"} & {tag for tag, _ in parser.elements}
    assert all(attrs.get("href", "#").startswith("#") for _, attrs in parser.elements)
    assert any(attrs.get("http-equiv") == "Content-Security-Policy" for _, attrs in parser.elements)


def test_html_injection_is_text(payload):
    payload["landing_page"]["headline"] = '<script>alert("oops")</script><img src=x onerror=alert(1)>'
    page = render_landing_page(LandingPageSpec.model_validate(payload["landing_page"]))
    assert "&lt;script&gt;" in page
    assert "<script>" not in page and "<img " not in page


def test_mocked_model_path(payload, fake_ollama):
    fake = fake_ollama(chat_replies=['{"hypothesis":"Facilitators recently recreated workshop checklists."}'])
    with_client = fake.client()
    try:
        bundle = prepare(BuilderInput.model_validate(payload["brief"]), LandingPageSpec.model_validate(payload["landing_page"]), with_client)
    finally:
        with_client.close()
    assert bundle.generator == "ollama"
    assert "recreated" in bundle.kit.hypothesis


def test_mocked_unsafe_model_rejected(payload, fake_ollama):
    fake = fake_ollama(chat_replies=['{"hypothesis":"Guaranteed success"}'] * 2)
    from llm import LLMError
    client = fake.client()
    try:
        with pytest.raises(LLMError):
            generate_kit(BuilderInput.model_validate(payload["brief"]), client)
    finally:
        client.close()
