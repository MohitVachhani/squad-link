import uuid
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .models import Base, Game, GameAttempt, GameMove, GameStatus, Puzzle, PuzzleKind, User


def engine_kwargs(serverless: bool) -> dict:
    """create_async_engine options. Shared by the app and Alembic (migrations run over the same pooler)."""
    if not serverless:
        return {"pool_pre_ping": True}
    # A transaction pooler hands each transaction to any backend connection, so a prepared statement made in one
    # transaction may not exist in the next: disable asyncpg's and SQLAlchemy's statement caches and give every
    # statement a unique name. Instances are short-lived, so don't hold a pool either.
    return {
        "poolclass": NullPool,
        "connect_args": {
            "statement_cache_size": 0,
            "prepared_statement_cache_size": 0,
            "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4().hex}__",
        },
    }


def make_sessionmaker(database_url: str, serverless: bool = False) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, **engine_kwargs(serverless))
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


__all__ = [
    "Base", "Game", "GameAttempt", "GameMove", "GameStatus", "Puzzle", "PuzzleKind", "User", "get_session",
    "engine_kwargs", "make_sessionmaker",
]
