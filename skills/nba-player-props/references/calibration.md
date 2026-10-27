# Calibration: what the v2 engine is fitted on, and how it tested

Built Oct 27, 2026. Data: 2010-11 to 2023-24 regular-season box scores (NocturneBear/NBA-Data-2010-2024): 424,478 player rows, 351,409 of them played, in 16,658 games. The research scripts, the backtest and the tests live in the GitHub repo josemonet/nba-bets (research/, tests/); every number below can be reproduced from them.

## 1. The backtest (out of sample)
Every 2021-22 to 2023-24 player-game with 10+ earlier games that season and 20+ projected minutes: 41,382 games. Every input is pregame only (his earlier games, last season, team ratings to date). None of these seasons was used to fit the noise, shrinkage or rate-uncertainty settings, which came from 2014-20 (and the dispersion and minutes tables from all seasons, which are structural per-game facts and stable across eras).

Variants: v1 = the original skill (its minutes recipe, shrink constants and engine); v1e = the new inputs run through the v1 engine (the engine-only effect); v2 = the new recipe and engine.

How honest are the ranges? Share of real outcomes inside the model's central 50%, 80% and 90% ranges (perfect = 50/80/90):

| Stat | v1 | v1e | v2 |
|---|---|---|---|
| Points | 43.9 / 72.8 / 84.1 | 44.8 / 73.9 / 84.8 | 50.8 / 80.5 / 90.2 |
| Rebounds | 47.1 / 76.6 / 87.5 | 47.2 / 77.1 / 87.6 | 50.5 / 80.4 / 90.2 |
| Assists | 47.0 / 76.4 / 87.3 | 47.7 / 77.4 / 88.1 | 50.7 / 80.6 / 90.3 |
| Threes made | 48.2 / 78.1 / 88.4 | 48.6 / 78.4 / 88.6 | 50.5 / 80.3 / 90.0 |
| PRA | 41.7 / 70.5 / 82.1 | 43.0 / 71.7 / 83.1 | 49.8 / 79.7 / 89.5 |
| Minutes | 36.2 / 63.5 / 76.1 | 38.2 / 66.5 / 78.8 | 51.2 / 81.0 / 90.8 |

Accuracy at a book-style line (his season average to date, rounded to a half point): log loss of the over/under call (lower is better) and CRPS of the whole distribution (lower is better).

| Stat | Log loss v1 | v2 | CRPS v1 | v2 |
|---|---|---|---|---|
| Points | 0.6859 | 0.6725 | 3.722 | 3.651 |
| Rebounds | 0.6788 | 0.6703 | 1.440 | 1.420 |
| Assists | 0.6760 | 0.6670 | 1.072 | 1.052 |
| Threes made | 0.6257 | 0.6225 | 0.690 | 0.687 |
| PRA | 0.6838 | 0.6623 | 4.780 | 4.635 |
| Minutes | 0.6953 | 0.6215 | 3.533 | 3.210 |

What that means for bets: when each model said an over was 60-70% or 70%+ likely, how often it hit.

| Stat | v1 said 64% | hit | v1 said 70%+ (avg) | hit | v2 said 64% | hit | v2 said 70%+ (avg) | hit |
|---|---|---|---|---|---|---|---|---|
| Points | 64.2% | 57.8% | 78.0% | 70.7% | 64.1% | 64.9% | 76.9% | 76.7% |
| Rebounds | 64.2% | 58.5% | 77.8% | 70.2% | 64.2% | 62.4% | 77.1% | 74.9% |
| Assists | 64.1% | 63.1% | 75.8% | 70.7% | 64.0% | 66.2% | 75.1% | 75.8% |
| Threes made | 64.0% | 58.8% | 74.2% | 68.3% | 64.0% | 59.6% | 73.9% | 71.7% |
| PRA | 64.3% | 57.2% | 80.4% | 71.6% | 64.2% | 62.9% | 79.1% | 78.0% |

v1 overstated its confident calls by 5-9 points for points, rebounds, threes and PRA (1-5 for assists). A v1 "64%" points over priced at -150 (breakeven 60%) actually hit 57.8%, a losing bet that looked like a winner. v2's confident calls hit within about 2 points of the stated rate for points, rebounds, assists and PRA. Two soft spots remain: threes overs in the 60-70% band ran 4 points under (the 3PA-share drift of 2014-19 had faded; the shipped engine sets it to zero, section 5), and points and PRA unders the model put near 60-64% ran 3-4.5 points short in both training and test (MIN_PULL trims the minutes part of it). The skill demands a 4-point edge on those two (section 6).

