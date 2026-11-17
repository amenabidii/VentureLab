"""Real browser audit with SYNTHETIC fixtures and hostile text, never market evidence."""
import os

import pytest

from builder_models import BuilderInput, LandingPageSpec
from builder_service import prepare
from tests.test_builder_variety import CASES

pytestmark = [pytest.mark.browser, pytest.mark.skipif(os.environ.get("VENTURELAB_BROWSER_TESTS") != "1", reason="set VENTURELAB_BROWSER_TESTS=1")]


@pytest.fixture(scope="module")
def browser():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("VENTURELAB_BROWSER_CHANNEL") or None)
        yield browser
        browser.close()


@pytest.mark.parametrize("case", CASES, ids=[case["brief"]["run_id"] for case in CASES])
@pytest.mark.parametrize("width", [1280, 390, 320])
def test_varied_pages_render_without_network(browser, tmp_path, case, width):
    bundle = prepare(BuilderInput.model_validate(case["brief"]), LandingPageSpec.model_validate(case["landing_page"]))
    artifact = tmp_path / "page.html"
    artifact.write_bytes(bundle.files()["phase3_step1_landing-page.html"])
    _check_page(browser, artifact, width, bundle.landing_page.headline)


@pytest.mark.parametrize("width", [1280, 390, 320])
def test_long_unicode_and_html_payload_remains_inert(browser, tmp_path, width):
    data = dict(CASES[0]["landing_page"])
    hostile = '<img src="https://example.org/pixel" onerror="window.injected=true"><script>window.injected=true</script>'
    data.update(product_name="界" * 80, headline="W" * 2000, value_proposition=hostile + " العربية & café 🧭 " * 30,
                problem="LongWord" * 250, features=["界" * 2000, hostile])
    from landing_page import render_landing_page
    artifact = tmp_path / "hostile.html"
    artifact.write_text(render_landing_page(LandingPageSpec.model_validate(data)), encoding="utf-8")
    _check_page(browser, artifact, width, data["headline"])


def _check_page(browser, artifact, width, headline):
    context = browser.new_context(viewport={"width": width, "height": 900})
    page = context.new_page()
    external, errors = [], []
    page.on("request", lambda request: external.append(request.url) if request.url.startswith(("http:", "https:")) else None)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(artifact.as_uri())
    assert page.get_by_role("heading", level=1).inner_text() == headline
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.locator("script,iframe,form,input,img,object,embed").count() == 0
    assert page.evaluate("window.injected === undefined")
    assert page.locator("a").evaluate_all("links => links.every(a => a.getAttribute('href').startsWith('#'))")
    page.get_by_role("link", name="Explore the proposed concept").click()
    assert page.url.endswith("#concept")
    assert not external and not errors
    context.close()
