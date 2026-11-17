"""Local thread-digest workbench. Inputs stay in memory; no model or persistence."""
from __future__ import annotations

from html import escape
from urllib.parse import parse_qs, urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from mvp.thread_digest import MAX_CHARS, digest, render_html, render_markdown

router = APIRouter()
HEADERS = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin", "Cache-Control": "no-store",
           "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
                                      "frame-ancestors 'none'; base-uri 'none'"}
# SYNTHETIC example for trying the tool, never customer evidence or a venture run.
EXAMPLE = """alice: SYNTHETIC example: our release discussion, not a customer conversation.
bob: Should we ship the summary feature on Friday or wait for review?
carol: We have not decided whether private-channel support is safe.
bob: OK, decided: we go with Friday, public channels only.
alice: I'll write the user guide by Thursday.
dana: Can you check that private channels are never read?"""

STYLE = """
:root{color-scheme:light;--ink:#182b25;--muted:#4f6259;--line:#d8e0d6;--paper:#f6f7f0;--green:#214d3b}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:16px/1.6 system-ui,sans-serif}
a{color:var(--green);text-underline-offset:4px}a:focus-visible,button:focus-visible,textarea:focus-visible{outline:3px solid #996100;outline-offset:4px}
header{border-bottom:1px solid var(--line);background:#fff}nav{max-width:1160px;margin:auto;padding:20px 24px;display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.brand{font-weight:800;text-decoration:none;letter-spacing:-.5px}.brand span{font-weight:400;color:var(--muted);margin-left:12px}
main{max-width:1160px;margin:auto;padding:48px 24px}h1{font-size:clamp(36px,6vw,66px);line-height:1.05;letter-spacing:-2px;margin:14px 0 22px;max-width:800px}h2{line-height:1.2;letter-spacing:-.6px}p{max-width:76ch}.eyebrow{font-size:12px;letter-spacing:1.6px;font-weight:750}.lead{font-size:20px;color:var(--muted);max-width:680px}
.chips{display:flex;gap:10px;flex-wrap:wrap;margin:24px 0 32px}.chips span{border:1px solid var(--line);border-radius:30px;padding:5px 12px;background:#fff;font-size:13px}
.workbench{display:grid;grid-template-columns:minmax(0,1fr) 270px;background:#fff;border:1px solid var(--line);border-radius:18px;overflow:hidden}.editor{padding:26px}.editor h2{margin-top:0}aside{background:#eaf0e5;padding:26px}aside h2{font-size:19px}aside ol{padding-left:20px}aside li{margin-bottom:18px}
label{display:block;font-weight:700;margin:12px 0}textarea{display:block;width:100%;min-height:250px;resize:vertical;border:1px solid #91a18f;border-radius:9px;background:#fbfcf8;color:var(--ink);padding:16px;font:14px/1.65 ui-monospace,monospace}
button,.button{font:inherit;font-weight:650;border:1px solid var(--green);border-radius:8px;padding:11px 18px;background:var(--green);color:#fff;cursor:pointer;text-decoration:none;display:inline-block}.secondary{background:#fff;color:var(--green)}.actions{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:18px}.muted{color:var(--muted);font-size:14px}.notice{padding:14px 18px;border-left:3px solid #8a681b;background:#f7eedb;font-size:14px}.error{border-color:#a12f2f;background:#fff1ee}
#digest{margin-top:48px}.result-head{display:flex;justify-content:space-between;gap:20px;align-items:center;flex-wrap:wrap}.result-head h2{font-size:32px;margin:8px 0 22px}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));border:1px solid var(--line);border-radius:12px;background:#fff;margin-bottom:22px}.metrics div{padding:18px}.metrics strong{display:block;font-size:32px}.metrics span{font-size:13px;color:var(--muted)}.digest-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:24px 0}.result-card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:24px;min-width:0}.full{grid-column:1/-1}.result-card ul{padding-left:20px}.result-card li{padding:9px 0;overflow-wrap:anywhere}.src{padding-left:24px}.src li{border-bottom:1px solid var(--line);padding:14px 12px;overflow-wrap:anywhere;scroll-margin-top:24px}.src li:target{background:#fff0b5;outline:2px solid #8a681b;border-radius:6px}footer{margin-top:48px;border-top:1px solid var(--line);padding-top:20px;color:var(--muted);font-size:13px}
@media(max-width:720px){main{padding:30px 16px}.workbench{grid-template-columns:1fr}.editor,aside{padding:20px}.digest-grid{grid-template-columns:1fr}.metrics{grid-template-columns:1fr 1fr}.brand span{display:none}h1{letter-spacing:-1px}.actions button{width:100%}}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
"""


