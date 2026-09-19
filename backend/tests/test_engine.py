import math
import random

import pytest

from squadlink.engine import (
    GameState, MoveError, MoveErrorCode, RandomPuzzleSource, Status, apply_move, build_result, give_up,
    link_rarity, optimal_hops, score, truncate, validate_move,
)
from squadlink.engine.scoring import rarity_for_size
from conftest import BIG, MID, OTHER, S1, S2, S3, SMALL


# --- graph ------------------------------------------------------------------------------------------


def test_graph_basics(graph, ids):
    assert graph.seasons == [S1, S2, S3]
    assert graph.season_range == "2014/15–2016/17"
    assert graph.max_squad_size == 8
    assert graph.shared_seasons(ids["A"], ids["B"], BIG) == [S1]
    assert graph.shared_seasons(ids["A"], ids["X"], BIG) == [S2]
    assert graph.are_teammates(ids["A"], ids["H"])
    assert not graph.are_teammates(ids["A"], ids["Y"])
    assert graph.neighbors(ids["Z"]) == {ids["B"], ids["Y"], ids["T"]}


def test_bfs(graph, ids):
    assert graph.shortest_path(ids["A"], ids["A"]) == [ids["A"]]
    assert graph.shortest_path(ids["A"], ids["Y"]) == [ids["A"], ids["B"], ids["Y"]]
    assert len(graph.shortest_path(ids["Y"], ids["Q"])) - 1 == 4  # Y-B-A-X-Q
    assert graph.distances_from(ids["T"])[ids["Q"]] == 4  # T-C-A-X-Q
    assert graph.shortest_path(ids["A"], 999) is None


def test_components(graph):
    comps = graph.components()
    assert len(comps) == 1 and len(comps[0]) == len(graph.players)


# --- rules ------------------------------------------------------------------------------------------


def play(graph, state, *moves):
    for next_id, club in moves:
        state = apply_move(graph, state, next_id, club)
    return state


def expect_error(graph, state, next_id, club, code):
    with pytest.raises(MoveError) as e:
        validate_move(graph, state, next_id, club)
    assert e.value.code == code
    return e.value


def test_valid_move_and_win(graph, ids):
    s = GameState(ids["A"], ids["Y"])
    s = play(graph, s, (ids["B"], BIG))
    assert s.status is Status.IN_PROGRESS and s.current_id == ids["B"]
    assert s.hops[0].seasons == (S1,)
    s = play(graph, s, (ids["Y"], MID))
    assert s.status is Status.WON
    assert s.chain == [ids["A"], ids["B"], ids["Y"]]


def test_errors(graph, ids):
    s = GameState(ids["A"], ids["Q"])
    expect_error(graph, s, 999, BIG, MoveErrorCode.UNKNOWN_PLAYER)
    expect_error(graph, s, ids["B"], 999, MoveErrorCode.UNKNOWN_CLUB)
    expect_error(graph, s, ids["A"], BIG, MoveErrorCode.SAME_PLAYER)
    expect_error(graph, s, ids["Z"], SMALL, MoveErrorCode.CURRENT_NOT_AT_CLUB)
    expect_error(graph, s, ids["Y"], BIG, MoveErrorCode.NEXT_NOT_AT_CLUB)

    err = expect_error(graph, s, ids["T"], OTHER, MoveErrorCode.CURRENT_NOT_AT_CLUB)
    assert "A never played for Other Athletic" in err.message

    # C was at BIG in 2014/15 and X in 2015/16: same club, different seasons.
    s2 = GameState(ids["C"], ids["Q"])
    err = expect_error(graph, s2, ids["X"], BIG, MoveErrorCode.DIFFERENT_SEASONS)
    assert "not in the same season" in err.message and "2014/15" in err.message and "2015/16" in err.message


def test_same_club_twice_in_a_row(graph, ids):
    s = play(graph, GameState(ids["B"], ids["Q"]), (ids["A"], BIG))
    # A -> X shares only BIG (2015/16). BIG was just used (2014/15): blocked, even across seasons.
    expect_error(graph, s, ids["X"], BIG, MoveErrorCode.SAME_CLUB_TWICE)
    # After a hop through a different club, BIG is allowed again.
    s = play(graph, GameState(ids["Y"], ids["Q"]), (ids["B"], MID), (ids["A"], BIG))
    assert s.last_club_id == BIG


def test_no_revisits(graph, ids):
    s = play(graph, GameState(ids["A"], ids["Q"]), (ids["B"], BIG), (ids["Z"], MID))
    s = play(graph, s, (ids["T"], SMALL), (ids["C"], OTHER))
    expect_error(graph, s, ids["A"], BIG, MoveErrorCode.ALREADY_IN_CHAIN)


def test_game_over(graph, ids):
    s = play(graph, GameState(ids["A"], ids["B"]), (ids["B"], BIG))
    expect_error(graph, s, ids["C"], BIG, MoveErrorCode.GAME_OVER)
    s = give_up(GameState(ids["A"], ids["Q"]))
    assert s.status is Status.ABANDONED
    expect_error(graph, s, ids["B"], BIG, MoveErrorCode.GAME_OVER)


