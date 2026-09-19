"""Vercel entry point: the FastAPI app as one Python function. vercel.json routes /api, /auth, /users and /health
here; FastAPI still sees the original path. The backend package and graph.json ship via `includeFiles`."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from squadlink.main import create_app  # noqa: E402

app = create_app()
