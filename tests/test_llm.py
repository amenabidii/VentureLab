"""Unit tests for the Ollama client, using the STUBBED Ollama from conftest."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from llm import LLMError


class Reply(BaseModel):
    status: str
    sum: int


MESSAGES = [{"role": "user", "content": "hi"}]


def test_chat_json_parses_valid_output(fake_ollama):
    fake = fake_ollama(chat_replies=['{"status": "ok", "sum": 5}'])
    result = fake.client().chat_json("qwen3:4b", MESSAGES, Reply)
    assert result.parsed == Reply(status="ok", sum=5)
    assert result.attempts == 1


def test_request_disables_thinking_and_sends_schema(fake_ollama):
    fake = fake_ollama(chat_replies=['{"status": "ok", "sum": 5}'])
    fake.client().chat_json("qwen3:4b", MESSAGES, Reply)
    path, body = fake.requests[-1]
    assert path == "/api/chat"
    assert body["think"] is False
    assert body["stream"] is False
    assert body["format"] == Reply.model_json_schema()
    assert body["options"]["temperature"] == 0


def test_chat_json_retries_once_then_succeeds(fake_ollama):
    fake = fake_ollama(chat_replies=["not json", '{"status": "ok", "sum": 5}'])
    result = fake.client().chat_json("qwen3:4b", MESSAGES, Reply)
    assert result.attempts == 2
    assert len(result.errors) == 1
    # The retry tells the model what went wrong.
    _, retry_body = fake.requests[-1]
    assert "not valid JSON" in retry_body["messages"][-1]["content"]


def test_chat_json_gives_up_after_retries(fake_ollama):
    fake = fake_ollama(chat_replies=['{"status": "ok"}', '{"sum": "five"}'])
    with pytest.raises(LLMError, match="No valid JSON"):
        fake.client().chat_json("qwen3:4b", MESSAGES, Reply)


def test_cut_off_output_is_reported(fake_ollama):
    import httpx

    from llm import OllamaClient

    fake = fake_ollama(chat_replies=['{"status": "o', '{"status": "o'])

    def cut_off(request):
        response = fake.handler(request)
        return httpx.Response(200, json=response.json() | {"done_reason": "length"})

    client = OllamaClient(fake.client().settings, transport=httpx.MockTransport(cut_off))
    with pytest.raises(LLMError, match="cut off at the num_predict limit"):
        client.chat_json("qwen3:4b", MESSAGES, Reply)


def test_metrics_converted_from_nanoseconds(fake_ollama):
    fake = fake_ollama(chat_replies=['{"status": "ok", "sum": 5}'])
    metrics = fake.client().chat_json("qwen3:4b", MESSAGES, Reply).metrics
    assert metrics.load_ms == 500
    assert metrics.prompt_tokens_per_s == pytest.approx(100)
    assert metrics.output_tokens_per_s == pytest.approx(20)


def test_unreachable_server_raises_llm_error(unreachable_client):
    with pytest.raises(LLMError):
        unreachable_client.version()
