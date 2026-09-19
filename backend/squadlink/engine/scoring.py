"""Scoring: 70% efficiency (optimal / hops) + 30% average link rarity."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .graph import Graph

EFFICIENCY_WEIGHT = 0.7
RARITY_WEIGHT = 0.3


def rarity_for_size(size: int, max_size: int) -> float:
    """1 - log(size)/log(max_size), clamped to [0, 1]. Squads of 1 can't form links, so min real size is 2."""
    if max_size <= 1 or size <= 1:
        return 1.0 if max_size > 1 else 0.0
    return max(0.0, min(1.0, 1 - math.log(size) / math.log(max_size)))


def link_rarity(graph: Graph, club_id: int, seasons: Iterable[str]) -> float:
    """Rarity of a link through club_id. If the pair shared several seasons, the rarest (smallest) squad counts.

    Squad size = players from that (club, season) in the filtered graph, so a Cádiz squad with 3 rated players
    is rarer than a Real Madrid squad with 25.
    """
    sizes = [graph.squad_size(club_id, s) for s in seasons]
    if not sizes:
        return 0.0
    return rarity_for_size(min(sizes), graph.max_squad_size)


@dataclass(frozen=True, slots=True)
class ScoreBreakdown:
    hops: int
    optimal_hops: int
    efficiency: float  # 0..1
    rarity: float  # 0..1, mean over the user's links
    efficiency_points: float  # 0..70
    rarity_points: float  # 0..30
    total: float  # 0..100


def score(hops: int, optimal: int, rarities: Sequence[float]) -> ScoreBreakdown:
    """Score a finished chain. A chain that didn't reach the target should not be scored."""
    if hops <= 0:
        raise ValueError("cannot score a chain with no hops")
    efficiency = min(1.0, optimal / hops)
    rarity = sum(rarities) / len(rarities) if rarities else 0.0
    eff_pts = 100 * EFFICIENCY_WEIGHT * efficiency
    rar_pts = 100 * RARITY_WEIGHT * rarity
    return ScoreBreakdown(
        hops=hops,
        optimal_hops=optimal,
        efficiency=round(efficiency, 4),
        rarity=round(rarity, 4),
        efficiency_points=round(eff_pts, 1),
        rarity_points=round(rar_pts, 1),
        total=round(eff_pts + rar_pts, 1),
    )


def rarity_emoji(r: float) -> str:
    if r >= 0.6:
        return "🟪"
    if r >= 0.3:
        return "🟩"
    return "🟨"


def share_text(
    start_name: str,
    end_name: str,
    rarities: Sequence[float],
    breakdown: ScoreBreakdown,
    season_range: str,
    label: str = "Squadlink",
) -> str:
    """Wordle-style result. Names only the endpoints, never the path, so it doesn't spoil the puzzle.

    `label` lets a daily puzzle pass e.g. 'Squadlink #42'.
    """
    squares = "".join(rarity_emoji(r) for r in rarities)
    extra = breakdown.hops - breakdown.optimal_hops
    par = "par" if extra <= 0 else f"+{extra}"
    return "\n".join([
        f"{label} ⚽ {start_name} → {end_name}",
        f"{breakdown.hops} hops (best {breakdown.optimal_hops}, {par}) · {breakdown.total:.1f}/100",
        squares,
        f"Efficiency {breakdown.efficiency_points:.1f}/70 · Rarity {breakdown.rarity_points:.1f}/30",
        f"Data: {season_range}",
    ])
