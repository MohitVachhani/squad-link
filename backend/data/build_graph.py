#!/usr/bin/env python3
"""raw/male_players.csv -> graph.json.

The only code that reads the raw Kaggle CSV. Deterministic: same input + flags = same output
(apart from meta.built_at). Validation failures exit non-zero and graph.json is not written.

    uv run python data/build_graph.py                    # top-5 leagues, overall >= 70
    uv run python data/build_graph.py --all-leagues --min-overall 75
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from squadlink.engine.graph import Graph

HERE = Path(__file__).resolve().parent
DEFAULT_CSV = HERE / "raw" / "male_players.csv"
DEFAULT_OUT = HERE / "graph.json"

GRAPH_VERSION = 1
SOURCE = "Kaggle: stefanoleone992/ea-sports-fc-24-complete-player-dataset (male_players.csv)"
# Filter on league_id, not league_name: names collide across countries and tiers in this dataset
# ("Bundesliga" = Germany 19 + Austria 80, "Serie A" = Italy 31 + Brazil 7, "Premier League" = England 13 +
# Russia/Ukraine/South Africa, and some second tiers share the top tier's name).
TOP5_LEAGUE_IDS = {13: "Premier League", 16: "Ligue 1", 19: "Bundesliga", 31: "Serie A", 53: "La Liga"}

COLUMNS = [
    "player_id", "short_name", "long_name", "dob", "nationality_name", "club_name", "club_team_id",
    "league_id", "league_name", "league_level", "overall", "fifa_version",
]
# The snapshot date column: older dataset releases call it fifa_update_date, the current one update_as_of.
DATE_COLUMNS = ("fifa_update_date", "update_as_of")
STR_COLUMNS = {c: "string" for c in ("short_name", "long_name", "dob", "nationality_name", "club_name",
                                      "league_name", *DATE_COLUMNS)}


def season_label(version: int) -> str:
    """24 -> '2023/24', 15 -> '2014/15'."""
    return f"{2000 + version - 1}/{version % 100:02d}"


def _iso_date(col: pd.Series) -> pd.Series:
    return pd.to_datetime(col, errors="coerce").dt.strftime("%Y-%m-%d")


def date_column(csv_path: Path) -> str:
    header = pd.read_csv(csv_path, nrows=0).columns
    for c in DATE_COLUMNS:
        if c in header:
            return c
    raise SystemExit(f"{csv_path}: none of the snapshot date columns {DATE_COLUMNS} present")


def _chunks(csv_path: Path, columns: list[str], chunksize: int):
    dtypes = {c: t for c, t in STR_COLUMNS.items() if c in columns}
    for chunk in pd.read_csv(csv_path, usecols=columns, dtype=dtypes, chunksize=chunksize):
        yield chunk.rename(columns={c: "update_date" for c in DATE_COLUMNS})


# --- load ----------------------------------------------------------------------------------------------


def latest_updates(csv_path: Path, chunksize: int) -> dict[int, str]:
    """Pass 1 (two columns only): the latest snapshot date per fifa_version."""
    latest: dict[int, str] = {}
    for chunk in _chunks(csv_path, ["fifa_version", date_column(csv_path)], chunksize):
        chunk = chunk.dropna(subset=["fifa_version"])
        dates = _iso_date(chunk["update_date"])
        for version, date in dates.groupby(chunk["fifa_version"].astype(int)).max().items():
            if isinstance(date, str) and date > latest.get(version, ""):
                latest[int(version)] = date
    return latest


def load_rows(
    csv_path: Path,
    latest: dict[int, str],
    league_ids: tuple[int, ...] | None,
    min_overall: int,
    chunksize: int,
) -> tuple[pd.DataFrame, Counter, dict[int, set[str]]]:
    """Pass 2: keep one snapshot per version, then apply filters. Returns rows, counters, leagues seen."""
    stats: Counter = Counter()
    level1_leagues: dict[int, set[str]] = defaultdict(set)
    kept = []
    for chunk in _chunks(csv_path, [*COLUMNS, date_column(csv_path)], chunksize):
        stats["rows_read"] += len(chunk)
        chunk = chunk.dropna(subset=["player_id", "fifa_version"])
        chunk = chunk.assign(
            fifa_version=chunk["fifa_version"].astype(int),
            update_date=_iso_date(chunk["update_date"]),
        )
        chunk = chunk[chunk["update_date"] == chunk["fifa_version"].map(latest)]
        stats["snapshot_rows"] += len(chunk)

        top = chunk[chunk["league_level"] == 1]
        for (version, lid), names in top.groupby(["fifa_version", "league_id"])["league_name"].unique().items():
            level1_leagues[int(version)].update(f"{n} ({int(lid)})" for n in names if pd.notna(n))

        has_club = chunk["club_team_id"].notna() & chunk["club_name"].notna()
        stats["dropped_no_club"] += int((~has_club).sum())
        chunk = chunk[has_club]
        if league_ids is not None:
            in_league = chunk["league_id"].isin(league_ids)
            stats["dropped_league"] += int((~in_league).sum())
            chunk = chunk[in_league]
        rated = chunk["overall"] >= min_overall
        stats["dropped_overall"] += int((~rated).sum())
        kept.append(chunk[rated])

    df = pd.concat(kept, ignore_index=True) if kept else pd.DataFrame(columns=COLUMNS)
    df = df.astype({"player_id": int, "club_team_id": int, "overall": int, "league_id": "Int64"})
    df["season"] = df["fifa_version"].map(season_label)
    stats["kept_rows"] = len(df)
    return df, stats, level1_leagues


# --- build ---------------------------------------------------------------------------------------------


def _str_or_none(v) -> str | None:
    return None if pd.isna(v) else str(v)


def build_graph(df: pd.DataFrame, latest: dict[int, str], filters: dict) -> dict:
    df = df.sort_values(["player_id", "fifa_version", "club_team_id"], kind="stable")

    players = {}
    peak = df.groupby("player_id")["overall"].max()
    for row in df.drop_duplicates("player_id", keep="last").itertuples(index=False):
        players[str(row.player_id)] = {
            "name": str(row.short_name),
            "full": _str_or_none(row.long_name) or str(row.short_name),
            "nation": _str_or_none(row.nationality_name) or "",
            "dob": _str_or_none(row.dob),
            "ovr": int(peak[row.player_id]),
        }

    by_club = df.sort_values(["club_team_id", "fifa_version", "club_name"], kind="stable")
    names_per_club = by_club.groupby("club_team_id")["club_name"].unique()
    clubs = {}
    for row in by_club.drop_duplicates("club_team_id", keep="last").itertuples(index=False):
        aliases = sorted({str(n) for n in names_per_club[row.club_team_id]} - {str(row.club_name)})
        clubs[str(row.club_team_id)] = {"name": str(row.club_name), "league": str(row.league_name)}
        if aliases:
            clubs[str(row.club_team_id)]["aliases"] = aliases

    memberships = sorted({(int(r.player_id), int(r.club_team_id), r.season) for r in df.itertuples(index=False)})
    versions = sorted(int(v) for v in df["fifa_version"].unique())
    return {
        "meta": {
            "source": SOURCE,
            "graph_version": GRAPH_VERSION,
            "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "versions": versions,
            "seasons": [season_label(v) for v in versions],
            "snapshots": {season_label(v): latest[v] for v in versions},
            "filters": filters,
            "players": len(players),
            "clubs": len(clubs),
            "memberships": len(memberships),
        },
        "players": players,
        "clubs": clubs,
        "memberships": [list(m) for m in memberships],
    }


# --- validate ------------------------------------------------------------------------------------------


def validate(
    df: pd.DataFrame,
    graph: dict,
    level1_leagues: dict[int, set[str]],
    league_ids: tuple[int, ...] | None,
    min_lcc: float,
) -> list[str]:
    errors: list[str] = []

    dupes = df[df.duplicated(["player_id", "fifa_version"], keep=False)]
    if len(dupes):
        cols = ["player_id", "short_name", "club_name", "club_team_id", "season"]
        errors.append(f"{dupes['player_id'].nunique()} player(s) appear twice in one season:\n"
                      + dupes[cols].head(10).to_string(index=False))

    bad_refs = [m for m in graph["memberships"]
                if str(m[0]) not in graph["players"] or str(m[1]) not in graph["clubs"]]
    if bad_refs:
        errors.append(f"{len(bad_refs)} membership(s) reference unknown players/clubs, e.g. {bad_refs[:5]}")

    if league_ids is not None:
        seen = df.groupby("fifa_version")["league_id"].unique()
        for version in graph["meta"]["versions"]:
            missing = sorted(set(league_ids) - {int(x) for x in seen.get(version, [])})
            if missing:
                available = ", ".join(sorted(level1_leagues.get(version, set()))[:15])
                errors.append(f"{season_label(version)}: no rows for league_id {missing}. "
                              f"Level-1 leagues in this version: {available}")

    g = Graph(graph)
    comps = g.components()
    n = len(g.player_squads)
    largest = len(comps[0]) if comps else 0
    print(f"components: {len(comps)}  largest: {largest}/{n} ({largest / max(n, 1):.1%})")
    if n and largest / n < min_lcc:
        errors.append(f"largest component has {largest / n:.1%} of players (< {min_lcc:.0%}); loosen filters")
    return errors


# --- report --------------------------------------------------------------------------------------------


def report(graph: dict, stats: Counter, samples: int, seed: int) -> None:
    g = Graph(graph)
    m = graph["meta"]
    print(f"rows read {stats['rows_read']:,} -> latest snapshots {stats['snapshot_rows']:,} -> kept {stats['kept_rows']:,}"
          f"  (dropped: no club {stats['dropped_no_club']:,}, league {stats['dropped_league']:,}, "
          f"overall {stats['dropped_overall']:,})")
    print(f"seasons: {g.season_range}  snapshots: {m['snapshots']}")
    careers = [len(s) for s in g.player_squads.values()]
    sizes = [len(p) for p in g.squads.values()]
    print(f"players {m['players']:,}  clubs {m['clubs']:,}  memberships {m['memberships']:,}  squads {len(sizes):,}")
    if not careers:
        return
    print(f"avg career {statistics.mean(careers):.2f} seasons  "
          f"squad size avg {statistics.mean(sizes):.1f} / max {max(sizes)}")

    rng = random.Random(seed)
    largest = sorted(g.components()[0])
    if len(largest) < 2:
        return
    dists = []
    for _ in range(300):
        a, b = rng.sample(largest, 2)
        dists.append(g.distances_from(a)[b])
    median = statistics.median(dists)
    print(f"BFS distance over 300 random pairs: median {median}, max {max(dists)}, "
          f"histogram {dict(sorted(Counter(dists).items()))}")
    if median < 2:
        print("WARNING: median distance < 2 — graph too dense, tighten filters")
    elif median > 6:
        print("WARNING: median distance > 6 — graph too sparse, loosen filters")

    famous = [p for p in largest if (g.players[p].ovr or 0) >= 80] or largest
    print(f"sample puzzles (players with peak overall >= 80 where possible, {len(famous)} candidates):")
    for _ in range(samples):
        a, b = rng.sample(famous, 2)
        path = g.shortest_path(a, b) or []
        print(f"  {g.players[a].name} -> {g.players[b].name}: {len(path) - 1} hops  "
              f"[{' > '.join(g.players[p].name for p in path)}]")


# --- output --------------------------------------------------------------------------------------------


def write_json(graph: dict, out: Path) -> None:
    """One player / club / membership per line so git diffs stay readable."""
    def dumps(v) -> str:
        return json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    def obj(d: dict) -> str:
        return ",\n".join(f"{json.dumps(k)}:{dumps(d[k])}" for k in sorted(d, key=int))

    body = [
        '{"meta":' + json.dumps(graph["meta"], ensure_ascii=False, sort_keys=True, indent=1),
        ',"players":{\n' + obj(graph["players"]) + "\n}",
        ',"clubs":{\n' + obj(graph["clubs"]) + "\n}",
        ',"memberships":[\n' + ",\n".join(dumps(m) for m in graph["memberships"]) + "\n]}\n",
    ]
    tmp = out.with_suffix(".json.tmp")
    tmp.write_text("\n".join(body), encoding="utf-8")
    tmp.replace(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--all-leagues", action="store_true", help="disable the top-5 league filter")
    ap.add_argument("--league-ids", default=",".join(map(str, sorted(TOP5_LEAGUE_IDS))),
                    help="comma-separated league_id values (default: top 5 European leagues)")
    ap.add_argument("--min-overall", type=int, default=70)
    ap.add_argument("--min-lcc", type=float, default=0.95, help="min share of players in the largest component")
    ap.add_argument("--chunksize", type=int, default=200_000)
    ap.add_argument("--samples", type=int, default=5)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args(argv)

    if not args.csv.exists():
        print(f"missing {args.csv} — run `make download` first", file=sys.stderr)
        return 2
    league_ids = None if args.all_leagues else tuple(sorted(int(s) for s in args.league_ids.split(",") if s.strip()))
    filters = {"league_ids": list(league_ids) if league_ids else "all", "min_overall": args.min_overall}

    latest = latest_updates(args.csv, args.chunksize)
    df, stats, level1 = load_rows(args.csv, latest, league_ids, args.min_overall, args.chunksize)
    graph = build_graph(df, latest, filters)
    report(graph, stats, args.samples, args.seed)
    errors = validate(df, graph, level1, league_ids, args.min_lcc)
    if errors:
        print("\nBUILD FAILED:", file=sys.stderr)
        for e in errors:
            print(f"- {e}", file=sys.stderr)
        return 1
    write_json(graph, args.out)
    print(f"wrote {args.out} ({args.out.stat().st_size / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
