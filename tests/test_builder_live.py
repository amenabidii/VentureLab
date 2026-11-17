"""Opt-in real local Ollama test; input remains clearly synthetic test data."""
import json
import os
from pathlib import Path

import pytest

from agents.builder import generate_kit
from builder_models import BuilderInput
from llm import OllamaClient


@pytest.mark.live
@pytest.mark.skipif(os.environ.get("VENTURELAB_LIVE_TESTS") != "1", reason="set VENTURELAB_LIVE_TESTS=1")
def test_live_builder_hypothesis():
    payload = json.loads((Path(__file__).parent / "fixtures/builder_input.json").read_text())
    client = OllamaClient()
    try:
        kit = generate_kit(BuilderInput.model_validate(payload["brief"]), client)
        assert kit.hypothesis.startswith("ASSUMPTION:")
        assert kit.success_criteria.label.startswith("PROPOSED ASSUMPTION")
        assert kit.results_status.startswith("NOT RUN")
    finally:
        client.close()