def test_truncate(graph, ids):
    s = play(graph, GameState(ids["A"], ids["Q"]), (ids["B"], BIG), (ids["Z"], MID), (ids["T"], SMALL))
    assert truncate(s, 2).chain == [ids["A"], ids["B"], ids["Z"]]  # undo last
    s1 = truncate(s, 1)  # remove Z and everything after it
    assert s1.chain == [ids["A"], ids["B"]] and s1.last_club_id == BIG
    # The club rule follows the new last hop: after truncating to 0, BIG is usable again from A.
    assert truncate(s, 0).last_club_id is None
    apply_move(graph, truncate(s, 0), ids["X"], BIG)
    # Removed players can be used again.
    assert apply_move(graph, s1, ids["Z"], MID).chain[-1] == ids["Z"]
    for bad in (-1, 3):
        with pytest.raises(MoveError) as e:
            truncate(s, bad)
        assert e.value.code == MoveErrorCode.NO_SUCH_HOP
    with pytest.raises(MoveError) as e:
        truncate(give_up(s), 0)
    assert e.value.code == MoveErrorCode.GAME_OVER


def test_state_is_immutable(graph, ids):
    s0 = GameState(ids["A"], ids["Y"])
    s1 = apply_move(graph, s0, ids["B"], BIG)
    assert s0.hops == () and len(s1.hops) == 1


# --- scoring ----------------------------------------------------------------------------------------


def test_rarity_formula():
    assert rarity_for_size(8, 8) == 0
    assert rarity_for_size(2, 8) == pytest.approx(1 - math.log(2) / math.log(8))  # 2/3
    assert rarity_for_size(4, 8) == pytest.approx(1 / 3)
    assert rarity_for_size(1, 1) == 0


def test_link_rarity_uses_rarest_shared_season(graph):
    assert link_rarity(graph, BIG, [S1]) == 0  # squad of 8 = max
    assert link_rarity(graph, BIG, [S1, S2]) == pytest.approx(2 / 3)  # 15/16 squad has 2
    assert link_rarity(graph, MID, [S2]) == pytest.approx(1 - math.log(3) / math.log(8))


def test_score_components():
    b = score(hops=4, optimal=3, rarities=[0.0, 0.5, 1.0, 0.5])
    assert b.efficiency == 0.75 and b.rarity == 0.5
    assert b.efficiency_points == 52.5 and b.rarity_points == 15.0 and b.total == 67.5
    perfect = score(hops=2, optimal=2, rarities=[1, 1])
    assert perfect.total == 100
    # Can't beat the lower bound, but cap anyway in case the graph changed under a stored game.
    assert score(hops=1, optimal=2, rarities=[0]).efficiency == 1


def test_result_and_share_text(graph, ids):
    s = play(graph, GameState(ids["T"], ids["Y"]), (ids["C"], OTHER), (ids["B"], BIG), (ids["Y"], MID))
    r = build_result(graph, s)
    assert r.status is Status.WON
    assert [h.to_id for h in r.optimal_hops] == [ids["Z"], ids["Y"]]  # T-Z (Small) - Y (Mid)
    assert r.score.hops == 3 and r.score.optimal_hops == 2
    assert r.data_range == "2014/15–2016/17"
    lines = r.share_text.splitlines()
    assert lines[0] == "Squadlink ⚽ T → Y"
    assert lines[1].startswith("3 hops (best 2, +1)")
    assert len(lines[2]) == 3  # one square per hop
    assert "Z" not in r.share_text.replace("⚽", "")  # never spoils the path


def test_result_for_give_up_has_no_score(graph, ids):
    r = build_result(graph, give_up(GameState(ids["A"], ids["Q"])))
    assert r.score is None and r.share_text is None
    assert len(r.optimal_hops) == 2


def test_result_requires_finished_game(graph, ids):
    with pytest.raises(ValueError):
        build_result(graph, GameState(ids["A"], ids["Q"]))


def test_optimal_hops_avoid_repeating_club_when_possible(graph, ids):
    hops = optimal_hops(graph, ids["B"], ids["X"])  # B -BIG 14/15- A -BIG 15/16- X
    assert [h.club_id for h in hops] == [BIG, BIG]  # only option; BFS is a lower bound
    hops = optimal_hops(graph, ids["Y"], ids["T"])  # Y -MID- Z -SMALL- T
    assert [h.club_id for h in hops] == [MID, SMALL]


# --- puzzles ----------------------------------------------------------------------------------------


def test_random_puzzles_respect_distance(graph):
    src = RandomPuzzleSource(graph, min_hops=3, max_hops=4, min_ovr=0, rng=random.Random(1))
    for _ in range(20):
        p = src.next()
        assert 3 <= p.optimal_hops <= 4
        assert p.optimal_hops == len(graph.shortest_path(p.start_id, p.end_id)) - 1
        assert p.optimal_path[0] == p.start_id and p.optimal_path[-1] == p.end_id


def test_random_puzzles_impossible_distance(graph):
    src = RandomPuzzleSource(graph, min_hops=9, max_hops=9, min_ovr=0, rng=random.Random(1), max_tries=5)
    with pytest.raises(RuntimeError):
        src.next()
