"""FastAPI app. Run: uv run uvicorn squadlink.main:app --reload"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import api
from .api.context import GameContext
from .auth import UserCreate, UserRead, UserUpdate, auth_backend, fastapi_users
from .config import Settings
from .db import make_sessionmaker
from .engine import ClubIndex, Graph, PlayerIndex, PuzzleSource, RandomPuzzleSource


def create_app(settings: Settings | None = None, puzzles: PuzzleSource | None = None) -> FastAPI:
    settings = settings or Settings()
    graph = Graph.load(settings.graph_path)  # precomputed at build time; loaded once

    app = FastAPI(title="Squadlink")
    app.state.settings = settings
    app.state.sessionmaker = make_sessionmaker(settings.database_url, settings.db_serverless)
    app.state.ctx = GameContext(
        graph=graph,
        players=PlayerIndex(graph),
        clubs=ClubIndex(graph),
        puzzles=puzzles or RandomPuzzleSource(
            graph, min_hops=settings.puzzle_min_hops, max_hops=settings.puzzle_max_hops,
            min_ovr=settings.puzzle_min_ovr,
        ),
    )

    app.add_middleware(
        CORSMiddleware, allow_origins=[settings.frontend_url], allow_credentials=True,
        allow_methods=["*"], allow_headers=["*"],
    )
    app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
    app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
    app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])
    app.include_router(api.search.router)
    app.include_router(api.games.router)

    @app.get("/health", tags=["meta"])
    def health():
        return {"ok": True, "graph_version": app.state.ctx.graph_version}

    return app


def __getattr__(name: str):
    # `uvicorn squadlink.main:app` builds the app lazily, so importing this module (e.g. in tests) needs no .env.
    if name == "app":
        return create_app()
    raise AttributeError(name)
