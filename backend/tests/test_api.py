"""API tests: real app, SQLite instead of Postgres, the hand-built conftest graph, and a fixed puzzle."""

import json

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from conftest import BIG, MID, OTHER, SMALL, graph_data
from squadlink.config import Settings
from squadlink.db import Base, GameAttempt
from squadlink.engine import Graph, Puzzle
from squadlink.main import create_app

# Players in the conftest graph
A, B, C, X, Y, Z, T, Q = 1, 2, 3, 20, 21, 22, 23, 24


class FixedPuzzles:
    """T -> Y (optimal: T -SMALL- Z -MID- Y, 2 hops)."""

    def next(self) -> Puzzle:
        return Puzzle(T, Y, 2, (T, Z, Y))


@pytest.fixture
async def app(tmp_path):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(graph_data()))
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}", auth_secret="test-secret-" + "x" * 32,
        graph_path=graph_path,
    )
    app = create_app(settings, puzzles=FixedPuzzles())
    engine = app.state.sessionmaker.kw["bind"]
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield app
    await engine.dispose()


@pytest.fixture
async def anon(app):
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as c:
        yield c


async def signed_in(app, email="player@example.com") -> AsyncClient:
    c = AsyncClient(transport=ASGITransport(app), base_url="http://test")
    r = await c.post("/auth/register", json={"email": email, "password": "correct-horse"})
    assert r.status_code == 201, r.text
    r = await c.post("/auth/jwt/login", data={"username": email, "password": "correct-horse"})
    assert r.status_code == 200, r.text
    c.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return c


@pytest.fixture
async def client(app):
    c = await signed_in(app)
    yield c
    await c.aclose()


# --- auth ---------------------------------------------------------------------------------------------


async def test_auth_flow(anon, client):
    me = await client.get("/users/me")
    assert me.status_code == 200 and me.json()["email"] == "player@example.com"
    assert (await anon.get("/users/me")).status_code == 401
    assert (await anon.post("/api/games")).status_code == 401


async def test_register_rejects_short_password(anon):
    r = await anon.post("/auth/register", json={"email": "a@example.com", "password": "short"})
    assert r.status_code == 400


async def test_wrong_password(anon, client):
    r = await anon.post("/auth/jwt/login", data={"username": "player@example.com", "password": "nope-nope"})
    assert r.status_code == 400


# --- public endpoints ---------------------------------------------------------------------------------


async def test_meta_and_search(anon):
    m = (await anon.get("/api/meta")).json()
    assert m["season_range"] == "2014/15–2016/17" and m["players"] == 13

    r = (await anon.get("/api/players/search", params={"q": "z"})).json()
    z = r["results"][0]
    assert z["id"] == Z and z["latest_club"] == {"id": SMALL, "name": "Small Town"}
    assert z["latest_season"] == "2016/17" and z["first_season"] == "2015/16"

    r = (await anon.get("/api/clubs/search", params={"q": "mid"})).json()
    assert r["results"][0]["id"] == MID

    assert (await anon.get("/api/players/search", params={"q": ""})).status_code == 422


# --- game loop ----------------------------------------------------------------------------------------


async def move(client, game_id, player_id, club_id):
    return await client.post(f"/api/games/{game_id}/moves", json={"player_id": player_id, "club_id": club_id})