def _page(thread: str, result: str = "", note: str = "") -> HTMLResponse:
    e = escape
    sample = thread.splitlines() == EXAMPLE.splitlines()
    body = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Thread digest · VentureLab</title><style>{STYLE}</style></head>
<body><header><nav aria-label="Product navigation"><a class="brand" href="/workspace">VentureLab <span>/ Thread digest</span></a>
<a href="/phases">Back to venture workflow →</a></nav></header><main>
<span class="eyebrow">A WORKING PRODUCT YOU CAN TRY NOW</span><h1>Catch up on the work.<br>Keep the context.</h1>
<p class="lead">Turn a long discussion into a source-linked brief of decisions, actions and questions. Every point takes you back to the words behind it.</p>
<div class="chips"><span>No model required</span><span>No account</span><span>Processed on your VentureLab server · not stored</span></div>
<div class="workbench"><section class="editor" aria-labelledby="editor-title"><h2 id="editor-title">Thread digest</h2>
<p class="muted">{'SYNTHETIC example loaded — not customer evidence. Replace it with your own thread, or try it as written.' if sample else 'Your input is processed in memory. Nothing is saved, sent to an external service or published.'}</p>
<form method="post" action="/mvp#digest"><label for="thread">Discussion</label><p id="format" class="muted">One message per line: <code>name: message</code>. Up to {MAX_CHARS:,} characters. Continuation lines join the preceding message.</p>
<textarea id="thread" name="thread" maxlength="{MAX_CHARS}" aria-describedby="format" required>{e(thread)}</textarea>
<div class="actions"><button type="submit" name="format" value="html">Make the digest →</button><button class="secondary" type="submit" name="format" value="markdown">Download Markdown</button><a href="/mvp?blank=1">Start blank</a></div></form></section>
<aside aria-label="How it works"><span class="eyebrow">FROM NOISE TO NEXT STEPS</span><ol><li><strong>Paste a thread.</strong><br>Chat, issue or meeting discussion in plain text.</li><li><strong>Inspect the brief.</strong><br>Candidate decisions, requests and questions to review.</li><li><strong>Follow the source.</strong><br>Review the original message before acting.</li></ol><p class="muted">Rules extract; they do not understand intent. Questions stay visible until you review them.</p><a href="/mvp">Load synthetic example</a></aside></div>
{f'<p class="notice error" role="alert">{e(note)}</p>' if note else ''}{result}
<footer>Working MVP for thread-digest products only. This tool is not proof of demand, a successful venture gate or permission to launch. <a href="/workspace#decision">Inspect your venture decision</a>.</footer>
</main></body></html>"""
    return HTMLResponse(body, headers=HEADERS)


@router.get("/mvp", response_class=HTMLResponse, include_in_schema=False)
def mvp_form(blank: bool = False) -> HTMLResponse:
    return _page("" if blank else EXAMPLE)


@router.post("/mvp", include_in_schema=False)
async def mvp_run(request: Request) -> Response:
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    try:
        parsed = urlsplit(origin)
        same_origin = parsed.scheme == request.url.scheme and parsed.netloc == request.headers.get("host", "")
    except ValueError:
        same_origin = False
    if not same_origin:
        raise HTTPException(403, "Accepted only from this VentureLab page")
    raw = await request.body()
    if len(raw) > MAX_CHARS * 12:
        return _page("", note="The thread is too long; paste a shorter part.")
    try:
        fields = parse_qs(raw.decode("utf-8", "replace"), max_num_fields=5)
        thread = (fields.get("thread") or [""])[0]
        if not thread.strip():
            return _page("", note="Paste a discussion before making a digest.")
        result = digest(thread)
        if (fields.get("format") or ["html"])[0] == "markdown":
            return Response(render_markdown(result), media_type="text/markdown; charset=utf-8",
                            headers={**HEADERS, "Content-Disposition": 'attachment; filename="thread-digest.md"'})
        return _page(thread, render_html(result))
    except ValueError as exc:
        return _page("", note=str(exc))
