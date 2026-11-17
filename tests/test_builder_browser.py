"""Real Chromium rendering; synthetic input, no mocked browser.

Enable with VENTURELAB_BROWSER_TESTS=1. Install requirements-dev.txt, then
python -m playwright install chromium (or set VENTURELAB_BROWSER_CHANNEL=msedge).
"""
import json
import os
from pathlib import Path

import pytest

from builder_models import BuilderInput, LandingPageSpec
from builder_service import prepare


@pytest.mark.browser
@pytest.mark.skipif(os.environ.get("VENTURELAB_BROWSER_TESTS") != "1", reason="set VENTURELAB_BROWSER_TESTS=1")
@pytest.mark.parametrize("width,height", [(1280, 900), (390, 844)])
def test_page_renders_responsively_without_network(tmp_path, width, height):
    from playwright.sync_api import sync_playwright
    payload = json.loads((Path(__file__).parent / "fixtures/builder_input.json").read_text())
    bundle = prepare(BuilderInput.model_validate(payload["brief"]), LandingPageSpec.model_validate(payload["landing_page"]))
    # Test-only materialization. Production writes go exclusively through ApprovalStore.execute.
    page_file = tmp_path / "page.html"
    page_file.write_bytes(bundle.files()["phase3_step1_landing-page.html"])
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=os.environ.get("VENTURELAB_BROWSER_CHANNEL") or None)
        page = browser.new_page(viewport={"width": width, "height": height})
        external_requests, errors = [], []
        page.on("request", lambda req: external_requests.append(req.url) if req.url.startswith(("http:", "https:")) else None)
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(page_file.as_uri())
        assert page.get_by_role("heading", level=1).is_visible()
        assert page.get_by_role("heading", name="Proposed features").is_visible()
        assert page.locator("form,input,script,iframe").count() == 0
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.get_by_role("link", name="Explore the proposed concept").click()
        assert page.url.endswith("#concept")
        assert not external_requests and not errors
        screenshot = os.environ.get("VENTURELAB_TEST_SCREENSHOTS")
        if screenshot:
            Path(screenshot).mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(Path(screenshot) / f"builder-{width}.png"), full_page=True)
        browser.close()
