#!/usr/bin/env bash
# Vercel build (vercel.json buildCommand): build the frontend, then (production deploys only) apply database
# migrations. If a migration fails the build fails, and Vercel keeps the current deployment live.
set -euo pipefail

(cd frontend && npm run build)

if [ "${VERCEL_ENV:-}" != "production" ]; then
  echo "Skipping database migrations (VERCEL_ENV=${VERCEL_ENV:-unset}); they only run for production."
  exit 0
fi

echo "Applying database migrations…"
if ! command -v uv >/dev/null 2>&1; then
  python3 -m pip install --quiet --user uv
  export PATH="$HOME/.local/bin:$PATH"
fi
# Runtime deps only (no pandas/pytest); uv fetches Python 3.12 if the build image lacks it.
# DATABASE_URL, DB_SERVERLESS etc. come from the project's production environment variables.
(cd backend && uv run --no-dev --frozen alembic upgrade head)
