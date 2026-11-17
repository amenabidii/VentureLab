"""Founder-operated local CLI. Never give an autonomous model the decide command."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import sqlite3

from approval import ApprovalError, ApprovalStore
from builder_models import ApprovalDecision, BuilderInput, LandingPageSpec
from builder_service import prepare
from llm import OllamaClient


def _portable(value, base: Path):
    """Show paths under the working directory relative to it, so exported receipts and
    decision logs do not embed the local account's absolute path. Display only: the
    approval store keeps and verifies the absolute destination."""
    if isinstance(value, dict):
        return {key: _portable(item, base) for key, item in value.items()}
    if isinstance(value, list):
        return [_portable(item, base) for item in value]
    if isinstance(value, str) and value.startswith(str(base)):
        try:
            return Path(value).relative_to(base).as_posix()
        except ValueError:
            return value
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, default=Path(".venturelab/builder-v2.sqlite3"))
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
    store = None
    try:
        store = ApprovalStore(args.state, args.outputs)
        if args.command == "prepare":
            with args.input.open("rb") as source:
                raw = source.read(262145)
            if len(raw) > 262144:
                raise ValueError("Input exceeds 256 KiB")
            def unique_keys(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("Duplicate JSON object key")
                    result[key] = value
                return result
            payload = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_keys)
            if not isinstance(payload, dict) or set(payload) != {"brief", "landing_page"}:
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
                                  decision=args.decision, actor="founder", reason=args.reason),
                                  founder_token=store.founder_path.read_bytes()).model_dump(mode="json")
        elif args.command == "execute":
            result = store.execute(args.action_id).model_dump(mode="json")
        else:
            result = store.audit_events()
        print(json.dumps(_portable(result, Path.cwd().absolute()), indent=2, ensure_ascii=True))
        return 0
    except (ValueError, OSError, RuntimeError, TypeError, sqlite3.Error, RecursionError) as exc:
        if store is not None and not isinstance(exc, ApprovalError):
            try:
                store.record_failure("prepare_artifacts" if args.command == "prepare" else args.command,
                                     exc, getattr(args, "action_id", None))
            except (ApprovalError, OSError, sqlite3.Error):
                pass  # Corrupt/unavailable audit storage must fail closed, never fabricate a log.
        print(f"Builder failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
