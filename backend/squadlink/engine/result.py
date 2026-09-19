"""Everything the results screen needs, computed from a finished GameState."""

from __future__ import annotations

from dataclasses import dataclass

from .game import GameState, Hop, Status, optimal_hops
from .graph import Graph
from .scoring import ScoreBreakdown, score, share_text


@dataclass(frozen=True, slots=True)
class GameResult:
    status: Status
    user_hops: tuple[Hop, ...]
    optimal_hops: tuple[Hop, ...]
    score: ScoreBreakdown | None  # None if the user gave up
    share_text: str | None
    data_range: str  # "optimal" is only optimal within this range


def build_result(graph: Graph, state: GameState, label: str = "Squadlink") -> GameResult:
    if state.status is Status.IN_PROGRESS:
        raise ValueError("game is still in progress")
    best = tuple(optimal_hops(graph, state.start_id, state.end_id) or ())
    breakdown = text = None
    if state.status is Status.WON:
        rarities = [h.rarity for h in state.hops]
        breakdown = score(len(state.hops), len(best), rarities)
        text = share_text(
            graph.players[state.start_id].name,
            graph.players[state.end_id].name,
            rarities,
            breakdown,
            graph.season_range,
            label,
        )
    return GameResult(state.status, state.hops, best, breakdown, text, graph.season_range)
