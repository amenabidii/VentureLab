"""Phase 3 (Build), core step "Build the product": MVP scope, clickable prototype, user guide
and executed checks.

What is real: a scope and acceptance criteria derived only from the brief and the Lean
Canvas (thresholds labelled ASSUMPTION); a clickable prototype of the core job (one HTML
file whose screens are joined by in-page links and shown with CSS `:target`, so it needs no
script, form, network or account; all content is the founder's own words or a labelled
PLACEHOLDER); a DRAFT user guide; and acceptance checks that actually execute: a user-journey
walk through the prototype's links (every screen reachable, no dead link, start to finish,
every result point linked to its source) plus checks on the store page, policies and guide.
What is STUBBED: the MVP's production application code. The prototype shows the intended
flow for usability sessions; it does not perform the core job.
"""
from __future__ import annotations

import re
from collections import deque
from html import escape
from html.parser import HTMLParser
from pathlib import Path

from builder_models import check_content

BANNED = ("testimonial", "five-star", "5-star", "limited time", "only 3 left", "guaranteed", "act now")


def mvp_scope(brief: dict, canvas: dict) -> dict:
    values = brief.get("values_and_constraints", [])
    return {
        "core_job": brief["idea"], "for": brief["target_customer"], "label": "FOUNDER-STATED scope",
        "in_scope": [f"The single core job: {brief['idea']}"],
        "out_of_scope": ["Accounts, payments and integrations beyond the core job",
                         "Any feature not needed to test the riskiest assumption"],
        "constraints": values,
        "acceptance_criteria": [
            {"id": "AC1", "text": "A target customer completes the core job unaided in one session.",
             "label": "ASSUMPTION (threshold set by the founder before testing)"},
            {"id": "AC2", "text": "The output links every point back to its original source.",
             "label": "FOUNDER-STATED (from the idea)" if "link" in brief["idea"].lower() else "ASSUMPTION"},
            {"id": "AC3", "text": "No data is read outside what the user explicitly installs it for.",
             "label": "FOUNDER-STATED (from values/constraints)" if values else "ASSUMPTION"},
        ],
        "riskiest_assumption_first": (canvas.get("summary") or {}).get("founder_assumptions_under_test", [])[:1],
        "prototype": "phase3_step1_prototype.html: clickable flow of the core job for usability sessions "
                     "(PROTOTYPE: placeholders, no working functionality)",
        "code_generation": "STUBBED — VentureLab does not yet generate the MVP's production application code; "
                           "the clickable prototype shows the intended flow only.",
    }


def user_guide(brief: dict, scope: dict) -> str:
    text = f"""# Phase 3, step 3: User guide (DRAFT)

> DRAFT for the founder to complete once the MVP exists. The MVP's code is STUBBED; this guide
> describes the intended core job, not delivered features.

## What it is for

{brief['target_customer']}: {brief['problem_statement']}

## Intended core job

{scope['core_job']}

## Getting started (intended)

1. Install or open the product.
2. Do the core job once on your own material.
3. Check every result against its original source before relying on it.

## Try the clickable prototype

Open `phase3_step1_prototype.html` in a browser and click through: start, choose your own
material, review the result (each point links to its original source), then check and give
feedback. It is a PROTOTYPE for usability sessions: placeholders stand in for real material
and nothing is read, stored or sent.

## Limits

- Results can be wrong; the original source is always the reference.
- Constraints honoured: {'; '.join(scope['constraints']) or 'none stated'}.
"""
    check_content(text)
    return text


PROTOTYPE = "phase3_step1_prototype.html"
RESULT_POINTS = 3
SESSION_QUESTIONS = (
    "At each screen, what did you expect to happen next?",
    "Where did you hesitate or go back, and why?",
    "Tell me about the last time you did this job without the prototype. What did you do?",
)


