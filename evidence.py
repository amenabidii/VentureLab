"""Evidence handling: passages, verified quotations, support assessment, promotion.

Design rules (enforced here, not left to the model):
- The model never writes quotation text. It points at numbered passages, and
  Python copies the exact text from the original source by character offsets.
- A quotation is VERIFIED only if its text is the exact source text at the
  recorded offsets. Anything else is UNVERIFIED and is never shown as a quote.
- A claim becomes an ESTABLISHED finding only if every quotation is verified,
  the assessment says `supports`, a second sceptical check agrees, every
  content word of the claim appears in the quoted text or its context (so the
  model cannot change the speaker, invent a count or add detail), a claim
  about people is attributed to one person, and the claim is not a demand claim (desk research cannot establish demand; any
  claim about paying, buying or demand counts as one).
- ESTABLISHED means "this source supports this attributed claim". Whether a
  finding holds across sources is decided later by the gates, not here.
  A confirmed claim that fails only the wording or attribution rule becomes
  NEEDS_REVIEW: kept, with the reason, for a person to check or reword.
  Every other claim stays partial evidence, unsupported, contradicted or an
  assumption, and is labelled as such. Nothing is dropped.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, Field

from llm import LLMError, LLMResult, OllamaClient

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

ClaimType = Literal["customer_problem", "competitor", "demand", "segment"]
Verdict = Literal["supports", "partially_supports", "does_not_support", "contradicts"]


# --- passages -----------------------------------------------------------------


@dataclass(frozen=True)
class Passage:
    id: int
    start: int
    end: int
    text: str


_SENTENCE_END = re.compile(r"(?<=[.!?])\s+|\n\s*\n|\n")


def split_passages(source: str, max_chars: int = 400) -> list[Passage]:
    """Split a source into sentence-sized passages with exact character offsets.

    `source[p.start:p.end] == p.text` always holds.
    """
    passages: list[Passage] = []
    cursor = 0
    for match in list(_SENTENCE_END.finditer(source)) + [None]:
        end = match.start() if match else len(source)
        chunk = source[cursor:end]
        start = cursor + (len(chunk) - len(chunk.lstrip()))
        stop = cursor + len(chunk.rstrip())
        # Very long sentences are cut at word boundaries so prompts stay small.
        while stop - start > max_chars:
            space = source.rfind(" ", start, start + max_chars)
            cut = space if space > start else start + max_chars
            passages.append(Passage(len(passages) + 1, start, cut, source[start:cut]))
            start = cut + 1 if space > start else cut
        if stop > start:
            passages.append(Passage(len(passages) + 1, start, stop, source[start:stop]))
        if match:
            cursor = match.end()
    return passages


_WORD = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    "a an and are as at be but by for from has have i in is it its my of on or so that the their them "
    "they this to was we were with you your our me do does did not no".split()
)


def _stem(word: str) -> str:
    return word[:-1] if len(word) > 3 and word.endswith("s") and not word.endswith("ss") else word


def _terms(text: str) -> set[str]:
    return {_stem(w) for w in _WORD.findall(text.lower()) if w not in _STOP and len(w) > 2}


def rank_passages(passages: list[Passage], query: str, k: int) -> list[Passage]:
    """Keep the k passages sharing the most terms with the query, in source order.

    A cheap, deterministic prefilter so the model reads fewer tokens.
    """
    query_terms = _terms(query)
    scored = [(len(query_terms & _terms(p.text)), p.id, p) for p in passages]
    top = sorted(scored, key=lambda s: (-s[0], s[1]))[:k]
    return sorted((p for score, _, p in top if score > 0), key=lambda p: p.id)


def numbered(passages: list[Passage]) -> str:
    return "\n".join(f"[P{p.id}] {p.text}" for p in passages)


# --- quotations ---------------------------------------------------------------


class QuoteStatus(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"


@dataclass(frozen=True)
class Quote:
    source_url: str | None
    text: str
    start: int | None
    end: int | None
    status: QuoteStatus
    note: str = ""

    @property
    def verified(self) -> bool:
        return self.status is QuoteStatus.VERIFIED

    def display(self) -> str:
        """Verified text is quoted; anything else is visibly marked."""
        if self.verified:
            return f"“{self.text}”"
        return f"[UNVERIFIED, not a quotation] {self.text}"


def _unverified(source_url: str | None, text: str, note: str) -> Quote:
    return Quote(source_url, text, None, None, QuoteStatus.UNVERIFIED, note)


def verify_span(source: str, start: int, end: int, source_url: str | None = None) -> Quote:
    if not (0 <= start < end <= len(source)):
        return _unverified(source_url, "", "span outside source")
    return Quote(source_url, source[start:end], start, end, QuoteStatus.VERIFIED)


def quotes_from_passages(
    source: str,
    passages: list[Passage],
    ids: list[int],
    source_url: str | None = None,
    *,
    breaks: frozenset[int] = frozenset(),
    url_at: Callable[[int], str] | None = None,
) -> list[Quote]:
    """Turn passage IDs chosen by the model into quotations copied from the source.

    Each run of consecutive IDs becomes one verified quotation. A run never
    continues into a passage listed in `breaks` (the first passage of another
    comment or document), and `url_at(offset)` gives each quotation the URL of
    the part of the source it comes from. Any unknown ID makes the result a
    single unverified quote with empty text.
    """
    by_id = {p.id: p for p in passages}
    wanted = sorted(set(ids))
    if not wanted:
        return [_unverified(source_url, "", "no passage ids")]
    if any(i not in by_id for i in wanted):
        return [_unverified(source_url, "", f"unknown passage id in {ids}")]
    runs: list[list[int]] = [[wanted[0]]]
    for i in wanted[1:]:
        if i == runs[-1][-1] + 1 and i not in breaks:
            runs[-1].append(i)
        else:
            runs.append([i])
    quotes = []
    for r in runs:
        start = by_id[r[0]].start
        url = url_at(start) if url_at else source_url
        quotes.append(verify_span(source, start, by_id[r[-1]].end, url))
    return quotes


def _loose(text: str) -> tuple[str, list[int]]:
    """Collapse whitespace and unify quote marks; keep a map back to source offsets."""
    table = {"‘": "'", "’": "'", "“": '"', "”": '"'}
    out: list[str] = []
    index: list[int] = []
    prev_space = True
    for i, ch in enumerate(text):
        ch = table.get(ch, ch)
        if ch.isspace():
            if prev_space:
                continue
            ch, prev_space = " ", True
        else:
            prev_space = False
        out.append(ch)
        index.append(i)
    return "".join(out), index


def verify_excerpt(source: str, excerpt: str, source_url: str | None = None) -> Quote:
    """Check text that someone claims is a quotation.

    Only whitespace and curly-quote differences are tolerated. If found, the
    returned quote holds the ORIGINAL source text, never the submitted text.
    Changed words, numbers or punctuation make it UNVERIFIED.
    """
    loose_source, index = _loose(source)
    loose_excerpt, _ = _loose(excerpt.strip())
    pos = loose_source.find(loose_excerpt) if loose_excerpt else -1
    if pos < 0:
        return _unverified(source_url, excerpt, "text not found in source")
    start = index[pos]
    end = index[pos + len(loose_excerpt) - 1] + 1
    return verify_span(source, start, end, source_url)


# --- claims and the promotion rule ----------------------------------------------


class Standing(str, Enum):
    ESTABLISHED = "established"  # verified quotes, full support, confirmed by a second check
    PARTIAL = "partial_evidence"  # verified quotes, partial or unconfirmed support
    # Verified quotes, support confirmed, but the claim's wording goes beyond the
    # quoted text (or the wording check did not run). Kept for a person to check
    # or reword; never treated as a finding.
    NEEDS_REVIEW = "needs_review"
    UNSUPPORTED = "unsupported"  # verified quotes do not support the claim
    CONTRADICTED = "contradicted"  # verified quotes contradict the claim
    ASSUMPTION = "assumption"  # no verified quote, or not assessed


# Willingness to pay, buying or demand, but not ordinary talk about invoices
# being paid ("paid late", "payments land in two accounts").
_PAYMENT_LANGUAGE = re.compile(
    r"\b(?:(?:would|will|willing to|happy to|happily|ready to|prepared to)\s+pay"
    r"|(?:pay|pays|paying|paid)\s+(?:for|to use|a subscription)"
    r"|paying\s+(?:customers?|subscribers?|users?|clients?)"
    r"|buy|buys|bought|buying|purchase[sd]?|purchasing"
    r"|subscribe[sd]?|subscribing|subscriptions?"
    r"|demand)\b",
    re.IGNORECASE,
)


def effective_claim_type(claim: str, claim_type: str | None) -> str | None:
    """Claims about paying, buying or demand are demand claims, whatever the model called them."""
    return "demand" if _PAYMENT_LANGUAGE.search(claim) else claim_type


# Words a claim may use without finding them in the quoted text: function words and
# the vocabulary of attributing a statement to ONE unnamed person. Deliberately
# absent, so they must appear in the text itself:
# - plural or role attributions ("posters", "editors", "customer", "reviewer"),
#   because one quote speaks only for the person who wrote it;
# - quantity and scope words ("most", "many", "every", "over"), which can widen a claim;
# - causal words ("because", "due", "since"), which can invent a cause.
_FREE_WORDS = _STOP | frozenset(
    "about after also been before being can could during "
    "he her his how if into just per she should such than then "
    "there these those up what when where which while who will would "
    "one someone person user poster speaker author commenter writer "
    "say says said report reports reported state states stated write writes wrote mention "
    "mentions mentioned describe describes described note notes noted explain explains "
    "claim claims think thinks feel feels find finds found according".split()
)
_CLAIM_WORD = re.compile(r"[a-z0-9]+")

# Claims about people must be attributed to one person ("One host says ...",
# "A bookkeeper reports ..."). The wording rule alone cannot see that
# "Bookkeepers say" turns one bookkeeper into a group, because plurals match.
PEOPLE_CLAIM_TYPES = frozenset({"customer_problem", "segment"})
_ONE_PERSON = re.compile(r"^\s*(?:at least\s+)?(?:one|a|an|someone)\b", re.IGNORECASE)


def attributed_to_one_person(claim: str, claim_type: str | None) -> bool:
    """True unless a claim about people is not phrased as one person's statement."""
    return claim_type not in PEOPLE_CLAIM_TYPES or bool(_ONE_PERSON.match(claim))


