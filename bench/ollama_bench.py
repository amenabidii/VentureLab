"""VentureLab model benchmark: quotation reliability, evidence assessment, latency.

Everything is measured on this machine and written to docs/benchmarks.md and
docs/benchmarks.json. Inputs are SYNTHETIC fixtures in bench/fixtures/.

Sections:
1. End-to-end evidence pipeline on two sources, comparing three designs:
   A  Milestone 1 extraction: the model writes "verbatim" excerpts from the full source.
   B  Passage IDs: the model points at numbered passages over the full source, and
      Python copies the quotes.
   C  Passage IDs over a keyword-prefiltered subset of passages, at most 3 claims.
   All three use the current assessment (reason before verdict, plus a second
   check before anything is established).
2. Evidence-assessment accuracy on labelled cases:
   - dev set (bench/fixtures/evidence_cases.json, 40 cases), current assessment;
   - held-out set (bench/fixtures/evidence_cases_heldout.json, 16 cases), with both the
     archived Milestone 1 prompt (bench/fixtures/assess_prompt_v1.md) and the current one.

The model stays loaded between requests, as in the application. Requests are
interleaved so the same prompt is never sent twice in a row; Ollama can then
only reuse the shared system-prompt prefix, as it would in normal use.

Run inside the compose stack:
    docker compose run --rm -v ./docs:/srv/docs app python -m bench.ollama_bench
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

import evidence as ev
from llm import LLMError, LLMResult, OllamaClient

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "bench" / "fixtures"
CASES_FILE = FIXTURES / "evidence_cases.json"
HELDOUT_FILE = FIXTURES / "evidence_cases_heldout.json"
V1_PROMPT_FILE = FIXTURES / "assess_prompt_v1.md"

SOURCES = {
    "short_thread": (
        (FIXTURES / "synthetic_source.txt").read_text(encoding="utf-8"),
        "freelancers tracking unpaid invoices and matching payments",
    ),
    "forum_page": (
        (FIXTURES / "synthetic_forum_page.txt").read_text(encoding="utf-8"),
        "AI-assisted podcast editing for solo podcast hosts: editing time, tools, prices, willingness to pay",
    ),
}
PREFILTER_PASSAGES = 16
FAST_MAX_CLAIMS = 3
LABELS = ["supports", "partially_supports", "does_not_support", "contradicts"]


# --- design A: the Milestone 1 extraction (model writes the quotes) -----------


class LegacyClaim(BaseModel):
    type: ev.ClaimType
    claim: str
    verbatim_excerpt: str


class LegacyClaimList(BaseModel):
    claims: list[LegacyClaim] = Field(max_length=5)


LEGACY_EXTRACT_PROMPT = (
    "You extract evidence claims from a source text. Return at most 5 claims. "
    "Each claim has a type (customer_problem, competitor, demand or segment), a one-sentence "
    "claim, and verbatim_excerpt: a short passage copied exactly, character for character, "
    "from the source that the claim is based on. Do not invent anything not in the source."
)


def extract_legacy(client: OllamaClient, model: str, source: str) -> tuple[list[ev.EvidenceItem], LLMResult]:
    messages = [
        {"role": "system", "content": LEGACY_EXTRACT_PROMPT},
        {"role": "user", "content": f"SOURCE TEXT:\n{source}"},
    ]
    result = client.chat_json(model, messages, LegacyClaimList, num_predict=700)
    items = [
        ev.EvidenceItem(claim=c.claim, claim_type=c.type, quotes=[ev.verify_excerpt(source, c.verbatim_excerpt)])
        for c in result.parsed.claims
    ]
    return items, result


# --- Milestone 1 assessment (verdict before reason), for the held-out comparison --


class V1Assessment(BaseModel):
    verdict: ev.Verdict
    reason: str
    limitations: str


def assess_v1(client: OllamaClient, model: str, case: dict) -> V1Assessment:
    messages = [
        {"role": "system", "content": V1_PROMPT_FILE.read_text(encoding="utf-8").strip()},
        {"role": "user", "content": f"CLAIM: {case['claim']}\nQUOTE: {case['quote']}\nCONTEXT: {case['context']}"},
    ]
    return client.chat_json(model, messages, V1Assessment, num_predict=160).parsed


# --- pipeline -------------------------------------------------------------------


def _item_record(item: ev.EvidenceItem) -> dict:
    return {
        "type": item.claim_type,
        "claim": item.claim,
        "quotes": [{"status": q.status.value, "text": q.text, "note": q.note} for q in item.quotes],
        "verdict": item.verdict,
        "confirmed": item.confirmed,
        "confirm_note": item.confirm_note,
        "unsourced_words": item.unsourced,
        "attributed": item.attributed,
        "review": item.review,
        "standing": item.standing.value,
    }


def run_pipeline(client: OllamaClient, model: str, design: str, source_name: str) -> dict:
    source, topic = SOURCES[source_name]
    started = time.perf_counter()
    if design == "A":
        items, res = extract_legacy(client, model, source)
    elif design == "B":
        items, res = ev.extract_claims(client, model, source, topic=topic)
    else:
        items, res = ev.extract_claims(
            client, model, source, topic=topic, max_passages=PREFILTER_PASSAGES, max_claims=FAST_MAX_CLAIMS,
            num_predict=250,
        )
    results = [res]
    extract_ms = (time.perf_counter() - started) * 1000
    assess_started = time.perf_counter()
    for item in items:
        results += ev.assess_item(client, model, item, source)
    assess_ms = (time.perf_counter() - assess_started) * 1000
    return {
        "design": design,
        "source": source_name,
        "extract_ms": round(extract_ms),
        "assess_ms": round(assess_ms),
        "total_ms": round(extract_ms + assess_ms),
        "claims": len(items),
        "claims_verified": sum(1 for i in items if i.verified),
        "standings": dict(Counter(i.standing.value for i in items)),
        "model_calls": len(results),
        "prompt_tokens": sum(r.metrics.prompt_tokens for r in results),
        "output_tokens": sum(r.metrics.output_tokens for r in results),
        "retries": sum(r.attempts - 1 for r in results),
        "items": [_item_record(i) for i in items],
    }


# --- labelled evaluation -----------------------------------------------------------


def load_cases(path: Path) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    return json.loads(raw)["cases"], hashlib.sha256(raw).hexdigest()


def run_eval(client: OllamaClient, model: str, cases: list[dict], version: str) -> tuple[list[dict], float]:
    out = []
    started = time.perf_counter()
    for case in cases:
        try:
            if version == "v1":
                a = assess_v1(client, model, case)
                out.append({"id": case["id"], "predicted": a.verdict, "reason": a.reason, "confirmed": None})
            else:
                a, check, _ = ev.evaluate(client, model, case["claim"], [case["quote"]], case["context"])
                out.append({"id": case["id"], "predicted": a.verdict, "reason": a.reason,
                            "confirmed": check.fully_supported if check else None,
                            "confirm_note": check.problems if check else ""})
        except LLMError as exc:
            out.append({"id": case["id"], "predicted": None, "reason": f"error: {exc}", "confirmed": None})
    return out, (time.perf_counter() - started) * 1000


def score(cases: list[dict], predictions: list[dict], version: str) -> dict:
    """Verdict accuracy, plus what would actually be promoted to an established finding.

    v1 had no second check, so a `supports` verdict alone would have promoted the claim.
    """
    by_id = {c["id"]: c for c in cases}
    per_category: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    confusion: dict[str, Counter] = defaultdict(Counter)
    errors, verdict_critical, false_established, missed_established = [], [], [], []
    false_before_demand_rule = []
    for p in predictions:
        case = by_id[p["id"]]
        exp, got = case["expected"], p["predicted"]
        per_category[case["category"]][1] += 1
        confusion[exp][got or "no_answer"] += 1
        # The cases carry no claim type, so the demand cap applies only through the
        # payment-language rule, exactly as it does for any claim in the application.
        passed_model = got == "supports" and (version == "v1" or p.get("confirmed") is True)
        is_demand = version == "v2" and ev.effective_claim_type(case["claim"], None) == "demand"
        # The wording guard, as in the application: claim words must be in the quote or context.
        unsourced = ev.unsourced_words(case["claim"], case.get("context", "")) if version == "v2" else []
        promoted = passed_model and not is_demand and not unsourced
        row = {"id": p["id"], "category": case["category"], "expected": exp, "predicted": got,
               "confirmed": p.get("confirmed"), "demand_rule": is_demand,
               "unsourced_words": unsourced, "reason": p["reason"]}
        if passed_model and exp != "supports":
            false_before_demand_rule.append(row)
        if promoted and exp != "supports":
            false_established.append(row)
        if exp == "supports" and not promoted:
            missed_established.append(row)
        if got == exp:
            per_category[case["category"]][0] += 1
            continue
        errors.append(row)
        if got == "supports":
            verdict_critical.append(row)
    return {
        "correct": sum(v[0] for v in per_category.values()),
        "total": len(predictions),
        "per_category": {k: f"{v[0]}/{v[1]}" for k, v in per_category.items()},
        "confusion": {k: dict(v) for k, v in confusion.items()},
        "errors": errors,
        "verdict_critical": verdict_critical,
        "false_before_demand_rule": false_before_demand_rule,
        "false_established": false_established,
        "missed_established": missed_established,
    }


def environment(client: OllamaClient, hashes: dict) -> dict:
    cpu, mem_gb = "unknown", None
    try:
        cpu = next(l.split(":", 1)[1].strip() for l in Path("/proc/cpuinfo").read_text().splitlines()
                   if l.startswith("model name"))
        kb = next(int(l.split()[1]) for l in Path("/proc/meminfo").read_text().splitlines() if l.startswith("MemTotal"))
        mem_gb = round(kb / 1024 / 1024, 1)
    except (OSError, StopIteration):
        pass
    return {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cpu": cpu,
        "logical_cpus_visible": os.cpu_count(),
        "memory_visible_gb": mem_gb,
        "gpu": "none (CPU inference)",
        "ollama_version": client.version(),
        "num_ctx": client.settings.num_ctx,
        **hashes,
    }


# --- per model ------------------------------------------------------------------


def bench_model(client: OllamaClient, model: str, reps: int, dev: list[dict], heldout: list[dict]) -> dict:
    print(f"\n== {model}", flush=True)
    if not client.has_model(model):
        print(f"   pulling {model} ...", flush=True)
        client.pull(model)

    out: dict = {"model": model}
    client.unload(model)  # only here: measure one cold start
    res = client.chat(model, [{"role": "user", "content": "Reply with the word ok."}], num_predict=8)
    out["cold_load_ms"] = round(res.metrics.load_ms)
    out["cold_first_request_ms"] = round(res.metrics.wall_ms)
    print(f"   cold start {out['cold_first_request_ms']} ms (load {out['cold_load_ms']} ms)", flush=True)

    out["pipeline"] = []
    for rep in range(reps):
        for source_name in SOURCES:
            for design in ("A", "B", "C"):
                try:
                    run = run_pipeline(client, model, design, source_name) | {"rep": rep + 1}
                except LLMError as exc:
                    run = {"design": design, "source": source_name, "rep": rep + 1, "error": str(exc)[:300]}
                out["pipeline"].append(run)
                print(f"   rep {rep + 1} {source_name} {design}: "
                      f"{ {k: run.get(k) for k in ('total_ms', 'claims', 'claims_verified', 'standings', 'error')} }",
                      flush=True)

    for name, cases, version in (("dev_v2", dev, "v2"), ("heldout_v2", heldout, "v2"), ("heldout_v1", heldout, "v1")):
        preds, ms = run_eval(client, model, cases, version)
        out[name] = score(cases, preds, version) | {"elapsed_ms": round(ms), "predictions": preds}
        s = out[name]
        print(f"   {name}: {s['correct']}/{s['total']} correct, false established {len(s['false_established'])}, "
              f"{round(ms / 1000)} s", flush=True)
    return out


# --- report -----------------------------------------------------------------------


def _median(values: list[float]) -> float | None:
    return round(statistics.median(values)) if values else None


def pipeline_summary(result: dict) -> dict:
    table: dict = {}
    for design in ("A", "B", "C"):
        for source_name in SOURCES:
            all_runs = [r for r in result["pipeline"] if r["design"] == design and r["source"] == source_name]
            runs = [r for r in all_runs if "error" not in r]
            table[(design, source_name)] = {
                "errors": len(all_runs) - len(runs),
                "extract_ms": _median([r["extract_ms"] for r in runs]),
                "assess_ms": _median([r["assess_ms"] for r in runs]),
                "total_ms": _median([r["total_ms"] for r in runs]),
                "claims": sum(r["claims"] for r in runs),
                "verified": sum(r["claims_verified"] for r in runs),
                "calls": _median([r["model_calls"] for r in runs]),
                "prompt_tokens": _median([r["prompt_tokens"] for r in runs]),
                "output_tokens": _median([r["output_tokens"] for r in runs]),
                "standings": dict(sum((Counter(r["standings"]) for r in runs), Counter())),
            }
    return table


def _eval_section(title: str, s: dict) -> list[str]:
    L = [f"#### {title}", "",
         f"Verdicts correct: **{s['correct']}/{s['total']}**. Wrong `supports` verdicts: {len(s['verdict_critical'])}. "
         f"Wrong `supports` that also passed the second check: {len(s['false_before_demand_rule'])}. "
         f"**Would be wrongly established after all safeguards (second check, demand rule, wording rule): "
         f"{len(s['false_established'])}.** "
         f"Correct `supports` cases not established (cost of caution): {len(s['missed_established'])}. "
         f"Time: {s['elapsed_ms'] / 1000:.0f} s.", "",
         "| Category | Correct |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in s["per_category"].items()]
    cols = LABELS + ["no_answer"]
    L += ["", "| label \\ model | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
    for exp in LABELS:
        row = s["confusion"].get(exp, {})
        L.append(f"| {exp} | " + " | ".join(str(row.get(c, 0)) for c in cols) + " |")
    if s["errors"]:
        L += ["", "| Case | Category | Label | Model | Second check | Model's reason |", "|---|---|---|---|---|---|"]
        for e in s["errors"]:
            flag = " **wrongly established**" if e in s["false_established"] else ""
            check = {True: "agreed", False: "rejected", None: "-"}[e["confirmed"]]
            if e.get("demand_rule") and e["predicted"] == "supports":
                check += "; capped by demand rule"
            if e.get("unsourced_words") and e["predicted"] == "supports":
                check += "; capped by wording rule (" + ", ".join(e["unsourced_words"]) + ")"
            L.append(f"| {e['id']} | {e['category']} | {e['expected']} | {e['predicted']}{flag} | {check} | "
                     f"{(e['reason'] or '').replace('|', '/')} |")
    return L + [""]


def render(env: dict, results: list[dict], reps: int) -> str:
    sec = lambda v: f"{v / 1000:.1f}" if v is not None else "n/a"  # noqa: E731
    L = [
        "# Model benchmark",
        "",
        f"Generated by `bench/ollama_bench.py` at {env['timestamp_utc']}. Every number below was measured in this run.",
        "All inputs are SYNTHETIC fixtures, not market evidence.",
        "",
        "## End-to-end evidence pipeline",
        "",
        f"Medians over {reps} repetitions with the model kept loaded; claim counts are totals over all repetitions. "
        "A: model writes quotes (Milestone 1 extraction). B: passage IDs, Python copies the quotes. "
        f"C: passage IDs over the {PREFILTER_PASSAGES} best keyword-matched passages, at most {FAST_MAX_CLAIMS} claims. "
        "All designs use the current assessment with the second check.",
        "",
    ]
    for r in results:
        L += [f"### `{r['model']}`", "",
              f"Cold start (load from disk + first reply): {r['cold_first_request_ms']} ms, "
              f"of which loading {r['cold_load_ms']} ms.", "",
              "| Design | Source | Total (s) | Extract (s) | Assess (s) | Calls | Prompt tok | Output tok "
              "| Claims with verified quotes | Standings |",
              "|---|---|---|---|---|---|---|---|---|---|"]
        for (design, source_name), s in pipeline_summary(r).items():
            standings = ", ".join(f"{k} {v}" for k, v in sorted(s["standings"].items()))
            L.append(f"| {design} | {source_name} | {sec(s['total_ms'])} | {sec(s['extract_ms'])} | "
                     f"{sec(s['assess_ms'])} | {s['calls']} | {s['prompt_tokens']} | {s['output_tokens']} | "
                     f"{s['verified']}/{s['claims']} | {standings} |"
                     + (f" ({s['errors']} failed runs)" if s["errors"] else ""))
        L.append("")
    L += ["## Evidence assessment", "",
          f"Dev set: `evidence_cases.json` (SHA-256 `{env['dev_cases_sha256']}`), 40 cases. "
          f"Held-out set: `evidence_cases_heldout.json` (SHA-256 `{env['heldout_cases_sha256']}`), 16 cases written "
          "after the first run and before the current prompt was evaluated. v1 = Milestone 1 prompt (verdict first, "
          "no second check; a `supports` verdict alone would establish the claim). v2 = current prompt (reason first) "
          "plus the second check.", ""]
    for r in results:
        L += [f"### `{r['model']}`", ""]
        L += _eval_section("Dev set, v2", r["dev_v2"])
        L += _eval_section("Held-out set, v1", r["heldout_v1"])
        L += _eval_section("Held-out set, v2", r["heldout_v2"])
    L += ["## Environment", ""] + [f"- {k}: {v}" for k, v in env.items()] + [""]
    return "\n".join(L)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VentureLab model benchmark")
    parser.add_argument("--models", nargs="+", default=["qwen3:4b", "qwen3:1.7b"])
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--out-dir", default=str(ROOT / "docs"))
    args = parser.parse_args(argv)

    dev, dev_sha = load_cases(CASES_FILE)
    heldout, heldout_sha = load_cases(HELDOUT_FILE)
    client = OllamaClient()
    try:
        env = environment(client, {"dev_cases_sha256": dev_sha, "heldout_cases_sha256": heldout_sha,
                                   "v1_prompt_sha256": hashlib.sha256(V1_PROMPT_FILE.read_bytes()).hexdigest()})
    except LLMError as exc:
        print(f"Ollama not reachable: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(env, indent=2), flush=True)

    results = [bench_model(client, m, args.reps, dev, heldout) for m in args.models]
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "benchmarks.json").write_text(json.dumps({"environment": env, "results": results}, indent=2),
                                             encoding="utf-8")
    (out_dir / "benchmarks.md").write_text(render(env, results, args.reps), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
