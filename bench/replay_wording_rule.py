"""Apply the wording and attribution rules to a recorded run, without calling a model.

Usage: python -m bench.replay_wording_rule docs/benchmark_runs/<run>.json

Both rules are deterministic, so their effect on recorded model outputs can be
computed exactly. Prints, for every pipeline claim the run recorded as
established, whether it stays established or moves to needs_review, and for the
labelled `supports` cases, which ones the wording rule holds for review. (The
labelled cases carry no claim type, so the attribution rule is not applied to them.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import evidence as ev
from bench.ollama_bench import CASES_FILE, HELDOUT_FILE

SOURCES = {
    "short_thread": Path("bench/fixtures/synthetic_source.txt"),
    "forum_page": Path("bench/fixtures/synthetic_forum_page.txt"),
}


def main(run_file: str) -> None:
    run = json.loads(Path(run_file).read_text(encoding="utf-8"))
    print(f"Run {run['environment']['timestamp_utc']}: pipeline claims recorded as established")
    for result in run["results"]:
        for p in result["pipeline"]:
            source = SOURCES[p["source"]].read_text(encoding="utf-8")
            for item in p.get("items") or []:
                if item["standing"] != "established":
                    continue
                quotes = []
                for q in item["quotes"]:
                    start = source.find(q["text"])
                    quotes.append(ev.verify_span(source, start, start + len(q["text"])))
                missing = ev.unsourced_words(item["claim"], ev.context_for(source, quotes))
                one_person = ev.attributed_to_one_person(item["claim"], item["type"])
                why = ([f"words not in text {missing}"] if missing else []) +                     ([] if one_person else ["not attributed to one person"])
                verdict = "NEEDS_REVIEW: " + "; ".join(why) if why else "STAYS ESTABLISHED"
                print(f"  {result['model']} {p['design']} {p['source']} rep {p['rep']}: {verdict} | {item['claim']}")
    for path in (CASES_FILE, HELDOUT_FILE):
        cases = json.loads(Path(path).read_text(encoding="utf-8"))["cases"]
        held = [c for c in cases if c["expected"] == "supports"]
        kept = [c["id"] for c in held if not ev.unsourced_words(c["claim"], c["context"])]
        print(f"{Path(path).name}: labelled `supports` cases that can still be established: "
              f"{len(kept)}/{len(held)} {kept}")
        for c in held:
            missing = ev.unsourced_words(c["claim"], c["context"])
            if missing:
                print(f"  {c['id']} held for review, words not in the text: {missing}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "docs/benchmarks.json")