def prototype_html(brief: dict, scope: dict, product: str) -> str:
    """A clickable prototype of the core job: screens joined by anchors, no script or form."""
    e = escape
    for text in (product, brief["idea"], brief["problem_statement"], brief["target_customer"], *scope["constraints"]):
        check_content(text)

    def nav(*links: tuple[str, str]) -> str:
        return '<p class="nav">' + " ".join(f'<a class="btn" href="#{t}">{e(label)}</a>' for t, label in links) + "</p>"

    constraints = "".join(f"<li>{e(c)}</li>" for c in scope["constraints"]) or "<li>None stated.</li>"
    points = "".join(
        f'<li class="point"><span class="ph">PLACEHOLDER result point {i}</span> '
        f'<a class="source-link" href="#source-{i}">Open original source {i}</a></li>' for i in range(1, RESULT_POINTS + 1))
    sources = "\n".join(
        f'<section class="screen" id="source-{i}"><h2>Original source {i}</h2>'
        f'<p class="ph">PLACEHOLDER: the original item that point {i} came from opens here, unchanged.</p>'
        + nav(("step-2", "Back to the result")) + "</section>" for i in range(1, RESULT_POINTS + 1))
    criteria = "".join(f"<li><b>{e(c['id'])}</b> {e(c['text'])} <small>({e(c['label'])})</small></li>"
                       for c in scope["acceptance_criteria"])
    questions = "".join(f"<li>{e(q)}</li>" for q in SESSION_QUESTIONS)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; form-action 'none'; base-uri 'none'">
