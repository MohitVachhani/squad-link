import json

import pytest

import build_graph
from fixtures import write_fixture_csv


def run(tmp_path, *flags, extra_rows=(), date_column="fifa_update_date"):
    csv_path = write_fixture_csv(tmp_path / "male_players.csv", list(extra_rows), date_column)
    out = tmp_path / "graph.json"
    # Only La Liga (53) and Serie A (31) exist in the fixture, so restrict --league-ids to those.
    code = build_graph.main(["--csv", str(csv_path), "--out", str(out), "--league-ids", "31,53",
                             "--min-lcc", "0", "--chunksize", "5", *flags])
    return code, (json.loads(out.read_text()) if out.exists() else None)


def memberships(graph):
    return {tuple(m) for m in graph["memberships"]}


def test_season_label():
    assert build_graph.season_label(24) == "2023/24"
    assert build_graph.season_label(15) == "2014/15"


def test_builds_expected_graph(tmp_path):
    code, g = run(tmp_path)
    assert code == 0
    assert g["meta"]["versions"] == [15, 16]
    assert g["meta"]["seasons"] == ["2014/15", "2015/16"]
    assert g["meta"]["snapshots"] == {"2014/15": "2015-02-22", "2015/16": "2016-03-01"}
    assert g["meta"]["filters"] == {"league_ids": [31, 53], "min_overall": 70}
    assert g["meta"]["players"] == len(g["players"]) == 9
    assert g["meta"]["memberships"] == len(g["memberships"])


def test_only_latest_snapshot_per_version(tmp_path):
    _, g = run(tmp_path)
    m = memberships(g)
    assert (5, 243, "2014/15") in m  # latest FIFA 15 update: Real Madrid
    assert (5, 45, "2014/15") not in m  # early FIFA 15 update: Juventus — ignored


def test_filters(tmp_path):
    _, g = run(tmp_path)
    assert "9" not in g["players"]  # overall 60 < 70
    assert "10" not in g["players"]  # no club
    assert "11" not in g["players"]  # Austrian "Bundesliga": same name as a top-5 league, different league_id

    _, g = run(tmp_path, "--all-leagues", "--min-overall", "80")
    assert "11" not in g["players"]  # 72 < 80
    assert g["meta"]["filters"] == {"league_ids": "all", "min_overall": 80}
    assert {int(p) for p in g["players"]} == {1, 2, 3, 5, 12}

    _, g = run(tmp_path, "--all-leagues")
    assert "11" in g["players"]


def test_club_identity_is_team_id_with_latest_name(tmp_path):
    _, g = run(tmp_path)
    assert g["clubs"]["241"] == {"name": "FC Barcelona", "league": "La Liga", "aliases": ["Barcelona"]}
    # Renamed club is still one club: Messi's two seasons point at the same id.
    assert {(1, 241, "2014/15"), (1, 241, "2015/16")} <= memberships(g)


def test_player_record(tmp_path):
    _, g = run(tmp_path)
    assert g["players"]["8"] == {
        "name": "N. Kanté", "full": "N'Golo Kanté", "nation": "France", "dob": "1991-03-29", "ovr": 79,
    }


def test_deterministic(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    a.mkdir(), b.mkdir()
    run(a)
    run(b)
    strip = lambda p: [ln for ln in (p / "graph.json").read_text().splitlines() if '"built_at"' not in ln]
    assert strip(a) == strip(b)


def test_duplicate_player_season_fails_build(tmp_path, capsys):
    code, g = run(tmp_path, extra_rows=[(1, 45, "Juventus", 94, 16, "2016-03-01")])
    assert code == 1
    assert g is None  # nothing written
    assert "appear twice in one season" in capsys.readouterr().err


def test_update_as_of_date_column(tmp_path):
    # The current Kaggle release names the snapshot date column update_as_of.
    code, g = run(tmp_path, date_column="update_as_of")
    assert code == 0
    assert g["meta"]["snapshots"] == {"2014/15": "2015-02-22", "2015/16": "2016-03-01"}
    assert (5, 45, "2014/15") not in memberships(g)


def test_missing_league_fails_build(tmp_path, capsys):
    code, _ = run(tmp_path, "--league-ids", "16,31,53")
    assert code == 1
    assert "no rows for league_id [16]" in capsys.readouterr().err


def test_low_connectivity_fails_build(tmp_path, capsys):
    # With all leagues, Austria Wien's lone player is an isolated component: 9/10 = 90% < 95%.
    code, _ = run(tmp_path, "--all-leagues", "--min-lcc", "0.95")
    assert code == 1
    assert "largest component" in capsys.readouterr().err


def test_missing_csv(tmp_path):
    assert build_graph.main(["--csv", str(tmp_path / "nope.csv"), "--out", str(tmp_path / "g.json")]) == 2


@pytest.fixture
def fixture_graph(tmp_path):
    from squadlink.engine import Graph
    run(tmp_path)
    return Graph.load(tmp_path / "graph.json")


def test_fixture_graph_loads_into_engine(fixture_graph):
    g = fixture_graph
    assert g.season_range == "2014/15–2015/16"
    assert g.shortest_path(1, 3) == [1, 13, 3]  # Messi -Barça 14/15- Bridge -Madrid 15/16- Ronaldo
    assert len(g.components()) == 1
