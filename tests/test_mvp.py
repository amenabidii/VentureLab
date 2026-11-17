"""Phase 3 working MVP (thread digest): real input -> real output. SYNTHETIC test threads only."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.mvp_page import EXAMPLE, router
from mvp.thread_digest import MAX_CHARS, digest, parse, render_html, supported

THREAD = """[09:01] maya: Release thread for v2, please read before standup.
[09:03] omar: Do we keep the old export format?
[09:05] lina: We agreed to drop it; nobody uses it.
[09:06] omar: OK, decided: drop the old export format in v2.
Migration notes go in the changelog.
[09:10] maya: Who checks the Windows installer?
[09:12] lina: I'll test the Windows installer by Friday.
[09:15] sam: Can we keep dark mode for v2.1?"""


def test_extracts_decisions_questions_and_actions_with_their_source_message():
    d = digest(THREAD).to_dict()
    assert d["messages"] == 7                                    # the continuation line joins message 4
    assert [x["message"] for x in d["decisions"]] == [3, 4]
    assert "Migration notes go in the changelog" in d["decisions"][1]["text"]
    assert [x["message"] for x in d["action_items"]] == [1, 6]  # "please read ..." is a request
    # Omar's question (#2) was settled by a later decision from someone else; Maya's and Sam's are still open.
    assert [x["message"] for x in d["open_questions"]] == [5, 7]
    assert d["participants"] == {"lina": 2, "maya": 2, "omar": 2, "sam": 1}


def test_output_quotes_messages_unchanged_and_links_every_point():
    html = render_html(digest(THREAD))
    for n in (3, 4, 5, 6, 7):
        assert f"href='#m{n}'" in html and f"id='m{n}'" in html
    assert "I&#x27;ll test the Windows installer by Friday." in html


def test_different_threads_give_different_digests():
    other = "ana: Should we rename the app?\nben: Let's go with the current name.\nana: I'll update the docs."
    a, b = digest(THREAD).to_dict(), digest(other).to_dict()
    assert a != b and b["decisions"][0]["author"] == "ben" and b["open_questions"] == []


def test_nothing_is_invented_for_an_empty_or_plain_thread():
    d = digest("just some notes without any structure").to_dict()
    assert d["decisions"] == d["action_items"] == d["open_questions"] == [] and d["messages"] == 1
    assert digest("").to_dict()["messages"] == 0


def test_hostile_input_is_escaped_and_limits_are_enforced():
    html = render_html(digest("eve: <script>alert(1)</script> decided?"))
    assert "<script>" not in html and "&lt;script&gt;" in html
    with pytest.raises(ValueError):
        parse("x" * (MAX_CHARS + 1))


@pytest.mark.parametrize(("idea", "ok"), [
    ("A browser extension that summarises long Slack threads a remote team member missed", True),
    ("A tool that writes a daily digest of long GitHub issue discussions", True),
    ("A CI plugin that detects flaky tests", False),
    ("An accessible PDF converter for screen reader users", False),
])
def test_supported_scope_is_explicit(idea, ok):
    assert supported(idea) is ok


def test_web_form_runs_the_mvp_locally_and_refuses_foreign_posts():
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)
    page = client.get("/mvp")
    assert page.status_code == 200 and "Thread digest" in page.text and "form-action 'self'" in page.headers["content-security-policy"]
    ok = client.post("/mvp", data={"thread": EXAMPLE}, headers={"origin": "http://testserver"})
    assert ok.status_code == 200 and "<h2>Decisions</h2>" in ok.text and "href='#m4'" in ok.text
    assert client.post("/mvp", data={"thread": EXAMPLE}).status_code == 403
    assert client.post("/mvp", data={"thread": EXAMPLE}, headers={"origin": "http://evil.example"}).status_code == 403
