import uuid
from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from .models import Base, Game, GameAttempt, GameMove, GameStatus, Puzzle, PuzzleKind, User


def make_sessionmaker(database_url: str, serverless: bool = False) -> async_sessionmaker[AsyncSession]:
    if serverless:
        # A transaction pooler hands each transaction to any backend connection, so a prepared statement made in
        # one transaction may not exist in the next: disable asyncpg's and SQLAlchemy's statement caches and give
        # every statement a unique name. Instances are short-lived, so don't hold a pool either.
        engine = create_async_engine(
            database_url,
            poolclass=NullPool,
            connect_args={
                "statement_cache_size": 0,
                "prepared_statement_cache_size": 0,
                "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4().hex}__",
            },
        )
    else:
        engine = create_async_engine(database_url, pool_pre_ping=True)
    return async_sessionmaker(engine, expire_on_commit=False)


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


__all__ = [
    "Base", "Game", "GameAttempt", "GameMove", "GameStatus", "Puzzle", "PuzzleKind", "User", "get_session",
    "make_sessionmaker",
]
