BACKEND := backend
KAGGLE_DATASET := stefanoleone992/ea-sports-fc-24-complete-player-dataset
RAW := $(BACKEND)/data/raw

.PHONY: install download graph test migrate api web dev requirements deploy

install:
	cd $(BACKEND) && uv sync
	cd frontend && npm install

# Needs KAGGLE_USERNAME + KAGGLE_API_TOKEN (or legacy KAGGLE_KEY) in backend/.env
download:
	set -a; [ -f $(BACKEND)/.env ] && . ./$(BACKEND)/.env; set +a; \
	uvx kaggle datasets download -d $(KAGGLE_DATASET) -p $(RAW) --unzip

# Build graph.json, then run the real-data spot checks. Any failure fails the target.
graph:
	cd $(BACKEND) && uv run python data/build_graph.py $(ARGS)
	cd $(BACKEND) && uv run pytest -q tests/test_graph.py

test:
	cd $(BACKEND) && uv run pytest -q

# Apply DB migrations (uses DATABASE_URL from backend/.env)
migrate:
	cd $(BACKEND) && uv run alembic upgrade head

# FastAPI on :8000 (auto-reload)
api:
	cd $(BACKEND) && uv run uvicorn squadlink.main:app --reload --port 8000

# React dev server on :5173, proxying /api, /auth, /users to :8000
web:
	cd frontend && npm run dev

# Both at once; Ctrl+C stops both
dev:
	trap 'kill 0' INT TERM EXIT; $(MAKE) api & $(MAKE) web & wait

# Runtime deps for the Vercel Python function (re-run after changing backend dependencies)
requirements:
	cd $(BACKEND) && uv export --no-dev --no-hashes --no-emit-project --format requirements-txt -q -o ../requirements.txt

# Deploy frontend + API to Vercel production. Uses VERCEL_TOKEN from backend/.env if set, else your `vercel login`.
deploy: requirements
	set -a; [ -f $(BACKEND)/.env ] && . ./$(BACKEND)/.env; set +a; \
	vercel deploy --prod --yes $${VERCEL_TOKEN:+--token $$VERCEL_TOKEN}
