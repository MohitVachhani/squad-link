"""Game endpoints. The DB stores (puzzle, moves); each request rebuilds an engine GameState from them,
so the rules live only in squadlink.engine."""

from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_user
from ..db import Game, GameAttempt, GameMove, GameStatus, Puzzle, PuzzleKind, User, get_session
from ..engine import GameState, Hop, MoveError, MoveErrorCode, Status, apply_move, build_result, give_up, truncate
from ..engine.scoring import EFFICIENCY_WEIGHT, RARITY_WEIGHT
from .context import GameContext, get_ctx
from .schemas import GameOut, GameSummaryOut, MoveErrorOut, MoveIn, ResultOut, ScoreOut

router = APIRouter(prefix="/api/games", tags=["games"])


def to_state(game: Game) -> GameState:
    hops = tuple(Hop(m.from_player_id, m.to_player_id, m.club_id, tuple(m.seasons), m.rarity) for m in game.moves)
    return GameState(game.puzzle.start_player_id, game.puzzle.end_player_id, hops, Status(game.status.value))


def game_out(ctx: GameContext, game: Game) -> GameOut:
    state = to_state(game)
    return GameOut(
        id=game.id, status=game.status,
        start=ctx.player_out(state.start_id), end=ctx.player_out(state.end_id),
        current=ctx.player_out(state.current_id),
        hops=[ctx.hop_out(h) for h in state.hops],
        last_club_id=state.last_club_id, par=game.puzzle.optimal_hops,
        data_range=ctx.graph.season_range, started_at=game.started_at,
    )


async def load_game(session: AsyncSession, user: User, game_id: uuid.UUID, *, lock: bool = False) -> Game:
    q = select(Game).where(Game.id == game_id, Game.user_id == user.id)
    if lock:  # serialise concurrent moves on the same game (no-op on SQLite)
        q = q.with_for_update(of=Game)
    game = (await session.execute(q)).unique().scalar_one_or_none()
    if game is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Game not found")
    return game


async def reload(session: AsyncSession, game: Game) -> Game:
    await session.refresh(game, ["moves"])
    return game


@router.post("", response_model=GameOut, status_code=status.HTTP_201_CREATED)
async def new_game(
    ctx: GameContext = Depends(get_ctx), session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
):
    p = ctx.puzzles.next()
    puzzle = Puzzle(
        kind=PuzzleKind.RANDOM, start_player_id=p.start_id, end_player_id=p.end_id,
        optimal_hops=p.optimal_hops, optimal_path=list(p.optimal_path), graph_version=ctx.graph_version,
    )
    game = Game(user_id=user.id, puzzle=puzzle, moves=[])
    session.add(game)
    await session.commit()
    return game_out(ctx, game)


@router.get("", response_model=list[GameSummaryOut])
async def list_games(
    limit: int = 20, ctx: GameContext = Depends(get_ctx), session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
):
    q = select(Game).where(Game.user_id == user.id).order_by(Game.started_at.desc()).limit(min(limit, 100))
    games = (await session.execute(q)).unique().scalars().all()
    return [
        GameSummaryOut(
            id=g.id, status=g.status, start=ctx.player_out(g.puzzle.start_player_id),
            end=ctx.player_out(g.puzzle.end_player_id), hops=len(g.moves), par=g.puzzle.optimal_hops,
            score=g.score, started_at=g.started_at,
        )
        for g in games
    ]


@router.get("/{game_id}", response_model=GameOut)
async def get_game(
    game_id: uuid.UUID, ctx: GameContext = Depends(get_ctx), session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
):
    return game_out(ctx, await load_game(session, user, game_id))


@router.post(
    "/{game_id}/moves", response_model=GameOut,
    responses={422: {"model": MoveErrorOut, "description": "Move rejected by the rules"}},
)
async def make_move(
    game_id: uuid.UUID, move: MoveIn, ctx: GameContext = Depends(get_ctx),
    session: AsyncSession = Depends(get_session), user: User = Depends(current_user),
):
    game = await load_game(session, user, game_id, lock=True)
    state = to_state(game)
    try:
        new_state = apply_move(ctx.graph, state, move.player_id, move.club_id)
    except MoveError as e:
        session.add(GameAttempt(game_id=game.id, player_id=move.player_id, club_id=move.club_id,
                                error_code=e.code.value))
        await session.commit()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            MoveErrorOut(code=e.code.value, message=e.message, details=e.details).model_dump(),
        )

    hop = new_state.hops[-1]
    session.add(GameMove(
        game_id=game.id, idx=len(state.hops), from_player_id=hop.from_id, to_player_id=hop.to_id,
        club_id=hop.club_id, seasons=list(hop.seasons), rarity=hop.rarity,
    ))
    if new_state.status is Status.WON:
        result = build_result(ctx.graph, new_state)
        game.status = GameStatus.WON
        game.finished_at = datetime.now(timezone.utc)
        game.hops = result.score.hops
        game.efficiency = result.score.efficiency
        game.rarity = result.score.rarity
        game.score = result.score.total
    await session.commit()
    return game_out(ctx, await reload(session, game))


@router.delete("/{game_id}/moves/{idx}", response_model=GameOut)
async def remove_moves(
    game_id: uuid.UUID, idx: int, ctx: GameContext = Depends(get_ctx),
    session: AsyncSession = Depends(get_session), user: User = Depends(current_user),
):
    """Remove hop `idx` and every hop after it (undo last = idx of the last hop). Only while in progress."""
    game = await load_game(session, user, game_id, lock=True)
    try:
        truncate(to_state(game), idx)
    except MoveError as e:
        code = status.HTTP_404_NOT_FOUND if e.code is MoveErrorCode.NO_SUCH_HOP else status.HTTP_409_CONFLICT
        raise HTTPException(code, MoveErrorOut(code=e.code.value, message=e.message, details={}).model_dump())
    await session.execute(delete(GameMove).where(GameMove.game_id == game.id, GameMove.idx >= idx))
    await session.commit()
    return game_out(ctx, await reload(session, game))


@router.post("/{game_id}/give-up", response_model=GameOut)
async def give_up_game(
    game_id: uuid.UUID, ctx: GameContext = Depends(get_ctx), session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
):
    game = await load_game(session, user, game_id, lock=True)
    try:
        give_up(to_state(game))
    except MoveError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, e.message)
    game.status = GameStatus.ABANDONED
    game.finished_at = datetime.now(timezone.utc)
    await session.commit()
    return game_out(ctx, game)


@router.get("/{game_id}/result", response_model=ResultOut)
async def get_result(
    game_id: uuid.UUID, ctx: GameContext = Depends(get_ctx), session: AsyncSession = Depends(get_session),
    user: User = Depends(current_user),
):
    game = await load_game(session, user, game_id)
    if game.status is GameStatus.IN_PROGRESS:
        raise HTTPException(status.HTTP_409_CONFLICT, "Game is still in progress")
    r = build_result(ctx.graph, to_state(game))
    score = None
    if r.score:
        score = ScoreOut(**dataclasses.asdict(r.score),
                         efficiency_weight=EFFICIENCY_WEIGHT, rarity_weight=RARITY_WEIGHT)
    return ResultOut(
        game=game_out(ctx, game), optimal_path=[ctx.hop_out(h) for h in r.optimal_hops],
        score=score, share_text=r.share_text, data_range=r.data_range,
    )