def _norm(word: str) -> str:
    """Light suffix stripping so inflections match ("checking"/"checked"/"checks")."""
    for suffix in ("ing", "ed", "es", "s"):
        if len(word) > len(suffix) + 3 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def unsourced_words(claim: str, support_text: str) -> list[str]:
    """Content words of the claim that appear nowhere in the quotes and their context.

    A deterministic guard against the model rewriting what the source says: a
    wrong speaker ("a translator" for a bookkeeper), a group made out of one
    person ("editors report"), an invented count ("two posters") or added detail
    ("significant limitations"). It is deliberately strict: a correct claim
    that paraphrases ("flashcards" for "decks") is held at NEEDS_REVIEW for a
    person, which is the safe direction.
    """
    available = {_norm(w) for w in _CLAIM_WORD.findall(support_text.lower())}
    # The one-person attribution formula ("At least one ...") is ours, not the source's.
    claim = _ONE_PERSON.sub("", claim, count=1)
    missing: list[str] = []
    for word in _CLAIM_WORD.findall(claim.lower()):
        if len(word) < 2 or word in _FREE_WORDS or _norm(word) in available or word in missing:
            continue
        missing.append(word)
    return missing


@dataclass
class EvidenceItem:
    claim: str
    claim_type: str
    quotes: list[Quote]
    verdict: Verdict | None = None
    reason: str = ""
    limitations: str = ""
    confirmed: bool | None = None  # result of the second, sceptical check
    confirm_note: str = ""
    # Claim words missing from the quotes and context; None until the check has run.
    unsourced: list[str] | None = None
    # Whether a claim about people is attributed to one person; None until checked.
    attributed: bool | None = None
    # Why a person should look at this item (wording, a verdict that disagrees with its reason).
    review: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    # Set when economical mode skipped the model because the outcome could not change.
    not_assessed: bool = False

    @property
    def verified(self) -> bool:
        return bool(self.quotes) and all(q.verified for q in self.quotes)

    @property
    def standing(self) -> Standing:
        if self.verified and self.verdict is None and self.not_assessed:
            # Deliberately not sent to the model because it can never be established:
            # kept, with its verified quote, for a person to review.
            return Standing.NEEDS_REVIEW
        return standing_for(self.verified, self.verdict, self.confirmed,
                            effective_claim_type(self.claim, self.claim_type),
                            grounded=self.grounded)

    @property
    def grounded(self) -> bool:
        return self.unsourced == [] and self.attributed is True

    @property
    def can_be_established(self) -> bool:
        """False once the deterministic checks rule out ESTABLISHED, whatever the model says."""
        return self.verified and self.grounded and effective_claim_type(self.claim, self.claim_type) != "demand"


