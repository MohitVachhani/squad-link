"""Graph-derived state loaded once at startup and shared by all requests, plus graph -> API model presenters."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from ..engine import ClubIndex, Graph, Hop, PlayerIndex, PuzzleSource
from .schemas import ClubOut, ClubRef, HopOut, PlayerOut


@dataclass
class GameContext:
    graph: Graph
    players: PlayerIndex
    clubs: ClubIndex
    puzzles: PuzzleSource

    @property
    def graph_version(self) -> int:
        return int(self.graph.meta.get("graph_version", 0))

    def club_ref(self, club_id: int) -> ClubRef:
        return ClubRef(id=club_id, name=self.graph.clubs[club_id].name)

    def club_out(self, club_id: int) -> ClubOut:
        c = self.graph.clubs[club_id]
        return ClubOut(id=c.id, name=c.name, league=c.league, aliases=list(c.aliases))

    def player_out(self, player_id: int) -> PlayerOut:
        g = self.graph
        p = g.players[player_id]
        latest = g.latest_squad(player_id)
        return PlayerOut(
            id=p.id, name=p.name, full=p.full, nation=p.nation, dob=p.dob, ovr=p.ovr,
            latest_club=self.club_ref(latest[0]) if latest else None,
            latest_season=latest[1] if latest else None,
            first_season=g.first_season(player_id),
        )

    def hop_out(self, hop: Hop) -> HopOut:
        return HopOut(
            from_id=hop.from_id, to=self.player_out(hop.to_id), club=self.club_ref(hop.club_id),
            seasons=list(hop.seasons), rarity=round(hop.rarity, 4),
        )


def get_ctx(request: Request) -> GameContext:
    return request.app.state.ctx
