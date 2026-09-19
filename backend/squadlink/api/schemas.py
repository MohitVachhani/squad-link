import uuid
from datetime import datetime

from pydantic import BaseModel

from ..db import GameStatus


class ClubRef(BaseModel):
    id: int
    name: str


class ClubOut(ClubRef):
    league: str
    aliases: list[str]


class PlayerOut(BaseModel):
    """Everything the dropdown needs to tell two 'Danilo's apart."""

    id: int
    name: str
    full: str
    nation: str
    dob: str | None
    ovr: int | None
    latest_club: ClubRef | None
    latest_season: str | None
    first_season: str | None


class PlayerSearchOut(BaseModel):
    query: str
    ambiguous: bool  # several players match the query exactly: the user must pick
    results: list[PlayerOut]


class ClubSearchOut(BaseModel):
    query: str
    results: list[ClubOut]


class HopOut(BaseModel):
    from_id: int
    to: PlayerOut
    club: ClubRef
    seasons: list[str]
    rarity: float


class GameOut(BaseModel):
    id: uuid.UUID
    status: GameStatus
    start: PlayerOut
    end: PlayerOut
    current: PlayerOut
    hops: list[HopOut]
    last_club_id: int | None  # can't be used for the next hop
    par: int  # BFS optimum
    data_range: str
    started_at: datetime | None


class MoveIn(BaseModel):
    player_id: int
    club_id: int


class MoveErrorOut(BaseModel):
    code: str
    message: str
    details: dict


class ScoreOut(BaseModel):
    hops: int
    optimal_hops: int
    efficiency: float
    rarity: float
    efficiency_points: float
    rarity_points: float
    total: float
    efficiency_weight: float
    rarity_weight: float


class ResultOut(BaseModel):
    game: GameOut
    optimal_path: list[HopOut]
    score: ScoreOut | None
    share_text: str | None
    data_range: str  # "optimal" is only optimal within this range


class GameSummaryOut(BaseModel):
    id: uuid.UUID
    status: GameStatus
    start: PlayerOut
    end: PlayerOut
    hops: int
    par: int
    score: float | None
    started_at: datetime | None


class MetaOut(BaseModel):
    season_range: str
    seasons: list[str]
    graph_version: int
    filters: dict
    players: int
    clubs: int
