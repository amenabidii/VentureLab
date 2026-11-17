"""Phase 3 clickable prototype: the user-journey checks execute, and they catch broken prototypes.

SYNTHETIC brief; no model, no network. The browser test clicks through the real page in
Chromium and is enabled with VENTURELAB_BROWSER_TESTS=1 (see tests/test_builder_browser.py).
"""
import json
import os

import pytest

from agents.product import PROTOTYPE, acceptance_checks, mvp_scope, prototype_html, user_guide, walk_prototype
from tests.test_later_phases import BRIEF, CLI, full_flow, make_run

CANVAS = {"summary": {"founder_assumptions_under_test": ["A1"]}}


def build() -> str:
    return prototype_html(BRIEF, mvp_scope(BRIEF, CANVAS), "Concept for remote engineers")


def test_walk_clicks_from_start_to_done_and_reaches_every_screen():
    walk = walk_prototype(build())
    assert walk["journey"] == ["start", "step-1", "step-2", "step-3", "done"]
    assert not walk["unreachable"] and not walk["dead_links"] and not walk["forbidden_tags"]
    assert set(walk["screens"]) == {"start", "step-1", "step-2", "step-3", "done", "source-1", "source-2", "source-3"}
    assert walk["result_points"] == walk["result_points_with_source"] == 3


def test_prototype_uses_the_founders_words_and_labels_everything_else():
    html = build()
    assert BRIEF["idea"].split(" (")[0] in html and BRIEF["target_customer"] in html
    assert "PLACEHOLDER" in html and "STUBBED" in html and "PROTOTYPE" in html
    for c in mvp_scope(BRIEF, CANVAS)["acceptance_criteria"]:
        assert c["id"] in html
    assert "<script" not in html and "<form" not in html and "http" not in html.replace("http-equiv", "")


@pytest.mark.parametrize(("break_it", "failed"), [
    (lambda h: h.replace('href="#done"', 'href="#nowhere"'), {"prototype: user journey reaches the end by clicking",
                                                             "prototype: every screen reachable from the start",
                                                             "prototype: no dead links"}),
    (lambda h: h.replace('<a class="source-link" href="#source-2">', '<a class="source-link" href="#missing">'),
     {"prototype: no dead links", "prototype: every result point links to its original source (AC2)",
      "prototype: every screen reachable from the start"}),
    (lambda h: h.replace("</body>", "<script>alert(1)</script></body>"), {"prototype: no script, form or external asset"}),
    (lambda h: h.replace("<p>Results can be wrong", '<p><a href="https://example.com">x</a> Results can be wrong'),
     {"prototype: no dead links", "prototype: no script, form or external asset"}),
    (lambda h: h.replace("PLACEHOLDER", "Sample"), {"prototype labelled PROTOTYPE and production code STUBBED"}),
    (lambda h: h.replace("</body>", "<p>Trusted by 500 customers</p></body>"), {"prototype passes content rules"}),
])
def test_acceptance_checks_fail_on_a_broken_prototype(tmp_path, break_it, failed):
    scope = mvp_scope(BRIEF, CANVAS)
    (tmp_path / "guide.md").write_text(user_guide(BRIEF, scope), encoding="utf-8")
    (tmp_path / PROTOTYPE).write_text(break_it(build()), encoding="utf-8")
    checks = {c["check"]: c["passed"] for c in acceptance_checks(tmp_path, "guide.md")}
    assert {name for name, ok in checks.items() if not ok} == failed


def test_pipeline_writes_the_prototype_and_launch_needs_its_checks(tmp_path, monkeypatch):
    cli = CLI(tmp_path, make_run(tmp_path))
    assert full_flow(cli, monkeypatch) == 0
    assert (cli.out / PROTOTYPE).exists()
    checks = json.loads((cli.out / "phase3_step4_acceptance-checks.json").read_text())["checks"]
    proto = [c for c in checks if c["check"].startswith("prototype")]
    assert len(proto) == 7 and all(c["passed"] for c in proto)
    assert json.loads((cli.out / "phase3_gate_build.json").read_text())["decision"].startswith("PROTOTYPE AND ARTIFACTS PASSED")
    actions = [e["action"] for e in cli.log()]
    assert "build_clickable_prototype" in actions


@pytest.mark.browser
@pytest.mark.skipif(os.environ.get("VENTURELAB_BROWSER_TESTS") != "1", reason="set VENTURELAB_BROWSER_TESTS=1")
def test_a_tester_can_click_through_the_prototype_in_a_real_browser(tmp_path):
    from playwright.sync_api import sync_playwright
    path = tmp_path / PROTOTYPE
    path.write_text(build(), encoding="utf-8")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("VENTURELAB_BROWSER_CHANNEL") or None)
        page = browser.new_page(viewport={"width": 390, "height": 844})
        external, errors = [], []
        page.on("request", lambda r: external.append(r.url) if r.url.startswith(("http:", "https:")) else None)
        page.on("pageerror", lambda err: errors.append(str(err)))
        page.goto(path.as_uri())
        visible = lambda sid: page.locator(f"section#{sid}").is_visible()  # noqa: E731
        assert visible("start") and not visible("step-1")
        page.get_by_role("link", name="Start the core job").click()
        assert visible("step-1") and not visible("start")
        page.locator("section#step-1").get_by_role("link", name="Continue").click()
        assert visible("step-2")
        page.get_by_role("link", name="Open original source 2").click()
        assert visible("source-2") and not visible("step-2")
        page.locator("section#source-2").get_by_role("link", name="Back to the result").click()
        page.locator("section#step-2").get_by_role("link", name="Continue").click()
        page.get_by_role("link", name="Finish").click()
        assert visible("done") and page.url.endswith("#done")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert not external and not errors
        browser.close()
