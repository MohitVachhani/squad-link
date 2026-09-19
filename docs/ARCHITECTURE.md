# Squadlink — architecture

## Project structure

```
squadlink/
├── Makefile                  # download / graph / test / (later) dev
├── docs/ARCHITECTURE.md
├── backend/
│   ├── pyproject.toml        # uv project; package = squadlink
│   ├── .env                  # DATABASE_URL (Supabase Postgres), git-ignored
│   ├── data/
│   │   ├── raw/              # git-ignored Kaggle CSVs
│   │   ├── build_graph.py    # raw CSV -> graph.json (the ONLY code that reads the CSV)
│   │   ├── graph.json        # committed build output, loaded at API startup
│   │   └── DATASET.md        # provenance
│   ├── squadlink/
│   │   ├── engine/           # pure Python, no FastAPI/DB imports, no I/O besides loading graph.json
│   │   │   ├── graph.py      # Graph: squads, teammates, BFS, components
│   │   │   ├── names.py      # normalisation + player/club search (exact > prefix > substring)
│   │   │   ├── game.py       # GameState, Hop, move validation (the rules)
│   │   │   ├── scoring.py    # rarity, efficiency, score breakdown, share text
│   │   │   ├── puzzles.py    # PuzzleSource protocol + RandomPuzzleSource
│   │   │   └── result.py     # results screen: user path, optimal path, score, share text
│   │   ├── api/              # (next step) FastAPI app, routers, schemas
│   │   └── db/               # (next step) SQLAlchemy models, Alembic migrations
│   └── tests/
│       ├── fixtures.py       # synthetic CSV in the real Kaggle schema
│       ├── test_build.py     # pipeline: snapshots, filters, identity, determinism, validation
│       ├── test_engine.py    # graph, rules, scoring, puzzles
│       ├── test_names.py     # accents, ambiguity, ranking
│       └── test_graph.py     # spot checks against the REAL graph.json (skipped until built)
└── frontend/                 # (later) Vite + React + TS
```

### Why the engine is stateless

The engine never stores a game. A game is `(puzzle, [hops])`. The API loads the hops from Postgres, rebuilds a
`GameState`, calls `validate_move` and saves the new hop. That's what makes the future features cheap:

- **Daily puzzle**: a new `PuzzleSource` (seeded by date) that writes a `puzzle` row with `kind='daily'`.
  The game loop doesn't change.
- **Leaderboards**: final scores are stored on `game`, so a leaderboard is a query on `(puzzle_id, score)`.
- **Multiplayer**: several `game` rows share one `puzzle_id` (and a future `match_id`). Each player still runs
  the same single-player loop.

## Rules as encoded

| Rule | Where |
|---|---|
| A link means both players were in the same squad: same `club_team_id` **and** season | `Graph.shared_seasons` |
| The same club can't be used two hops in a row (in any season) | `game.validate_move` → `SAME_CLUB_TWICE` |
| A player can't appear twice in the chain | `ALREADY_IN_CHAIN` |
| Optimal = plain BFS on the player graph, ignoring the club rule (a lower bound) | `Graph.shortest_path` |
| rarity(link) = 1 − log(squad_size)/log(max_squad_size), where squad = (club, season) in the filtered graph; if a link works in several seasons, the rarest one counts | `scoring.link_rarity` |
| score = 100 × (0.7 × min(1, optimal/hops) + 0.3 × mean rarity) | `scoring.score` |

Players are matched by ID, never by name. The UI's autocomplete supplies `player_id` and `club_id`. The name
search never auto-resolves an ambiguous query; it returns `ambiguous: true` with the candidates.

## Database schema (Postgres)

Plain Postgres, hosted on Supabase and used only as a database: no Supabase Auth, no client-side access.
The connection string lives in `backend/.env` as `DATABASE_URL`, which is git-ignored; `.env.example` shows the
shape. Auth uses fastapi-users; database access uses SQLAlchemy + asyncpg, with Alembic for migrations.

The graph is **not** in Postgres. Player and club IDs point into `graph.json`, and every puzzle and game
records the `graph_version` it was played on.