Shipped-engine check (the constants in scripts/nba_props.py, with the drift refit on 2014-24 and MIN_PULL; partly in-sample for those multipliers): see section 6.

## 2. Game script

| Constant | v1 | v2 | Evidence |
|---|---|---|---|
| SIG (margin SD around the spread) | 12.0 | 13.0 | Residual SD of the final margin around a ratings-based expectation ran 12.8-14.1 in 2021-23; 20+ point games were 18.9%, 15.6% and 19.1% of 2021, 2022 and 2023 games. SD 12 predicts 13-16%; 13 matches. |
| Overtime | 2.1 x normal density at SD 12 | 0.070 x exp(-m^2/(2 x 11.5^2)) | 5.8% of games went to OT. By expected margin: 7.0% at 0-2 points, 6.0-6.2% at 2-6, 5.6% at 6-8, 5.0% at 8-10, 3.8% at 10-14, 2.8% at 14+. |
| Second overtime | none | 13.8% of OT games | Multi-OT share of overtime games, 2010-24. |
| POSS_SD | 3.5 | 4.6 | Game pace residual SD around both teams' season paces: 4.5-5.2 per season (4.9 since 2019); a market total knows a little more than season paces. |

Pace scaling: against pregame expected pace, shot attempts (1.03), rebounds (1.04) and assists (1.07) scale about 1:1, so the engine keeps elasticity 1. Points scale 1.33x because fast games are also efficient games; read a points thesis off the implied team total.

## 3. Minutes
Margin effects (minutes vs his average in games decided by 9 or less; from 2010-24, about 351,000 games):

| Final margin | Star (34+) | Starter (28-34) | Rotation (18-28) | Bench |
|---|---|---|---|---|
| 0-3 | +0.19 | +0.13 | +0.01 | -0.11 |
| 9-12 | -1.04 | -0.72 | -0.15 | +0.29 |
| 15-18 | -3.27 | -2.38 | -0.61 | +0.32 |
| 21-24 | -5.48 | -3.65 | -1.05 | +1.04 |
| 27-30 | -6.60 | -4.92 | -1.22 | +1.84 |
| 35+ | -8.59 | -6.25 | -1.70 | +2.78 |
| Each overtime | +4.6 | +4.0 | +2.1 | +0.8 |

