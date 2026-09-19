"""Accent-insensitive name search for players and clubs.

Ranking: exact normalised match > prefix (of the whole name or of any word) > substring.
Within a tier, higher-rated players come first so the famous "Danilo" is on top, but an ambiguous
query is never auto-resolved: callers get `ambiguous=True` and must let the user pick.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .graph import Graph

# Letters that NFKD does not decompose into base + combining mark.
_SPECIAL = str.maketrans({
    "ø": "o", "Ø": "o", "æ": "ae", "Æ": "ae", "œ": "oe", "Œ": "oe", "ß": "ss",
    "ł": "l", "Ł": "l", "đ": "d", "Đ": "d", "ð": "d", "þ": "th", "ı": "i",
})
_SEPARATORS = re.compile(r"[\s\-_./]+")
_OTHER_PUNCT = re.compile(r"[^\w ]")

EXACT, PREFIX, SUBSTRING = 0, 1, 2


def normalize(text: str) -> str:
    """'N'Golo Kanté' -> 'ngolo kante'; 'Paris Saint-Germain' -> 'paris saint germain'."""
    text = unicodedata.normalize("NFKD", text.translate(_SPECIAL))
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    text = _SEPARATORS.sub(" ", text)
    text = _OTHER_PUNCT.sub("", text)
    return " ".join(text.split())


def _tier(query: str, name: str) -> int | None:
    if name == query:
        return EXACT
    if name.startswith(query) or any(word.startswith(query) for word in name.split()):
        return PREFIX
    if query in name:
        return SUBSTRING
    return None


@dataclass(frozen=True, slots=True)
class SearchResult:
    ids: list[int]
    ambiguous: bool  # more than one entity matched the best tier exactly


class _Index:
    """Maps normalised names -> entity ids. Each entity can have several names."""

    def __init__(self, names: dict[int, list[str]], popularity: dict[int, int]):
        self._entries = sorted(
            {(normalize(n), eid) for eid, ns in names.items() for n in ns if n and normalize(n)}
        )
        self._popularity = popularity

    def search(self, query: str, limit: int = 10) -> SearchResult:
        q = normalize(query)
        if not q:
            return SearchResult([], False)
        best: dict[int, int] = {}
        for name, eid in self._entries:
            t = _tier(q, name)
            if t is not None and t < best.get(eid, 99):
                best[eid] = t
        ranked = sorted(best, key=lambda eid: (best[eid], -self._popularity.get(eid, 0), eid))
        exact = [eid for eid in ranked if best[eid] == EXACT]
        return SearchResult(ranked[:limit], ambiguous=len(exact) > 1)


class PlayerIndex(_Index):
    def __init__(self, graph: Graph):
        super().__init__(
            {pid: [p.name, p.full] for pid, p in graph.players.items()},
            {pid: p.ovr or 0 for pid, p in graph.players.items()},
        )


class ClubIndex(_Index):
    def __init__(self, graph: Graph):
        # Bigger squads first in ties, so "Real Madrid" beats "Real Madrid Castilla" for "real".
        size = {cid: 0 for cid in graph.clubs}
        for (cid, _), members in graph.squads.items():
            size[cid] += len(members)
        names = {cid: [c.name, *c.aliases] for cid, c in graph.clubs.items()}
        super().__init__(names, size)
