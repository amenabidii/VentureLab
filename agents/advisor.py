"""Advisor: idea-specific proposals for phases 2–6, from the local open-weight model.

The model (Qwen3 via Ollama) proposes; code decides what may be used:
- every text item must pass the content rules (`builder_models.check_content`); items that
  fail are dropped and listed under `dropped`, never rewritten;
- interview questions must be past-behaviour questions (no "would", no pitch) and end in "?";
- price points are integers between 1 and 300 EUR/month; at most three, sorted;
- finding IDs it cites must exist in the run; others are removed;
- every surviving item is labelled ASSUMPTION with the model's name: proposals, not evidence.
If the model is unavailable or returns nothing usable, a deterministic fallback is used and
labelled as such, so the pipeline never stalls and never pretends the model ran.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from builder_models import check_content

LEADING = re.compile(r"\b(would|wouldn't|will you|do you agree|love|amazing|our (app|product|tool))\b", re.I)
PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "advisor.md"


class Channel(BaseModel):
    name: str = Field(max_length=120)
    why: str = Field(max_length=300)


class Advice(BaseModel):
    value_proposition: str = Field(max_length=300)
    current_alternatives: list[str] = Field(max_length=5)
    channels: list[Channel] = Field(max_length=5)
    key_metric: str = Field(max_length=300)
    price_anchor: str = Field(max_length=300)
    price_points_eur_per_month: list[int] = Field(max_length=4)
    pricing_rationale: str = Field(max_length=400)
    interview_questions: list[str] = Field(max_length=8)
    launch_angle: str = Field(max_length=300)
    riskiest_assumption: str = Field(max_length=300)
    kill_criterion: str = Field(max_length=300)
    evidence_ids: list[str] = Field(default_factory=list, max_length=10)


def _ok(text: str) -> bool:
    try:
        check_content(text)
        return bool(text.strip())
    except ValueError:
        return False


def context_message(brief: dict, gate: dict, investigation: dict | None, challenge: dict | None) -> str:
    findings = [f"{f['id']} | {f.get('type')} | {f.get('standing')} | {f['claim']}"
                for f in (investigation or {}).get("findings", [])]
    risks = [r.get("text", "") for r in (challenge or {}).get("risks", [])]
    hyps = [h.get("text", "") for h in (challenge or {}).get("new_hypotheses", [])]
    missing = (gate.get("counterfactual") or {}).get("missing_evidence", [])
    return json.dumps({
        "idea": brief["idea"], "problem": brief["problem_statement"], "customer": brief["target_customer"],
        "market": brief["market"], "skills": brief.get("founder_skills", []),
        "hours_per_week": brief.get("hours_per_week"), "budget_eur": brief.get("budget_eur"),
        "values_and_constraints": brief.get("values_and_constraints", []),
        "discover_gate": {"decision": gate.get("decision"), "rule": gate.get("rule"), "missing": missing},
        "findings (id | type | standing | claim)": findings, "challenger_risks": risks,
        "challenger_alternative_hypotheses": hyps}, ensure_ascii=False)


def sanitize(raw: Advice, known_ids: set[str], model: str) -> dict[str, Any]:
    label = f"ASSUMPTION (proposed by {model}; not evidence)"
    dropped: list[str] = []

    def keep(field: str, text: str) -> str | None:
        if _ok(text):
            return text.strip()
        dropped.append(field)
        return None

    questions = []
    for q in raw.interview_questions:
        q = q.strip()
        asks = q.endswith("?") or re.match(r"(tell me about|walk me through|describe)\b", q, re.I)
        if asks and not LEADING.search(q) and _ok(q):
            questions.append(q)
        else:
            dropped.append(f"interview question: {q[:80]}")
    channels = [{"name": c.name.strip(), "why": c.why.strip()} for c in raw.channels
                if keep("channel", f"{c.name} {c.why}")]
    prices = sorted({p for p in raw.price_points_eur_per_month if 1 <= p <= 300})[:3]
    kill = raw.kill_criterion.strip()
    if not re.match(r"stop if\b", kill, re.I) or not re.search(r"\d", kill):
        dropped.append("kill_criterion (not phrased as a measurable stop rule)")
        kill = ""
    dropped += [f"price {p}" for p in raw.price_points_eur_per_month if not 1 <= p <= 300]
    return {
        "source": "model", "model": model, "label": label,
        "value_proposition": keep("value_proposition", raw.value_proposition),
        "current_alternatives": [a.strip() for a in raw.current_alternatives if keep("alternative", a)],
        "channels": channels, "key_metric": keep("key_metric", raw.key_metric),
        "price_anchor": keep("price_anchor", raw.price_anchor), "price_points_eur_per_month": prices,
        "pricing_rationale": keep("pricing_rationale", raw.pricing_rationale),
        "interview_questions": questions[:7], "launch_angle": keep("launch_angle", raw.launch_angle),
        "riskiest_assumption": keep("riskiest_assumption", raw.riskiest_assumption),
        "kill_criterion": keep("kill_criterion", kill) if kill else None,
        "evidence_ids": [i for i in raw.evidence_ids if i in known_ids], "dropped": dropped,
    }


def PAST_BEHAVIOUR(brief: dict) -> list[str]:
    problem = brief["problem_statement"].rstrip(".")
    return [f"Tell me about the last time this happened to you: {problem}.",
            "What did you do about it that time?",
            "What do you use today to deal with it, and what does that cost you in time or money?",
            "When did it last happen before that?",
            "What have you already tried to change, and why did you stop?"]


def fallback(brief: dict, reason: str) -> dict[str, Any]:
    return {
        "source": "deterministic-fallback", "model": None, "reason": reason,
        "label": "ASSUMPTION (deterministic fallback; the model was not used)",
        "value_proposition": f"For {brief['target_customer']}: {brief['idea']}",
        "current_alternatives": ["Their current manual workaround (to be named in interviews)"],
        "channels": [{"name": brief["market"], "why": "The market the founder named in the brief"}],
        "key_metric": "Share of interviewees describing a recent, specific occurrence of the problem",
        "price_anchor": "Unknown: ask what they spend today on the problem",
        "price_points_eur_per_month": [4, 8, 15], "pricing_rationale": "Generic test grid; no anchor available",
        "interview_questions": PAST_BEHAVIOUR(brief), "launch_angle": brief["problem_statement"],
        "riskiest_assumption": "Enough of these customers would pay for it",
        "kill_criterion": "Stop if fewer than 3 of 10 qualified interviewees describe a recent, specific occurrence",
        "evidence_ids": [], "dropped": [],
    }


def advise(brief: dict, gate: dict, investigation: dict | None, challenge: dict | None,
           client: Any | None, model: str | None) -> tuple[dict[str, Any], dict | None]:
    """Returns (advice, call metadata). Never raises for model problems: falls back instead."""
    if client is None or not model:
        return fallback(brief, "model disabled"), None
    known = {f["id"] for f in (investigation or {}).get("findings", [])}
    messages = [{"role": "system", "content": PROMPT.read_text(encoding="utf-8")},
                {"role": "user", "content": context_message(brief, gate, investigation, challenge)}]
    try:
        result = client.chat_json(model, messages, Advice, num_predict=900)
    except Exception as exc:  # unreachable model, invalid JSON twice: honest fallback, recorded
        return fallback(brief, f"model call failed: {type(exc).__name__}"), None
    advice = sanitize(result.parsed, known, model)
    if len(advice["interview_questions"]) < 3:  # top up with checked past-behaviour questions
        advice["interview_questions"] += [q for q in PAST_BEHAVIOUR(brief) if q not in advice["interview_questions"]][
            : 5 - len(advice["interview_questions"])]
        advice["topped_up_questions"] = True
    if not advice["kill_criterion"]:
        advice["kill_criterion"] = ("Stop if fewer than 3 of 10 qualified interviewees describe "
                                    f"'{brief['problem_statement'].rstrip('.')}' as a recent, specific problem "
                                    "(VentureLab default stop rule)")
    usable = advice["value_proposition"] and advice["interview_questions"] and advice["price_points_eur_per_month"]
    if not usable:
        return fallback(brief, "model reply had no usable proposals after the content rules"), None
    meta = {"model": model, "attempts": getattr(result, "attempts", 1),
            "wall_s": round(getattr(getattr(result, "metrics", None), "wall_ms", 0) / 1000, 1)}
    return advice, meta
