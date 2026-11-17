"""Runtime settings, read from environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass

# Every environment variable the app reads, with its default.
DEFAULTS: dict[str, str] = {
    "OLLAMA_BASE_URL": "http://ollama:11434",
    "VENTURELAB_MODEL": "qwen3:4b",
    "VENTURELAB_FALLBACK_MODEL": "qwen3:1.7b",
    "VENTURELAB_LLM_TIMEOUT_S": "300",
    "VENTURELAB_NUM_CTX": "4096",
    "OLLAMA_KEEP_ALIVE": "30m",
    "APP_PORT": "8000",
}


@dataclass(frozen=True)
class Settings:
    ollama_base_url: str
    model: str
    fallback_model: str
    llm_timeout_s: float
    num_ctx: int
    keep_alive: str
    app_port: int


def _get(name: str) -> str:
    value = os.environ.get(name, "").strip()
    return value or DEFAULTS[name]


def get_settings() -> Settings:
    return Settings(
        ollama_base_url=_get("OLLAMA_BASE_URL").rstrip("/"),
        model=_get("VENTURELAB_MODEL"),
        fallback_model=_get("VENTURELAB_FALLBACK_MODEL"),
        llm_timeout_s=float(_get("VENTURELAB_LLM_TIMEOUT_S")),
        num_ctx=int(_get("VENTURELAB_NUM_CTX")),
        keep_alive=_get("OLLAMA_KEEP_ALIVE"),
        app_port=int(_get("APP_PORT")),
    )