def standing_for(
    verified: bool,
    verdict: str | None,
    confirmed: bool | None = None,
    claim_type: str | None = None,
    *,
    grounded: bool = False,
) -> Standing:
    """The single promotion rule. Nothing else can mark a claim established.

    `grounded` means the wording check ran and found every content word of the
    claim in the quoted text; it defaults to False so that skipping the check
    can never promote a claim.
    """
    if not verified or verdict is None:
        return Standing.ASSUMPTION
    if verdict == "supports":
        if confirmed is not True or claim_type == "demand":
            # Unconfirmed support, or a demand claim: desk research is never enough.
            return Standing.PARTIAL
        # Supported and confirmed, but wording beyond the quoted text: kept for a
        # person to check or reword, never a finding.
        return Standing.ESTABLISHED if grounded else Standing.NEEDS_REVIEW
    return {
        "partially_supports": Standing.PARTIAL,
        "does_not_support": Standing.UNSUPPORTED,
        "contradicts": Standing.CONTRADICTED,
    }.get(verdict, Standing.ASSUMPTION)


def established(items: list[EvidenceItem]) -> list[EvidenceItem]:
    return [i for i in items if i.standing is Standing.ESTABLISHED]


# --- model calls ----------------------------------------------------------------


def load_prompt(name: str, **values: object) -> str:
    text = (PROMPTS_DIR / f"{name}.md").read_text(encoding="utf-8").strip()
    return text.format(**values) if values else text