```sql
-- fastapi-users (SQLAlchemyBaseUserTableUUID + OAuth account table), unchanged apart from extra columns
CREATE TABLE "user" (
  id              uuid PRIMARY KEY,
  email           varchar(320) NOT NULL UNIQUE,
  hashed_password varchar(1024) NOT NULL,        -- fastapi-users sets an unusable one for OAuth-only users
  is_active       boolean NOT NULL DEFAULT true,
  is_superuser    boolean NOT NULL DEFAULT false,
  is_verified     boolean NOT NULL DEFAULT false,
  display_name    varchar(50),
  created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE oauth_account (
  id             uuid PRIMARY KEY,
  user_id        uuid NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  oauth_name     varchar(100) NOT NULL,           -- 'google'
  access_token   varchar(1024) NOT NULL,
  expires_at     integer,
  refresh_token  varchar(1024),
  account_id     varchar(320) NOT NULL,
  account_email  varchar(320) NOT NULL
);
CREATE INDEX ON oauth_account (oauth_name, account_id);

CREATE TYPE puzzle_kind AS ENUM ('random', 'daily');   -- 'daily' unused for now
CREATE TABLE puzzle (
  id              uuid PRIMARY KEY,
  kind            puzzle_kind NOT NULL DEFAULT 'random',
  daily_date      date,                            -- only for kind='daily'
  start_player_id integer NOT NULL,
  end_player_id   integer NOT NULL,
  optimal_hops    smallint NOT NULL,
  optimal_path    integer[] NOT NULL,              -- player ids, start..end
  graph_version   integer NOT NULL,
  created_at      timestamptz NOT NULL DEFAULT now(),
  UNIQUE (kind, daily_date)
);

CREATE TYPE game_status AS ENUM ('in_progress', 'won', 'abandoned');
CREATE TABLE game (
  id            uuid PRIMARY KEY,
  user_id       uuid NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
  puzzle_id     uuid NOT NULL REFERENCES puzzle(id),
  status        game_status NOT NULL DEFAULT 'in_progress',
  started_at    timestamptz NOT NULL DEFAULT now(),
  finished_at   timestamptz,
  -- filled on finish; stored so leaderboards never need to recompute
  hops          smallint,
  efficiency    real,
  rarity        real,
  score         real
);
CREATE INDEX ON game (user_id, started_at DESC);
CREATE INDEX ON game (puzzle_id, score DESC);      -- future leaderboard

CREATE TABLE game_move (                            -- accepted hops only
  game_id        uuid NOT NULL REFERENCES game(id) ON DELETE CASCADE,
  idx            smallint NOT NULL,                 -- 0-based hop number
  from_player_id integer NOT NULL,
  to_player_id   integer NOT NULL,
  club_id        integer NOT NULL,
  seasons        text[] NOT NULL,                   -- seasons both were in the squad
  rarity         real NOT NULL,
  created_at     timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (game_id, idx)
);

CREATE TABLE game_attempt (                         -- rejected guesses; shows where name matching fails
  id           bigserial PRIMARY KEY,
  game_id      uuid NOT NULL REFERENCES game(id) ON DELETE CASCADE,
  player_id    integer,
  club_id      integer,
  error_code   varchar(32) NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);
```

Sessions use fastapi-users' JWT strategy (stateless), so there's no session table. If we want server-side
revocation later, we can switch to its `DatabaseStrategy` (an `accesstoken` table).

## API (planned, next step)

| Method | Path | Notes |
|---|---|---|
| * | `/auth/jwt/login`, `/auth/register`, `/auth/google/authorize`, `/auth/google/callback`, `/users/me` | fastapi-users |
| GET | `/api/meta` | data range ("2014/15–2023/24"), graph_version, filters |
| GET | `/api/players/search?q=` | `{ambiguous, results:[{id,name,full,nation,dob,latest_club,latest_season,first_season}]}` |
| GET | `/api/clubs/search?q=` | same ranking for clubs |
| POST | `/api/games` | new random puzzle → game |
| GET | `/api/games/{id}` | state: start, end, chain |
| POST | `/api/games/{id}/moves` | `{player_id, club_id}` → hop, or 422 `{code, message}` |
| POST | `/api/games/{id}/give-up` | |
| GET | `/api/games/{id}/result` | user path, optimal path, score breakdown, share text |
