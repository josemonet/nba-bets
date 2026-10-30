# NFL research: how the nfl-player-props engine was calibrated and tested

Everything runs from the repo root (about 10 minutes for the analyses and 1-2 minutes per backtest season range on 8 cores).

## Setup
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install numpy scipy pandas pytest
research/nfl/fetch_data.sh          # nflverse play-by-play 2016-26, snap counts, injuries, players, schedule with lines -> data/raw/nfl/ (not committed)
python research/nfl/data.py         # player-game and team-game tables -> data/cache/nfl/tables.pkl
research/nfl/run_all.sh             # every analysis, the passing calibration, the 2023-25 backtest and the audit -> research/nfl/results/
```
Data: [nflverse](https://github.com/nflverse/nflverse-data) play-by-play (481,511 regular-season plays, 2,746 games, 2016 through 2026 week 7) and [nflverse/nfldata](https://github.com/nflverse/nfldata) games.csv (closing spread, total, roof, weather, rest). data.py derives official-stat player lines from the plays (the 2025-26 player_stats files 404) and was checked against official 2023 weekly stats. Team codes are normalized (OAK to LV, SD to LAC, STL to LA) and snap counts are joined so a player who played and touched nothing counts as zeros.

## Analyses (research/nfl/analyses; outputs in research/nfl/results)
| Script | What it measures | Where it lands in the engine |
|---|---|---|
| 01_game_level.py | Margin and total SDs around the closing line, key numbers, overtime, team points vs the implied total, the TD/FG split, pass share of TDs by margin | game constants, TD_RATE, PASS_TD_SLOPE |
| 02_volume_script.py | Plays and pass rate vs the market and the realized script; sacks, scrambles, kneels | PLAYS, PLAYS_PTS, PASS_RATE, KNEELS |
| 03_shares.py | Game-to-game dispersion of target and carry shares beyond binomial | TGT_KAPPA, CAR_KAPPA (raw) |
| 04_share_projection.py | Recency and prior weight for the next-game share | SHARE_HL, SHARE_K |
| 05_per_play.py | Catch rate by depth, per-catch and per-carry yard shapes, efficiency shrinkage | SHAPE, EFF_K |
| 06_td_allocation.py | Which share predicts who scores; position factors | REC_TD_W, RUSH_TD_W, REC_TD_POS, RUSH_TD_POS |
| 07_absences.py | Teammates' shares when a key pass-catcher, the lead back or the QB sits | usage_shift_nfl() |
| 08_opponent_weather.py | Opponent and defense-vs-position effects beyond the lines; wind, temperature, roof, home | weather() (opponent effects rejected) |
| 09_qb_def_kick.py | QB rate reliability, QB rushing, tackles, kicking by implied total | QB_K, TKL_EXTRA |
| 10_engine_tables.py | Drives, TD and FG rates by implied points, per-catch and per-carry shape tables | DRIVES, TD_RATE, FGA_RATE, SHAPE |
| 11_market_quality.py | What the market's view of team quality explains beyond the shrunk team inputs (2020-22 fit, 2023-25 test) | IMP_EFF |

Fitting and checks:
- calibrate_passing.py: joint grid over the per-catch spread, depth shock, score-link scale, field constraint and target-share noise against within-team-season moments (team passing yards SD 69.7, a WR1's yards SD 39.3, QB-WR1 correlation 0.47).
- backtest.py [first] [last] [n_sims] [tag]: walk-forward scoring of every game in the range, old football_model (old_football_model.py) vs this engine, with identical pregame inputs (season-to-date team and player inputs, fresh-absence usage shifts, return discounts, the share budget, the first-snap QB). NO_BUDGET=1 turns off the share budget; DRIFT_K carries part of the recent over/under drift into totals (tested, not adopted).
- audit.py [backtest.pkl]: 50/80/90% coverage and bias by stat, position, uncertainty tier, games into the season, spread, first game back, absence shift and season, plus anytime-TD calibration bands.

Results and every constant: skills/nfl-player-props/references/calibration.md.

Limits: there are no historical prop prices in the data, so the backtest's lines are book-style proxies (the season average). It shows the probabilities are honest and sharper than the old model; tracked CLV and results show whether they beat the books.
