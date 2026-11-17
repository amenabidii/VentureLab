"""Minimal client for a local Ollama server.

Only open-weight models served by Ollama are used; there is no paid API.
Structured output uses Ollama's JSON-schema `format` field, then the reply is
validated again with Pydantic, with one retry on invalid output.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from config import Settings, get_settings

T = TypeVar("T", bound=BaseModel)

NS_PER_MS = 1_000_000


class LLMError(RuntimeError):
    """The model server could not be reached or returned unusable output."""


@dataclass
class LLMMetrics:
    wall_ms: float
    total_ms: float
    load_ms: float
    prompt_tokens: int
    prompt_eval_ms: float
    output_tokens: int
    eval_ms: float

    @property
    def prompt_tokens_per_s(self) -> float | None:
        return self.prompt_tokens / (self.prompt_eval_ms / 1000) if self.prompt_eval_ms > 0 else None

    @property
    def output_tokens_per_s(self) -> float | None:
        return self.output_tokens / (self.eval_ms / 1000) if self.eval_ms > 0 else None


@dataclass
class LLMResult:
    model: str
    text: str
    metrics: LLMMetrics
    parsed: Any = None
    done_reason: str = ""
    attempts: int = 1
    errors: list[str] = field(default_factory=list)


def _metrics(body: dict[str, Any], wall_ms: float) -> LLMMetrics:
    return LLMMetrics(
        wall_ms=wall_ms,
        total_ms=body.get("total_duration", 0) / NS_PER_MS,
        load_ms=body.get("load_duration", 0) / NS_PER_MS,
        prompt_tokens=body.get("prompt_eval_count", 0),
        prompt_eval_ms=body.get("prompt_eval_duration", 0) / NS_PER_MS,
        output_tokens=body.get("eval_count", 0),
        eval_ms=body.get("eval_duration", 0) / NS_PER_MS,
    )


class OllamaClient:
    def __init__(
        self,
        settings: Settings | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._http = httpx.Client(
            base_url=self.settings.ollama_base_url,
            timeout=httpx.Timeout(self.settings.llm_timeout_s, connect=5.0),
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        try:
            response = self._http.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise LLMError(f"Ollama {path} returned {exc.response.status_code}: {exc.response.text[:200]}") from exc
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            raise LLMError(f"Ollama {path} failed: {exc}") from exc

    # --- server and model management ---------------------------------------

    def version(self) -> str:
        return self._request("GET", "/api/version").get("version", "unknown")

    def list_models(self) -> list[str]:
        return [m["name"] for m in self._request("GET", "/api/tags").get("models", [])]

    def has_model(self, name: str) -> bool:
        return name in self.list_models()

    def pull(self, name: str) -> None:
        self._request("POST", "/api/pull", json={"model": name, "stream": False}, timeout=None)

    def warm(self, name: str) -> None:
        """Load a model into memory and keep it there for `keep_alive`."""
        self._request("POST", "/api/generate", json={"model": name, "keep_alive": self.settings.keep_alive})

    def unload(self, name: str) -> None:
        """Evict a model from memory so the next request measures a cold load."""
        self._request("POST", "/api/generate", json={"model": name, "keep_alive": 0})

    # --- inference -----------------------------------------------------------

    def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        schema: dict[str, Any] | None = None,
        temperature: float = 0.0,
        num_predict: int = 512,
        seed: int = 42,
    ) -> LLMResult:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            # Qwen3 "thinking" output is slow on CPU and is not used here.
            "think": False,
            "keep_alive": self.settings.keep_alive,
            "options": {
                "temperature": temperature,
                "num_predict": num_predict,
                "num_ctx": self.settings.num_ctx,
                "seed": seed,
            },
        }
        if schema is not None:
            payload["format"] = schema
        started = time.perf_counter()
        body = self._request("POST", "/api/chat", json=payload)
        wall_ms = (time.perf_counter() - started) * 1000
        text = body.get("message", {}).get("content", "")
        return LLMResult(model=model, text=text, metrics=_metrics(body, wall_ms),
                         done_reason=body.get("done_reason", ""))

    def chat_json(
        self,
        model: str,
        messages: list[dict[str, str]],
        output_type: type[T],
        *,
        retries: int = 1,
        **kwargs: Any,
    ) -> LLMResult:
        """Ask for JSON matching `output_type`; retry with the error message if invalid."""
        schema = output_type.model_json_schema()
        history = list(messages)
        errors: list[str] = []
        for attempt in range(1, retries + 2):
            result = self.chat(model, history, schema=schema, **kwargs)
            try:
                result.parsed = output_type.model_validate_json(result.text)
                result.attempts = attempt
                result.errors = errors
                return result
            except ValidationError as exc:
                error = f"attempt {attempt}: {exc.errors()[0].get('msg', 'invalid output')}"
                if result.done_reason == "length":
                    error += " (output cut off at the num_predict limit)"
                errors.append(error)
                history = list(messages) + [
                    {"role": "assistant", "content": result.text},
                    {
                        "role": "user",
                        "content": "That reply was not valid JSON for the required schema "
                        f"({error}). Reply again with only valid JSON.",
                    },
                ]
        raise LLMError(f"No valid JSON from {model} after {retries + 1} attempts: {errors}")
