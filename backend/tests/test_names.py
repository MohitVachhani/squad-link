import pytest

from squadlink.engine import ClubIndex, Graph, PlayerIndex, normalize


@pytest.mark.parametrize("raw, expected", [
    ("N'Golo Kanté", "ngolo kante"),
    ("  Kylian   MBAPPÉ ", "kylian mbappe"),
    ("Paris Saint-Germain", "paris saint germain"),
    ("Martin Ødegaard", "martin odegaard"),
    ("Robert Lewandowski", "robert lewandowski"),
    ("Łukasz Fabiański", "lukasz fabianski"),
    ("İlkay Gündoğan", "ilkay gundogan"),
    ("Thomas Müller", "thomas muller"),
    ("Sergio Agüero", "sergio aguero"),
    ("A. Rüdiger", "a rudiger"),
    ("Borussia M'gladbach", "borussia mgladbach"),
    ("!!!", ""),
])
def test_normalize(raw, expected):
    assert normalize(raw) == expected


@pytest.fixture
def names_graph():
    def p(name, full, nation, ovr):
        return {"name": name, "full": full, "nation": nation, "dob": None, "ovr": ovr}
    return Graph({
        "meta": {},
        "players": {
            "1": p("Danilo", "Danilo Luiz da Silva", "Brazil", 80),
            "2": p("Danilo", "Danilo Pereira", "Portugal", 82),
            "3": p("Danilo Pereira", "Danilo Pereira", "Portugal", 70),  # a different Danilo Pereira
            "4": p("N. Kanté", "N'Golo Kanté", "France", 88),
            "5": p("K. Mbappé", "Kylian Mbappé Lottin", "France", 91),
            "6": p("E. Dani", "Dani Something", "Spain", 60),
        },
        "clubs": {
            "10": {"name": "FC Barcelona", "league": "La Liga", "aliases": ["Barcelona"]},
            "11": {"name": "Real Madrid", "league": "La Liga"},
            "12": {"name": "Real Madrid Castilla", "league": "Segunda"},
            "13": {"name": "Paris Saint-Germain", "league": "Ligue 1"},
        },
        "memberships": [[1, 10, "2020/21"], [2, 11, "2020/21"], [4, 11, "2020/21"], [5, 13, "2020/21"],
                        [3, 12, "2020/21"]],
    })


def test_accent_insensitive(names_graph):
    idx = PlayerIndex(names_graph)
    assert idx.search("kante").ids == [4]
    assert idx.search("MBAPPE").ids == [5]
    assert idx.search("ngolo").ids == [4]
    assert idx.search("n'golo kanté").ids == [4]


def test_ambiguous_name_is_not_auto_resolved(names_graph):
    r = PlayerIndex(names_graph).search("danilo")
    assert r.ambiguous
    # Both exact "Danilo"s first (higher rated first), then the prefix match.
    assert r.ids == [2, 1, 3]


def test_ranking_exact_prefix_substring(names_graph):
    idx = PlayerIndex(names_graph)
    r = idx.search("danilo pereira")
    assert r.ambiguous  # player 2's full name and player 3's short name both match exactly
    assert set(r.ids) == {2, 3}
    assert idx.search("dan").ids[:3] == [2, 1, 3]  # prefix tier, by rating
    assert idx.search("dan").ids[-1] == 6  # "dani" prefix too; lowest rating last
    assert idx.search("ppe").ids == [5]  # substring only
    assert not idx.search("kante").ambiguous


def test_empty_query(names_graph):
    assert PlayerIndex(names_graph).search(" ").ids == []


def test_club_search(names_graph):
    idx = ClubIndex(names_graph)
    assert idx.search("barcelona").ids == [10]  # via alias exact, or prefix of "fc barcelona"
    assert idx.search("psg").ids == []  # no fuzzy magic: add aliases if we want this
    assert idx.search("paris saint germain").ids == [13]
    assert idx.search("real").ids == [11, 12]