class ExtractedClaim(BaseModel):
    type: ClaimType
    claim: str
    passages: list[int] = Field(min_length=1, max_length=3)


class ExtractionOutput(BaseModel):
    claims: list[ExtractedClaim] = Field(max_length=5)


class AssessmentOutput(BaseModel):
    # Field order matters: the model writes its reasoning before choosing a label.
    reason: str
    limitations: str
    verdict: Verdict


class ConfirmOutput(BaseModel):
    problems: str
    fully_supported: bool


def extract_claims(
    client: OllamaClient,
    model: str,
    source: str,
    *,
    topic: str,
    source_url: str | None = None,
    max_passages: int | None = None,
    max_claims: int = 5,
    num_predict: int = 400,
    breaks: frozenset[int] = frozenset(),
    url_at: Callable[[int], str] | None = None,
    exclude: frozenset[int] = frozenset(),
) -> tuple[list[EvidenceItem], LLMResult]:
    """Ask the model which passages carry claims; Python builds the quotes.

    Passages in `exclude` (for example headers the application wrote itself) are
    never shown, so they can never be quoted as evidence.
    """
    passages = split_passages(source)
    candidates = [p for p in passages if p.id not in exclude]
    shown = rank_passages(candidates, topic, max_passages) if max_passages else candidates
    messages = [
        {"role": "system", "content": load_prompt("investigator_extract", max_claims=max_claims)},
        {"role": "user", "content": f"TOPIC: {topic}\n\nPASSAGES:\n{numbered(shown)}"},
    ]
    result = client.chat_json(model, messages, ExtractionOutput, num_predict=num_predict)
    shown_ids = {p.id for p in shown}
    items = []
    for c in result.parsed.claims[:max_claims]:
        if not set(c.passages) <= shown_ids:
            quotes = [_unverified(source_url, "", f"passage not shown to the model: {c.passages}")]
        else:
            quotes = quotes_from_passages(source, passages, c.passages, source_url, breaks=breaks, url_at=url_at)
        items.append(EvidenceItem(claim=c.claim, claim_type=c.type, quotes=quotes))
    return items, result


def context_for(source: str, quotes: list[Quote], window: int = 1, exclude: frozenset[int] = frozenset()) -> str:
    """The quoted passages plus `window` neighbouring passages on each side.

    Passages in `exclude` (text the application wrote, such as comment headers) are
    left out, so they can neither inform the assessment nor satisfy the wording check.
    """
    if not quotes or not all(q.verified for q in quotes):
        return ""
    passages = split_passages(source)
    spans: list[tuple[int, int]] = []
    for q in quotes:
        inside = [p.id for p in passages if p.start < q.end and p.end > q.start]
        lo, hi = max(1, inside[0] - window), min(len(passages), inside[-1] + window)
        run: list[int] = []
        for pid in [*range(lo, hi + 1), None]:  # split the window around excluded passages
            if pid is not None and pid not in exclude:
                run.append(pid)
                continue
            if run:
                spans.append((passages[run[0] - 1].start, passages[run[-1] - 1].end))
            run = []
    merged: list[list[int]] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return "\n...\n".join(source[s:e] for s, e in merged)


