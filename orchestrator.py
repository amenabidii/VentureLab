"""Phase 1 (Discover) workflow: founder brief -> Investigator -> Challenger -> gate -> counterfactual.

Run inside the compose stack, with the repository mounted so outputs land in it:

    docker compose run --rm -v "$PWD:/srv" app python orchestrator.py --brief briefs/<file>.json [--quick]

`--quick` is a shorter demonstration run (one search, fewer comments and
claims). Every step still runs, with live retrieval and live model inference.

Writes, named by phase and step (CLAUDE.md):
    outputs/phase1_step1_founder_brief<suffix>.json
    outputs/phase1_step2_investigation<suffix>.json / .md
    outputs/phase1_step3_challenge<suffix>.json / .md
    outputs/phase1_gate_decision<suffix>.json / .md
and appends one entry per agent action to decision_log.json.

Nothing here publishes, sends, spends or signs anything, so no founder
approval step is needed in this phase.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import ValidationError

import evidence as ev
from agents.challenger import FULL_LIMITS, QUICK_LIMITS, Challenge, challenge
from agents.investigator import FULL, QUICK, Effort, Finding, Investigation, investigate
from audit import AuditLog, utc_now
from brief import FounderBrief, load_brief, screen_brief
from config import get_settings
from counterfactual import explain
from gates import GateResult, decide, pre_research_stop
from llm import LLMError, OllamaClient
from sources import SourceFetcher


@dataclass
class RunResult:
    run_id: str
    brief: FounderBrief
    investigation: Investigation | None
    challenge: Challenge | None
    gate: GateResult
    counterfactual: dict[str, Any]
    files: list[Path]
    timings_s: dict[str, float]
    model_calls: int


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _json(obj: Any) -> str:
    return json.dumps(obj, indent=1, ensure_ascii=False, default=str) + "\n"


def run_discover(
    brief: FounderBrief,
    *,
    client: OllamaClient,
    model: str,
    fetcher: SourceFetcher,
    log_path: str | Path,
    out_dir: str | Path,
    suffix: str = "",
    effort: Effort = FULL,
    warm: bool = False,
    run_id: str | None = None,
    listener=None,
) -> RunResult:
    started = time.perf_counter()
    run_id = run_id or f"run-{utc_now()}-{uuid.uuid4().hex[:6]}"
    log = AuditLog(log_path, run_id, listener=listener)
    out = Path(out_dir)
    files: list[Path] = []
    timings: dict[str, float] = {}

    screen = screen_brief(brief)
    log.record("orchestrator", "validate_brief", outcome="accepted" if screen.allowed else "prohibited_category",
               screen=screen.summary())
    files.append(_write(out / f"phase1_step1_founder_brief{suffix}.json", _json({
        "run_id": run_id, "brief": brief.model_dump(mode="json"),
        "category_screen": {"allowed": screen.allowed, "matches": screen.matches},
    })))

    inv: Investigation | None = None
    chal: Challenge | None = None
    if pre_research_stop(brief, screen):
        log.record("orchestrator", "skip_research", outcome="skipped",
                   reason="a STOP rule applies before research; no model time spent")
    else:
        if warm:  # load the model once; keep_alive keeps it loaded between requests
            t = time.perf_counter()
            try:
                client.warm(model)
                log.record("orchestrator", "load_model", model=model, outcome="ok")
            except LLMError as exc:
                log.record("orchestrator", "load_model", model=model, outcome="failed", error=str(exc)[:200])
            timings["model_load"] = time.perf_counter() - t
        t = time.perf_counter()
        inv = investigate(brief, client, model, fetcher, log, effort=effort)
        timings["investigator"] = time.perf_counter() - t
        files.append(_write(out / f"phase1_step2_investigation{suffix}.json",
                            _json({"run_id": run_id, "model": model} | inv.to_dict())))
        files.append(_write(out / f"phase1_step2_investigation{suffix}.md", render_investigation(inv, model)))
        t = time.perf_counter()
        chal = challenge(brief, inv.findings, client, model, log,
                         limits=QUICK_LIMITS if effort.name == "quick" else FULL_LIMITS)
        timings["challenger"] = time.perf_counter() - t
        files.append(_write(out / f"phase1_step3_challenge{suffix}.json",
                            _json({"run_id": run_id, "model": model} | chal.to_dict())))
        files.append(_write(out / f"phase1_step3_challenge{suffix}.md", render_challenge(chal)))

    gate = decide(brief, screen, inv)
    log.record("gate", "evidence_gate", sources=gate.evidence.supporting_sources
               + gate.evidence.contradicting_sources, outcome=gate.decision.value.lower(), rule=gate.rule.id)
    cf = explain(gate, brief, chal)
    log.record("counterfactual", "explain_decision", outcome=gate.decision.value.lower(), rule=gate.rule.id,
               missing=len(cf["missing_evidence"]), experiments=len(cf["experiments"]))
    timings["total"] = time.perf_counter() - started
    timings = {k: round(v, 1) for k, v in timings.items()}
    calls = (inv.calls if inv else []) + (chal.calls if chal else [])
    files.append(_write(out / f"phase1_gate_decision{suffix}.json", _json(
        {"run_id": run_id, "model": model if inv else None, "effort": effort.name if inv else None}
        | gate.to_dict() | {"counterfactual": cf, "timings_s": timings, "model_calls": len(calls),
                            "model_seconds": round(sum(c["wall_s"] for c in calls), 1)})))
    files.append(_write(out / f"phase1_gate_decision{suffix}.md", render_gate(gate, cf, timings, len(calls))))
    return RunResult(run_id, brief, inv, chal, gate, cf, files, timings, len(calls))


# --- Markdown renderings of the JSON outputs -------------------------------------------------

def _quote_lines(f: Finding) -> list[str]:
    lines = []
    for q in f.item.quotes:
        if q.verified:
            lines.append(f"  > {q.text.strip()[:400]}  \n  > Source: {q.source_url}")
        else:
            lines.append(f"  - {q.display()} ({q.note})")
    return lines


def _finding_block(f: Finding) -> list[str]:
    i = f.item
    lines = [f"- **{f.id}** [{f.claim_type}, {f.relevance.replace('_', '-')}] {i.claim}"]
    if i.verdict:
        lines.append(f"  - Verdict: {i.verdict}; second check: "
                     f"{ {True: 'agreed', False: 'disagreed', None: 'not run'}[i.confirmed] }. {i.reason}")
    for r in i.review:
        lines.append(f"  - Needs review: {r}")
    for n in i.notes:
        lines.append(f"  - Note: {n}")
    return lines + _quote_lines(f)


SECTIONS = [
    (ev.Standing.ESTABLISHED, "Established (verified quote, supported, confirmed, wording checked)"),
    (ev.Standing.NEEDS_REVIEW, "Needs review (kept with its quote; wording, attribution or relevance is uncertain)"),
    (ev.Standing.PARTIAL, "Partial evidence (not counted by the gate)"),
    (ev.Standing.CONTRADICTED, "Contradicted"),
    (ev.Standing.UNSUPPORTED, "Unsupported (the quote does not back the claim)"),
    (ev.Standing.ASSUMPTION, "ASSUMPTION (no verified quote, or not assessed)"),
]


def render_investigation(inv: Investigation, model: str) -> str:
    sel = inv.selection
    L = ["# Phase 1, step 2: Investigation", "",
         f"Model: `{model}` (local, via Ollama), effort `{inv.effort}`. Searches: {', '.join(inv.queries)} "
         f"({inv.query_origin}). Model calls: {inv.model_calls}. Time: {inv.elapsed_s:.0f} s.",
         "Every quotation below was copied from the retrieved source by code, not written by the model, and "
         "cites the comment or page it came from. Only established findings about the founder's problem "
         "statement count as evidence.", "",
         "## Sources", "", "| Kind | Status | Items | Source |", "|---|---|---|---|"]
    for src in inv.sources:
        detail = f" ({src.error})" if src.error else ""
        L.append(f"| {src.kind} | {src.status}{detail} | {len(src.segments)} | {src.url} |")
    if sel:
        L += ["", f"Relevance selection: {sel.get('comments_seen', 0)} comments retrieved, "
                  f"{sel.get('off_topic_dropped', 0)} set aside as off-topic (fewer than two key words shared "
                  f"with the brief), {sel.get('kept', 0)} analysed. Key words: "
                  f"{', '.join(sel.get('topic_terms', []))}."]
    extracted = inv.by_origin("extracted")
    groups = [
        ("Customer problem and segment findings",
         [f for f in extracted if f.claim_type in ("customer_problem", "segment")]),
        ("Competitor findings (existing products; not evidence of demand)",
         [f for f in extracted if f.claim_type == "competitor"]),
        ("Demand signals (desk research can never establish demand)",
         [f for f in extracted if f.claim_type == "demand"]),
    ]
    for title, group in groups:
        L += ["", f"## {title}", ""]
        if not group:
            L.append("None found.")
        for standing, label in SECTIONS:
            members = [f for f in group if f.standing is standing]
            if members:
                L += [f"### {label}", ""]
                for f in members:
                    L += _finding_block(f)
                L.append("")
    L += ["", "## Founder's problem statement checked against the sources", ""]
    checks = inv.by_origin("hypothesis_check")
    if not checks:
        L.append("No passage shared two key words with the problem statement.")
    for f in checks:
        L += [f"- **{f.id}** standing: {f.standing.value}"] + _finding_block(f)[1:]
    return "\n".join(L).rstrip() + "\n"


def render_challenge(chal: Challenge) -> str:
    L = ["# Phase 1, step 3: Challenge", ""]
    if chal.status != "ok":
        L += [f"The Challenger failed: {chal.error}", "Contradictions below are listed by code.", ""]
    L += ["Each founder assumption has a fixed ID. The label on each review is set by code from the findings "
          "it cites: EVIDENCE (an established, relevant finding), CONTRADICTING EVIDENCE, UNCONFIRMED (only "
          "findings that are not established) or ASSUMPTION (no valid finding). A stance the cited findings "
          f"do not back is reset to 'untested'. Grounded reviews: {chal.grounded_reviews} of "
          f"{len(chal.reviews)}.", "", "## The founder's assumptions, reviewed", ""]
    for r in chal.reviews:
        who = "stated" if r["stated"] else "implied"
        refs = f" (findings {', '.join(r['evidence'])})" if r["evidence"] else ""
        L.append(f"- **{r['assumption']}** ({who}) {r['assumption_text']}")
        L.append(f"  - **{r['basis']}**, stance: {r['stance']}{refs}. {r['reason']}")
        for u in r["sources"]:
            L.append(f"  - {u}")
    L += ["", "## New hypotheses raised by the Challenger (not the founder's claims)", ""]
    if not chal.new_hypotheses:
        L.append("None.")
    for h in chal.new_hypotheses:
        refs = f" (findings {', '.join(h['evidence'])})" if h["evidence"] else ""
        L.append(f"- **{h['basis']}**: {h['text']}{refs}")
    L += ["", "## Market and feasibility risks", ""]
    if not chal.risks:
        L.append("None.")
    for r in chal.risks:
        refs = f" (findings {', '.join(r['evidence'])})" if r["evidence"] else ""
        L.append(f"- **{r['basis']}**: {r['kind']} risk to {r['assumption']}: {r['text']}{refs}")
    L += ["", "## Contradicting evidence (listed by code)", ""]
    if not chal.contradictions:
        L.append("No finding contradicts its claim.")
    for c in chal.contradictions:
        L.append(f"- {c['finding']} ({c['status']}): {c['claim']} {', '.join(c['sources'])}")
    L += ["", "## Proposed experiments (not run)", ""]
    if not chal.experiments:
        L.append("None proposed.")
    for e in chal.experiments:
        L += [f"- **{e['name']}** (tests {e['assumption']})", f"  - Method: {e['method']}",
              f"  - Supports if: {e['support_if']}", f"  - Weakens if: {e['weaken_if']}"]
    if chal.removed:
        L += ["", "## Corrected or removed by code", ""] + [f"- {r}" for r in chal.removed]
    return "\n".join(L).rstrip() + "\n"


def render_gate(gate: GateResult, cf: dict[str, Any], timings: dict[str, float], n_calls: int = 0) -> str:
    L = ["# Phase 1 gate decision", "",
         f"**Decision: {gate.decision.value}** (rule `{gate.rule.id}`)", "",
         gate.rule.meaning, "",
         "This decision is made by fixed rules in `gates.py`, not by a model. GO means only: go on to further "
         "validation with customers. It is never proof of demand, of a market or of future sales.", "",
         "## Rules checked, in order", "", "| Rule | Applies | Inputs |", "|---|---|---|"]
    for c in gate.checks:
        mark = "**decided**" if c["decided"] else ("yes" if c["applies"] else "no")
        L.append(f"| `{c['rule']}` | {mark} | `{json.dumps(c['inputs'], ensure_ascii=False)}` |")
    e = gate.evidence
    L += ["", "## Evidence counted", "",
          f"- Sources readable: {e.sources_readable} of {e.sources_total}; analysed after relevance "
          f"selection: {e.sources_analysed}",
          f"- Established findings about the problem statement: {len(e.supporting)} "
          f"({', '.join(e.supporting) or 'none'}), from {len(e.supporting_sources)} sources",
          f"- Established findings about a different problem (possible alternatives): {len(e.alternatives)}",
          f"- Sources contradicting the problem statement: {len(e.contradicting_sources)}",
          f"- Not counted: {len(e.needs_review)} needs review, {len(e.partial)} partial, {len(e.off_topic)} "
          f"off-topic, {len(e.assumptions)} assumptions, {len(e.demand_signals)} demand signals"]
    if gate.feasibility_notes:
        L += ["", "## Feasibility notes (adjust or clarify; they do not decide)", ""]
        L += [f"- {n}" for n in gate.feasibility_notes]
    L += ["", "## Counterfactual challenge", "", "Missing evidence:", ""]
    L += [f"- {m}" for m in cf["missing_evidence"]] or ["- None identified."]
    if cf.get("alternative_hypothesis"):
        a = cf["alternative_hypothesis"]
        L += ["", f"Alternative hypothesis to test: {a['hypothesis']} (findings {', '.join(a['based_on'])}; "
                  f"{', '.join(a['sources'])})"]
    L += ["", "Experiments that could address it:", ""]
    if not cf["experiments"]:
        L.append("- None: no experiment can change this decision.")
    for x in cf["experiments"]:
        L += [f"- **{x['name']}** ({x['origin']}, tests {x.get('assumption', '-')}): {x['method']}",
              f"  - Would support the hypothesis if: {x['support_if']}",
              f"  - Would weaken it if: {x['weaken_if']}"]
    L += ["", f"Reconsidered by: {cf['reconsidered_by']}.", "", cf["no_guarantee"], "",
          f"Run time: {timings.get('total', 0):.0f} s with {n_calls} model calls (model load "
          f"{timings.get('model_load', 0):.0f} s, investigator {timings.get('investigator', 0):.0f} s, "
          f"challenger {timings.get('challenger', 0):.0f} s)."]
    return "\n".join(L).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Discover phase for a founder brief.")
    parser.add_argument("--brief", required=True, help="path to a founder brief JSON file")
    parser.add_argument("--out", default="outputs", help="output directory")
    parser.add_argument("--log", default="decision_log.json", help="audit log file")
    parser.add_argument("--suffix", default="", help="added to output file names, e.g. _prohibited_example")
    parser.add_argument("--model", default=None, help="Ollama model (default: VENTURELAB_MODEL)")
    parser.add_argument("--quick", action="store_true",
                        help="shorter demonstration run: one search, fewer comments and claims; every step "
                             "still runs with live retrieval and live inference")
    args = parser.parse_args(argv)
    try:
        brief = load_brief(args.brief)
    except (ValidationError, ValueError, OSError) as exc:
        print(f"Invalid founder brief: {exc}", file=sys.stderr)
        return 2
    settings = get_settings()
    client, fetcher = OllamaClient(settings), SourceFetcher()
    try:
        result = run_discover(brief, client=client, model=args.model or settings.model, fetcher=fetcher,
                              log_path=args.log, out_dir=args.out, suffix=args.suffix,
                              effort=QUICK if args.quick else FULL, warm=True)
    finally:
        client.close()
        fetcher.close()
    print(f"{result.gate.decision.value} by rule {result.gate.rule.id} in {result.timings_s['total']:.0f} s "
          f"with {result.model_calls} model calls")
    for f in result.files:
        print(f"  wrote {f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