async def test_full_game(app, client):
    r = await client.post("/api/games")
    assert r.status_code == 201
    g = r.json()
    gid = g["id"]
    assert (g["start"]["id"], g["end"]["id"], g["current"]["id"], g["par"]) == (T, Y, T, 2)
    assert g["status"] == "in_progress" and g["hops"] == [] and g["data_range"] == "2014/15–2016/17"

    # Rejected move: explained, recorded, and the game is unchanged.
    r = await move(client, gid, X, BIG)
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "CURRENT_NOT_AT_CLUB"
    async with app.state.sessionmaker() as s:
        assert await s.scalar(select(func.count()).select_from(GameAttempt)) == 1

    # T -OTHER- C -BIG- B -MID- Y  (3 hops vs par 2)
    r = await move(client, gid, C, OTHER)
    assert r.status_code == 200 and r.json()["current"]["id"] == C and r.json()["last_club_id"] == OTHER
    r = await move(client, gid, B, BIG)
    assert r.json()["hops"][-1]["seasons"] == ["2014/15"]
    r = await move(client, gid, Y, MID)
    g = r.json()
    assert g["status"] == "won" and [h["to"]["id"] for h in g["hops"]] == [C, B, Y]

    res = (await client.get(f"/api/games/{gid}/result")).json()
    assert res["score"]["hops"] == 3 and res["score"]["optimal_hops"] == 2
    assert res["score"]["efficiency_weight"] == 0.7
    assert res["score"]["total"] == pytest.approx(res["score"]["efficiency_points"] + res["score"]["rarity_points"])
    assert [h["to"]["id"] for h in res["optimal_path"]] == [Z, Y]
    assert res["share_text"].startswith("Squadlink ⚽ T → Y")
    assert res["data_range"] == "2014/15–2016/17"

    # Finished: no more moves; listed in history with its score.
    assert (await move(client, gid, Z, SMALL)).json()["detail"]["code"] == "GAME_OVER"
    games = (await client.get("/api/games")).json()
    assert games[0]["id"] == gid and games[0]["score"] == res["score"]["total"]


async def test_same_club_twice_via_api(client):
    gid = (await client.post("/api/games")).json()["id"]
    await move(client, gid, C, OTHER)
    assert (await move(client, gid, A, BIG)).status_code == 200  # C -BIG 14/15- A
    r = await move(client, gid, X, BIG)  # A -BIG 15/16- X: a different season, but still BIG twice in a row
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "SAME_CLUB_TWICE"
    assert "Big FC" in r.json()["detail"]["message"]


async def test_undo_and_edit(client):
    gid = (await client.post("/api/games")).json()["id"]
    await move(client, gid, C, OTHER)
    await move(client, gid, A, BIG)
    g = (await move(client, gid, X, BIG)).json()  # rejected: BIG twice
    assert g["detail"]["code"] == "SAME_CLUB_TWICE"

    # Undo last link (A): back on C, BIG no longer the last club.
    r = await client.delete(f"/api/games/{gid}/moves/1")
    assert r.status_code == 200
    g = r.json()
    assert [h["to"]["id"] for h in g["hops"]] == [C] and g["current"]["id"] == C and g["last_club_id"] == OTHER

    # "Edit" = re-add a different link from there.
    g = (await move(client, gid, B, BIG)).json()
    assert [h["to"]["id"] for h in g["hops"]] == [C, B]

    # Remove from the first link: everything goes, back at the start.
    g = (await client.delete(f"/api/games/{gid}/moves/0")).json()
    assert g["hops"] == [] and g["current"]["id"] == T and g["last_club_id"] is None

    r = await client.delete(f"/api/games/{gid}/moves/0")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "NO_SUCH_HOP"

    # The chain can then be completed normally.
    for pid, club in [(Z, SMALL), (Y, MID)]:
        g = (await move(client, gid, pid, club)).json()
    assert g["status"] == "won" and len(g["hops"]) == 2
    r = await client.delete(f"/api/games/{gid}/moves/0")
    assert r.status_code == 409 and r.json()["detail"]["code"] == "GAME_OVER"  # finished games are final


async def test_result_requires_finished_game_and_give_up(client):
    gid = (await client.post("/api/games")).json()["id"]
    assert (await client.get(f"/api/games/{gid}/result")).status_code == 409
    r = await client.post(f"/api/games/{gid}/give-up")
    assert r.json()["status"] == "abandoned"
    assert (await client.post(f"/api/games/{gid}/give-up")).status_code == 409
    res = (await client.get(f"/api/games/{gid}/result")).json()
    assert res["score"] is None and res["share_text"] is None
    assert len(res["optimal_path"]) == 2  # still show the answer


async def test_games_are_private(app, client):
    gid = (await client.post("/api/games")).json()["id"]
    other = await signed_in(app, "other@example.com")
    try:
        assert (await other.get(f"/api/games/{gid}")).status_code == 404
        assert (await move(other, gid, Z, SMALL)).status_code == 404
        assert (await other.delete(f"/api/games/{gid}/moves/0")).status_code == 404
        assert (await other.get("/api/games")).json() == []
    finally:
        await other.aclose()


def test_graph_fixture_matches_constants():
    g = Graph(graph_data())
    assert {g.players[i].name for i in (A, B, C, X, Y, Z, T, Q)} == set("ABCXYZTQ")
