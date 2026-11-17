"""Local validation design. Template mode is deterministic, not a model stub."""
from __future__ import annotations

from pathlib import Path

from builder_models import BuilderInput, Criterion, ExperimentKit, Text, Contract, check_content
from pydantic import field_validator
from llm import OllamaClient


class HypothesisDraft(Contract):
    hypothesis: Text
    _safe = field_validator("hypothesis")(check_content)


def generate_kit(brief: BuilderInput, client: OllamaClient | None = None) -> ExperimentKit:
    hypothesis = f"ASSUMPTION: {brief.main_assumptions[0]}"
    if client is not None:
        result = client.chat_json(client.settings.model, [
            {"role": "system", "content": (Path(__file__).resolve().parent.parent / "prompts/builder.md").read_text(encoding="utf-8")},
            {"role": "user", "content": brief.model_dump_json()},
        ], HypothesisDraft, num_predict=180)
        hypothesis = f"ASSUMPTION: {result.parsed.hypothesis}"
    return ExperimentKit(
        hypothesis=hypothesis,
        target_audience=brief.target_customer,
        interview_questions=(
            "Tell me about the last time you encountered this problem. What happened?",
            "What steps did you take to address it that time?",
            "Which tools or alternatives did you use, and how did they fit your process?",
            "What time or effort did that experience require?",
            "What was difficult about your existing approach?",
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
            metric="Participants describing a recent concrete instance and an existing workaround",
            threshold=3, sample_size=5,
        ),
        failure_criteria=(
            "If fewer participants meet the approved criterion, the hypothesis is weakened. "
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


def kit_markdown(kit: ExperimentKit) -> str:
    # Plain Markdown, with raw HTML neutralized. URL references are supplied context, not verification.
    import html
    def safe(value: str) -> str:
        return html.escape(value)
    sections = ["# Validation Experiment Kit", "ASSUMPTION: this is a proposed experiment, not market validation.",
                kit.results_status, "## Hypothesis", safe(kit.hypothesis), "## Target Audience", safe(kit.target_audience),
                "## Customer Interview Guide", "\n".join(f"- {safe(q)}" for q in kit.interview_questions),
                "## Validation Experiment", safe(kit.validation_experiment), "## Success Criteria",
                f"{kit.success_criteria.label}: {kit.success_criteria.threshold} of {kit.success_criteria.sample_size} participants. "
                + safe(kit.success_criteria.metric), "## Failure Criteria", safe(kit.failure_criteria),
                "## Recommended Next Steps", "\n".join(f"- {safe(s)}" for s in kit.recommended_next_steps),
                "## Founder Constraints", "\n".join(f"- {safe(s)}" for s in kit.constraints),
                "## Supplied Context (not independently verified)",
                "\n".join(f"- UNVERIFIED_CONTEXT: {safe(e.statement)} — {safe(str(e.source_url))}" for e in kit.evidence)
                or "No supporting evidence supplied."]
    return "\n\n".join(sections) + "\n"