<title>{e(product)} — clickable prototype</title>
<style>
body{{margin:0;font:17px/1.6 system-ui,sans-serif;color:#17251f;background:#f6f7f2}}
.wrap{{max-width:760px;margin:auto;padding:20px 16px}}
.banner{{background:#24475a;color:#fff;padding:10px 14px;border-radius:8px;font-weight:600}}
.screen{{display:none;background:#fff;border:1px solid #d4ddd4;border-radius:12px;padding:22px;margin:18px 0}}
.screen:target,body:not(:has(.screen:target)) #start{{display:block}}
.btn{{display:inline-block;margin:4px 8px 4px 0;padding:10px 16px;border-radius:8px;background:#1f5d46;color:#fff;text-decoration:none}}
.ph{{display:inline-block;background:#fff4d6;border:1px dashed #a07a12;padding:2px 8px;border-radius:6px}}
.point{{margin:8px 0}} small{{color:#4a5a52}}
</style>
</head>
<body><div class="wrap">
<p class="banner" role="status">CLICKABLE PROTOTYPE — placeholders only, no working functionality; production code STUBBED. Nothing is read, stored or sent.</p>
<section class="screen" id="start"><h1>{e(product)}</h1>
<p><b>For:</b> {e(brief['target_customer'])}</p>
<p><b>Problem (FOUNDER-STATED):</b> {e(brief['problem_statement'])}</p>
<p><b>Core job:</b> {e(brief['idea'])}</p>
{nav(("step-1", "Start the core job"))}</section>
<section class="screen" id="step-1"><h2>Step 1 of 3: Choose your own material</h2>
<p class="ph">PLACEHOLDER: the material you choose for the core job appears here. The prototype reads nothing.</p>
<p>Honoured in this step:</p><ul>{constraints}</ul>
{nav(("step-2", "Continue"), ("start", "Back"))}</section>
<section class="screen" id="step-2"><h2>Step 2 of 3: Review the result</h2>
<p>Each point of the result links back to where it came from.</p>
<ol>{points}</ol>
{nav(("step-3", "Continue"), ("step-1", "Back"))}</section>
{sources}
<section class="screen" id="step-3"><h2>Step 3 of 3: Check and give feedback</h2>
<p>Results can be wrong; the original source is always the reference.</p>
<p>What a usability session checks:</p><ul>{criteria}</ul>
{nav(("done", "Finish"), ("step-2", "Back"))}</section>
<section class="screen" id="done"><h2>End of the prototype journey</h2>
<p>Questions for the founder to ask after a session (about what the tester did, not a pitch):</p>
<ol>{questions}</ol>
{nav(("start", "Restart"))}</section>
</div></body></html>
"""


class _Screens(HTMLParser):
    """Collects each screen (a <section id>) and the links inside it, as a tester would see them."""

    FORBIDDEN = ("script", "form", "iframe", "img", "object", "embed", "input", "link")

    def __init__(self):
        super().__init__()
        self.links: dict[str, list[tuple[str, str]]] = {}
        self.current: str | None = None
        self.forbidden: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in self.FORBIDDEN:
            self.forbidden.append(tag)
        if tag == "section" and a.get("id"):
            self.current = a["id"]
            self.links[self.current] = []
        elif tag == "a" and self.current:
            self.links[self.current].append((a.get("href") or "", a.get("class") or ""))

    def handle_endtag(self, tag):
        if tag == "section":
            self.current = None


def walk_prototype(html: str, start: str = "start", end: str = "done") -> dict:
    """Click through the prototype: follow every link from the start screen (breadth first)."""
    parser = _Screens()
    parser.feed(html)
    links = parser.links
    dead = sorted({f"{s} -> {h}" for s, items in links.items() for h, _ in items
                   if not h.startswith("#") or h[1:] not in links})
    parent: dict[str, str | None] = {start: None} if start in links else {}
    queue = deque(parent)
    while queue:
        node = queue.popleft()
        for href, _ in links[node]:
            target = href[1:]
            if href.startswith("#") and target in links and target not in parent:
                parent[target] = node
                queue.append(target)
    journey, node = [], end if end in parent else None
    while node:
        journey.append(node)
        node = parent[node]
    points = html.count('class="point"')
    with_source = sum(1 for h, c in links.get("step-2", []) if "source-link" in c and h[1:] in links)
    return {"screens": sorted(links), "reachable": sorted(parent), "unreachable": sorted(set(links) - set(parent)),
            "dead_links": dead, "journey": journey[::-1], "forbidden_tags": parser.forbidden,
            "result_points": points, "result_points_with_source": with_source}


def acceptance_checks(out: Path, guide_name: str) -> list[dict]:
    """Executed checks over generated artifacts; each records what was actually checked."""
    checks = []

    def add(name: str, passed: bool, detail: str):
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    page = out / "phase5_step1_store-page.html"
    guide = (out / guide_name).read_text(encoding="utf-8")
    add("user guide marked DRAFT and code STUBBED", "DRAFT" in guide and "STUBBED" in guide, guide_name)
    add("user guide passes content rules", _passes(guide), "builder_models.check_content")
    proto = out / PROTOTYPE
    if proto.exists():
        html = proto.read_text(encoding="utf-8")
        walk = walk_prototype(html)
        add("prototype: user journey reaches the end by clicking",
            walk["journey"][:1] == ["start"] and walk["journey"][-1:] == ["done"],
            " -> ".join(walk["journey"]) or "no path from start to done")
        add("prototype: every screen reachable from the start", not walk["unreachable"] and len(walk["screens"]) > 1,
            f"{len(walk['reachable'])}/{len(walk['screens'])} screens; unreachable: {walk['unreachable'] or 'none'}")
        add("prototype: no dead links", not walk["dead_links"], ", ".join(walk["dead_links"]) or "all links resolve")
        add("prototype: every result point links to its original source (AC2)",
            walk["result_points"] > 0 and walk["result_points_with_source"] == walk["result_points"],
            f"{walk['result_points_with_source']}/{walk['result_points']} points")
        add("prototype: no script, form or external asset",
            not walk["forbidden_tags"] and not re.search(r"https?://", html, re.I), PROTOTYPE)
        add("prototype labelled PROTOTYPE and production code STUBBED",
            all(w in html for w in ("PROTOTYPE", "STUBBED", "PLACEHOLDER")), PROTOTYPE)
        add("prototype passes content rules", _passes(html), "builder_models.check_content")
    for name in ("terms", "privacy", "refund"):
        path = out / f"phase4_step2_{name}-policy-draft.md"
        if path.exists():
            text = path.read_text(encoding="utf-8")
            add(f"{name} policy is a labelled draft", "DRAFT" in text and "Not legal advice" in text, path.name)
    if page.exists():
        html = page.read_text(encoding="utf-8")
        add("store page has no form, script or external asset",
            not re.search(r"<(form|script|iframe|img)\b|https?://", html, re.I), page.name)
        add("store page checkout disabled and MOCKED", "disabled" in html and "MOCKED" in html, page.name)
        add("store page has no social proof or urgency", not any(b in html.lower() for b in BANNED), page.name)
    return checks


def _passes(text: str) -> bool:
    try:
        check_content(text)
        return True
    except ValueError:
        return False
