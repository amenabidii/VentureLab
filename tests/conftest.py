"""Shared fixtures.

`fake_ollama` is a STUBBED stand-in for the Ollama HTTP API, used only by
offline unit tests. Live tests (marked `live`) talk to the real server.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from config import Settings
from llm import OllamaClient

TEST_SETTINGS = Settings(
    ollama_base_url="http://ollama.test:11434",
    model="qwen3:4b",
    fallback_model="qwen3:1.7b",
    llm_timeout_s=5,
    num_ctx=2048,
    keep_alive="1m",
    app_port=8000,
)


def chat_body(content: str) -> dict:
    return {
        "message": {"role": "assistant", "content": content},
        "total_duration": 2_000_000_000,
        "load_duration": 500_000_000,
        "prompt_eval_count": 40,
        "prompt_eval_duration": 400_000_000,
        "eval_count": 20,
        "eval_duration": 1_000_000_000,
    }


class FakeOllama:
    """STUBBED Ollama: replies to /api/chat with queued contents; records requests."""

    def __init__(self, models: list[str] | None = None, chat_replies: list[str] | None = None) -> None:
        self.models = models if models is not None else ["qwen3:4b"]
        self.chat_replies = list(chat_replies or [])
        self.requests: list[tuple[str, dict]] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else {}
        self.requests.append((request.url.path, body))
        if request.url.path == "/api/version":
            return httpx.Response(200, json={"version": "0.0.0-test"})
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": m} for m in self.models]})
        if request.url.path == "/api/generate":
            return httpx.Response(200, json={"done": True})
        if request.url.path == "/api/chat":
            return httpx.Response(200, json=chat_body(self.chat_replies.pop(0)))
        return httpx.Response(404, json={"error": "not found"})

    def client(self) -> OllamaClient:
        return OllamaClient(TEST_SETTINGS, transport=httpx.MockTransport(self.handler))


@pytest.fixture
def fake_ollama() -> Callable[..., FakeOllama]:
    return FakeOllama


@pytest.fixture
def unreachable_client() -> OllamaClient:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    return OllamaClient(TEST_SETTINGS, transport=httpx.MockTransport(refuse))
