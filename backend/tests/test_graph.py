"""Spot checks against the REAL graph.json (top-5 leagues, overall >= 70). Skipped until it's been built.

IDs are sofifa player ids (the dataset's player_id). Each check also asserts the name, so a wrong id fails
loudly instead of silently testing the wrong player.
"""

from pathlib import Path

import pytest

from squadlink.engine import Graph

GRAPH_PATH = Path(__file__).resolve().parents[1] / "data" / "graph.json"

MESSI, NEYMAR, RONALDO, BENZEMA, DYBALA = 158023, 190871, 20801, 165153, 211110
MBAPPE, LEWANDOWSKI, MULLER, SALAH, MANE = 231747, 188545, 189596, 209331, 208722
KANE, SON, DE_BRUYNE, AGUERO, VAN_DIJK = 202126, 200104, 192985, 153079, 203376

NAMES = {
    MESSI: "messi", NEYMAR: "neymar", RONALDO: "ronaldo", BENZEMA: "benzema", DYBALA: "dybala",
    MBAPPE: "mbapp", LEWANDOWSKI: "lewandowski", MULLER: "ller", SALAH: "salah", MANE: "man",
    KANE: "kane", SON: "son", DE_BRUYNE: "bruyne", AGUERO: "ag", VAN_DIJK: "dijk",
}

# (a, b, club name fragment, season that must be shared)
LINKED = [
    (MESSI, NEYMAR, "barcelona", "2015/16"),
    (MESSI, NEYMAR, "barcelona", "2016/17"),
    (RONALDO, BENZEMA, "real madrid", "2016/17"),
    (RONALDO, DYBALA, "juventus", "2019/20"),
    (NEYMAR, MBAPPE, "paris", "2018/19"),
    (LEWANDOWSKI, MULLER, "bayern", "2016/17"),
    (SALAH, MANE, "liverpool", "2018/19"),
    (KANE, SON, "tottenham", "2017/18"),
    (DE_BRUYNE, AGUERO, "manchester city", "2017/18"),
    (SALAH, VAN_DIJK, "liverpool", "2019/20"),
]
NOT_LINKED = [(MESSI, RONALDO), (KANE, SALAH), (SON, SALAH)]  # not Müller–Mané: Bayern 2022/23


@pytest.fixture(scope="module")
def graph():
    if not GRAPH_PATH.exists():
        pytest.skip("data/graph.json not built yet — run `make download graph`")
    return Graph.load(GRAPH_PATH)


def test_ids_are_who_we_think(graph):
    for pid, fragment in NAMES.items():
        assert pid in graph.players, f"{pid} ({fragment}) missing from graph"
        p = graph.players[pid]
        assert fragment in f"{p.name} {p.full}".lower(), f"{pid} is {p.full}, expected ~{fragment}"


@pytest.mark.parametrize("a, b, club, season", LINKED)
def test_known_links(graph, a, b, club, season):
    shared = [(graph.clubs[c].name, s) for c, s in graph.shared_squads(a, b)]
    assert any(club in name.lower() and s == season for name, s in shared), \
        f"{graph.players[a].name}–{graph.players[b].name} should share {club} {season}; shared: {shared}"


@pytest.mark.parametrize("a, b", NOT_LINKED)
def test_known_non_links(graph, a, b):
    assert not graph.are_teammates(a, b), graph.shared_squads(a, b)


def test_meta(graph):
    assert graph.meta["graph_version"] >= 1
    assert graph.seasons[0] == "2014/15"
    assert len(graph.components()[0]) / len(graph.player_squads) >= 0.95
