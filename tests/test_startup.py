"""Startup and connectivity smoke tests for the web app (offline, STUBBED Ollama)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app, get_client, warm_model


@pytest.fixture
def http():
    yield TestClient(app)
    app.dependency_overrides.clear()


def use(client):
    app.dependency_overrides[get_client] = lambda: client


def test_health_needs_no_model(http, unreachable_client):
    use(unreachable_client)
    response = http.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_model_ready_when_installed(http, fake_ollama):
    use(fake_ollama(models=["qwen3:4b", "qwen3:1.7b"]).client())
    response = http.get("/health/model")
    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_model_not_ready_while_downloading(http, fake_ollama):
    use(fake_ollama(models=[]).client())
    response = http.get("/health/model")
    assert response.status_code == 503
    assert response.json()["model_installed"] is False


def test_model_not_ready_when_ollama_down(http, unreachable_client):
    use(unreachable_client)
    response = http.get("/health/model")
    assert response.status_code == 503
    assert response.json()["ollama"] == "unreachable"


def test_inference_check_validates_answer(http, fake_ollama):
    use(fake_ollama(chat_replies=['{"status": "ok", "sum": 5}']).client())
    body = http.get("/health/inference").json()
    assert body["ok"] is True
    assert body["reply"] == {"status": "ok", "sum": 5}


def test_inference_check_flags_wrong_answer(http, fake_ollama):
    use(fake_ollama(chat_replies=['{"status": "ok", "sum": 4}']).client())
    assert http.get("/health/inference").json()["ok"] is False


def test_startup_warm_up_loads_and_keeps_model(fake_ollama):
    fake = fake_ollama()
    assert warm_model(fake.client()) is True
    path, body = fake.requests[-1]
    assert path == "/api/generate"
    assert body["model"] == "qwen3:4b"
    assert body["keep_alive"] != 0  # keeps the model loaded, never unloads it


def test_startup_warm_up_survives_ollama_down(unreachable_client):
    assert warm_model(unreachable_client) is False


def test_index_page_renders_and_labels_stubs(http, fake_ollama):
    use(fake_ollama().client())
    response = http.get("/")
    assert response.status_code == 200
    assert "VentureLab" in response.text
    assert "STUBBED" in response.text
