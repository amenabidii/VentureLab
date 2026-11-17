"""Founder-operated local CLI. Never give an autonomous model the decide command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from approval import ApprovalError, ApprovalStore
from builder_models import ApprovalDecision, BuilderInput, LandingPageSpec
from builder_service import prepare
from llm import OllamaClient


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path(".venturelab/builder.sqlite3"))
    parser.add_argument("--outputs", type=Path, default=Path("outputs"))
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("prepare", help="Prepare a reviewable request; no output files are written")
    make.add_argument("input", type=Path, help="JSON containing brief and landing_page")
    make.add_argument("--model", action="store_true", help="Use the existing Ollama client for hypothesis drafting")
    show = commands.add_parser("inspect", help="Show the exact bundle and required SHA-256")
    show.add_argument("action_id")
    receipt = commands.add_parser("receipt", help="Print the recorded founder gate and its audit events")
    receipt.add_argument("action_id")
    decide = commands.add_parser("decide", help="Founder decision for the inspected fingerprint")
    decide.add_argument("action_id")
    decide.add_argument("decision", choices=["approve", "reject"])
    decide.add_argument("--sha256", required=True)
    decide.add_argument("--reason", required=True)
    run = commands.add_parser("execute", help="Write the approved artifacts locally, once")
    run.add_argument("action_id")
    commands.add_parser("audit", help="Print recorded events as compatible decision-log JSON")
    args = parser.parse_args(argv)
    store = ApprovalStore(args.state, args.outputs)
    try:
        if args.command == "prepare":
            payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
            if set(payload) != {"brief", "landing_page"}:
                raise ValueError("Input requires exactly brief and landing_page")
            brief = BuilderInput.model_validate(payload["brief"])
            spec = LandingPageSpec.model_validate(payload["landing_page"])
            client = OllamaClient() if args.model else None
            try:
                bundle = prepare(brief, spec, client)
            finally:
                if client:
                    client.close()
            result = store.create(bundle).model_dump(mode="json")
        elif args.command == "inspect":
            request, bundle = store.inspect(args.action_id)
            result = {"request": request.model_dump(mode="json"), "bundle": bundle.model_dump(mode="json"),
                      "files": {name: data.decode() for name, data in bundle.files().items()}}
        elif args.command == "receipt":
            request, bundle = store.inspect(args.action_id)
            result = {"request": request.model_dump(mode="json"),
                      "events": [event for event in store.audit_events() if event["action_id"] == args.action_id],
                      "artifact_sha256_matches_current_renderer": bundle.fingerprint() == request.artifact_sha256,
                      "note": "Founder approval gate only; no business GO/REPEAT/PIVOT/STOP decision."}
        elif args.command == "decide":
            result = store.decide(ApprovalDecision(action_id=args.action_id, artifact_sha256=args.sha256,
                                  decision=args.decision, actor="founder", reason=args.reason)).model_dump(mode="json")
        elif args.command == "execute":
            result = store.execute(args.action_id).model_dump(mode="json")
        else:
            result = store.audit_events()
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 0
    except (ValueError, OSError, ApprovalError, RuntimeError) as exc:
        print(f"Builder failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
