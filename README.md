# nba-bets

The NBA player props model: a Claude skill (`nba-player-props`, v2) plus the simulation engine behind it, calibrated on 351,409 real player-games and backtested against the original version.

## Install the skill
1. Download `dist/nba-player-props.zip` from this repo.
2. In Claude, open Settings > Capabilities > Skills, and replace the existing `nba-player-props` skill with the zip.
3. Ask for picks the usual way: "Give me 5 NBA props and two parlays for tonight" with a FanDuel screenshot, or "Is Jalen Brunson over 6.5 assists a bet?".

Rebuild the zip after any change: `tools/build_skill.sh`.

## What v2 changes
- **Calibrated engine.** Minutes noise, blowout cuts, overtime, stat variance, shooting noise, usage shifts when a teammate sits, shrinkage, home court and in-season drift are all fitted on 2010-24 box scores instead of set by hand. The v1 spreads were too tight, so its confident calls were overstated by 5-9 points.
- **Profit layer.** The score still measures the chance to hit and the evidence. A straight now also has to clear its breakeven by 2 points at the posted price, and it carries a "bet to" price, a quarter-Kelly stake cap and a line-shopping check across books. Parlays must be +EV on the simulated joint chance.
- **Market weight** in the final blend goes from 25% to 40% until tracked bets measure the right value.
- **Fixes:** a crash on players who never shoot threes, push handling on whole-number lines, usage bumps that were about 3x too big and pointed at the wrong player, a close-game minutes bonus 6-8x too big, and single-overtime-only games.
- **Leaner skill file.** The engine moved to `scripts/nba_props.py`, and sources and calibration notes moved to `references/`.

## Backtest (every 2021-22 to 2023-24 player-game with 20+ projected minutes, 41,382 games, pregame inputs only)

| Stat | v1: 80% range held | v2 | v1: its "64%" overs hit | v2 |
|---|---|---|---|---|
| Points | 72.8% | 80.5% | 57.8% | 64.9% |
| Rebounds | 76.6% | 80.4% | 58.5% | 62.4% |
| Assists | 76.4% | 80.6% | 63.1% | 66.2% |
| Threes | 78.1% | 80.3% | 58.8% | 59.6% |
| PRA | 70.5% | 79.7% | 57.2% | 62.9% |

Log loss improved for every stat. Full tables and every fitted constant: `skills/nba-player-props/references/calibration.md`.

No model guarantees profit. Books hold about 4.5-7% on main-line props (more on parlays), and the data has no historical prop prices, so the backtest shows the probabilities are honest, not that they beat the books. Tracked CLV and results do that (SKILL.md Step 15). Bet only what you can afford to lose.

## Layout
```
skills/nba-player-props/      the skill (what gets zipped)
  SKILL.md                    workflow
  scripts/nba_props.py        engine v2
  references/calibration.md   fitted constants, evidence, backtest
  references/sources.md       data, odds and news sources; dead ends
research/                     data loading, calibration analyses, drift and rate-uncertainty fits, backtest (see research/README.md)
tests/                        pytest suite for the engine
tools/build_skill.sh          builds dist/nba-player-props.zip
```

## Develop
```bash
python3 -m venv .venv && . .venv/bin/activate && pip install numpy scipy pandas pytest
python -m pytest -q tests
research/fetch_data.sh && python research/data.py && python research/backtest.py 2021 2000 all 2023
```
