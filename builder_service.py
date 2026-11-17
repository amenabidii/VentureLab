"""Prepare immutable, reviewable artifact bytes; materialization requires approval."""
from __future__ import annotations

import hashlib
import json
from typing import Protocol

from pydantic import Field, model_validator

from agents.builder import assemble_kit, generate_kit, kit_markdown, model_selects
from builder_models import BuilderInput, Contract, ExperimentKit, Identifier, LandingPageSpec
from landing_page import render_landing_page
from llm import OllamaClient


class Milestone2Adapter(Protocol):
    """Amen implements this boundary against his actual output types after merging."""
    def to_builder_input(self) -> BuilderInput: ...


class ArtifactBundle(Contract):
    schema_version: int = Field(default=2, ge=2, le=2, strict=True)
    run_id: Identifier
    artifact_identity: Identifier
    brief: BuilderInput
    kit: ExperimentKit
    landing_page: LandingPageSpec
    model: str | None = None
    generator: str = Field(pattern=r"^(deterministic-template|ollama)$")

    @model_validator(mode="after")
    def consistent_bundle(self):
        if self.run_id != self.brief.run_id:
            raise ValueError("Bundle and brief run IDs differ")
        if self.brief.gate_context and self.brief.gate_context.outcome != "GO":
            raise ValueError("Upstream gate does not admit a landing-page build")
        if self.landing_page.target_audience != self.brief.target_customer:
            raise ValueError("Landing-page audience must match the brief target customer")
        if self.kit != assemble_kit(self.brief, self.kit.assumption_index):
            raise ValueError("Experiment kit is inconsistent with the validated brief and design")
        if (self.generator == "ollama") != bool(self.model):
            raise ValueError("Generator/model provenance mismatch")
        return self

    def files(self) -> dict[str, bytes]:
        return {
            "phase2_step1_validation-kit.json": (self.kit.model_dump_json(indent=2) + "\n").encode(),
            "phase2_step1_validation-kit.md": kit_markdown(self.kit).encode(),
            "phase3_step1_landing-spec.json": (self.landing_page.model_dump_json(indent=2) + "\n").encode(),
            "phase3_step1_landing-page.html": render_landing_page(self.landing_page).encode(),
        }

    def fingerprint(self) -> str:
        return self.snapshot()[1]

    def snapshot(self) -> tuple[dict[str, bytes], str]:
        # Includes inputs, model identity, exact output bytes and names. Template edits invalidate approval.
        files = self.files()
        payload = {"bundle": self.model_dump(mode="json"),
                   "files": {name: data.decode() for name, data in files.items()}}
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
        return files, digest


def prepare(brief: BuilderInput, spec: LandingPageSpec, client: OllamaClient | None = None) -> ArtifactBundle:
    # Revalidate even if a caller used model_construct or model_copy(update=...).
    brief = BuilderInput.model_validate(brief.model_dump())
    spec = LandingPageSpec.model_validate(spec.model_dump())
    # Provenance records "ollama" only when the model actually made the selection.
    used_model = model_selects(brief, client)
    return ArtifactBundle(run_id=brief.run_id, artifact_identity="validation-artifacts", brief=brief,
                          kit=generate_kit(brief, client), landing_page=spec,
                          model=client.settings.model if used_model else None,
                          generator="ollama" if used_model else "deterministic-template")