def _quote_block(quotes: list[str]) -> str:
    return "\n".join(f"- {q}" for q in quotes)


def assess_messages(claim: str, quotes: list[str], context: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": load_prompt("investigator_assess")},
        {"role": "user", "content": f"CLAIM: {claim}\nQUOTES:\n{_quote_block(quotes)}\nCONTEXT: {context}"},
    ]


# Output caps are safety limits against runaway output, not length targets: the
# prompts ask for short answers, and a verbose model must not be cut off mid-JSON.
def assess(
    client: OllamaClient, model: str, claim: str, quotes: list[str], context: str, *, num_predict: int = 320
) -> tuple[AssessmentOutput, LLMResult]:
    result = client.chat_json(model, assess_messages(claim, quotes, context), AssessmentOutput, num_predict=num_predict)
    return result.parsed, result


def confirm_support(
    client: OllamaClient, model: str, claim: str, quotes: list[str], context: str, *, num_predict: int = 240
) -> tuple[ConfirmOutput, LLMResult]:
    """Second, sceptical check, run only when the first assessment says `supports`."""
    messages = [
        {"role": "system", "content": load_prompt("investigator_confirm")},
        {"role": "user", "content": f"CLAIM: {claim}\nQUOTES:\n{_quote_block(quotes)}\nCONTEXT: {context}"},
    ]
    result = client.chat_json(model, messages, ConfirmOutput, num_predict=num_predict)
    return result.parsed, result


def evaluate(
    client: OllamaClient, model: str, claim: str, quotes: list[str], context: str, *, confirm: bool = True
) -> tuple[AssessmentOutput, ConfirmOutput | None, list[LLMResult]]:
    """Assessment plus, for `supports` only (and if `confirm`), the confirmation check."""
    answer, res = assess(client, model, claim, quotes, context)
    results = [res]
    check = None
    if answer.verdict == "supports" and confirm:
        check, res2 = confirm_support(client, model, claim, quotes, context)
        results.append(res2)
    return answer, check, results


_CONTRADICTION_WORDING = re.compile(r"\bcontradict", re.IGNORECASE)


def assess_item(
    client: OllamaClient, model: str, item: EvidenceItem, source: str, *, economical: bool = False,
    assess_unpromotable: bool = True, exclude: frozenset[int] = frozenset(),
) -> list[LLMResult]:
    """Fill in an item's verdict. Items without verified quotes are not sent to the model.

    If the model fails (unreachable, or no valid JSON after a retry), the item
    stays unassessed, which keeps it an assumption, and the failure is noted.

    Economical mode skips model calls whose answer cannot change the standing.
    It never makes a claim easier to establish:
    - the second check is skipped when the deterministic checks already rule
      out ESTABLISHED (demand claims, wording beyond the quote, no attribution);
    - with `assess_unpromotable=False`, such a claim is not assessed at all and
      stays NEEDS_REVIEW with its verified quote.
    """
    if not item.verified:
        item.notes.append("not assessed: quotation not verified")
        return []
    texts = [q.text for q in item.quotes]
    context = context_for(source, item.quotes, exclude=exclude)
    item.unsourced = unsourced_words(item.claim, context)
    if item.unsourced:
        item.review.append("wording goes beyond the quoted text: " + ", ".join(item.unsourced))
    item.attributed = attributed_to_one_person(item.claim, item.claim_type)
    if not item.attributed:
        item.review.append("a claim about people must be attributed to one person (\"One host says ...\")")
    if economical and not item.can_be_established and not assess_unpromotable:
        item.not_assessed = True
        item.notes.append("not sent to the model: the wording or attribution checks already rule out "
                          "establishing it")
        return []
    confirm = not economical or item.can_be_established
    try:
        answer, check, results = evaluate(client, model, item.claim, texts, context, confirm=confirm)
    except LLMError as exc:
        item.notes.append(f"assessment failed: {exc}")
        return []
    item.verdict, item.reason, item.limitations = answer.verdict, answer.reason, answer.limitations
    if answer.verdict != "contradicts" and _CONTRADICTION_WORDING.search(answer.reason):
        # Not overridden, since the reason may say "does not contradict". Flagged instead.
        item.review.append(f"verdict is {answer.verdict} but the reason mentions a contradiction")
    if check is not None:
        item.confirmed, item.confirm_note = check.fully_supported, check.problems
    elif answer.verdict == "supports" and not confirm:
        item.notes.append("second check skipped: this claim cannot be established whatever it says")
    return results
