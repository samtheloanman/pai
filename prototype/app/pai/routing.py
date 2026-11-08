"""Tiered request routing: rules (tier 1), embedding similarity (tier 2), decision model (tier 3)."""
import asyncio
import logging
import math
import re
from dataclasses import dataclass

log = logging.getLogger("pai.routing")

ROUTES = ("remember", "memory_query", "calendar", "email", "action", "chat")
EMBED_THRESHOLD = 0.55  # initial value; the route bench tunes it
MAX_CHARS = 4000

RULES = [
    (re.compile(r"^\s*remember(?: that)?[:,]?\s+\S", re.I), "remember"),
    (re.compile(r"^\s*(forget|delete)\s+memory\s+(\d+)", re.I), "action"),
]

# chat has no examples: it is the default when nothing else matches
EXAMPLES = {
    "memory_query": [
        "what did I tell you about my dentist",
        "do you remember when my rent is due",
        "what do you know about my sister",
        "look up what I saved about the garage code",
    ],
    "calendar": [
        "what's on my schedule tomorrow",
        "am I free on Thursday afternoon",
        "when is my next meeting",
        "what does my calendar look like this week",
        "find a time for lunch with Sam",
    ],
    "email": [
        "any new emails from my accountant",
        "summarise my unread email",
        "did the landlord reply to me",
        "check my inbox for the invoice",
    ],
    "action": [
        "send an email to Sam saying I'm running late",
        "book a table for four on Friday",
        "cancel my 3pm meeting",
        "delete all the old files in my downloads",
    ],
}

_example_vecs: tuple | None = None  # (embedder, [(route, vec)]) built once per embedder
_lock = asyncio.Lock()


@dataclass
class Route:
    name: str
    tier: int  # 1 rules, 2 embedding, 3 model
    score: float


def _cos(a, b) -> float:
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(x * x for x in b))
    return sum(x * y for x, y in zip(a, b)) / (na * nb) if na and nb else 0.0


async def _examples(embed):
    global _example_vecs
    if _example_vecs and _example_vecs[0] is embed:
        return _example_vecs[1]
    async with _lock:
        if not (_example_vecs and _example_vecs[0] is embed):
            vecs = [(r, await asyncio.to_thread(embed, s)) for r, ss in EXAMPLES.items() for s in ss]
            _example_vecs = (embed, vecs)
    return _example_vecs[1]


async def route(text: str, embed=None, decide=None) -> Route:
    text = text[:MAX_CHARS]
    for pat, name in RULES:
        if pat.match(text):
            return Route(name, 1, 1.0)
    if embed:
        try:
            ex = await _examples(embed)
            q = await asyncio.to_thread(embed, text)
            best = max(((_cos(q, v), r) for r, v in ex), default=(0.0, "chat"))
            if best[0] >= EMBED_THRESHOLD:
                return Route(best[1], 2, best[0])
        except Exception as e:  # model missing/offline: skip tier 2, never crash the request
            log.warning("embedding unavailable, skipping tier 2: %s", e)
    if decide:
        try:
            name, p = await decide(text)
            if name in ROUTES:
                return Route(name, 3, float(p))
        except Exception as e:
            log.warning("decision model failed, defaulting to chat: %s", e)
    return Route("chat", 3, 0.0)
