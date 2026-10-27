# Research: how the v2 engine was calibrated and tested

Everything here runs from the repo root on a laptop (about 15 minutes for the analyses, 10 for the full backtest on 4 cores).

## Setup
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install numpy scipy pandas pytest
research/fetch_data.sh            # 2010-11 to 2023-24 box scores (about 75 MB) into data/raw/, not committed
python research/data.py           # cleaned player-game table -> data/cache/player_games.pkl
```
Data: [NocturneBear/NBA-Data-2010-2024](https://github.com/NocturneBear/NBA-Data-2010-2024), 424,478 player rows (351,409 played) in 16,658 regular-season games. Starters are the rows with a position; margins, overtime periods and possessions come from the team totals file.

## Analyses (run in order; later ones read caches written by earlier ones)
| Script | What it measures | Where it lands in the engine |
|---|---|---|
| analyses/01_game_script.py | Overtime rate by spread, margin SD, blowout share by season, pace noise | SIG, OT_PEAK, OT_WIDTH, OT_MORE, POSS_SD |
| analyses/02_minutes_by_margin.py | Minutes vs final margin by role, overtime minutes, close-game effect | ROLE[...]['dm'], ROLE[...]['ot'] |
| analyses/03_minutes_projection.py | Which pregame minutes projection predicts best (EWMA, last-N, season) | MIN_HALFLIFE |
| analyses/04_count_dispersion.py | Variance/mean of every stat at fixed minutes and pace; cross-stat correlations | PHI, FGA_D |
| analyses/05_shooting_and_teammates.py | Game-level shooting overdispersion; teammate correlations | KAPPA, PCT_N, SIG_U |
| analyses/06_usage_absences.py | Teammates' minutes and rates when a key player sits | usage_shift() |
| analyses/07_usage_split_sample.py | The same, with split samples so noisy rates can't fake the pattern | usage_shift() |
| analyses/08_shrinkage.py | Prior weight on last season and the last-10 blend, by stat | STAB, RECENT_W |
| analyses/09_matchups_home_rest.py | Opponent factors, defense-vs-position, home and back-to-back effects | MATCH_K, HOME |
| analyses/10_minutes_noise_modern.py | Minutes noise around the engine's projection (2014-24), role changes, era check | ROLE noise, reg, PROMOTED, DEMOTED |
| analyses/11_rate_uncertainty.py | Leftover rate uncertainty by sample size; realized-pace elasticity | rate_cv defaults (then tuned below) |
| analyses/12_pace_elasticity.py | Stat elasticity to pregame expected pace | pace scaling (kept at 1) |
| analyses/13_foul_tail_and_combos.py | Foul rate vs minutes-loss tail; home factors; combo-prop dispersion | PF_KNOTS, PF_TAIL, HOME |
| analyses/14_minutes_pull.py | Pulling recent minutes toward the season average | MIN_PULL |
| analyses/15_engine_checks.py | The engine's variance and same-game correlations vs the data | ASSIST_LINK check |

Fitting and tuning:
- `python research/fit_drift.py 2014 2023`: in-season drift multipliers (DRIFT).
- `python research/tune_rate_cv.py`: RATE_CV multipliers so 50/80/90% ranges hold coverage (2014-20 rows only).

## Backtest
`python research/backtest.py 2021 2000 all 2023 [tag]` scores every 2021-22 to 2023-24 player-game (10+ prior games, 20+ projected minutes) with pregame-only inputs for three variants: v1 (the original skill's recipe and engine, `old_engine.py`), v1e (new inputs, old engine) and v2. It reports interval coverage, PIT shape, CRPS, and log loss and Brier at a book-style proxy line (his season average to date, rounded to a half point), plus calibration bands. Results: skills/nba-player-props/references/calibration.md.

Limits: there are no historical prop odds in the data, so the backtest measures how honest and sharp the probabilities are, not ROI against real lines. Track CLV and results (SKILL.md Step 15) to measure that.

## Tests
`python -m pytest -q tests` checks the odds math, pushes, the profit gate and Kelly cap, the fitted rules, same-game correlation, the parlay builder and v1 API compatibility.
