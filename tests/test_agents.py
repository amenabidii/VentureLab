"""Investigator and Challenger agents, run on STUBBED sources and a STUBBED model."""

from __future__ import annotations

import json
import re

import httpx
import pytest

import evidence as ev
from agents.challenger import (
    BASIS_ASSUMPTION,
    BASIS_CONTRADICTING,
    BASIS_ESTABLISHED,
    BASIS_PARTIAL,
    BASIS_UNCONFIRMED,
    challenge,
    founder_assumptions,
    output_model,
)
from agents.investigator import FULL, QUICK, fallback_queries, investigate, segment_breaks
from audit import AuditLog, check_entry
from brief import FounderBrief
from sources import HN_ITEM_URL, SourceFetcher
from tests.conftest import RoutedOllama, hn_hits, stub_sources

BRIEF = FounderBrief.model_validate({
    "idea": "A web app that drafts release notes from merged pull requests.",
    "problem_statement": "Small software teams spend too much time writing release notes.",
    "target_customer": "developers at small SaaS companies",
    "market": "online",
    "founder_skills": ["Python"],
    "hours_per_week": 10,
    "budget_eur": 0,
})
ALICE = "As a product manager I write the release notes, and it takes me an hour every Friday."
BOB = "As a developer I spend two hours writing release notes for each release."
DAVE = "We moved our web app to a new pull request workflow. Our team adopted a four-day week."
CAROL = "I love hiking in the Alps on weekends."
COMMENTS = hn_hits(("201", "alice", f"<p>{ALICE}</p>"), ("202", "bob", f"<p>{BOB}</p>"),
                   ("203", "carol", CAROL), ("204", "dave", DAVE))
URL = {name: HN_ITEM_URL.format(id=i) for name, i in (("alice", "201"), ("bob", "202"), ("dave", "204"))}


def pid(user_message: str, phrase: str) -> int:
    for number, text in re.findall(r"\[P(\d+)\] (.*)", user_message):
        if phrase in text:
            return int(number)
    raise AssertionError(f"no passage with {phrase!r} in {user_message!r}")


def extraction(*claims: tuple[str, str, list[str]]):
    """Reply builder: (type, claim, [phrases of passages]) -> extraction JSON naming passage IDs."""
    def reply(user: str) -> str:
        return json.dumps({"claims": [
            {"type": t, "claim": c, "passages": [pid(user, p) for p in phrases]} for t, c, phrases in claims]})
    return reply


SUPPORTS = json.dumps({"reason": "The quote says this.", "limitations": "one person", "verdict": "supports"})
CONFIRMED = json.dumps({"problems": "none", "fully_supported": True})
QUERIES = json.dumps({"queries": ["release notes chore", "changelog time"]})
NONE = json.dumps({"claims": []})
FAITHFUL = extraction(
    ("customer_problem", "One product manager says the release notes take an hour every Friday.",
     ["takes me an hour"]),
    ("customer_problem", "One developer says I spend two hours writing release notes for each release.",
     ["two hours writing"]),
)


def run(tmp_path, replies, routes=None, effort=FULL):
    model = RoutedOllama({"queries": QUERIES, "assess": SUPPORTS, "confirm": CONFIRMED} | replies)
    log = AuditLog(tmp_path / "log.json", "run-test")
    fetcher = stub_sources(routes or {"hn.algolia.com": COMMENTS})
    inv = investigate(BRIEF, model.client(), "qwen3:4b", fetcher, log, effort=effort)
    return inv, model, log


# --- retrieval and relevance ----------------------------------------------------------------------

def test_off_topic_comments_are_set_aside_and_duplicates_merged(tmp_path):
    inv, model, log = run(tmp_path, {"extract": NONE})
    # Two searches return the same four comments: each is analysed once, the off-topic one not at all.
    assert inv.selection["comments_seen"] == 4 and inv.selection["off_topic_dropped"] == 1
    assert len(inv.analysed) == 1 and CAROL not in inv.analysed[0].text
    assert model.calls.count("extract") == 1  # one extraction for all searches
    assert any(e["action"] == "select_relevant_comments" for e in log.entries())


