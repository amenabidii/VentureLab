"""Public-source retrieval, with the STUBBED web from conftest."""

from __future__ import annotations

import httpx

from sources import HN_ITEM_URL, html_to_text
from tests.conftest import hn_hits, stub_sources


def test_html_to_text_drops_scripts_and_keeps_blocks():
    text = html_to_text("<html><head><title>T</title></head><body><script>x=1</script>"
                        "<p>First &amp; one</p><p>Second</p><nav>menu</nav></body></html>")
    assert text == "First & one\n\nSecond"


def test_hn_comments_keep_a_permalink_per_comment():
    fetcher = stub_sources({"hn.algolia.com": hn_hits(
        ("101", "alice", "<p>Writing release notes takes me an hour every Friday.</p>"),
        ("102", "bob", "We generate the changelog from commit messages."),
    )})
    source = fetcher.hn_comments("release notes")
    assert source.available and len(source.segments) == 2
    first, second = source.segments
    assert source.text[first.start:first.end].startswith("Comment by alice")
    assert source.url_at(first.start + 5) == HN_ITEM_URL.format(id="101")
    assert source.url_at(second.start) == HN_ITEM_URL.format(id="102")
    assert "release+notes" in source.url


def test_unavailable_source_is_recorded_not_invented():
    fetcher = stub_sources({"hn.algolia.com": httpx.ConnectError("offline")})
    source = fetcher.hn_comments("release notes")
    assert source.status == "unavailable" and "ConnectError" in source.error
    assert source.text == "" and source.segments == []


def test_server_error_and_empty_results():
    assert stub_sources({"hn.algolia.com": 503}).hn_comments("x").status == "unavailable"
    empty = stub_sources({"hn.algolia.com": {"hits": []}}).hn_comments("x")
    assert empty.status == "empty" and not empty.available


def test_web_page_is_fetched_as_text_with_its_title():
    fetcher = stub_sources({"example.test": "<html><title>Pricing</title><body><p>Pro is 9 dollars.</p></body></html>"})
    source = fetcher.web_page("https://example.test/pricing")
    assert source.available and source.title == "Pricing"
    assert "Pro is 9 dollars." in source.text
    assert source.url_at(0) == "https://example.test/pricing"


def test_web_page_unsupported_type_and_404():
    def handler(request):
        if "pdf" in str(request.url):
            return httpx.Response(200, content=b"%PDF", headers={"content-type": "application/pdf"})
        return httpx.Response(404)

    from sources import SourceFetcher
    fetcher = SourceFetcher(transport=httpx.MockTransport(handler))
    assert "unsupported content type" in fetcher.web_page("https://example.test/a.pdf").error
    assert fetcher.web_page("https://example.test/missing").status == "unavailable"
