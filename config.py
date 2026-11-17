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
    "VENTURELAB_STATE_DIR": ".venturelab",
    "VENTURELAB_OUTPUT_DIR": "outputs",
    "VENTURELAB_DECISION_LOG": "decision_log.json",
    "VENTURELAB_APPROVAL_TTL_S": "7200",
    "VENTURELAB_MAX_QUEUED_RUNS": "3",
    "VENTURELAB_MODEL_WAIT_S": "900",
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
    state_dir: str = DEFAULTS["VENTURELAB_STATE_DIR"]
    output_dir: str = DEFAULTS["VENTURELAB_OUTPUT_DIR"]
    decision_log: str = DEFAULTS["VENTURELAB_DECISION_LOG"]
    approval_ttl_s: float = float(DEFAULTS["VENTURELAB_APPROVAL_TTL_S"])
    max_queued_runs: int = int(DEFAULTS["VENTURELAB_MAX_QUEUED_RUNS"])
    model_wait_s: float = float(DEFAULTS["VENTURELAB_MODEL_WAIT_S"])


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
        state_dir=_get("VENTURELAB_STATE_DIR"),
        output_dir=_get("VENTURELAB_OUTPUT_DIR"),
        decision_log=_get("VENTURELAB_DECISION_LOG"),
        approval_ttl_s=float(_get("VENTURELAB_APPROVAL_TTL_S")),
        max_queued_runs=int(_get("VENTURELAB_MAX_QUEUED_RUNS")),
        model_wait_s=float(_get("VENTURELAB_MODEL_WAIT_S")),
    )