def test_faithful_relevant_claims_are_established_and_cite_their_comment(tmp_path):
    inv, _, log = run(tmp_path, {"extract": FAITHFUL})
    f1, f2 = inv.by_origin("extracted")
    assert (f1.standing, f2.standing) == (ev.Standing.ESTABLISHED, ev.Standing.ESTABLISHED)
    assert (f1.relevance, f2.relevance) == ("statement", "statement")
    assert f1.urls == [URL["alice"]] and f2.urls == [URL["bob"]]
    for q in f1.item.quotes + f2.item.quotes:
        assert q.verified and q.text in inv.analysed[0].text
    for entry in log.entries():
        check_entry(entry)


@pytest.mark.parametrize(
    ("claim", "why"),
    [
        ("One developer says the release notes take an hour every Friday.", "wording"),  # wrong speaker
        ("Most product managers say the release notes take an hour every Friday.", "attributed"),  # group
        ("One product manager says release notes are the worst part of the job.", "wording"),  # unsupported
    ],
)
def test_wrong_attribution_and_unsupported_claims_stay_needs_review_without_a_model_call(tmp_path, claim, why):
    inv, model, _ = run(tmp_path, {"extract": extraction(("customer_problem", claim, ["takes me an hour"]))})
    f = inv.by_origin("extracted")[0]
    assert f.standing is ev.Standing.NEEDS_REVIEW and f.item.not_assessed
    assert any(why in r for r in f.item.review)
    assert all(q.verified for q in f.item.quotes)  # the quote is kept for the reviewer
    assert inv.by_origin("extracted")[0].item.confirmed is None  # no second check for the claim itself
    assert model.calls.count("confirm") == sum(1 for h in inv.by_origin("hypothesis_check") if h.item.verdict == "supports")


def test_off_topic_quote_is_kept_but_never_counted(tmp_path):
    inv, model, _ = run(tmp_path, {"extract": extraction(
        ("customer_problem", "One commenter says our team adopted a four-day week.", ["four-day week"]))})
    f = inv.by_origin("extracted")[0]
    assert f.relevance == "off_topic" and f.standing is ev.Standing.NEEDS_REVIEW
    assert any("does not share two key words" in r for r in f.item.review)
    assert f.urls == [URL["dave"]]


def test_demand_claims_skip_the_pointless_second_check(tmp_path):
    inv, model, _ = run(tmp_path, {"extract": extraction(
        ("demand", "One product manager says I would pay for release notes.", ["takes me an hour"]))})
    assert inv.by_origin("extracted")[0].item.confirmed is None  # no second check for the claim itself
    assert model.calls.count("confirm") == sum(1 for h in inv.by_origin("hypothesis_check") if h.item.verdict == "supports")
    assert inv.by_origin("extracted")[0].standing is not ev.Standing.ESTABLISHED


def test_no_quotation_joins_two_comments():
    source = stub_sources({"hn.algolia.com": COMMENTS}).hn_comments("release notes")
    passages = ev.split_passages(source.text)
    # P1 alice header, P2 alice body, P3 bob header, P4 bob body: 2-4 are consecutive IDs.
    quotes = ev.quotes_from_passages(source.text, passages, [2, 3, 4],
                                     breaks=segment_breaks(source, passages), url_at=source.url_at)
    assert [q.source_url for q in quotes] == [URL["alice"], URL["bob"]]
    assert quotes[0].text.startswith("As a product manager") and quotes[1].text.startswith("Comment by bob")


