"""Settings and .env.example consistency."""

from __future__ import annotations

import re
from pathlib import Path

from config import DEFAULTS, get_settings

ROOT = Path(__file__).resolve().parent.parent


def _example_keys() -> dict[str, str]:
    pairs = {}
    for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            pairs[key.strip()] = value.strip()
    return pairs


def test_env_example_lists_every_setting():
    assert set(_example_keys()) == set(DEFAULTS)


def test_env_example_has_no_secrets():
    for key, value in _example_keys().items():
        assert not re.search(r"(KEY|SECRET|TOKEN|PASSWORD)", key), key
        assert not re.search(r"(sk[-_]|pk_live|rk_live|ghp_)", value), key


def test_defaults_point_at_compose_ollama(monkeypatch):
    for key in DEFAULTS:
        monkeypatch.delenv(key, raising=False)
    settings = get_settings()
    assert settings.ollama_base_url == "http://ollama:11434"
    assert settings.model and settings.fallback_model


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("VENTURELAB_MODEL", "qwen3:1.7b")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/")
    settings = get_settings()
    assert settings.model == "qwen3:1.7b"
    assert settings.ollama_base_url == "http://localhost:11434"
