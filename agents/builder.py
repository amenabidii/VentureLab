"""Local validation design. Template mode is deterministic, not a model stub."""
from __future__ import annotations

import html
from pathlib import Path
import re

from builder_models import BuilderInput, Criterion, ExperimentKit, Contract
from pydantic import Field
from llm import OllamaClient


class AssumptionSelection(Contract):
    assumption_index: int = Field(ge=0, le=11, strict=True)


def model_selects(brief: BuilderInput, client: OllamaClient | None) -> bool:
    """The model is consulted only when there is a real choice between assumptions."""
    return client is not None and len(brief.main_assumptions) > 1


def generate_kit(brief: BuilderInput, client: OllamaClient | None = None) -> ExperimentKit:
    brief = BuilderInput.model_validate(brief.model_dump())
    index = brief.experiment_design.assumption_index
    if model_selects(brief, client):
        result = client.chat_json(client.settings.model, [
            {"role": "system", "content": (Path(__file__).resolve().parent.parent / "prompts/builder.md").read_text(encoding="utf-8")},
            {"role": "user", "content": brief.model_dump_json()},
        ], AssumptionSelection, num_predict=64)
        index = result.parsed.assumption_index
    return assemble_kit(brief, index)


def assemble_kit(brief: BuilderInput, index: int) -> ExperimentKit:
    """Operational problem-discovery proxy; not proof of solution adoption.

    Model output selects a supplied assumption, never introduces factual prose.
    A founder must judge whether this proxy is appropriate for their premise.
    """
    brief = BuilderInput.model_validate(brief.model_dump())
    if type(index) is not int or not 0 <= index < len(brief.main_assumptions):
        raise ValueError("Model selected an assumption outside the supplied brief")
    design = brief.experiment_design
    hypothesis = (
        "ASSUMPTION: all numerical values are PROPOSED ASSUMPTIONS until founder approval. "
        f"At least {design.success_minimum} of {design.sample_size} consenting adult participants "
        f"from this segment: {brief.target_customer}, can describe a concrete occurrence within "
        f"the past {design.recall_days} days of this stated problem: {brief.core_problem}, "
        "and an action they actually took to address it. This tests a problem-discovery proxy "
        f"for the founder premise: {brief.main_assumptions[index]}. It does not establish demand for the proposed solution."
    )
    return ExperimentKit(
        hypothesis=hypothesis,
        assumption_index=index,
        assumption_under_test=brief.main_assumptions[index],
        untested_assumptions=tuple(a for i, a in enumerate(brief.main_assumptions) if i != index),
        target_audience=brief.target_customer,
        interviewer_brief=(
            f"Situation to listen for: {brief.core_problem}. Questions say \"this situation\" so the "
            "participant describes it in their own words; name it neutrally if they ask. Do not "
            "describe or show the proposed solution until every question has been answered. "
            "A participant with no recent occurrence is a valid result, not a failed interview."
        ),
        interview_questions=(
            "Tell me about the last time, if any, you encountered this situation. What happened?",
            "What steps did you take to address it that time?",
            "Which tools or alternatives did you use, and how did they fit your process?",
            "What time or effort did that experience require?",
            "What, if anything, was difficult about your existing approach?",
            "When did this last occur before that occasion?",
            "What, if anything, have you already tried to change about this process?",
        ),
        validation_experiment=(
            f"Invite consenting adults from this segment: {brief.target_customer}. "
            f"Investigate this problem without pitching a solution: {brief.core_problem}. "
            "Conduct voluntary interviews about recent actual behavior. Explain the research purpose; "
            "allow skipping any question or withdrawing. Keep only anonymous aggregate notes outside "
            "this prototype; do not collect identifying or sensitive information. No outreach is automated."
        ),
        success_criteria=Criterion(
            metric=f"Participants describing a concrete instance within the proposed {design.recall_days}-day recall window and an action they took",
            threshold=design.success_minimum, sample_size=design.sample_size,
        ),
        failure_criteria=(
            f"PROPOSED ASSUMPTION until approved: in a completed sample of {design.sample_size}, "
            f"fewer than {design.success_minimum} qualifying accounts weakens the hypothesis. "
            "Repeated absence of the problem or satisfactory existing alternatives also weakens it. "
            "An incomplete or biased sample is inconclusive; this kit makes no business gate decision."
        ),
        recommended_next_steps=(
            "Review the hypothesis, audience, constraints and interview guide before recruitment.",
            "Approve or revise the proposed sample size and success threshold before collecting results; freeze the approved version.",
            "Recruit voluntarily through channels you are permitted to use; do not send messages from this tool.",
            "Ask about past behavior before showing any concept. Record anonymous observations, including contradictory observations.",
            "Compare collected observations to the approved criteria and return real evidence to the research workflow.",
        ),
        constraints=brief.founder_constraints, evidence=brief.supporting_evidence,
    )


def _md(value: str) -> str:
    """Render untrusted text as inert, readable Markdown on a single line.

    HTML is escaped; link/image/emphasis/code syntax and leading block markers are
    neutralized. Ordinary punctuation is left alone so the raw file stays readable.
    """
    value = html.escape(value, quote=False).replace("\r", " ").replace("\n", " ")
    value = re.sub(r"([\\`*_\[\]|~])", lambda m: "\\" + m.group(1), value).replace("!", "&#33;")
    value = re.sub(r"^(\s*\d+)([.)])", lambda m: m.group(1) + "\\" + m.group(2), value)
    return re.sub(r"^(\s*)([#>+=-])", lambda m: m.group(1) + "\\" + m.group(2), value)


def kit_markdown(kit: ExperimentKit) -> str:
    """Readable Markdown report. URL references are supplied context, not verification."""
    def bullets(values, empty="None supplied."):
        return "\n".join(f"- {_md(v)}" for v in values) or empty

    def numbered(values):
        return "\n".join(f"{i}. {_md(v)}" for i, v in enumerate(values, 1))

    criterion = kit.success_criteria
    sections = [
        "# Validation Experiment Kit",
        "ASSUMPTION: this is a proposed experiment, not market validation.",
        f"**Results status:** {kit.results_status}",
        "## Hypothesis", _md(kit.hypothesis),
        "## Target Audience", _md(kit.target_audience),
        "## Founder assumption under investigation", _md(kit.assumption_under_test),
        "## Assumptions not tested by this experiment", bullets(kit.untested_assumptions),
        "## Customer Interview Guide", _md(kit.interviewer_brief), numbered(kit.interview_questions),
        "## Validation Experiment", _md(kit.validation_experiment),
        "## Success Criteria",
        f"{criterion.label}: at least {criterion.threshold} of {criterion.sample_size} participants. "
        f"{_md(criterion.metric)}.",
        "## Failure Criteria", _md(kit.failure_criteria),
        "## Recommended Next Steps", numbered(kit.recommended_next_steps),
        "## Founder Constraints", bullets(kit.constraints),
        "## Supplied Context (not independently verified)",
        "\n".join(f"- UNVERIFIED_CONTEXT: {_md(e.statement)} ({_md(str(e.source_url))})" for e in kit.evidence)
        or "No supporting evidence supplied.",
    ]
    return "\n\n".join(sections) + "\n"