def test_founder_statement_is_checked_only_against_relevant_passages_and_can_be_contradicted(tmp_path):
    def assess(user: str) -> str:
        if "this problem: Small software teams" in user:
            return json.dumps({"reason": "They say it is quick.", "limitations": "", "verdict": "contradicts"})
        return SUPPORTS
    inv, _, _ = run(tmp_path, {"extract": NONE, "assess": assess})
    checks = inv.by_origin("hypothesis_check")
    # One check per relevant commenter, each quoting only that person's own words.
    assert [c.item.quotes[0].text for c in checks] == [BOB, ALICE]
    assert [c.urls for c in checks] == [[URL["bob"]], [URL["alice"]]]
    for check in checks:
        assert check.standing is ev.Standing.CONTRADICTED and check.relevance == "statement"
        assert len(check.item.quotes) == 1


def test_founder_statement_support_never_becomes_established(tmp_path):
    inv, model, _ = run(tmp_path, {"extract": NONE})
    check = inv.by_origin("hypothesis_check")[0]
    assert check.item.verdict == "supports" and check.standing is not ev.Standing.ESTABLISHED
    # The second check runs only to decide corroboration; the check still can never be established.
    assert model.calls.count("confirm") == len(inv.by_origin("hypothesis_check"))
    assert check.item.claim.startswith("One commenter says that they personally, as one of the target customers")
    assert check.speaker in ("alice", "bob")  # the commenter is recorded, so one person counts once


def test_unavailable_source_is_logged_and_yields_nothing(tmp_path):
    def handler(request):
        if "changelog" in str(request.url):
            raise httpx.ConnectError("offline", request=request)
        return httpx.Response(200, json=COMMENTS)

    model = RoutedOllama({"queries": QUERIES, "extract": NONE, "assess": SUPPORTS, "confirm": CONFIRMED})
    log = AuditLog(tmp_path / "log.json", "run-test")
    inv = investigate(BRIEF, model.client(), "qwen3:4b", SourceFetcher(transport=httpx.MockTransport(handler)), log)
    assert sorted(s.status for s in inv.sources) == ["available", "unavailable"]
    retrieved = [e for e in log.entries() if e["action"] == "retrieve_source"]
    assert {e["outcome"] for e in retrieved} == {"available", "unavailable"}


def test_quick_effort_runs_every_step_with_less_material(tmp_path):
    inv, model, _ = run(tmp_path, {"extract": FAITHFUL}, effort=QUICK)
    assert inv.queries == ["release notes chore"] and inv.effort == "quick"
    assert {"queries", "extract", "assess"} <= set(model.calls)
    assert inv.model_calls == len(model.calls)


def test_query_planning_failure_falls_back_without_the_model(tmp_path):
    inv, _, log = run(tmp_path, {"queries": "not json", "extract": NONE})
    assert inv.query_origin == "fallback" and inv.queries == fallback_queries(BRIEF)[:3]
    assert any(e["action"] == "plan_searches_fallback" and e["model"] is None for e in log.entries())


def test_extraction_failure_is_recorded_not_fatal(tmp_path):
    inv, _, log = run(tmp_path, {"extract": "not json"})
    assert inv.by_origin("extracted") == []
    assert any(e["action"] == "extract_claims" and e["outcome"] == "failed" for e in log.entries())


# --- Challenger ---------------------------------------------------------------------------------

def test_founder_assumptions_have_stable_ids():
    first, second = founder_assumptions(BRIEF), founder_assumptions(BRIEF)
    assert [a.id for a in first] == ["A1", "A2", "A3", "A4", "A5", "A6"] and first == second
    assert first[0].text == BRIEF.problem_statement and first[0].stated
    assert not first[-1].stated  # willingness to pay is implied, not stated


def test_strict_schema_only_allows_existing_ids():
    schema = json.dumps(output_model(["A1", "A2"], ["F1", "H1"]).model_json_schema())
    assert '"A1"' in schema and '"F1"' in schema and '"F2"' not in schema


