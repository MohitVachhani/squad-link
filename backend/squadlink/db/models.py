"""Postgres schema. Player/club ids point into graph.json (not FKs); graph_version records which build a row used.

Portable types (JSON rather than ARRAY) so tests can run on SQLite.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from sqlalchemy import (
    JSON, Date, DateTime, Enum, Float, ForeignKey, Index, Integer, SmallInteger, String, UniqueConstraint, Uuid, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(SQLAlchemyBaseUserTableUUID, Base):
    __tablename__ = "users"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class PuzzleKind(enum.StrEnum):
    RANDOM = "random"
    DAILY = "daily"  # not used yet


class GameStatus(enum.StrEnum):
    IN_PROGRESS = "in_progress"
    WON = "won"
    ABANDONED = "abandoned"


def _enum(e: type[enum.Enum], name: str) -> Enum:
    return Enum(e, name=name, values_callable=lambda members: [m.value for m in members])


class Puzzle(Base):
    __tablename__ = "puzzles"
    __table_args__ = (UniqueConstraint("kind", "daily_date"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[PuzzleKind] = mapped_column(_enum(PuzzleKind, "puzzle_kind"), default=PuzzleKind.RANDOM)
    daily_date: Mapped[date | None] = mapped_column(Date)
    start_player_id: Mapped[int] = mapped_column(Integer)
    end_player_id: Mapped[int] = mapped_column(Integer)
    optimal_hops: Mapped[int] = mapped_column(SmallInteger)
    optimal_path: Mapped[list[int]] = mapped_column(JSON)
    graph_version: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class Game(Base):
    __tablename__ = "games"
    __table_args__ = (
        Index("ix_games_user_started", "user_id", "started_at"),
        Index("ix_games_puzzle_score", "puzzle_id", "score"),  # future leaderboards
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    puzzle_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("puzzles.id"))
    status: Mapped[GameStatus] = mapped_column(_enum(GameStatus, "game_status"), default=GameStatus.IN_PROGRESS)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Filled in on a win, so leaderboards never recompute.
    hops: Mapped[int | None] = mapped_column(SmallInteger)
    efficiency: Mapped[float | None] = mapped_column(Float)
    rarity: Mapped[float | None] = mapped_column(Float)
    score: Mapped[float | None] = mapped_column(Float)

    puzzle: Mapped[Puzzle] = relationship(lazy="joined", innerjoin=True)
    moves: Mapped[list[GameMove]] = relationship(
        order_by="GameMove.idx", lazy="selectin", cascade="all, delete-orphan"
    )


class GameMove(Base):
    """Accepted hops only."""

    __tablename__ = "game_moves"

    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), primary_key=True)
    idx: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    from_player_id: Mapped[int] = mapped_column(Integer)
    to_player_id: Mapped[int] = mapped_column(Integer)
    club_id: Mapped[int] = mapped_column(Integer)
    seasons: Mapped[list[str]] = mapped_column(JSON)
    rarity: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())


class GameAttempt(Base):
    """Rejected guesses — shows where players (and our name matching) struggle."""

    __tablename__ = "game_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("games.id", ondelete="CASCADE"), index=True)
    player_id: Mapped[int | None] = mapped_column(Integer)
    club_id: Mapped[int | None] = mapped_column(Integer)
    error_code: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, server_default=func.now())
