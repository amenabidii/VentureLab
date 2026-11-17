"""/mvp: the working Phase 3 MVP for the supported product type (thread digest), in the browser.

Local only: the pasted thread is processed in memory and returned; nothing is stored, logged,
sent or published, and no model is called. POSTs are accepted only from this page's origin.
"""
from __future__ import annotations

from html import escape
from urllib.parse import parse_qs

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse

from mvp.thread_digest import MAX_CHARS, SUPPORTED_TYPE, digest, render_html

router = APIRouter()
HEADERS = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin",
           "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
                                      "frame-ancestors 'none'; base-uri 'none'"}
EXAMPLE = """alice: The Slack export for the release thread is ready, it's long.
bob: Should we ship the summary feature on Friday or wait for review?
carol: I think we agreed last week that links back to each message are required.
bob: OK, decided: we go with Friday, links included.
alice: I'll write the user guide by Thursday.
dana: Can you check that private channels are never read?"""


def _page(thread: str, result: str = "", note: str = "") -> HTMLResponse:
    e = escape
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Thread digest MVP · VentureLab</title>
<style>body{{font:16px/1.55 system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 16px;color:#17251f}}
textarea{{width:100%;min-height:220px;font:14px/1.4 ui-monospace,monospace}}button{{font:inherit;padding:8px 16px}}
.banner{{background:#1f5d46;color:#fff;padding:10px 14px;border-radius:8px}}.muted{{color:#4a5a52}}
.err{{background:#fde8e8;padding:8px 12px;border-radius:6px}}li{{margin:4px 0}}</style></head><body>
<p><a href="/phases">← Phases 1–6</a></p>
<p class="banner">Phase 3 working MVP for one supported product type: {e(SUPPORTED_TYPE)}. Runs locally with fixed
rules; nothing is stored, sent or published. Other product types get the clickable prototype only (UNSUPPORTED here).</p>
<h1>Thread digest</h1>
<p>Paste a discussion, one message per line as <code>name: message</code>. You get the decisions, open questions and
action items, each linked to the message it came from.</p>
<form method="post" action="/mvp"><textarea name="thread" maxlength="{MAX_CHARS}" aria-label="Thread">{e(thread)}</textarea>
<p><button type="submit">Make the digest</button></p></form>
{f'<p class="err">{e(note)}</p>' if note else ''}{result}</body></html>"""
    return HTMLResponse(body, headers=HEADERS)


@router.get("/mvp", response_class=HTMLResponse, include_in_schema=False)
def mvp_form() -> HTMLResponse:
    return _page(EXAMPLE)


@router.post("/mvp", response_class=HTMLResponse, include_in_schema=False)
async def mvp_run(request: Request) -> HTMLResponse:
    host = request.headers.get("host", "")
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    if not origin or origin.split("://", 1)[-1].split("/", 1)[0] != host:
        raise HTTPException(403, "Accepted only from this VentureLab page")
    raw = await request.body()
    if len(raw) > MAX_CHARS * 4:
        return _page("", note="The thread is too long; paste a shorter part.")
    thread = (parse_qs(raw.decode("utf-8", "replace"), max_num_fields=5).get("thread") or [""])[0]
    try:
        return _page(thread, render_html(digest(thread)))
    except ValueError as exc:
        return _page(thread[:MAX_CHARS], note=str(exc))
