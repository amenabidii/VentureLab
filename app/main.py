"""VentureLab web app: health and model status. The Discover workflow runs from the CLI (orchestrator.py)."""

from __future__ import annotations

import html
import logging
import threading
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from config import get_settings
from llm import LLMError, OllamaClient

APP_VERSION = "0.1.0"
log = logging.getLogger("venturelab")


def warm_model(client: OllamaClient) -> bool:
    """Load the configured model so the first real request does not pay the load time.

    Never raises: if Ollama is down or the model is still downloading, the app
    keeps running and the model loads on first use instead.
    """
    try:
        client.warm(client.settings.model)
        log.info("model %s loaded", client.settings.model)
        return True
    except LLMError as exc:
        log.warning("model warm-up skipped: %s", exc)
        return False
    finally:
        client.close()


@asynccontextmanager
async def lifespan(app_: FastAPI) -> AsyncIterator[None]:
    threading.Thread(target=warm_model, args=(OllamaClient(),), daemon=True).start()
    if getattr(app_.state, "services", None) is None:
        # Run store, background worker and approval store. Runs left unfinished by a
        # previous process are marked failed ("interrupted") here, not resumed.
        from app.api import build_services
        app_.state.services = build_services()
    yield


app = FastAPI(title="VentureLab", version=APP_VERSION, lifespan=lifespan)


def get_client() -> Iterator[OllamaClient]:
    client = OllamaClient()
    try:
        yield client
    finally:
        client.close()


def model_status(client: OllamaClient) -> dict:
    model = client.settings.model
    try:
        version = client.version()
        installed = client.list_models()
    except LLMError as exc:
        return {"ollama": "unreachable", "error": str(exc), "model": model, "ready": False}
    present = model in installed
    return {
        "ollama": "ok",
        "ollama_version": version,
        "model": model,
        "model_installed": present,
        "installed_models": installed,
        "ready": present,
    }


@app.get("/health")
def health() -> dict:
    """Liveness: the web app itself is running. Does not touch the model."""
    return {"status": "ok", "app": "venturelab", "version": APP_VERSION}


@app.get("/health/model")
def health_model(client: OllamaClient = Depends(get_client)) -> JSONResponse:
    """Readiness: Ollama is reachable and the configured model is downloaded."""
    status = model_status(client)
    return JSONResponse(status, status_code=200 if status["ready"] else 503)


class PingReply(BaseModel):
    status: str
    sum: int


@app.get("/health/inference")
def health_inference(client: OllamaClient = Depends(get_client)) -> JSONResponse:
    """Runs one tiny structured-output request against the configured model."""
    model = client.settings.model
    messages = [
        {"role": "system", "content": "Reply with JSON only."},
        {"role": "user", "content": 'Set "status" to "ok" and "sum" to 2 + 3.'},
    ]
    try:
        result = client.chat_json(model, messages, PingReply, num_predict=32)
    except LLMError as exc:
        return JSONResponse({"ok": False, "model": model, "error": str(exc)}, status_code=503)
    reply: PingReply = result.parsed
    return JSONResponse(
        {
            "ok": reply.status == "ok" and reply.sum == 5,
            "model": model,
            "reply": reply.model_dump(),
            "attempts": result.attempts,
            "wall_ms": round(result.metrics.wall_ms),
            "load_ms": round(result.metrics.load_ms),
        }
    )


# Feature status shown on the start page. Kept in one place so the page and
# the README table can be checked against each other later.
FEATURES = [
    ("Local model server (Ollama) and health checks", "Working"),
    ("Discover workflow in the web workspace and CLI: brief, Investigator, Challenger", "Working"),
    ("Evidence verification, deterministic gate (Judge) and counterfactual", "Working"),
    ("Builder: validation experiment kit; local landing page only after GO", "Working (local files only)"),
    ("Founder approval for Builder actions (backend enforced)", "Working"),
    ("Commercial Setup, Launch, Operate & Learn phases", "STUBBED (not built)"),
    ("Payments and sale-to-cash", "STUBBED (design only, never implemented)"),
]


@app.get("/diagnostics", response_class=HTMLResponse)
def index(client: OllamaClient = Depends(get_client)) -> str:
    status = model_status(client)
    if status["ready"]:
        model_line = f"Model <code>{html.escape(status['model'])}</code> is downloaded and ready."
    elif status["ollama"] == "ok":
        model_line = (
            f"Ollama is running, but <code>{html.escape(status['model'])}</code> is still downloading. "
            "Reload this page in a minute."
        )
    else:
        model_line = "Ollama is not reachable yet. Reload this page in a few seconds."
    rows = "".join(
        f"<tr><td>{html.escape(name)}</td><td>{html.escape(state)}</td></tr>" for name, state in FEATURES
    )
    settings = get_settings()
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VentureLab</title>
<style>
 body {{ font-family: system-ui, sans-serif; max-width: 760px; margin: 2rem auto; padding: 0 16px; color: #1d1d1f; background: #fff; }}
 table {{ border-collapse: collapse; width: 100%; }} td {{ border-bottom: 1px solid #ddd; padding: .4rem .2rem; }}
 code {{ background: #f2f2f2; padding: 0 .25rem; border-radius: 3px; }}
</style></head><body>
<h1>VentureLab</h1>
<p>{model_line}</p>
<p>Fallback model: <code>{html.escape(settings.fallback_model)}</code>.
Checks: <a href="/health/model">/health/model</a>, <a href="/health/inference">/health/inference</a>.</p>
<h2>Status</h2>
<table>{rows}</table>
</body></html>"""

# Isolated founder workspace; model health and domain endpoints remain unchanged.
from app.ui.router import router as workspace_router
from app.api import router as api_router
app.include_router(workspace_router)
app.include_router(api_router)

from app.recordings import router as recordings_router
app.include_router(recordings_router)
