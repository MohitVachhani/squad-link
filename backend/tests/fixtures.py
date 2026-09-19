"""A tiny synthetic male_players.csv in the real Kaggle schema (plus a couple of extra columns we must ignore).

World (latest snapshots only):
  2014/15: Barcelona(241, named "Barcelona")  {Messi 1, Neymar 2, Bridge 13, LowRated 9 (60 ovr)}
           Real Madrid(243)                    {Ronaldo 3, Mover 5, Danilo-BR 6}
           Cádiz CF(1968)                      {Danilo-PT 7, Kanté 8}
           Juventus(45)                        {JuveGuy 12}
           Austria Wien(15040, non-top-5)      {Austrian 11}
           no club                             {FreeAgent 10}
  2015/16: Barcelona(241, renamed "FC Barcelona") {Messi 1, Neymar 2}
           Real Madrid(243)                    {Ronaldo 3, Bridge 13}
           Juventus(45)                        {Mover 5, JuveGuy 12, Kanté 8}
Earlier roster updates put Mover at Juventus in 2014/15 — they must be ignored.
"""

from __future__ import annotations

import csv
from pathlib import Path

HEADER = [
    "player_id", "player_url", "fifa_version", "fifa_update", "fifa_update_date", "short_name", "long_name",
    "overall", "potential", "dob", "league_id", "league_name", "league_level", "club_team_id", "club_name",
    "nationality_name",
]

# club_team_id -> (league_id, league_name). Austria's league is also called "Bundesliga", like in the real data.
CLUBS = {
    241: (53, "La Liga"), 243: (53, "La Liga"), 1968: (53, "La Liga"), 45: (31, "Serie A"),
    15040: (80, "Bundesliga"),
}

PEOPLE = {
    1: ("L. Messi", "Lionel Andrés Messi Cuccittini", "1987-06-24", "Argentina"),
    2: ("Neymar Jr", "Neymar da Silva Santos Júnior", "1992-02-05", "Brazil"),
    3: ("Cristiano Ronaldo", "Cristiano Ronaldo dos Santos Aveiro", "1985-02-05", "Portugal"),
    5: ("A. Mover", "Adam Mover", "1990-01-01", "England"),
    6: ("Danilo", "Danilo Luiz da Silva", "1991-07-15", "Brazil"),
    7: ("Danilo", "Danilo Pereira", "1991-09-09", "Portugal"),
    8: ("N. Kanté", "N'Golo Kanté", "1991-03-29", "France"),
    9: ("L. Rated", "Low Rated", "1995-01-01", "Spain"),
    10: ("F. Agent", "Free Agent", "1990-01-01", "Spain"),
    11: ("A. Wiener", "Anton Wiener", "1993-01-01", "Austria"),
    12: ("J. Guy", "Juve Guy", "1992-01-01", "Italy"),
    13: ("B. Bridge", "Ben Bridge", "1994-01-01", "Wales"),
}

# (player_id, club_team_id | None, club_name | None, overall, fifa_version, update_date)
ROWS = [
    # FIFA 15 early update (superseded)
    (1, 241, "Barcelona", 93, 15, "2014-09-18"),
    (5, 45, "Juventus", 80, 15, "2014-09-18"),
    # FIFA 15 latest update
    (1, 241, "Barcelona", 93, 15, "2015-02-22"),
    (2, 241, "Barcelona", 88, 15, "2015-02-22"),
    (13, 241, "Barcelona", 72, 15, "2015-02-22"),
    (9, 241, "Barcelona", 60, 15, "2015-02-22"),
    (3, 243, "Real Madrid", 92, 15, "2015-02-22"),
    (5, 243, "Real Madrid", 80, 15, "2015-02-22"),
    (6, 243, "Real Madrid", 78, 15, "2015-02-22"),
    (7, 1968, "Cádiz CF", 72, 15, "2015-02-22"),
    (8, 1968, "Cádiz CF", 75, 15, "2015-02-22"),
    (12, 45, "Juventus", 85, 15, "2015-02-22"),
    (11, 15040, "Austria Wien", 72, 15, "2015-02-22"),
    (10, None, None, 74, 15, "2015-02-22"),
    # FIFA 16 early update (superseded)
    (1, 241, "FC Barcelona", 94, 16, "2015-09-21"),
    # FIFA 16 latest update
    (1, 241, "FC Barcelona", 94, 16, "2016-03-01"),
    (2, 241, "FC Barcelona", 90, 16, "2016-03-01"),
    (3, 243, "Real Madrid", 93, 16, "2016-03-01"),
    (13, 243, "Real Madrid", 74, 16, "2016-03-01"),
    (5, 45, "Juventus", 81, 16, "2016-03-01"),
    (12, 45, "Juventus", 86, 16, "2016-03-01"),
    (8, 45, "Juventus", 79, 16, "2016-03-01"),
]


def write_fixture_csv(path: Path, extra_rows: list[tuple] = (), date_column: str = "fifa_update_date") -> Path:
    header = [date_column if c == "fifa_update_date" else c for c in HEADER]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for pid, cid, cname, ovr, version, date in [*ROWS, *extra_rows]:
            short, long, dob, nation = PEOPLE[pid]
            league_id, league = CLUBS[cid] if cid else ("", "")
            w.writerow([
                pid, f"/player/{pid}", f"{version}.0", 2, date, short, long, ovr, ovr + 2, dob,
                f"{league_id}.0" if cid else "", league, "1" if cid else "", f"{cid}.0" if cid else "",
                cname or "", nation,
            ])
    return path
