"""Phase 5 (Launch), core step "Open the store": store page and launch-post drafts.

Content comes only from the founder's brief and the founder-approved price. It passes
the Builder's content rules (no testimonials, reviews, user counts, urgency, income
claims or impersonation). Publishing is MOCKED and needs founder approval of the exact
page fingerprint (enforced in `workflow.py`); posts are drafts that are never sent.
"""
from __future__ import annotations

from html import escape

from agents.commercial import idea_phrase
from builder_models import check_content


def store_page_html(product: str, brief: dict, price_option: dict, *, rehearsal: bool) -> str:
    for text in (product, brief["idea"], brief["problem_statement"], brief["target_customer"]):
        check_content(text)
    price = price_option["price_eur_per_month"]
    price_line = "Free core features" if price == 0 else f"Planned test price: €{price} per month"
    banner = ("MOCKED STORE · REHEARSAL — the Discover gate did not decide GO; this page is not for sale."
              if rehearsal else "MOCKED STORE — local preview; nothing is sold or charged.")
    e = escape
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; form-action 'none'; base-uri 'none'">
<title>{e(product)} — store page (MOCKED)</title>
<style>
body{{margin:0;font:17px/1.6 system-ui,sans-serif;color:#17251f;background:#f6f7f2}}
.wrap{{max-width:860px;margin:auto;padding:24px}}
.banner{{background:#7a2e0e;color:#fff;padding:10px 14px;border-radius:8px;font-weight:600}}
.card{{background:#fff;border:1px solid #d4ddd4;border-radius:12px;padding:22px;margin:18px 0}}
.price{{font-size:22px;font-weight:700}}
button{{font:inherit;padding:12px 18px;border-radius:8px;border:0;background:#9aa69d;color:#fff}}
small{{color:#4a5a52}}
</style>
</head>
<body><div class="wrap">
<p class="banner" role="status">{e(banner)}</p>
<h1>{e(product)}</h1>
<p>{e(brief['idea'])}</p>
<div class="card"><h2>Who it is for</h2><p>{e(brief['target_customer'])}</p>
<h2>The problem it addresses</h2><p>{e(brief['problem_statement'])}</p>
<p><small>ASSUMPTION: this problem and its importance are still being tested with customers.</small></p></div>
<div class="card"><p class="price">{e(price_line)}</p>
<p><small>ASSUMPTION: a test price chosen by the founder, not evidence that anyone will pay.</small></p>
<button type="button" disabled aria-disabled="true">Checkout disabled (MOCKED — no payments of any kind)</button></div>
<p><small>No reviews, ratings or customer counts are shown because none exist yet. Policies: draft terms,
privacy and refund policy (Phase 4), pending professional review.</small></p>
</div></body></html>
"""


def launch_posts(product: str, brief: dict, price_option: dict, advice: dict | None = None) -> str:
    price = price_option["price_eur_per_month"]
    offer = "free to try" if price == 0 else f"planned at €{price}/month (test price)"
    # The announcement is in the founder's voice, so it uses only the founder's own words;
    # model suggestions appear below, labelled, for the founder to adopt or ignore.
    lead = f"Early concept: {idea_phrase(brief)}"
    problem = brief["problem_statement"].rstrip(".")
    posts = [
        # Mom Test: recruit people to talk about the problem; do not pitch the idea.
        ("Interview recruiting post (draft, problem only, no pitch)",
         f"I'm researching how {brief['target_customer']} deal with this: {problem}. If it happened to you "
         f"in the last month, could I ask you about it for 15 minutes? I'm not selling anything."),
        ("Short announcement for after the interviews (draft)",
         f"{lead}. For {brief['target_customer']}; {offer}. Feedback welcome; nothing is for sale yet."),
    ]
    for _, text in posts:
        check_content(text)
    body = "\n\n".join(f"## {title}\n\n> {text}\n\nStatus: DRAFT, not posted. Posting needs founder approval "
                       f"and is MOCKED in this prototype." for title, text in posts)
    if advice and advice.get("source") == "model":
        where = "\n".join(f"- **{c['name']}**: {c['why']}" for c in advice["channels"])
        body += (f"\n\n## Where to post first ({advice['label']})\n\n{where or '- none proposed'}\n\n"
                 f"Angle to lead with ({advice['label']}): "
                 f"{advice.get('launch_angle') or brief['problem_statement']}")
        if advice.get("value_proposition"):
            body += f"\n\nSuggested value proposition ({advice['label']}): {advice['value_proposition']}"
    return ("# Phase 5, step 1: Launch posts (drafts)\n\nWritten in the founder's voice for the founder to "
            "edit and post themselves. VentureLab never posts or messages anyone.\n\n" + body + "\n")
