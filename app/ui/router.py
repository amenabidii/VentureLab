"""Static UI routes. No domain operations or approval authority live here."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter()
ASSETS = Path(__file__).parent / "static"
HEADERS = {
    "Content-Security-Policy": "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-src 'self' about:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}

@router.get("/", include_in_schema=False)
@router.get("/workspace", include_in_schema=False)
@router.get("/workspace/", include_in_schema=False)
def workspace():
    return FileResponse(ASSETS / "index.html", headers=HEADERS)

@router.get("/workspace/assets/{name}", include_in_schema=False)
def asset(name: str):
    # An explicit allowlist prevents filesystem traversal and configuration exposure.
    if name not in {"app.js", "views.js", "service.js", "contracts.js", "fixtures.js", "styles.css", "normalize.js", "preview.js"}:
        raise HTTPException(404)
    return FileResponse(ASSETS / name, headers=HEADERS)
