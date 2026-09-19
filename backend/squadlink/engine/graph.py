"""Player graph loaded from graph.json.

Players are linked when they share a squad: the same club (club_team_id) in the same season. Internally
the graph is bipartite (player <-> squad), so we never materialise the player-player edge list; BFS walks
player -> squad -> player and marks squads as expanded, which gives the same distances.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

Squad = tuple[int, str]  # (club_id, season)


@dataclass(frozen=True, slots=True)
class Player:
    id: int
    name: str
    full: str
    nation: str
    dob: str | None
    ovr: int | None


@dataclass(frozen=True, slots=True)
class Club:
    id: int
    name: str
    league: str
    aliases: tuple[str, ...] = ()  # older names of the same club_team_id


class Graph:
    def __init__(self, data: dict):
        self.meta: dict = data["meta"]
        self.players: dict[int, Player] = {
            int(pid): Player(int(pid), p["name"], p["full"], p["nation"], p.get("dob"), p.get("ovr"))
            for pid, p in data["players"].items()
        }
        self.clubs: dict[int, Club] = {
            int(cid): Club(int(cid), c["name"], c["league"], tuple(c.get("aliases", ())))
            for cid, c in data["clubs"].items()
        }

        squads: dict[Squad, list[int]] = defaultdict(list)
        player_squads: dict[int, list[Squad]] = defaultdict(list)
        for pid, cid, season in data["memberships"]:
            squads[(cid, season)].append(pid)
            player_squads[pid].append((cid, season))
        # Sorted so BFS (and therefore "the" optimal path) is deterministic.
        self.squads: dict[Squad, tuple[int, ...]] = {k: tuple(sorted(v)) for k, v in squads.items()}
        self.player_squads: dict[int, tuple[Squad, ...]] = {
            pid: tuple(sorted(v, key=lambda s: (s[1], s[0]))) for pid, v in player_squads.items()
        }
        self.seasons: list[str] = sorted({s for _, s in self.squads})
        self.max_squad_size: int = max((len(m) for m in self.squads.values()), default=0)

    @classmethod
    def load(cls, path: str | Path) -> Graph:
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f))

    # --- queries -----------------------------------------------------------------------------------

    @property
    def season_range(self) -> str:
        """Human label for the data range, e.g. '2014/15–2023/24'."""
        if not self.seasons:
            return ""
        return f"{self.seasons[0]}–{self.seasons[-1]}"

    def squad_size(self, club_id: int, season: str) -> int:
        return len(self.squads.get((club_id, season), ()))

    def seasons_at(self, player_id: int, club_id: int) -> list[str]:
        return [s for c, s in self.player_squads.get(player_id, ()) if c == club_id]

    def shared_seasons(self, a: int, b: int, club_id: int) -> list[str]:
        """Seasons in which a and b were both in club_id's squad (sorted)."""
        return sorted(set(self.seasons_at(a, club_id)) & set(self.seasons_at(b, club_id)))

    def shared_squads(self, a: int, b: int) -> list[Squad]:
        sa = set(self.player_squads.get(a, ()))
        return [sq for sq in self.player_squads.get(b, ()) if sq in sa]

    def are_teammates(self, a: int, b: int) -> bool:
        return a != b and bool(self.shared_squads(a, b))

    def neighbors(self, player_id: int) -> set[int]:
        out: set[int] = set()
        for sq in self.player_squads.get(player_id, ()):
            out.update(self.squads[sq])
        out.discard(player_id)
        return out

    def latest_squad(self, player_id: int) -> Squad | None:
        squads = self.player_squads.get(player_id)
        return squads[-1] if squads else None

    def first_season(self, player_id: int) -> str | None:
        squads = self.player_squads.get(player_id)
        return squads[0][1] if squads else None

    # --- search ------------------------------------------------------------------------------------

    def distances_from(self, source: int) -> dict[int, int]:
        dist, _ = self._bfs(source, None)
        return dist

    def shortest_path(self, source: int, target: int) -> list[int] | None:
        """Plain BFS on the player graph (ignores the no-same-club-twice rule, so it's a lower bound)."""
        if source not in self.player_squads or target not in self.player_squads:
            return None
        dist, parent = self._bfs(source, target)
        if target not in dist:
            return None
        path = [target]
        while path[-1] != source:
            path.append(parent[path[-1]])
        return path[::-1]

    def _bfs(self, source: int, target: int | None) -> tuple[dict[int, int], dict[int, int]]:
        dist = {source: 0}
        parent: dict[int, int] = {}
        expanded: set[Squad] = set()
        queue = deque([source])
        while queue:
            p = queue.popleft()
            if p == target:
                break
            for sq in self.player_squads.get(p, ()):
                if sq in expanded:
                    continue
                expanded.add(sq)
                for n in self.squads[sq]:
                    if n not in dist:
                        dist[n] = dist[p] + 1
                        parent[n] = p
                        queue.append(n)
        return dist, parent

    def components(self) -> list[set[int]]:
        """Connected components of the player graph, largest first."""
        seen: set[int] = set()
        comps: list[set[int]] = []
        for pid in sorted(self.player_squads):
            if pid in seen:
                continue
            comp = set(self.distances_from(pid))
            seen |= comp
            comps.append(comp)
        comps.sort(key=len, reverse=True)
        return comps