v1 used a straight-line cut that started at 11 points and reached 7 minutes at 25 for both stars and starters (11.2 at 33+), a close-game bonus of +1.5 for stars and +0.8 for starters, a +5 bench gain at 25, and one overtime only. The data says the close-game bonus is about 0.1-0.2 (v1's +1.5 and +0.8 were 6-8x too big, which inflated stars' overs in pick'ems), starters lose about two-thirds of what stars lose, bench players gain only 1-3, and winners and losers lose about the same minutes.

Projection (2010-24 games, 10+ prior games, same role): RMSE of next-game minutes (after margin effects):

| Projection | RMSE |
|---|---|
| Last game | 7.72 |
| Season average | 7.03 |
| Last 10 average | 6.59 |
| Last 5 average | 6.55 |
| EWMA, half-life 2 (raw minutes) | 6.34 |
| EWMA, half-life 2.5, margin-adjusted (v2) | 5.96 |

Then MIN_PULL = 0.1 toward his margin-adjusted season average (best on 2014-20; it halves the 0.4-0.6 minute bias after a two-game dip) and the role regression (stars -0.63, starters -0.08, rotation -0.14, bench +0.37: a recent run of high minutes tends to come back down).

Noise around that projection (2014-24; 2010-13 minutes were noisier, star SD 5.05 vs 4.24-4.49 since):

| Role | Normal core SD | Big-loss chance | Average big loss | Total SD |
|---|---|---|---|---|
| Star | 3.07 | 12.4% | 7.7 | 4.45 |
| Starter | 3.98 | 21.1% | 6.6 | 5.26 |
| Rotation | 5.82 | 4.9% | 8.4 | 6.14 |
| Bench | 4.81 | 57.9% chance of an upward swing | 6.2 | 6.57 |

v1 used SD 2.2 for stars and 2.6 for starters, plus a small foul-trouble and exit draw: about half the real spread. That is why its 80% minutes range held only 64% of games.

Foul rate: the chance of losing 8+ minutes for stars rises from 5.2% at 2.5 or fewer fouls per 36 to 8.0% at 3.5-4, 11.2% at 4-4.5 and 13.6% at 4.5+; starters 6.8% to 10.3%; rotation players flat. The engine scales the big-loss chance by PF_TAIL.

Role changes (2014-24): a player newly starting gains 11.5 minutes from a 0-18 minute average (SD 8.3), 7.3 from 18-24, 5.05 from 24-30 and 3.1 from 30-36. A starter moved to the bench loses 4.0 to 8.9, more from bigger roles. When a key teammate sits, the player who takes his starting spot gains 10.4 (from 10-18), 8.1 (18-24), 5.7 (24-30) or 4.8 (30-36); the others gain 2.7, 1.7, 1.4, 0.6 and about 0 above 36 minutes.

Back-to-backs: when he plays, stars and starters lose 0.2-0.3 minutes, rotation and bench players gain 0.4-1.0 (others rest), and per-minute output moves less than 1.5%.

## 4. Stat noise at fixed minutes and pace
Variance divided by mean, from each player-season's leave-one-out rate (40+ games, 15+ minutes):

| Stat | Data | v1 engine | v2 engine |
|---|---|---|---|
| FGA | 0.82-0.91 (falls with volume) | 0.35-0.9 by role plus a 10% usage shock | 0.82-0.87 |
| FTA | 1.92-2.14 (trips come in pairs) | 1.3 | 2.05 |
| Rebounds | 1.03-1.13 | 1.0 | 1.08 |
| Assists | 1.06-1.14 | 1.0 | 1.10 |
| Steals | 1.00-1.11 | 1.0 | 1.04 |
| Blocks | 1.05-1.17 | 1.1 | 1.08 |
| Points | 2.06-2.26 | | 1.85-2.35 by player type |
| PRA | 1.72-1.92 | | 1.5-1.95 |
| Threes made | 1.05-1.06 | | 0.99-1.01 |

Shooting: makes given attempts showed no overdispersion beyond binomial for 2P% and 3P% (beta-binomial rho -0.001 and -0.001): no hot or cold nights beyond plain chance. v1 added game noise with kappa 150 and 100, which made threes props too swingy. v2 keeps only estimate uncertainty (PCT_N: 1500 attempts for 2P%, 700 for 3P%). FT% does vary by game (kappa 64). The 3PA share of FGA varies less than v1 assumed (kappa 160 vs 60).

Cross-stat links at fixed minutes are small: points-assists -0.02, rebounds-assists +0.05, FGA-rebounds +0.13. Combos come out right without extra links (PRA variance/mean 1.81 for a star vs 1.72-1.92 in the data).

Same game: teammates' FGA correlate -0.03 (-0.045 among 10+ FGA players; engine -0.052), and a playmaker's assists correlate +0.12 with a scoring teammate's points (engine +0.122 with ASSIST_LINK 0.65). Teammates' FG% residuals correlate +0.005: teams don't run hot together.

## 5. Rates, matchups, home court and usage
Shrinkage toward last season (minutes of prior weight that minimized next-game error, 2012-24):

| Stat | v1 STAB | v2 STAB | Last-10 blend |
|---|---|---|---|
| Points | 300 | 200 | 20% |
| Rebounds | 250 | 100 | 10% |
| Assists | 250 | 100 | 30% |
| FGA / 3PA | 300 | 100 | 30% / 40% |
| FTA | 300 | 200 | 20% |
| Steals | 800 | 600 | 10% |
| Blocks | 500 | 200 | 10% |
| Turnovers | 500 | 400 | 10% |

In-season drift (next-game rate / projected rate, 2014-24): assists +3.6% (every season +2% to +6%), FGA +0.8%, rebounds -0.5%, steals -1.6%, blocks -3.6%, turnovers -2.5%, FTA -0.3%, 2P% +0.6%, 3P% +0.4%. The 3PA-share drift was +1.9% in 2014-19 and about zero in 2020-24, so the shipped engine uses zero.

Opponent factors (team level, per possession, season to date): best shrinkage 20 games (rebounds, assists, blocks), 40 (points, threes, steals, turnovers), 5 (3PA allowed) at full strength. They cut next-game error by 0.13% (points) to 1.38% (3PA). Defense-vs-position on top of the team factor: 0.00-0.13% across 126,269 starter games, so it is noise for betting.

Home court (weighted home/road rate ratio per player-season, square root): assists 1.020, blocks 1.032, FTA 1.014, points 1.011, rebounds 1.010, threes made 1.007, FGA 0.999, 3PA 0.995, steals 0.998, turnovers 0.992. The assist and block gaps match known home-scorekeeper bias.

Usage when a key player sits (1,490 absences of 26+ minute players, split-sample so noisy rates can't fake the pattern):
- Teammates' FGA per 36 rise by about 0.135 x (his FGA per 36 - 10.6): +0.0 when a 10-FGA starter sits, +0.3 for 13, +0.7 for 15.6, +1.2 for 19. The rise is similar in size for low- and high-usage teammates (+0.40 to +0.65 per 36).
- Only 31% of the missing shots come from teammates shooting more per minute (48% for the highest-usage stars); the rest come from the replacement's minutes. v1's usage_bumps() assumed 85% minus whatever replacement number was passed (default 0) and tilted the bump toward the next star (tilt 1.5): about 3x too big and pointed at the wrong player.
- Assists: +17% for every teammate when the missing player is a playmaker (7+ assists per 36); about +1% otherwise.
- Rebounds: +3.6 to 5.5% for teammates when the missing player is a big (10+ per 36); about 0 otherwise.

## 6. Rate uncertainty and the shipped engine
rate_cv (0.05 settled, 0.09 for 10-20 games or no last season, 0.13 for a new role or team) is multiplied per stat group (RATE_CV: shot volume 2.8, threes 2.0, rebounds 0.9, assists 1.4) and shares half its variance across his stats (RATE_RHO 0.5). Tuned on 8,000 random 2014-20 player-games until the 50/80/90% ranges held: points 50.5/79.7/89.6, rebounds 49.9/79.7/90.0, assists 50.0/79.7/89.6, threes 50.8/79.9/90.0, PRA 49.0/79.2/89.1.

Shipped constants on 2021-24 (41,103 games; partly in-sample for DRIFT and MIN_PULL, which were refit on 2014-24 after the clean test above):

| Stat | 50/80/90% coverage | Log loss | Said 60-70% (avg), hit | Said 70%+ (avg), hit |
|---|---|---|---|---|
| Points | 50.8 / 80.5 / 90.2 | 0.6725 | 63.9% -> 66.7% | 76.6% -> 78.4% |
| Rebounds | 50.4 / 80.5 / 90.2 | 0.6696 | 64.0% -> 65.0% | 76.8% -> 76.6% |
| Assists | 50.8 / 80.5 / 90.3 | 0.6668 | 63.9% -> 67.1% | 74.8% -> 76.9% |
| Threes made | 50.3 / 80.1 / 89.9 | 0.6216 | 63.8% -> 61.0% | 73.5% -> 73.0% |
| PRA | 49.8 / 79.7 / 89.6 | 0.6618 | 64.1% -> 65.4% | 78.7% -> 80.2% |
| Minutes | 51.2 / 81.2 / 90.8 | 0.6176 | | |

Confident overs now hit as often as stated or a little more (the safe direction). Two soft spots: threes overs the model puts at 60-70% hit 2.8 points less, and points and PRA unders it puts near 60-64% (overs at 36%) hit about 3-4 points less. The skill demands a 4-point edge on those two (Step 11d).

## 7. Settings that are policy, not fitted
- W_MKT 0.40 (v1 0.25): the market's weight in the final blend. The backtest has no historical prop odds, so this weight can't be fitted here; it moved toward the market because the market also sees injury news, lineups and sharp money. fit_blend() on 100+ tracked bets sets it.
- Profit gate: MIN_EDGE 2 points over breakeven at the posted price and p_cons at or above breakeven. KELLY_FRAC 0.25. Parlays: +EV on our joint chance, legs no worse than -3% EV at their own price.
- BOOK_W: Pinnacle and Circa 3x, Bookmaker 2x, BetOnline 1.5x, FanDuel, DraftKings and Kalshi 1x, slower books 0.7-0.8x.

## 8. Bugs fixed from v1
- sim_player crashed on a 0% three-point share (non-shooting bigs) or a 100% FT mark (Beta with a zero parameter).
- Whole-number lines gave half credit for a push; p_outcomes() now returns win, push and loss, and breakeven and EV treat a push as a refund.
- usage_bumps() defaulted to 85% absorption with no replacement player, tripling usage bumps.
- The same-game usage shock was shared by FGA and FTA, adding a correlation the data doesn't show (+0.13 vs +0.02).
- One overtime period at most; 13.8% of overtime games have more.

## 9. Limits
- No historical prop prices, so no ROI backtest: the backtest proves the probabilities are honest and sharper than v1, not that they beat the books. CLV and tracked results (SKILL.md Step 15) measure that.
- Box scores end with 2023-24; refresh when the dataset adds seasons (research/README.md).
- First-quarter props: there are no quarter splits in the data, so the Q1 model (q1_min share of his game) is untested.
- The backtest's pregame inputs come from box scores only. Real cards add injury news, lineups and coach quotes, so their minutes projections should be at least this good.
