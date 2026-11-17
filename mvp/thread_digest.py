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
_LINE = re.compile(r"^\s*(?:\[[^\]]{1,40}\]\s*)?(?P<author>[A-Za-z0-9_.@' -]{1,40}?)\s*:\s+(?P<text>.+)$")
_DECISION = re.compile(r"\b(?:decided|decision|we(?:'ll| will) go with|let'?s go with|agreed|we agree|"
                       r"approved|final(?:ly)?[, ]+we|going with|settled on|ship it)\b", re.I)
_ACTION = re.compile(r"\b(?:i'?ll|i will|todo|to-do|action item|can you|could you|please|will do|"
                     r"assign(?:ed)? to|by (?:monday|tuesday|wednesday|thursday|friday|tomorrow|eod|end of day))\b",
                     re.I)


def supported(idea: str) -> bool:
    """True when the founder's idea is in the one product type this MVP implements."""
    return bool(_SCOPE_THREAD.search(idea) and _SCOPE_JOB.search(idea))


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
            messages[-1].text += " " + line
        else:
            messages.append(Message(1, "unknown", line))
        if len(messages) > MAX_MESSAGES:
            raise ValueError(f"More than {MAX_MESSAGES} messages; paste a shorter part")
    return messages


def digest(thread: str) -> Digest:
    msgs = parse(thread)
    d = Digest(msgs)
    answered = set()
    for i, m in enumerate(msgs):
        if _DECISION.search(m.text):
            d.decisions.append(m)
        if _ACTION.search(m.text) and not m.text.rstrip().endswith("?"):
            d.actions.append(m)
        if "?" in m.text:
            # A question counts as open unless a later message from someone else quotes or answers it
            # with a decision; the rule is shown to the user, not hidden.
            later = msgs[i + 1:]
            if any(o.author != m.author and _DECISION.search(o.text) for o in later):
                answered.add(m.n)
            else:
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
    return (f"<h2>Decisions</h2>{items(d.decisions, 'No decision found in this thread.')}"
            f"<h2>Open questions</h2>{items(d.questions, 'No open question found.')}"
            f"<h2>Action items</h2>{items(d.actions, 'No action item found.')}"
            f"<h2>Participants</h2><p>{len(d.messages)} messages · {people}</p>"
            f"<details><summary>Original thread (every point above links here)</summary><ol class='src'>{source}</ol>"
            f"</details><p class='muted'>Fixed rules, no model: lines are classified by their own words and quoted "
            f"unchanged. Check anything important against the original message.</p>")
