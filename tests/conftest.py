"""Shared fixtures.

`fake_ollama` is a STUBBED stand-in for the Ollama HTTP API, used only by
offline unit tests. Live tests (marked `live`) talk to the real server.
"""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

import os
import tempfile
from pathlib import Path

# Tests never touch a running application's run records, approvals or audit log:
# any code path that builds the default services uses a throwaway directory.
# Expand Windows short-name aliases in test-owned paths; production path checks remain strict.
_TEST_STATE = str(Path(tempfile.mkdtemp(prefix="venturelab-tests-")).resolve())
os.environ["VENTURELAB_STATE_DIR"] = os.path.join(_TEST_STATE, "state")
os.environ["VENTURELAB_OUTPUT_DIR"] = os.path.join(_TEST_STATE, "outputs")
os.environ["VENTURELAB_DECISION_LOG"] = os.path.join(_TEST_STATE, "decision_log.json")

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


# --- Milestone 2: a STUBBED model that answers by role, and STUBBED public sources ---------

ROLE_MARKERS = {
    "queries": "plan searches of Hacker News",
    "extract": "read numbered passages",
    "assess": "check whether quotations from a source support a claim",
    "confirm": "second, sceptical reviewer",
    "challenge": "sceptical advisor",
}


class RoutedOllama:
    """STUBBED Ollama that picks a reply by the agent prompt it receives.

    `replies` maps a role (see ROLE_MARKERS) to a function(user_message) -> reply
    text, or to a fixed string. `calls` records the role of every chat request.
    """

    def __init__(self, replies: dict) -> None:
        self.replies = replies
        self.calls: list[str] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content) if request.content else {}
        if request.url.path != "/api/chat":
            return httpx.Response(200, json={"version": "0.0.0-test", "models": [], "done": True})
        system = body["messages"][0]["content"]
        user = body["messages"][1]["content"]
        role = next((r for r, marker in ROLE_MARKERS.items() if marker in system), "unknown")
        self.calls.append(role)
        reply = self.replies.get(role)
        if reply is None:
            return httpx.Response(500, json={"error": f"no stubbed reply for {role}"})
        return httpx.Response(200, json=chat_body(reply(user) if callable(reply) else reply))

    def client(self) -> OllamaClient:
        return OllamaClient(TEST_SETTINGS, transport=httpx.MockTransport(self.handler))


def hn_hits(*comments: tuple[str, str, str]) -> dict:
    """Algolia-style search result from (objectID, author, comment HTML) tuples."""
    return {"hits": [{"objectID": oid, "author": author, "comment_text": text, "story_title": "Ask HN: tools"}
                     for oid, author, text in comments]}


def stub_sources(routes: dict) -> "SourceFetcher":
    """STUBBED public web: `routes` maps a URL substring to a JSON dict, text, or an exception."""
    from sources import SourceFetcher

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for key, value in routes.items():
            if key in url:
                if isinstance(value, Exception):
                    raise value
                if isinstance(value, int):
                    return httpx.Response(value)
                if isinstance(value, dict):
                    return httpx.Response(200, json=value)
                return httpx.Response(200, text=value, headers={"content-type": "text/html"})
        raise httpx.ConnectError("no route", request=request)

    return SourceFetcher(transport=httpx.MockTransport(handler))
