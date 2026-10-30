# nba-bets

Player prop models for Claude: `nba-player-props` (v2) and `nfl-player-props` (v1). Each is a Claude skill plus the simulation engine behind it, calibrated on real games and backtested against the version it replaced.

## Install a skill
1. Download the zip from `dist/`:
   - NBA: `dist/nba-player-props.zip`
   - NFL: `dist/nfl-player-props.zip` (one self-contained SKILL.md, the same format as the NBA skill in your Claude account), or `dist/nfl-player-props-files.zip` (the same skill split into SKILL.md, scripts/ and references/; lighter to load if your Claude accepts multi-file skills)
2. In Claude, open Settings > Capabilities > Skills, and upload the zip (replace the existing skill of the same name).
3. Ask the usual way: "Give me 5 NFL props and two parlays for Sunday" with a FanDuel screenshot, or "Is [player] over 64.5 receiving yards a bet?".

Rebuild after any change: `tools/build_skill.sh` (NBA) and `python tools/build_single.py nfl-player-props` (NFL; it checks that the single file's Step 0a command recreates the engine byte for byte).

## NFL v1 (Oct 2026)
- **One shared game simulation.** Every prop in a game (both QBs, receivers, backs, TDs, the kicker, defenders) comes from one run: plays and pass rate from the spread, total and the realized score; one team TD pool; a passing game whose catches add up to the QB's yards; real per-catch and per-carry yard shapes (so lines read as medians); starter exits; weather; kneel-downs.
- **Fitted on 481,511 plays (2016-26).** Volume, script effects, share noise, shrinkage, TD allocation, usage shifts when a teammate sits, first-game-back discounts, the team share budget, QB exits and rushing, weather and a market-quality efficiency term are all measured, not guessed. League norms are season-aware (scrambles, sneaks and pass volume have drifted).
- **Live input builder.** `nfl_inputs.py` downloads nflverse play-by-play, snap counts and the schedule with lines, and builds every input the way the backtest did (with `out=`, `back=` and lineup splits for injuries).
- **Same profit layer as NBA v2**, plus per-stat soft-spot edges, same-game stake scaling, TD-menu hold handling, first-TD pricing, exchange ladders, settlement rules, and a calibration tripwire.

Walk-forward backtest, every 2023-25 game (720 games, 11,928 player slots, pregame inputs only), old football_model vs v1 with identical inputs:

| Stat | Old: 80% range held | v1 | Old: average miss | v1 |
|---|---|---|---|---|
| Pass attempts | 56.6% | 79.8% | +5.5 | +0.5 |
| Passing yards | 73.4% | 78.9% | +35.0 | +1.1 |
| Rushing attempts | 62.7% | 79.7% | -0.45 | -0.31 |
| Rushing yards | 72.6% | 80.4% | -0.97 | +0.27 |
| Receptions | 74.1% | 78.1% | +0.36 | +0.04 |
| Receiving yards | 75.9% | 78.8% | +4.1 | +0.5 |

The old model's "64%" overs hit 54%; v1's hit 61%, and its unders hit within 1-2 points of their stated chance. Log loss and CRPS improved for every stat; anytime-TD log loss 0.495 to 0.492 (season-rate baseline 0.588). Full tables, subgroup audits, soft spots and known gaps: `skills/nfl-player-props/references/calibration.md`.

## NBA v2 (Oct 2026)
- **Calibrated engine.** Minutes noise, blowout cuts, overtime, stat variance, shooting noise, usage shifts when a teammate sits, shrinkage, home court and in-season drift are all fitted on 2010-24 box scores instead of set by hand. The v1 spreads were too tight, so its confident calls were overstated by 5-9 points.
- **Profit layer.** The score still measures the chance to hit and the evidence. A straight now also has to clear its breakeven by 2 points at the posted price, and it carries a "bet to" price, a quarter-Kelly stake cap and a line-shopping check across books. Parlays must be +EV on the simulated joint chance.
- **Market weight** in the final blend goes from 25% to 40% until tracked bets measure the right value.

Backtest (every 2021-22 to 2023-24 player-game with 20+ projected minutes, 41,382 games, pregame inputs only):

| Stat | v1: 80% range held | v2 | v1: its "64%" overs hit | v2 |
|---|---|---|---|---|
| Points | 72.8% | 80.5% | 57.8% | 64.9% |
| Rebounds | 76.6% | 80.4% | 58.5% | 62.4% |
| Assists | 76.4% | 80.6% | 63.1% | 66.2% |
| Threes | 78.1% | 80.3% | 58.8% | 59.6% |
| PRA | 70.5% | 79.7% | 57.2% | 62.9% |

No model guarantees profit. Books hold about 4.5-7% on main-line props (15-40% on TD menus, more on parlays), and neither dataset has historical prop prices, so the backtests show the probabilities are honest, not that they beat the books. Tracked CLV and results do that (each SKILL.md, Step 15). Bet only what you can afford to lose.

## Layout
```
skills/nba-player-props/       NBA skill: SKILL.md, scripts/nba_props.py, references/
skills/nfl-player-props/       NFL skill: SKILL.md, scripts/nfl_props.py and nfl_inputs.py, references/ (calibration, sources, markets)
research/                      NBA data loading, calibration analyses, backtest (research/README.md)
research/nfl/                  NFL data loading, analyses, passing calibration, backtest, audit, results (research/nfl/README.md)
tests/                         pytest suites for both engines
tools/                         build_skill.sh (NBA zip), build_single.py (single-file and multi-file skill zips)
dist/                          the zips to upload
```

## Develop
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install numpy scipy pandas pytest
python -m pytest -q tests
research/fetch_data.sh && python research/data.py && python research/backtest.py 2021 2000 all 2023
research/nfl/fetch_data.sh && python research/nfl/data.py && research/nfl/run_all.sh
```
