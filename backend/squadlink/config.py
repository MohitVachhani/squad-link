from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", extra="ignore")

    database_url: str
    # Serverless (Vercel): no connection pool, and no prepared-statement caching, for Supabase's transaction
    # pooler (port 6543). Long-running servers leave this off and use the session pooler (5432).
    db_serverless: bool = False
    auth_secret: str
    frontend_url: str = "http://localhost:5173"
    graph_path: Path = BACKEND_DIR / "data" / "graph.json"
    jwt_lifetime_seconds: int = 60 * 60 * 24 * 7

    # Random puzzle tuning (see engine/puzzles.py)
    puzzle_min_hops: int = 3
    puzzle_max_hops: int = 5
    puzzle_min_ovr: int = 85
