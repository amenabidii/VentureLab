"""Prepare immutable, reviewable artifact bytes; materialization requires approval."""
from __future__ import annotations

import hashlib
import json
from typing import Protocol

from pydantic import Field

from agents.builder import generate_kit, kit_markdown
from builder_models import BuilderInput, Contract, ExperimentKit, Identifier, LandingPageSpec
from landing_page import render_landing_page
from llm import OllamaClient


class Milestone2Adapter(Protocol):
    """Amen implements this boundary against his actual output types after merging."""
    def to_builder_input(self) -> BuilderInput: ...


class ArtifactBundle(Contract):
    run_id: Identifier
    artifact_identity: Identifier
    brief: BuilderInput
    kit: ExperimentKit
    landing_page: LandingPageSpec
    model: str | None = None
    generator: str = Field(pattern=r"^(deterministic-template|ollama)$")

    def files(self) -> dict[str, bytes]:
        return {
            "phase2_step1_validation-kit.json": (self.kit.model_dump_json(indent=2) + "\n").encode(),
            "phase2_step1_validation-kit.md": kit_markdown(self.kit).encode(),
            "phase3_step1_landing-spec.json": (self.landing_page.model_dump_json(indent=2) + "\n").encode(),
            "phase3_step1_landing-page.html": render_landing_page(self.landing_page).encode(),
        }

    def fingerprint(self) -> str:
        # Includes inputs, model identity, exact output bytes and names. Template edits invalidate approval.
        payload = {"bundle": self.model_dump(mode="json"),
                   "files": {name: data.decode() for name, data in self.files().items()}}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def prepare(brief: BuilderInput, spec: LandingPageSpec, client: OllamaClient | None = None) -> ArtifactBundle:
    # Revalidate even if a caller used model_construct or model_copy(update=...).
    brief = BuilderInput.model_validate(brief.model_dump())
    spec = LandingPageSpec.model_validate(spec.model_dump())
    return ArtifactBundle(run_id=brief.run_id, artifact_identity="validation-artifacts", brief=brief,
                          kit=generate_kit(brief, client), landing_page=spec,
                          model=client.settings.model if client else None,
                          generator="ollama" if client else "deterministic-template")
