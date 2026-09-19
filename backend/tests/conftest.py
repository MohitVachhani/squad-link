import pytest

from squadlink.engine import Graph

S1, S2, S3 = "2014/15", "2015/16", "2016/17"
BIG, MID, SMALL, OTHER = 1, 2, 3, 4  # club ids


def _player(name, full=None, nation="X", ovr=80):
    return {"name": name, "full": full or name, "nation": nation, "dob": "1990-01-01", "ovr": ovr}


def graph_data() -> dict:
    """Hand-built graph.

    BIG   2014/15: A B C D E F G H       (8 players — the biggest squad)
    BIG   2015/16: A X
    MID   2015/16: B Y Z
    SMALL 2016/17: Z T
    OTHER 2014/15: C T
    OTHER 2016/17: X Q
    """
    players = {
        "1": _player("A"), "2": _player("B"), "3": _player("C"), "4": _player("D"), "5": _player("E"),
        "6": _player("F"), "7": _player("G"), "8": _player("H"), "20": _player("X"), "21": _player("Y"),
        "22": _player("Z"), "23": _player("T"), "24": _player("Q"),
    }
    ids = {p["name"]: int(pid) for pid, p in players.items()}
    squads = {
        (BIG, S1): "ABCDEFGH", (BIG, S2): "AX", (MID, S2): "BYZ", (SMALL, S3): "ZT",
        (OTHER, S1): "CT", (OTHER, S3): "XQ",
    }
    memberships = [[ids[n], cid, season] for (cid, season), names in squads.items() for n in names]
    return {
        "meta": {"graph_version": 1},
        "players": players,
        "clubs": {
            str(BIG): {"name": "Big FC", "league": "L"}, str(MID): {"name": "Mid United", "league": "L"},
            str(SMALL): {"name": "Small Town", "league": "L"}, str(OTHER): {"name": "Other Athletic", "league": "L"},
        },
        "memberships": memberships,
    }


@pytest.fixture
def graph() -> Graph:
    return Graph(graph_data())


@pytest.fixture
def ids(graph):
    return {p.name: pid for pid, p in graph.players.items()}
