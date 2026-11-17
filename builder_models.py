"""Milestone 3 contracts. No dependency on the Milestone 2 workflow."""
from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, field_validator, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


def check_content(text: str) -> str:
    """Conservative deny rules, not a claim of semantic truth verification.

    All accepted founder/model assertions are still explicitly assumptions.
    Input is never interpreted as HTML, code, instructions, or an evidence verdict.
    """
    rules = (
        r"testimonial|\breviews\b|\b(?:fake|customer|five.star|5.star) review\b|\bstar[- ]rat(?:ing|ed)",
        r"\b(?:trusted|used|loved) by\b|\b\d[\d,]*\s+(?:customers|users|signups|sign-ups)\b",
        r"\b(?:guarantee\w*|risk.free|countdown|limited.time|act now|hurry|only \d+ left)\b",
        r"\b(?:revenue|income|profit)\b|\b(?:impersonat\w*|pretend to be|pose as)\b",
        r"\b(?:password|credit.card|card.number|cvv|api.key)\b|sk-[a-zA-Z0-9]{12,}",
        r"\b(?:crypto\w*|investment|financial|medical|health|legal|physical goods|stock trading|banking)\b",
        r"\b(?:hundreds|thousands|millions) of (?:users|customers|signups)\b",
        r"\b(?:interviews?|experiments?|surveys?)\s+(?:proved|confirmed|showed|found)\b",
        r"\b(?:validated demand|proven demand|customers said)\b",
    )
    normalized = text.casefold()
    if any(re.search(rule, normalized) for rule in rules):
        raise ValueError("Content violates the local prototype safety policy; revise the claim or concept")
    if any(ord(c) < 32 and c not in "\n\t\r" for c in text):
        raise ValueError("Control characters are not permitted")
    return text


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True, hide_input_in_errors=True)


class EvidenceReference(Contract):
    statement: Text
    source_url: HttpUrl
    standing: Literal["UNVERIFIED_CONTEXT"] = "UNVERIFIED_CONTEXT"

    _safe = field_validator("statement")(check_content)

    @field_validator("source_url")
    @classmethod
    def no_url_credentials(cls, value: HttpUrl) -> HttpUrl:
        from urllib.parse import parse_qsl
        if value.username or value.password:
            raise ValueError("Source URLs must not contain credentials")
        if any(key.casefold() in {"token", "key", "api_key", "password", "access_token"}
               for key, _ in parse_qsl(value.query or "")):
            raise ValueError("Source URLs must not contain secret parameters")
        return value


class BuilderInput(Contract):
    run_id: Identifier
    business_idea: Text
    target_customer: Text
    core_problem: Text
    main_assumptions: tuple[Text, ...] = Field(min_length=1, max_length=12)
    supporting_evidence: tuple[EvidenceReference, ...] = Field(default=(), max_length=20)
    founder_constraints: tuple[Text, ...] = Field(min_length=1, max_length=12)
    product_category: Literal["digital_product"]

    _safe = field_validator("business_idea", "target_customer", "core_problem")(check_content)

    @field_validator("main_assumptions", "founder_constraints")
    @classmethod
    def safe_list(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            check_content(value)
        return values


class Criterion(Contract):
    metric: Text
    threshold: int = Field(ge=1, le=100)
    sample_size: int = Field(ge=1, le=100)
    label: Literal["PROPOSED ASSUMPTION — requires founder approval"] = "PROPOSED ASSUMPTION — requires founder approval"

    _safe = field_validator("metric")(check_content)

    @model_validator(mode="after")
    def threshold_within_sample(self):
        if self.threshold > self.sample_size:
            raise ValueError("Threshold cannot exceed the proposed sample size")
        return self


class ExperimentKit(Contract):
    hypothesis: Text
    target_audience: Text
    interview_questions: tuple[Text, ...] = Field(min_length=5, max_length=12)
    validation_experiment: Text
    success_criteria: Criterion
    failure_criteria: Text
    recommended_next_steps: tuple[Text, ...] = Field(min_length=3, max_length=12)
    constraints: tuple[Text, ...]
    evidence: tuple[EvidenceReference, ...]
    results_status: Literal["NOT RUN — no responses or results collected"] = "NOT RUN — no responses or results collected"

    _safe = field_validator("hypothesis", "target_audience", "validation_experiment", "failure_criteria")(check_content)

    @field_validator("recommended_next_steps", "constraints")
    @classmethod
    def safe_items(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            check_content(value)
        return values

    @field_validator("interview_questions")
    @classmethod
    def non_leading(cls, questions: tuple[str, ...]) -> tuple[str, ...]:
        for question in questions:
            check_content(question)
            if re.search(r"would|wouldn't|don't you|do you agree|will you|love|amazing", question, re.I):
                raise ValueError("Interview questions must investigate past behavior, not invite agreement")
        return questions


class LandingPageSpec(Contract):
    product_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
    headline: Text
    value_proposition: Text
    target_audience: Text
    problem: Text
    proposed_solution: Text
    features: tuple[Text, ...] = Field(min_length=1, max_length=6)
    cta: Literal["Explore the proposed concept"] = "Explore the proposed concept"

    _safe = field_validator("product_name", "headline", "value_proposition", "target_audience", "problem", "proposed_solution")(check_content)

    @field_validator("features")
    @classmethod
    def safe_features(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            check_content(value)
        return values


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed_execution"
    EXECUTING = "executing"
    EXECUTED = "executed"


class ApprovalRequest(Contract):
    action_id: Identifier
    action_type: Literal["generate_local_artifacts"]
    run_id: Identifier
    artifact_identity: Identifier
    artifact_sha256: Digest
    description: Text
    status: ApprovalStatus = ApprovalStatus.PENDING
    destination: Text


class ApprovalDecision(Contract):
    action_id: Identifier
    artifact_sha256: Digest
    decision: Literal["approve", "reject"]
    actor: Literal["founder"]
    reason: Text
    _safe = field_validator("reason")(check_content)


class BuilderResult(Contract):
    action_id: Identifier
    run_id: Identifier
    artifact_sha256: Digest
    output_directory: str
    files: tuple[str, ...]
    status: Literal["executed"] = "executed"


class AuditEvent(Contract):
    timestamp: str
    agent: Literal["builder", "approval"]
    action: str
    sources: list[str]
    model: str | None
    cost: Literal[0] = 0
    approved_by: Literal["founder"] | None
    action_id: str | None = None
    run_id: str | None = None
    outcome: str
