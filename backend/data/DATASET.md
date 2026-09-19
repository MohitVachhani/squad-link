# Dataset provenance

| | |
|---|---|
| Dataset | EA Sports FC 24 complete player dataset (FIFA 15 → FC 24), by stefanoleone992 |
| URL | https://www.kaggle.com/datasets/stefanoleone992/ea-sports-fc-24-complete-player-dataset |
| File used | `male_players.csv` |
| Downloaded | 2026-09-19 (Kaggle CLI, 28 MB zip, `male_players.csv` 92 MB, 180,021 rows) |
| Snapshot rule | latest snapshot date per `fifa_version` (`update_as_of` in this release; it ships one update per version, taken at launch, Aug–Sep); version N → season `20(N-1)/N` |
| Filters | league_id ∈ {13 Premier League, 16 Ligue 1, 19 Bundesliga, 31 Serie A, 53 La Liga}; overall ≥ 70; club required. **By id, not name**: "Bundesliga" also = Austria (80), "Serie A" also = Brazil (7), "Premier League" also = Russia (67), Ukraine (332), South Africa (347), and some 2nd tiers reuse the name. |
| Identity | player = `player_id`, club = `club_team_id` (display name from latest version, older names kept as aliases) |

## Build output (update after each rebuild)

Build of 2026-09-19 with default filters:

- rows 180,021 → kept 20,154 (dropped: no club 1,865 · league 148,592 · overall < 70: 9,410)
- seasons 2014/15–2023/24 · 5,481 players · 160 clubs · 976 squads · 20,154 memberships · graph.json 1.08 MB
- avg career 3.68 seasons · squad size avg 20.6, max 33
- components: 2; largest 5,478/5,481 (99.9%). The other one is a 3-player Paderborn 2014/15 island.
- BFS distance over 300 random pairs: median 3, max 4 ({1: 1, 2: 53, 3: 201, 4: 45}). That's dense: most
  puzzles are 3 hops. To stretch distances, raise `--min-overall`.

## History

| graph_version | date | change |
|---|---|---|
| 1 | 2026-09-19 | initial build |
