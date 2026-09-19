"""Puzzle generation. PuzzleSource is the extension point: a DailyPuzzleSource would seed its RNG from the date."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Protocol

from .graph import Graph


@dataclass(frozen=True, slots=True)
class Puzzle:
    start_id: int
    end_id: int
    optimal_hops: int
    optimal_path: tuple[int, ...]


class PuzzleSource(Protocol):
    def next(self) -> Puzzle: ...


class RandomPuzzleSource:
    """Picks two recognisable players whose BFS distance is in [min_hops, max_hops].

    "Recognisable" = peak overall >= min_ovr: 85 gives ~240 players on the default graph; 80 lets in ~1,100,
    many of them journeymen.
    """

    def __init__(
        self,
        graph: Graph,
        *,
        min_hops: int = 3,
        max_hops: int = 5,
        min_ovr: int = 85,
        rng: random.Random | None = None,
        max_tries: int = 200,
    ):
        if min_hops < 1 or max_hops < min_hops:
            raise ValueError("need 1 <= min_hops <= max_hops")
        self.graph = graph
        self.min_hops, self.max_hops = min_hops, max_hops
        self.rng = rng or random.Random()
        self.max_tries = max_tries
        largest = graph.components()[0] if graph.player_squads else set()
        pool = sorted(pid for pid in largest if (graph.players[pid].ovr or 0) >= min_ovr)
        self.pool = pool if len(pool) >= 2 else sorted(largest)

    def next(self) -> Puzzle:
        pool_set = set(self.pool)
        for _ in range(self.max_tries):
            start = self.rng.choice(self.pool)
            dist = self.graph.distances_from(start)
            candidates = sorted(
                pid for pid, d in dist.items() if self.min_hops <= d <= self.max_hops and pid in pool_set
            )
            if candidates:
                end = self.rng.choice(candidates)
                path = self.graph.shortest_path(start, end)
                assert path is not None
                return Puzzle(start, end, len(path) - 1, tuple(path))
        raise RuntimeError(
            f"no pair at distance {self.min_hops}-{self.max_hops} after {self.max_tries} tries; loosen filters"
        )
