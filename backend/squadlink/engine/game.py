"""Game rules. Stateless: a game is (start, end, hops); the API persists hops and rebuilds GameState.

This module knows nothing about users, puzzles kinds, or storage, so daily puzzles / multiplayer can reuse it.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

from .graph import Graph
from .scoring import link_rarity


class Status(StrEnum):
    IN_PROGRESS = "in_progress"
    WON = "won"
    ABANDONED = "abandoned"


class MoveErrorCode(StrEnum):
    GAME_OVER = "GAME_OVER"
    UNKNOWN_PLAYER = "UNKNOWN_PLAYER"
    UNKNOWN_CLUB = "UNKNOWN_CLUB"
    SAME_PLAYER = "SAME_PLAYER"
    ALREADY_IN_CHAIN = "ALREADY_IN_CHAIN"
    SAME_CLUB_TWICE = "SAME_CLUB_TWICE"
    CURRENT_NOT_AT_CLUB = "CURRENT_NOT_AT_CLUB"
    NEXT_NOT_AT_CLUB = "NEXT_NOT_AT_CLUB"
    DIFFERENT_SEASONS = "DIFFERENT_SEASONS"
    NO_SUCH_HOP = "NO_SUCH_HOP"


class MoveError(Exception):
    def __init__(self, code: MoveErrorCode, message: str, **details):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


@dataclass(frozen=True, slots=True)
class Hop:
    from_id: int
    to_id: int
    club_id: int
    seasons: tuple[str, ...]
    rarity: float


@dataclass(frozen=True, slots=True)
class GameState:
    start_id: int
    end_id: int
    hops: tuple[Hop, ...] = field(default_factory=tuple)
    status: Status = Status.IN_PROGRESS

    @property
    def current_id(self) -> int:
        return self.hops[-1].to_id if self.hops else self.start_id

    @property
    def chain(self) -> list[int]:
        return [self.start_id, *(h.to_id for h in self.hops)]

    @property
    def last_club_id(self) -> int | None:
        return self.hops[-1].club_id if self.hops else None


def _span(seasons: list[str]) -> str:
    return seasons[0] if len(seasons) == 1 else f"{seasons[0]}–{seasons[-1]}"


def validate_move(graph: Graph, state: GameState, next_id: int, club_id: int) -> Hop:
    """Return the Hop this move would add, or raise MoveError with a user-facing message."""
    if state.status is not Status.IN_PROGRESS:
        raise MoveError(MoveErrorCode.GAME_OVER, "This game is already finished.")
    if next_id not in graph.players:
        raise MoveError(MoveErrorCode.UNKNOWN_PLAYER, "That player isn't in our dataset.")
    if club_id not in graph.clubs:
        raise MoveError(MoveErrorCode.UNKNOWN_CLUB, "That club isn't in our dataset.")

    cur = state.current_id
    cur_p, next_p, club = graph.players[cur], graph.players[next_id], graph.clubs[club_id]

    if next_id == cur:
        raise MoveError(MoveErrorCode.SAME_PLAYER, f"You're already on {cur_p.name}.")
    if next_id in state.chain:
        raise MoveError(MoveErrorCode.ALREADY_IN_CHAIN, f"{next_p.name} is already in your chain.")
    if club_id == state.last_club_id:
        raise MoveError(
            MoveErrorCode.SAME_CLUB_TWICE,
            f"You just used {club.name} — pick a different club for this link.",
        )

    cur_seasons = graph.seasons_at(cur, club_id)
    next_seasons = graph.seasons_at(next_id, club_id)
    if not cur_seasons:
        raise MoveError(
            MoveErrorCode.CURRENT_NOT_AT_CLUB,
            f"{cur_p.name} never played for {club.name} (in our data).",
        )
    if not next_seasons:
        raise MoveError(
            MoveErrorCode.NEXT_NOT_AT_CLUB,
            f"{next_p.name} never played for {club.name} (in our data).",
        )
    shared = sorted(set(cur_seasons) & set(next_seasons))
    if not shared:
        raise MoveError(
            MoveErrorCode.DIFFERENT_SEASONS,
            f"Both played for {club.name}, but not in the same season "
            f"({cur_p.name}: {_span(cur_seasons)}, {next_p.name}: {_span(next_seasons)}).",
            current_seasons=cur_seasons,
            next_seasons=next_seasons,
        )

    return Hop(cur, next_id, club_id, tuple(shared), link_rarity(graph, club_id, shared))


def apply_move(graph: Graph, state: GameState, next_id: int, club_id: int) -> GameState:
    hop = validate_move(graph, state, next_id, club_id)
    status = Status.WON if next_id == state.end_id else Status.IN_PROGRESS
    return replace(state, hops=(*state.hops, hop), status=status)


def truncate(state: GameState, keep: int) -> GameState:
    """Remove hop `keep` and every hop after it (a chain only makes sense in order, so a middle hop can't be
    removed on its own). Editing a hop = truncate, then apply_move with the corrected player/club."""
    if state.status is not Status.IN_PROGRESS:
        raise MoveError(MoveErrorCode.GAME_OVER, "This game is already finished.")
    if not 0 <= keep < len(state.hops):
        raise MoveError(MoveErrorCode.NO_SUCH_HOP, "There's no such link in your chain.")
    return replace(state, hops=state.hops[:keep])


def give_up(state: GameState) -> GameState:
    if state.status is not Status.IN_PROGRESS:
        raise MoveError(MoveErrorCode.GAME_OVER, "This game is already finished.")
    return replace(state, status=Status.ABANDONED)


def optimal_hops(graph: Graph, start_id: int, end_id: int) -> list[Hop] | None:
    """BFS path with a club chosen for each link, for the results screen.

    BFS ignores the club rule, but when choosing clubs we still avoid repeating the previous one where
    possible, and otherwise prefer the rarest squad.
    """
    path = graph.shortest_path(start_id, end_id)
    if path is None:
        return None
    hops: list[Hop] = []
    prev_club: int | None = None
    for a, b in zip(path, path[1:]):
        by_club: dict[int, list[str]] = {}
        for cid, season in graph.shared_squads(a, b):
            by_club.setdefault(cid, []).append(season)
        options = sorted(
            by_club.items(),
            key=lambda kv: (kv[0] == prev_club, -link_rarity(graph, kv[0], kv[1]), kv[0]),
        )
        cid, seasons = options[0]
        seasons = sorted(seasons)
        hops.append(Hop(a, b, cid, tuple(seasons), link_rarity(graph, cid, seasons)))
        prev_club = cid
    return hops
