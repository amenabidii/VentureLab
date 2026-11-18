"""Phase 3 working MVP for one supported product type: a thread digest.

Supported scope (checked by `supported()`): ideas whose core job is to summarise a long
discussion (chat threads, issue threads, comment threads) and link every point back to its
source. For those ideas VentureLab ships this small, working, local tool instead of a
placeholder: the user pastes a thread, and the tool returns the decisions, open questions
and action items, each linked to the exact message it came from, plus who took part.

Deliberately simple and honest:
- deterministic fixed rules, no model, nothing leaves the machine, nothing is stored;
- every output line quotes its source message number, so it can be checked;
- it extracts and links; it never invents content or rewrites what people said.
Ideas outside this scope are labelled UNSUPPORTED: they get the clickable prototype only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from html import escape

SUPPORTED_TYPE = "thread digest: summarise a long discussion and link each point to its source message"
MAX_CHARS = 20_000
MAX_MESSAGES = 400

_SCOPE_THREAD = re.compile(r"\b(?:threads?|messages?|chats?|discussions?|conversations?|comments?|channels?|"
                           r"issues?|slack|discord|teams|forum)\b", re.I)
_SCOPE_JOB = re.compile(r"\b(?:summar\w*|digest\w*|recap\w*|catch(?:ing)? up|tl;?dr|missed)\b", re.I)

# "author: text" or "[time] author: text"; anything else continues the previous message.
_LINE = re.compile(r"^\s*(?:\[[^\]]{1,40}\]\s*)?(?P<author>[\w.@' -]{1,40}?)\s*:\s+(?P<text>.+)$")
_DECISION = re.compile(r"\b(?:decided|decision|we(?:'ll| will) go with|let'?s go with|agreed|we agree|"
                       r"approved|final(?:ly)?[, ]+we|going with|settled on|ship it)\b", re.I)
_ACTION = re.compile(r"\b(?:i'?ll|i will|todo|to-do|action item|can you|could you|please|will do|"
                     r"assign(?:ed)? to|by (?:monday|tuesday|wednesday|thursday|friday|tomorrow|eod|end of day))\b",
                     re.I)


_OTHER_MEDIA = re.compile(r"\b(?:games?|gaming|video\w*|voice|audio|podcasts?|music|courses?|streams?|"
                          r"streaming|images?|photos?|hardware)\b", re.I)


def supported(idea: str) -> bool:
    """True when the founder's idea is in the one product type this MVP implements.

    The summarising word and the discussion word must be close together ("summarises long Slack
    threads", "digest of long GitHub issue discussions"), and ideas about other media are excluded,
    so "a game where players catch up on chapters told through chat" is not a thread digest.
    """
    if _OTHER_MEDIA.search(idea):
        return False
    words = re.findall(r"[\w;']+", idea)
    jobs = [i for i, w in enumerate(words) if _SCOPE_JOB.fullmatch(w) or _SCOPE_JOB.match(w)]
    things = [i for i, w in enumerate(words) if _SCOPE_THREAD.fullmatch(w)]
    return any(abs(j - t) <= 6 for j in jobs for t in things)


@dataclass
class Message:
    n: int
    author: str
    text: str


@dataclass
class Digest:
    messages: list[Message]
    decisions: list[Message] = field(default_factory=list)
    questions: list[Message] = field(default_factory=list)
    actions: list[Message] = field(default_factory=list)

    @property
    def participants(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for m in self.messages:
            counts[m.author] = counts.get(m.author, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))

    def to_dict(self) -> dict:
        item = lambda m: {"message": m.n, "author": m.author, "text": m.text}  # noqa: E731
        return {"messages": len(self.messages), "participants": self.participants,
                "decisions": [item(m) for m in self.decisions], "open_questions": [item(m) for m in self.questions],
                "action_items": [item(m) for m in self.actions]}


def parse(thread: str) -> list[Message]:
    if len(thread) > MAX_CHARS:
        raise ValueError(f"The thread is longer than {MAX_CHARS} characters; paste a shorter part")
    messages: list[Message] = []
    for raw in thread.splitlines():
        line = raw.strip()
        if not line:
            continue
        m = _LINE.match(line)
        if m:
            messages.append(Message(len(messages) + 1, m["author"].strip(), m["text"].strip()))
        elif messages:
            messages[-1].text += "\n" + line
        else:
            messages.append(Message(1, "unknown", line))
        if len(messages) > MAX_MESSAGES:
            raise ValueError(f"More than {MAX_MESSAGES} messages; paste a shorter part")
    return messages


def digest(thread: str) -> Digest:
    msgs = parse(thread)
    d = Digest(msgs)
    for m in msgs:
        # These are candidates, not semantic conclusions. Negation and questions
        # must not silently become settled decisions.
        negated = re.search(r"\b(?:not|never|haven't|hasn't|isn't|wasn't|no)\b", m.text, re.I)
        if _DECISION.search(m.text) and "?" not in m.text and not negated:
            d.decisions.append(m)
        if _ACTION.search(m.text) and not m.text.rstrip().endswith("?"):
            d.actions.append(m)
        if "?" in m.text:
            # A later decision cannot prove that this particular question was answered.
            d.questions.append(m)
    return d


def render_html(d: Digest) -> str:
    e = escape

    def items(ms: list[Message], empty: str) -> str:
        if not ms:
            return f"<p class='muted'>{e(empty)}</p>"
        return "<ul>" + "".join(f"<li><a href='#m{m.n}'>#{m.n}</a> <b>{e(m.author)}</b>: {e(m.text)}</li>"
                                for m in ms) + "</ul>"

    people = ", ".join(f"{e(a)} ({n})" for a, n in d.participants.items()) or "none"
    source = "".join(f"<li id='m{m.n}'><b>#{m.n} {e(m.author)}</b>: {e(m.text)}</li>" for m in d.messages)
    return (f"<section id='digest' aria-labelledby='digest-title'><div class='result-head'><div><span class='eyebrow'>YOUR THREAD, ORGANIZED</span>"
            f"<h2 id='digest-title'>The catch-up brief.</h2></div><a class='text-link' href='#source-thread'>Inspect original messages ↓</a></div>"
            f"<div class='metrics'><div><strong>{len(d.messages)}</strong><span>messages read</span></div>"
            f"<div><strong>{len(d.decisions)}</strong><span>decision candidates</span></div>"
            f"<div><strong>{len(d.actions)}</strong><span>action candidates</span></div>"
            f"<div><strong>{len(d.questions)}</strong><span>questions to review</span></div></div>"
            f"<p class='notice'>A working extraction tool, not a launch decision. Fixed rules identify candidates; "
            f"they cannot verify intent, completion or whether a question was answered. Review every important point.</p>"
            f"<div class='digest-grid'><article class='result-card'><span class='eyebrow'>01 / ALIGN</span><h2>Decisions</h2>"
            f"<p class='muted'>Candidate decision language, quoted from the thread.</p>{items(d.decisions, 'No decision candidate found.')}</article>"
            f"<article class='result-card'><span class='eyebrow'>02 / FOLLOW THROUGH</span><h2>Action items</h2>"
            f"<p class='muted'>Requests and commitments. The speaker is not necessarily the owner.</p>{items(d.actions, 'No action candidate found.')}</article>"
            f"<article class='result-card full'><span class='eyebrow'>03 / KEEP VISIBLE</span><h2>Questions to review</h2>"
            f"<p class='muted'>All detected questions stay visible. A later decision never silently closes an unrelated question.</p>"
            f"{items(d.questions, 'No question mark found in this thread.')}</article></div>"
            f"<section id='source-thread'><h2>Original thread</h2><p class='muted'>{len(d.messages)} messages · {people}</p>"
            f"<ol class='src'>{source}</ol></section></section>")


def render_markdown(d: Digest) -> str:
    """Portable local output; no network, persistence or invented attribution."""
    lines = ["# Thread digest", "", "Fixed-rule candidates; verify against the source messages below.",
             "Questions are not automatically marked answered. Speakers are not inferred task owners.", ""]
    for title, messages in [("Decision candidates", d.decisions), ("Action candidates", d.actions),
                            ("Questions to review", d.questions), ("Source messages", d.messages)]:
        lines += ["## " + title, ""]
        if not messages:
            lines.append("None detected.")
        for m in messages:
            # A variable-length fence keeps raw HTML, links and embedded backticks
            # literal in Markdown viewers instead of activating source content.
            text = m.author + ": " + m.text
            fence = "`" * max(3, 1 + max((len(x) for x in re.findall(r"`+", text)), default=0))
            lines += [f"Message #{m.n}", fence + "text", text, fence, ""]
        lines.append("")
    return "\n".join(lines)