def _findings(tmp_path):
    def assess(user: str) -> str:
        if "this problem: Small software teams" in user:
            return json.dumps({"reason": "It says the opposite.", "limitations": "", "verdict": "contradicts"})
        return SUPPORTS
    inv, _, _ = run(tmp_path, {"assess": assess, "extract": extraction(
        ("customer_problem", "One product manager says the release notes take an hour every Friday.",
         ["takes me an hour"]),
        ("customer_problem", "Most developers hate changelogs.", ["two hours writing"]),
    )})
    by = {f.id: f for f in inv.findings}
    assert by["F1"].standing is ev.Standing.ESTABLISHED and by["F2"].standing is ev.Standing.NEEDS_REVIEW
    assert by["H1"].standing is ev.Standing.CONTRADICTED
    return inv.findings


def test_challenger_grounds_reviews_and_rejects_wrong_or_invented_references(tmp_path):
    findings = _findings(tmp_path)
    reply = json.dumps({
        "reviews": {
            "A1": {"stance": "supported", "reason": "A PM spends an hour.", "evidence": ["F1"]},
            "A2": {"stance": "supported", "reason": "Developers hate it (see F2, F99).", "evidence": []},
            "A3": {"stance": "contradicted", "reason": "Nobody wants it.", "evidence": []},
            "A4": {"stance": "weakened", "reason": "Contradicted.", "evidence": ["H1"]},
            "A9": {"stance": "untested", "reason": "Invented assumption.", "evidence": []},
        },
        "new_hypotheses": [{"text": "Product managers, not developers, write release notes.", "evidence": ["F1"]}],
        "risks": [{"assumption": "A5", "kind": "feasibility", "text": "GitHub API limits.", "evidence": []},
                  {"assumption": "A7", "kind": "market", "text": "Invented.", "evidence": []}],
        "experiments": [
            {"assumption": "A1", "name": "Interviews", "method": "Talk to 8 PMs.", "support_if": "6 of 8 describe it",
             "weaken_if": "fewer than 3 do"},
            {"assumption": "A6", "name": "Pre-order page", "method": "Collect pre-orders with a countdown.",
             "support_if": "10 pre-orders", "weaken_if": "none"},
        ],
    })
    # The support check (existing assessment prompt) judges one PM's hour a week as partial
    # support for "small software teams spend too much time": it is one person, not teams.
    partial = json.dumps({"reason": "One PM, not teams in general.", "limitations": "one person",
                          "verdict": "partially_supports"})
    model = RoutedOllama({"challenge": reply, "assess": partial})
    log = AuditLog(tmp_path / "c.json", "run-test")
    c = challenge(BRIEF, findings, model.client(), "qwen3:4b", log)
    r = {x["assumption"]: x for x in c.reviews}
    assert list(r) == ["A1", "A2", "A3", "A4", "A5", "A6"]  # every founder assumption, nothing invented
    assert (r["A1"]["basis"], r["A1"]["stance"]) == (BASIS_PARTIAL, "partly_supported")
    assert r["A1"]["sources"] == [URL["alice"]] and model.calls.count("assess") == 1
    # F2 is not about "developers have this problem" (one shared concept): irrelevant, so not cited;
    # the invented F99 is dropped.
    assert (r["A2"]["basis"], r["A2"]["stance"], r["A2"]["evidence"]) == (BASIS_ASSUMPTION, "untested", [])
    assert r["A2"]["links"][0]["relationship"] == "irrelevant"
    assert (r["A3"]["basis"], r["A3"]["stance"]) == (BASIS_ASSUMPTION, "untested")
    # H1 contradicts the problem statement (A1), not the market assumption (A4).
    assert (r["A4"]["basis"], r["A4"]["stance"]) == (BASIS_ASSUMPTION, "untested")
    assert "did not review" in r["A5"]["reason"] or "not reviewed" in r["A5"]["reason"]
    assert r["A5"]["basis"] == BASIS_ASSUMPTION and r["A5"]["stance"] == "untested"
    assert all(x["reason_is_advisory"] for x in c.reviews)
    removed = " ".join(c.removed)
    for expected in ("F99", "A9", "A7", "Pre-order page", "A2: model said 'supported'",
                     "A3: model said 'contradicted'", "A4: model said 'weakened'"):
        assert expected in removed, expected
    # Hypotheses are never checked for support, so the best they get is UNCONFIRMED.
    assert c.new_hypotheses[0]["raised_by"] == "challenger" and c.new_hypotheses[0]["basis"] == BASIS_UNCONFIRMED
    assert [e["name"] for e in c.experiments] == ["Interviews"]
    assert c.grounded_reviews == 1
    check_entry(log.entries()[-1])


