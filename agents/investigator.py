"""Investigator agent: public research on the founder's idea, with verified evidence.

Steps (model calls marked *):
1. * Plan keyword searches from the brief (deterministic fallback if the model fails).
2.   Retrieve Hacker News comments for each search, plus any pages the founder listed.
     Unavailable or empty sources are recorded, never filled in.
3.   Select relevant material in code: comments sharing at least two key words
     with the brief are kept (best first, duplicates across searches merged);
     the rest is set aside and counted. Kept comments form one source for
     analysis, each still citing its own permalink.
4. * Extract claims: the model points at passages; Python copies the quotations
     (evidence.py). Each quote is checked for relevance to the brief.
5. * Assess claims that could become evidence. Claims that the deterministic
     checks already rule out (off-topic, wording beyond the quote, no
     attribution) are kept as NEEDS_REVIEW without a model call, and the second
     check runs only when it could change the outcome.
6. * Check the founder's problem statement against the passages that share key
     words with it. A `supports` here can never be ESTABLISHED (the statement is
     general); only `contradicts` and `does_not_support` carry weight.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

import evidence as ev
import relevance as rel
from audit import AuditLog
from brief import FounderBrief
from llm import LLMError, LLMResult, OllamaClient
from sources import Segment, Source, SourceFetcher, combine, looks_like_instructions

AGENT = "investigator"


@dataclass(frozen=True)
class Effort:
    """How much research a run does. Both levels run every step with real inference."""

    name: str
    max_queries: int
    comments_per_query: int
    max_comments: int  # relevant comments kept for analysis, across all searches
    prefilter_passages: int
    max_claims: int
    statement_checks: int  # independent commenters checked against the founder's statement


FULL = Effort("full", max_queries=3, comments_per_query=10, max_comments=8, prefilter_passages=12, max_claims=4,
              statement_checks=4)
QUICK = Effort("quick", max_queries=1, comments_per_query=10, max_comments=4, prefilter_passages=6, max_claims=2,
               statement_checks=2)


class QueryPlan(BaseModel):
    queries: list[str] = Field(min_length=1, max_length=3)


@dataclass
class Finding:
    id: str  # F1, F2 ... for extracted claims; H1, H2 ... for checks of the founder's statement
    origin: str  # "extracted" or "hypothesis_check"
    source_kind: str
    item: ev.EvidenceItem
    # "statement": about the founder's problem statement; "topic": about the brief but a different
    # point; "off_topic": shares too few key words with the brief to count for anything.
    relevance: str = "statement"
    shared_terms: list[str] = field(default_factory=list)
    speaker: str | None = None  # the commenter, for checks of one person's words

    @property
    def standing(self) -> ev.Standing:
        return self.item.standing

    @property
    def claim_type(self) -> str:
        return ev.effective_claim_type(self.item.claim, self.item.claim_type) or self.item.claim_type

    @property
    def urls(self) -> list[str]:
        return list(dict.fromkeys(q.source_url for q in self.item.quotes if q.verified and q.source_url))

    def to_dict(self) -> dict[str, Any]:
        i = self.item
        return {
            "id": self.id,
            "origin": self.origin,
            "type": self.claim_type,
            "model_type": i.claim_type,
            "claim": i.claim,
            "standing": self.standing.value,
            "relevance": self.relevance,
            "shared_terms": self.shared_terms,
            "speaker": self.speaker,
            "quotes": [{"text": q.text, "url": q.source_url, "status": q.status.value, "note": q.note}
                       for q in i.quotes],
            "verdict": i.verdict,
            "reason": i.reason,
            "limitations": i.limitations,
            "second_check": i.confirmed,
            "second_check_note": i.confirm_note,
            "unsourced_words": i.unsourced,
            "attributed": i.attributed,
            "review": i.review,
            "notes": i.notes,
        }


@dataclass
class Investigation:
    queries: list[str]
    query_origin: str  # "model" or "fallback"
    sources: list[Source]  # everything retrieved, including unavailable sources
    analysed: list[Source] = field(default_factory=list)  # what the model actually read
    findings: list[Finding] = field(default_factory=list)
    calls: list[dict[str, Any]] = field(default_factory=list)  # one entry per model call
    selection: dict[str, Any] = field(default_factory=dict)
    effort: str = FULL.name
    elapsed_s: float = 0.0

    @property
    def model_calls(self) -> int:
        return len(self.calls)

    def by_origin(self, origin: str) -> list[Finding]:
        return [f for f in self.findings if f.origin == origin]

    def to_dict(self) -> dict[str, Any]:
        return {
            "effort": self.effort,
            "queries": self.queries,
            "query_origin": self.query_origin,
            "sources": [
                {"kind": s.kind, "url": s.url, "title": s.title, "status": s.status, "error": s.error,
                 "retrieved_at": s.retrieved_at, "items": len(s.segments)}
                for s in self.sources
            ],
            "selection": self.selection,
            "findings": [f.to_dict() for f in self.findings],
            "model_calls": self.model_calls,
            "calls": self.calls,
            "model_seconds": round(sum(c["wall_s"] for c in self.calls), 1),
            "elapsed_s": round(self.elapsed_s, 1),
        }


def record_calls(calls: list[dict[str, Any]], action: str, results: list[LLMResult]) -> None:
    for r in results:
        calls.append({"action": action, "wall_s": round(r.metrics.wall_ms / 1000, 1),
                      "prompt_tokens": r.metrics.prompt_tokens, "output_tokens": r.metrics.output_tokens})


_WORD = re.compile(r"[A-Za-z][A-Za-z'-]+")
_FALLBACK_STOP = set("a an and are as at be by for from has have in is it of on or that the their they this "
                     "to too was with who which when spend spends long much more most many".split())


def personal_claim(problem_statement: str, target_customer: str = "") -> str:
    """The founder's statement as a question about one commenter's own experience."""
    who = f", as one of the target customers ({target_customer.strip()})," if target_customer.strip() else ""
    return f"One commenter says that they personally{who} experience this problem: {problem_statement.strip()}"


def fallback_queries(brief: FounderBrief) -> list[str]:
    """Keyword searches built without the model, used if query planning fails."""
    words = [w.lower() for w in _WORD.findall(brief.problem_statement) if w.lower() not in _FALLBACK_STOP]
    return [" ".join(words[:3])] if words else [brief.target_customer]


def plan_queries(
    client: OllamaClient, model: str, brief: FounderBrief, log: AuditLog, calls: list[dict[str, Any]],
    limit: int,
) -> tuple[list[str], str]:
    messages = [
        {"role": "system", "content": ev.load_prompt("investigator_queries")},
        {"role": "user", "content": f"IDEA: {brief.idea}\nPROBLEM: {brief.problem_statement}\n"
                                    f"CUSTOMER: {brief.target_customer}\nMARKET: {brief.market}"},
    ]
    try:
        result = client.chat_json(model, messages, QueryPlan, num_predict=60)
        record_calls(calls, "plan_searches", [result])
        queries: list[str] = []
        for q in result.parsed.queries:
            q = " ".join(_WORD.findall(q))[:60].strip()
            if q and q.lower() not in {x.lower() for x in queries}:
                queries.append(q)
        if queries:
            queries = queries[:limit]
            log.record(AGENT, "plan_searches", model=model, outcome="ok", queries=queries)
            return queries, "model"
        log.record(AGENT, "plan_searches", model=model, outcome="failed", error="no usable query")
    except LLMError as exc:
        calls.append({"action": "plan_searches", "wall_s": 0.0, "prompt_tokens": 0, "output_tokens": 0,
                      "failed": True})
        log.record(AGENT, "plan_searches", model=model, outcome="failed", error=str(exc)[:300])
    queries = fallback_queries(brief)[:limit]
    log.record(AGENT, "plan_searches_fallback", model=None, outcome="ok", queries=queries)
    return queries, "fallback"


def select_comments(
    sources: list[Source], terms: rel.BriefTerms, limit: int
) -> tuple[list[tuple[Source, Segment]], dict[str, Any]]:
    """Keep the comments most about the brief; drop duplicates and off-topic ones."""
    scored, seen, dropped = [], set(), 0
    for src in sources:
        if src.kind != "hn_comments" or not src.available:
            continue
        for seg in src.segments:
            if seg.url in seen:
                continue
            seen.add(seg.url)
            shared = terms.topic_match(src.text[seg.start:seg.end])
            if shared:
                scored.append((len(shared), seg.url, src, seg))
            else:
                dropped += 1
    scored.sort(key=lambda s: (-s[0], s[1]))
    kept = [(src, seg) for _, _, src, seg in scored[:limit]]
    return kept, {"comments_seen": len(seen), "off_topic_dropped": dropped,
                  "relevant": len(scored), "kept": len(kept), "kept_urls": [seg.url for _, seg in kept]}


def segment_breaks(source: Source, passages: list[ev.Passage]) -> frozenset[int]:
    """IDs of the first passage of each comment, so no quotation joins two comments."""
    firsts = set()
    for seg in source.segments:
        inside = [p.id for p in passages if seg.start <= p.start < seg.end]
        if inside:
            firsts.add(min(inside))
    return frozenset(firsts)


def classify(finding: Finding, terms: rel.BriefTerms) -> None:
    """Set how the finding's quoted text relates to the founder's brief."""
    text = " ".join(q.text for q in finding.item.quotes if q.verified)
    on_statement, on_topic = terms.statement_match(text), terms.topic_match(text)
    if on_statement:
        finding.relevance, finding.shared_terms = "statement", sorted(on_statement)
    elif on_topic:
        finding.relevance, finding.shared_terms = "topic", sorted(on_topic)
    else:
        finding.relevance, finding.shared_terms = "off_topic", sorted(rel.shared(terms.topic, text))
        finding.item.review.append("the quoted text does not share two key words with the brief, including "
                                   "one about the problem or idea rather than the customer, so it is not "
                                   "counted as evidence about it")


def _record_assessment(log: AuditLog, model: str, finding: Finding, used_model: bool) -> None:
    item = finding.item
    action = "check_founder_statement" if finding.origin == "hypothesis_check" else "assess_claim"
    log.record(AGENT, action, sources=finding.urls, model=model if used_model else None,
               finding=finding.id, standing=finding.standing.value, relevance=finding.relevance,
               verdict=item.verdict, second_check=item.confirmed, review=item.review, notes=item.notes)


def investigate(
    brief: FounderBrief,
    client: OllamaClient,
    model: str,
    fetcher: SourceFetcher,
    log: AuditLog,
    *,
    effort: Effort = FULL,
) -> Investigation:
    started = time.perf_counter()
    calls: list[dict[str, Any]] = []
    queries, origin = plan_queries(client, model, brief, log, calls, effort.max_queries)
    sources = [fetcher.hn_comments(q, effort.comments_per_query) for q in queries]
    sources += [fetcher.web_page(str(u)) for u in brief.source_urls]
    inv = Investigation(queries=queries, query_origin=origin, sources=sources, calls=calls, effort=effort.name)
    for s in sources:
        log.record(AGENT, "retrieve_source", sources=[s.url], model=None, outcome=s.status,
                   kind=s.kind, items=len(s.segments), error=s.error or None)

    terms = rel.BriefTerms(brief.problem_statement, brief.idea, brief.target_customer)
    kept, inv.selection = select_comments(sources, terms, effort.max_comments)
    inv.selection["topic_terms"] = sorted(terms.topic)
    inv.selection["problem_terms"] = sorted(terms.problem)
    log.record(AGENT, "select_relevant_comments", sources=inv.selection["kept_urls"], model=None,
               outcome="ok", **{k: v for k, v in inv.selection.items() if k not in ("kept_urls", "topic_terms")})
    hn = [s for s in sources if s.kind == "hn_comments"]
    if hn:
        title = "Relevant Hacker News comments for: " + "; ".join(queries)
        merged = combine(title, hn[0].url, kept)
        if merged.available:
            inv.analysed.append(merged)
    inv.analysed += [s for s in sources if s.kind == "web_page" and s.available]

    topic = f"{brief.problem_statement} (customer: {brief.target_customer}; idea: {brief.idea})"
    n_extracted = n_checks = 0
    seen_claims: set[str] = set()
    for source in inv.analysed:
        passages = ev.split_passages(source.text)
        breaks = segment_breaks(source, passages)
        # "Comment by <author> on the thread ..." lines are written by this application,
        # not by the commenter, so they are never shown to the model or quoted as evidence.
        headers = frozenset(p.id for p in passages if p.id in breaks and p.text.startswith("Comment by "))
        # Retrieved text that reads like instructions to an AI is untrusted in a stronger
        # sense: it is never shown to the model, quoted, or used as context (it stays in the
        # stored source text, so nothing is hidden from the founder).
        # A comment that contains such text is untrusted as a whole: its other sentences could be
        # written to look like ordinary evidence.
        flagged = [seg for seg in source.segments if looks_like_instructions(source.text[seg.start:seg.end])]
        untrusted = frozenset(p.id for p in passages
                              if any(seg.start <= p.start < seg.end for seg in flagged)
                              or looks_like_instructions(p.text))
        if untrusted:
            inv.selection["instruction_like_passages_skipped"] = (
                inv.selection.get("instruction_like_passages_skipped", 0) + len(untrusted))
        headers = headers | untrusted
        try:
            items, result = ev.extract_claims(
                client, model, source.text, topic=topic, source_url=source.url,
                max_passages=effort.prefilter_passages, max_claims=effort.max_claims, num_predict=250,
                breaks=breaks, url_at=source.url_at, exclude=headers,
            )
            record_calls(calls, "extract_claims", [result])
            log.record(AGENT, "extract_claims", sources=[seg.url for seg in source.segments][:20] or [source.url],
                       model=model, outcome="ok", claims=len(items))
        except LLMError as exc:
            calls.append({"action": "extract_claims", "wall_s": 0.0, "prompt_tokens": 0, "output_tokens": 0,
                          "failed": True})
            log.record(AGENT, "extract_claims", sources=[source.url], model=model, outcome="failed",
                       error=str(exc)[:300])
            items = []
        for item in items:
            key = " ".join(re.findall(r"[a-z0-9]+", item.claim.lower()))
            if key in seen_claims:  # the model sometimes repeats a claim word for word
                inv.selection["duplicate_claims_dropped"] = inv.selection.get("duplicate_claims_dropped", 0) + 1
                continue
            seen_claims.add(key)
            n_extracted += 1
            finding = Finding(f"F{n_extracted}", "extracted", source.kind, item)
            classify(finding, terms)
            if finding.relevance == "off_topic" and item.verified:
                item.not_assessed = True
                item.notes.append("not sent to the model: off-topic for this brief")
                results = []
            else:
                results = ev.assess_item(client, model, item, source.text, economical=True,
                                         assess_unpromotable=False, exclude=headers)
            record_calls(calls, "assess_claim", results)
            inv.findings.append(finding)
            _record_assessment(log, model, finding, bool(results))

        # Check the founder's own statement against each commenter separately, using that
        # person's exact words: the most relevant passage per comment, up to a limit. Each
        # check cites one comment, so independent people are counted independently.
        # Only the commenter's own first-person words can describe their own experience: quoted
        # material ("> ...", someone else's words) and statements about other people are skipped.
        body = [p for p in passages if p.id not in headers]
        scored, not_own = [], 0
        for p in body:
            shared = terms.statement_match(p.text)
            if not shared:
                continue
            if ev.quoted_line(source.text, p.start) or not ev.speaks_for_self(p.text):
                not_own += 1
                continue
            scored.append((len(shared), p.id, p))
        if not_own:
            inv.selection["statement_passages_not_own_experience"] = (
                inv.selection.get("statement_passages_not_own_experience", 0) + not_own)
        picks, seen_urls = [], set()
        for _, _, p in sorted(scored, key=lambda s: (-s[0], s[1])):
            url = source.url_at(p.start)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            picks.append(p)
            if len(picks) >= effort.statement_checks:
                break
        for url in sorted({source.url_at(passages[pid - 1].start) for pid in untrusted}):
            log.record(AGENT, "check_founder_statement", sources=[url], model=None, outcome="skipped",
                       reason="the comment contains text that reads like instructions to an AI; never sent to the model")
        if not picks:
            log.record(AGENT, "check_founder_statement", sources=[source.url], model=None, outcome="skipped",
                       reason="no passage in a commenter's own first-person words shares two key words "
                              "with the problem statement")
            continue
        for p in picks:
            quotes = ev.quotes_from_passages(source.text, passages, [p.id], breaks=breaks, url_at=source.url_at)
            n_checks += 1
            # The question is about this one person, so one person's words can answer it fully.
            check = Finding(f"H{n_checks}", "hypothesis_check", source.kind,
                            ev.EvidenceItem(personal_claim(brief.problem_statement, brief.target_customer),
                                            "customer_problem", quotes),
                            speaker=source.author_at(p.start))
            classify(check, terms)
            results = ev.assess_item(client, model, check.item, source.text, economical=True, exclude=headers)
            if check.item.verdict == "supports" and check.item.verified:
                # Only full support can corroborate, and only if the sceptical second check
                # (scope, context, supply vs demand, changed details) agrees.
                context = ev.context_for(source.text, check.item.quotes, exclude=headers)
                texts = [q.text for q in check.item.quotes]
                try:
                    confirm, res = ev.confirm_support(client, model, check.item.claim, texts, context)
                    results.append(res)
                    check.item.confirmed, check.item.confirm_note = confirm.fully_supported, confirm.problems
                except LLMError as exc:
                    check.item.notes.append(f"second check failed: {exc}"[:300])
            record_calls(calls, "check_founder_statement", results)
            inv.findings.append(check)
            _record_assessment(log, model, check, bool(results))

    inv.elapsed_s = time.perf_counter() - started
    return inv
