"""Milestone 3 contracts. No dependency on the Milestone 2 workflow."""
from __future__ import annotations

import re
import unicodedata
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, field_validator, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
ReportText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=12000)]
Identifier = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")]
Digest = Annotated[str, StringConstraints(pattern=r"^[a-f0-9]{64}$")]


def check_content(text: str) -> str:
    """Conservative deny rules, not a claim of semantic truth verification.

    All accepted founder/model assertions are still explicitly assumptions.
    Input is never interpreted as HTML, code, instructions, or an evidence verdict.
    """
    rules = (
        r"testimonial|\b(?:fake|customer|five.star|5.star) reviews?\b|\bstar[- ]rat(?:ing|ed)",
        r"\b(?:trusted|used|loved) by\b|\b\d[\d,]*(?:\s+\w+){0,2}\s+(?:customers|users|signups|sign-ups)\b",
        r"\b(?:guarantee\w*|risk.free|countdown|limited.time|act now|hurry|only \d+ left)\b",
        r"\b(?:revenue|income|profit)\b|\b(?:impersonat\w*|pretend to be|pose as)\b",
        r"\b(?:password|credit.card|card.number|cvv|api.key)\b|sk-[a-zA-Z0-9]{12,}",
        r"\b(?:crypto\w*|investment|financial|medical advice|health advice|legal advice|physical goods|stock trading|banking)\b",
        r"\b(?:hundreds|thousands|millions) of (?:users|customers|signups)\b",
        r"\b(?:interviews?|experiments?|surveys?)\s+(?:proved|confirmed|showed|found|revealed|demonstrated)\b",
        r"\b(?:validated demand|proven demand|customers said)\b",
        r"(?:javascript|vbscript)\s*:|data\s*:\s*(?:text|application)",
    )
    normalized = ''.join(c for c in unicodedata.normalize("NFKC", text).casefold()
                         if unicodedata.category(c) != "Cf")
    if any(re.search(rule, normalized) for rule in rules):
        raise ValueError("Content violates the local prototype safety policy; revise the claim or concept")
    if any((ord(c) < 32 and c not in "\n\t\r") or ord(c) in range(0x202A, 0x202F)
           or ord(c) in range(0x2066, 0x206A) or 0xD800 <= ord(c) <= 0xDFFF for c in text):
        raise ValueError("Control characters are not permitted")
    return text


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, validate_default=True,
                              revalidate_instances="always", hide_input_in_errors=True)


class ExperimentDesign(Contract):
    sample_size: int = Field(default=5, ge=1, le=100, strict=True)
    success_minimum: int = Field(default=3, ge=1, le=100, strict=True)
    recall_days: int = Field(default=30, ge=1, le=365, strict=True)
    assumption_index: int = Field(default=0, ge=0, le=11, strict=True)

    @model_validator(mode="after")
    def valid_threshold(self):
        if self.success_minimum > self.sample_size:
            raise ValueError("Success minimum must not exceed sample size")
        return self


class GateContext(Contract):
    """Optional upstream admission, mapped by an adapter; never a Builder verdict."""
    decision_id: Identifier
    outcome: Literal["GO", "REPEAT", "PIVOT", "STOP"]


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
    experiment_design: ExperimentDesign = Field(default_factory=ExperimentDesign)
    gate_context: GateContext | None = None

    @model_validator(mode="after")
    def valid_focus(self):
        if self.experiment_design.assumption_index >= len(self.main_assumptions):
            raise ValueError("Selected assumption does not exist")
        return self

    _safe = field_validator("business_idea", "target_customer", "core_problem")(check_content)

    @field_validator("main_assumptions", "founder_constraints")
    @classmethod
    def safe_list(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            check_content(value)
        return values


class Criterion(Contract):
    metric: Text
    threshold: int = Field(ge=1, le=100, strict=True)
    sample_size: int = Field(ge=1, le=100, strict=True)
    label: Literal["PROPOSED ASSUMPTION — requires founder approval"] = "PROPOSED ASSUMPTION — requires founder approval"

    _safe = field_validator("metric")(check_content)

    @model_validator(mode="after")
    def threshold_within_sample(self):
        if self.threshold > self.sample_size:
            raise ValueError("Threshold cannot exceed the proposed sample size")
        return self


class ExperimentKit(Contract):
    hypothesis: ReportText
    assumption_index: int = Field(ge=0, le=11, strict=True)
    assumption_under_test: Text
    untested_assumptions: tuple[Text, ...]
    target_audience: Text
    interviewer_brief: ReportText
    interview_questions: tuple[Text, ...] = Field(min_length=5, max_length=12)
    validation_experiment: ReportText
    success_criteria: Criterion
    failure_criteria: Text
    recommended_next_steps: tuple[Text, ...] = Field(min_length=3, max_length=12)
    constraints: tuple[Text, ...]
    evidence: tuple[EvidenceReference, ...]
    results_status: Literal["NOT RUN — no responses or results collected"] = "NOT RUN — no responses or results collected"

    _safe = field_validator("hypothesis", "interviewer_brief", "target_audience", "validation_experiment",
                            "failure_criteria")(check_content)

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
    reason: str = Field(default="", max_length=500)
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
    artifact_sha256: Digest | None = None
    artifact_identity: str | None = None
    action_type: str | None = None
    destination: str | None = None
    outcome: str
