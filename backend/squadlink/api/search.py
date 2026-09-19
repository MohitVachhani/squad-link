from fastapi import APIRouter, Depends, Query

from .context import GameContext, get_ctx
from .schemas import ClubSearchOut, MetaOut, PlayerSearchOut

router = APIRouter(prefix="/api", tags=["search"])


@router.get("/meta", response_model=MetaOut)
def meta(ctx: GameContext = Depends(get_ctx)):
    m = ctx.graph.meta
    return MetaOut(
        season_range=ctx.graph.season_range, seasons=ctx.graph.seasons, graph_version=ctx.graph_version,
        filters=m.get("filters", {}), players=len(ctx.graph.players), clubs=len(ctx.graph.clubs),
    )


@router.get("/players/search", response_model=PlayerSearchOut)
def search_players(q: str = Query(min_length=1, max_length=80), limit: int = Query(10, ge=1, le=25),
                   ctx: GameContext = Depends(get_ctx)):
    r = ctx.players.search(q, limit)
    return PlayerSearchOut(query=q, ambiguous=r.ambiguous, results=[ctx.player_out(pid) for pid in r.ids])


@router.get("/clubs/search", response_model=ClubSearchOut)
def search_clubs(q: str = Query(min_length=1, max_length=80), limit: int = Query(10, ge=1, le=25),
                 ctx: GameContext = Depends(get_ctx)):
    r = ctx.clubs.search(q, limit)
    return ClubSearchOut(query=q, results=[ctx.club_out(cid) for cid in r.ids])