def test_challenger_failure_still_lists_contradictions_from_code(tmp_path):
    findings = _findings(tmp_path)
    c = challenge(BRIEF, findings, RoutedOllama({}).client(), "qwen3:4b", AuditLog(tmp_path / "c.json", "r"))
    assert c.status == "failed" and [x["finding"] for x in c.contradictions] == ["H1", "H2"]


def test_strict_schema_limits_reviews_and_text_length():
    schema = output_model(["A1", "A2", "A6"], ["F1"], review_ids=["A1", "A6"]).model_json_schema()
    reviews = schema["$defs"]["Reviews"]
    assert sorted(reviews["properties"]) == ["A1", "A6"] and sorted(reviews["required"]) == ["A1", "A6"]
    assert schema["$defs"]["Review"]["properties"]["reason"]["maxLength"] == 110


def test_customer_words_alone_do_not_make_a_text_relevant():
    import relevance as rel

    terms = rel.BriefTerms("Indie game developers lose track of player bug reports scattered across Discord.",
                           "A web app that triages bug reports from Discord.",
                           "solo indie game developers with a Discord community")
    assert terms.statement_match("I lose hours playing indie games on Linux.") is None
    assert terms.topic_match("It's easy to lose time playing indie games that work on Linux.") is None
    # A comment about players is on the topic, but never counts as support for the statement.
    assert terms.statement_match("StartPlaying.Games is for indie game players and game masters.") is None
    assert terms.statement_match("Players post bug reports in Discord and I lose track of them.")


def test_repeated_claims_are_dropped(tmp_path):
    same = ("customer_problem", "One product manager says the release notes take an hour every Friday.",
            ["takes me an hour"])
    inv, _, _ = run(tmp_path, {"extract": extraction(same, same)})
    assert len(inv.by_origin("extracted")) == 1 and inv.selection["duplicate_claims_dropped"] == 1


def test_application_written_headers_are_never_quoted(tmp_path):
    # A thread title in the header shares words with the statement; it must still never be quoted.
    titled = {"hits": [{"objectID": "301", "author": "erin", "story_title": "Writing release notes takes forever",
                        "comment_text": "We gave up and stopped publishing them."}] + COMMENTS["hits"]}

    def assess(user: str) -> str:
        assert "Comment by" not in user  # no header text reaches the assessment
        return SUPPORTS

    inv, model, _ = run(tmp_path, {"extract": NONE, "assess": assess}, routes={"hn.algolia.com": titled})
    for f in inv.findings:
        for q in f.item.quotes:
            assert not q.text.startswith("Comment by"), q.text


def test_a_header_cited_by_the_model_is_unverified(tmp_path):
    inv, _, _ = run(tmp_path, {"extract": lambda user: json.dumps({"claims": [
        {"type": "customer_problem", "claim": "One user says so.", "passages": [1]}]})})
    f = inv.by_origin("extracted")[0]
    assert not f.item.verified and f.standing is ev.Standing.ASSUMPTION


def test_thread_title_words_cannot_satisfy_the_wording_check(tmp_path):
    titled = {"hits": [{"objectID": "301", "author": "erin", "story_title": "Writing release notes takes forever",
                        "comment_text": "Our team stopped publishing release notes last year."}]}
    claim = ("customer_problem", "One user says writing release notes takes forever.", ["stopped publishing"])
    inv, _, _ = run(tmp_path, {"extract": extraction(claim)}, routes={"hn.algolia.com": titled})
    f = inv.by_origin("extracted")[0]
    assert f.standing is not ev.Standing.ESTABLISHED
    assert {"takes", "forever"} <= set(f.item.unsourced or [])
