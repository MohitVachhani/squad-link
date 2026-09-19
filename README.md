# Squadlink

Link two footballers through teammates: each hop is a player who shared a club squad in the same season.

## Run locally

Needs `uv`, Node 20+, and `backend/.env` filled in (see `backend/.env.example`: `DATABASE_URL`, `AUTH_SECRET`).

```sh
make install     # Python + npm dependencies
make migrate     # create/upgrade DB tables (safe to re-run)
make dev         # API on :8000 + web on :5173 (Ctrl+C stops both)
```

Open http://localhost:5173, create an account, start a puzzle.
API docs: http://localhost:8000/docs.

## Deploy (Vercel)

Live: https://squadlink-eight.vercel.app. One Vercel project (personal scope `mohit-vachhanis-projects`, region `sin1`,
next to the Supabase DB): the React build as static files, and FastAPI as a Python function (`api/index.py`) serving
`/api`, `/auth`, `/users` and `/health` on the same domain.

```sh
make deploy      # regenerates requirements.txt, then `vercel deploy --prod` (uses VERCEL_TOKEN from backend/.env)
```

- Production env vars live in Vercel: `DATABASE_URL` (Supabase **transaction pooler**, port 6543), `DB_SERVERLESS=true`,
  `AUTH_SECRET`, `FRONTEND_URL`. Change them with `vercel env add NAME production --force`.
- Schema changes: run `make migrate` locally before deploying; Vercel doesn't run migrations.
- The frontend sends `/health` on page load to warm the function before the user needs it.

## Other commands

- `make test`: backend tests
- `make download graph`: re-download the Kaggle data and rebuild `backend/data/graph.json` (needs Kaggle credentials in `.env`)
- `make api` / `make web`: run the servers separately

See `docs/ARCHITECTURE.md` for the design and `backend/data/DATASET.md` for data provenance.
