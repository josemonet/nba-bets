# Calibration: what the v1.0 engine is fitted on, and how it tested

Built Oct 29, 2026. Data: nflverse regular-season play-by-play 2016 through 2026 week 7 (481,511 plays, 2,746 games), snap counts, rosters, injuries and the schedule with closing spreads, totals and weather (nflverse-data releases and nflverse/nfldata). Stats follow official conventions (gross passing yards; scrambles and kneel-downs are rushes; no two-point tries) and were checked against official 2023 weekly stats: 100% match on attempts, completions, carries and targets, 99.9% on receiving yards. The research scripts, the backtest, this file's evidence logs (research/nfl/results/) and the tests live in the GitHub repo josemonet/nba-bets; every number below can be reproduced with research/nfl/run_all.sh.

## 1. The backtest (walk-forward, out of sample)
Every 2023, 2024 and 2025 regular-season game where both teams had played 2+ games: 720 games and 11,928 player slots (every QB who took his team's first snap, every pass-catcher at 5%+ projected target share and every back at 8%+ projected carry share). Every input is pregame only: the closing spread and total, the weather, season-to-date team tendencies shrunk by the fitted weights, last season, and the players who were active. Absences were handled the way the skill handles them live: a regular who played the team's last game and was inactive got usage_shift_nfl() applied to his teammates, a player back from a missed game got return_keep(), and every team's list got share_budget(). The QB is the one who took the first snap (known before kickoff), not the game's top passer.

v1 = the old football_model from the sports-betting-research skill, fed the same inputs (so the comparison isolates the engine). v2 = this engine.

How honest are the ranges? Share of real outcomes inside the model's central 50%, 80% and 90% ranges (perfect = 50/80/90):

| Stat | n | v1 | v2 |
|---|---|---|---|
| Pass attempts | 1,409 | 33.4 / 56.6 / 69.1 | 48.6 / 79.8 / 90.1 |
| Completions | 1,409 | 39.0 / 64.0 / 74.0 | 50.9 / 80.7 / 91.1 |
| Passing yards | 1,409 | 45.8 / 73.4 / 82.3 | 47.7 / 78.9 / 88.5 |
| Passing TDs | 1,409 | 46.8 / 78.4 / 88.1 | 47.3 / 78.1 / 88.4 |
| Rushing attempts (backs) | 3,332 | 36.6 / 62.7 / 74.6 | 50.8 / 79.7 / 90.7 |
| Rushing yards (QBs and backs) | 4,741 | 39.5 / 72.6 / 86.8 | 50.4 / 80.4 / 90.4 |
| Receptions | 9,245 | 44.6 / 74.1 / 85.8 | 47.7 / 78.1 / 88.7 |
| Receiving yards | 9,245 | 47.0 / 75.9 / 86.8 | 48.5 / 78.8 / 89.5 |
| Rush + receiving yards | 10,519 | 46.1 / 75.8 / 86.6 | 48.3 / 78.6 / 89.0 |

Accuracy: CRPS of the whole distribution (lower is better), log loss of the over/under call at a book-style line (the player's season average to date, rounded down to a half point), and the average miss (projected mean minus actual).

| Stat | CRPS v1 | v2 | Log loss v1 | v2 | Mean miss v1 | v2 |
|---|---|---|---|---|---|---|
| Pass attempts | 5.97 | 4.77 | 0.825 | 0.601 | +5.52 | +0.54 |
| Completions | 4.04 | 3.38 | | | | |
| Passing yards | 47.6 | 42.0 | 0.685 | 0.619 | +35.0 | +1.1 |
| Passing TDs | 0.606 | 0.605 | | | | |
| Rushing attempts | 2.59 | 2.53 | 0.650 | 0.637 | -0.45 | -0.31 |
| Rushing yards | 13.62 | 12.87 | 0.706 | 0.649 | -0.97 | +0.27 |
| Receptions | 1.076 | 1.043 | 0.670 | 0.652 | +0.36 | +0.04 |
| Receiving yards | 14.19 | 13.87 | 0.670 | 0.659 | +4.14 | +0.52 |
| Rush + receiving yards | 16.34 | 16.06 | 0.667 | 0.658 | +2.77 | +0.01 |
| Anytime TD (log loss) | | | 0.4949 | 0.4920 | | |

The anytime-TD baseline (the player's season TD rate) scored 0.588, so both engines' TD pools beat it by a wide margin; v2's stated chances averaged 21.8% against 23.1% actual (2023-25 games beat their closing totals, section 13).

What that means for bets: when each engine called a side 60%+ likely at the book-style line, how often it hit.

| Calls | v1 stated | hit | v2 stated | hit |
|---|---|---|---|---|
| Overs at 60-70% | 64.5% | 54.4% | 64.3% | 60.7% |
| Overs at 70%+ | 81.2% | 64.8% | 80.5% | 75.5% |
| Unders at 60-70% | 64.5% | 66.5% | 64.6% | 63.2% |
| Unders at 70%+ | 78.3% | 73.4% | 76.2% | 74.6% |
| Pass attempts, either side 60%+ | 83.3% | 59.5% | 73.4% | 71.5% |
| Passing yards, either side 60%+ | 76.8% | 63.6% | 73.8% | 72.0% |
| Rushing yards, either side 60%+ | 74.5% | 62.9% | 70.0% | 67.7% |

v1 overstated its confident calls by 10-24 points on QB volume and passing yards, because it over-projected attempts by 5.5 and passing yards by 35 a game (it ignored sacks, scrambles, starter exits and the league's falling pass volume). v2's unders are calibrated within 1-2 points. Its soft spots, which the profit gate covers with a 4-point edge (SOFT_SPOTS, min_edge_for()):

| Soft spot | Stated | Hit | n |
|---|---|---|---|
| Receptions overs at 60-70% / 70%+ | 64.5% / 76.1% | 60.3% / 68.1% | 794 / 376 |
| Receiving-yard overs at 60-70% / 70%+ | 64.1% / 76.3% | 59.7% / 69.7% | 687 / 267 |
| Rush + receiving overs at 60-70% / 70%+ | 64.1% / 78.4% | 59.3% / 72.2% | 830 / 475 |
| Rushing-yard overs at 70%+ | 80.5% | 73.7% | 312 |
| Pass-attempt overs at 60-70% | 64.3% | 56.7% | 238 |
| Passing-yard unders at 70%+ | 76.0% | 68.1% | 94 |

In live use the market keeps 40% of the blend, which pulls these back toward the line; the extra edge covers what's left.

Subgroup audit (research/nfl/results/audit_2023_2025.txt; the NBA lesson was to check every tier separately): 80% coverage stays within 76-82% for every stat by position, uncertainty tier (share_cv 0.10, 0.14, 0.20), games into the season, spread size and season, with three exceptions. Players in their first game back ran narrow at share_cv 0.20 (74% at 80%), so the skill uses 0.30 and caps those bets at 5. Passing TDs ran 5.5% under overall and 12-16% under in games with a 7+ point spread, where both teams beat their implied totals in 2023-25 (section 13). QB rushing yards ran 5.8% high.

## 2. Game script

| Constant | Value | Evidence |
|---|---|---|
| Margin SD around the spread | 12.7 (old model 13.5) | 2,746 games 2016-26; 12.6-13.0 at every spread size. The engine's drive model runs 13.1-13.3 (a known 3% wide gap). |
| Total SD around the closing total | 13.2 | 12.7-13.6 by total range. Engine 13.6-13.7. |
| Key margins | 3: 14.6%, 7: 8.6%, 6: 6.9%, 14: 5.0%, 10: 4.8%, 4: 4.7%, 1: 4.6% | Final margin frequencies. Overtime 5.6%, ties 0.4%. |
| Team points around the implied total | SD 8.5-9.5 | By implied total (8.5 at 17 or less, 9.5 at 26-29). The two teams' surprises correlate 0.036. |
| DRIVES, DRIVE_SLOPE, DRIVE_SD | 11.09 per team, -0.027 per implied point; shared SD 1.55, team SD 0.65 | Drives per team-game mean 11.09 (SD 1.68), the two teams' drive counts correlate 0.85. |
| TD_RATE | -0.0756 + 0.01316 x implied points per drive | 13.6% of drives at 16 implied points, 32.7% at 30.5. drive_rates() solves the rate exactly so team points match the implied total. |
| FGA_RATE, FG_MAKE | 0.142 + 0.00166 x implied; 0.846 | |
| CONV, NONOFF_TD | 0.906 extra points per TD, 0.024 two-pointers; 0.15 defensive and return TDs per team-game | |
| TD_VMR, GAME_SHOCK | TD count variance/mean 1.085 - 0.0164 x implied (0.83 at 16, 0.61 at 29); shared game shock 0.10 | Independent drive binomials plus a team shock overstated team scoring variance (team points SD 10.5, margin 14.3); this structure gives margin 13.1, total 13.6, correlation 0.034. |
| PASS_TD share | 0.615 league (2023-26); slope -0.0045 per point of realized margin, centered on the TD-weighted margin | Pass share of TDs 0.68 for teams trailing by 7+, 0.59 for teams leading by 7+. Without the centering the slope pulled the average pass share 3 points low (passing TDs ran 8% under). |

## 3. Volume

| Constant | Value | Evidence |
|---|---|---|
| PLAYS | league pace + 0.12 x (total - league total) + 0.161 x expected margin + 0.389 x (own pace - league) + 0.02 x (opponent pace - league) | Pregame plays model on 2016-26 team-games (residual SD 8.27). Given the realized game: +0.178 plays per point above the implied total, residual SD 8.14. |
| LG_SEASON | 2026 to date: 62.3 plays per team-game, 45.3 average total, 0.54 neutral pass rate | League plays per team-game fell from 63.9 (2016) to 61.3 (2025); fitting on all seasons over-projected recent volume. The backtest blends last season and this season to date by weeks played (league()). |
| PASS_RATE | 0.185 + 0.78 x neutral pass rate + 0.0017 x expected margin - 0.0049 x realized margin (capped at 28) | Pass rate by realized margin: 0.68 trailing by 10+, 0.61 within 3, 0.56 leading by 4-10, 0.51 leading by 17+. Residual SD 0.085, of which 0.063 is binomial noise on 63 plays; PASS_RATE_SD 0.065 tuned so attempts' SD is 7.7. |
| Sacks, scrambles, interceptions | league 6.4% of dropbacks, 5.9% of non-sack dropbacks, 2.1% of attempts (2023-26) | Interceptions rise 1% per point the team trails (capped at 21). |
| KNEELS | 1.45 a game when leading by 4+, 0.62 within 3, 0.18 trailing | Each about -1 yard on the QB's rushing line. |
| Targets per attempt | 0.953 (2023-26) | 0.98 in 2016-17, 0.95 since 2023 (more throwaways). |

## 4. Shares and their noise

| Constant | Value | Evidence |
|---|---|---|
| SHARE_HL, SHARE_K | targets: half-life 4 games, 50 team targets on last season's share; carries: half-life 2, 25 team carries | Next-game target share error 2.39 points (season average 2.44, last game alone 2.55); carry share error 4.36 (season average 4.64). |
| TGT_KAPPA | WR 117, TE 140, RB 122 | Raw within-season Beta-binomial concentration was 64 (WR), 95 (TE) and 80 (RB); once shares compete in the engine (normalized with the rest of the team) the joint passing calibration (section 7) wanted 1.5x, and TEs were lowered from 188 to 140 after their 80% ranges ran at 75%. |
| CAR_KAPPA | 12 | Raw 6.7 (committees and in-game script); carries compete through gamma draws normalized with the rest of the team, which fixed an 8% shortfall the old scale-down created (named backs got 0.855 of carries against 0.939 projected). |
| SHARE_CV | 0.10 settled (last season plus 6+ games), 0.14 normal, 0.20 under 3 games, 0.30 first game back | Coverage by tier in section 1. |
| EFF_CV | 0.08 | Uncertainty in projected catch rate and yards per catch or carry. |

## 5. Absences, returns and the team budget
- usage_shift_nfl(): 133 absences of an 18%+ target-share pass-catcher (2,454 teammate pairs) and 99 of a 45%+ carry-share back (1,101 pairs), split-sample baselines. Target gains by position pair (missing player down the side, teammate across): WR out: WR +3.8 points, TE +0.8, RB +0.6; TE out: TE +3.5, WR +2.0, RB +0.6; RB out: RB +2.5, TE +1.8, WR +1.3. The top three remaining targets gain 2.7, 2.7 and 2.1 points. Lead back out: the next back 31% to 58% of carries, the third 19% to 34%, the fourth 9% to 19%.
- Without the shift, active backs in fresh-absence games were projected 39% short (2025 pilot); with it they were as accurate as everyone else.
- QB out: team attempts 33.1 vs 34.2, passing yards 220.6 vs 245.9 and points 19.8 vs 23.2 with and without the starter; points ran 0.7 under the implied total with the backup (0.3 over with the starter), so the closing line prices nearly all of it.
- RETURN_KEEP (players at 8%+ of targets or 20%+ of carries, 2016-26): projected target share realized at 0.98 in a normal week, 0.92 in week 1 on last season's share alone, 0.88 after one missed game, 0.86 after 2-3, 0.86 after 4+, and 0.52-0.68 in a first game of the season after missing the early weeks. After a team change, week-1 target shares came in at 0.78 (WR), 0.76 (TE) and 0.66 (RB) of last season's, carries at 0.74 (NEW_TEAM_KEEP). Carries: 0.99, 0.92, 0.91, 0.94, 0.79 and 0.50-0.80.
- SHARE_BUDGET: a team's listed players (5%+ of targets; 8%+ of carries) realized 0.467 + 0.456 x the sum of their projected target shares and 0.664 + 0.271 x the sum of their carry shares (fitted on 1,406 team-games in 2020-22; 2023-25 gave 0.515 + 0.405 and 0.696 + 0.247). Applied to 2023-25 it improved CRPS and log loss for every receiving, rushing and passing-yard stat on identical rows (receptions 1.046 to 1.043, rushing attempts 2.549 to 2.534, rushing-yard log loss 0.6520 to 0.6491; QB attempts and TDs unchanged).

## 6. Per-play shapes and efficiency
- Catch rate by air yards: 0.80 behind the line, 0.76 at 1-4, 0.71 at 5-8, 0.59 at 9-12, 0.56 at 13-18, 0.38 beyond.
- Catch yards divided by the player's season yards per catch: median 0.79 (WR), 0.83 (TE), 0.83 (RB); 10% of catches go for 2x his average, 2-4% for 3x. The engine samples these shapes per catch, so a receiver's median runs below his mean and longest-reception props come from the same draws.
- Carry yards: backs mean 4.27, median 3, 9.6% lose yards, 10.3% gain 10+, 2.3% gain 20+, 0.5% gain 40+. QB designed runs mean 3.1 (2023-26; 3.6 before the sneak era), median 2; scrambles mean 7.5, median 6; receivers' carries mean 5.8.
- Game-level yards beyond the per-play noise: receiving yards' variance 1.12x the i.i.d. per-target variance, rushing 1.10x.
- EFF_K: catch rate 40 targets of weight on last season or the position norm, yards per target 80, yards per carry 100 (grid search on next-game error).
- QB_K (split-half season reliability): completion % 368 attempts (reliability 0.58), yards per attempt 332 (0.60), TD rate 424 (0.54), interceptions 2,490 (0.17), sacks 489 dropbacks (0.53); his designed-run share 21 team runs (0.89), scramble rate 64 passes (0.79), yards per designed run 18 runs, yards per scramble 101.
- EFF_LINK: per SD of the team's own scoring surprise, yards per attempt +12.8% at the team level (catch rate +4.7%, yards per completion +7.9%) and yards per carry +5.1%. ATT_LINK: per SD of pass attempts beyond the score, yards per completion -2.4% and yards per carry -5.9%.
- IMP_EFF: season-to-date efficiency is shrunk toward the league, and the market knows which offenses are good. Fitted on 2020-22 backtest residuals, yards per attempt rose 0.92% per implied point above the league's average team total (a 28-point offense about +5%, a 17-point offense about -5%). On 2023-25 it cut team yards-per-attempt error 3.7% and passing-yard error 1.9%, and the player backtest's passing-yard log loss went from 0.626 to 0.619 (big underdogs' passing yards were 12.5% high before, 7.6% after; big favorites' 5.9% low before, 1.3% after).

## 7. The passing layer (joint calibration)
Targets from within-team-season real games (each team's own average removed): team passing yards SD 69.7, attempts 7.7, completions 5.48, yards per completion 2.36, completion%/yards-per-completion correlation -0.045; a 22-30% target-share WR's yards SD 39.3, targets SD 3.15, receptions SD 2.47; his yards' correlation with his QB's 0.469 and with the WR2's -0.021.
Engine (calibrate_passing.py, current constants): team passing yards SD 66.9, attempts 7.49, completions 5.56, yards per completion 2.07, correlation -0.059; WR1 yards SD 39.2, targets 3.24, receptions 2.49; QB-WR1 0.487, WR1-WR2 -0.017. The pieces: per-catch shapes (SPREAD catch 1.0, carry 0.9), a game-level depth shock (DEPTH_SD 0.14, catch-rate tilt -0.31: deeper games complete fewer and gain more per catch), the field constraint (YARD_COMP 0.65: a long catch ends a drive, so teammates' catch-yard luck partly offsets) and competing target shares. Remaining gaps: team yards per completion 12% narrow and the team's passing-rushing yards correlation -0.08 vs -0.26.

## 8. TDs
- Who scores (2016-26): receiving TDs follow target share better than red-zone share (log loss 0.385 vs 0.459; inside-10 share 0.610; past TD share 0.639). The best blend: 85% target share + 15% inside-10 share (0.3846). Rushing: 75% carry share + 25% red-zone carry share (0.3396); goal-line share added nothing.
- Position factors (actual / predicted): receiving TDs WR 1.047, TE 1.157, RB 0.696; rushing TDs QB 1.206, RB 0.951, WR 1.049, TE 1.076, FB 1.711.
- Anytime TD by stated band (2023-25): 7.7% stated / 7.8% actual, 14.8 / 14.4, 24.7 / 28.4, 34.3 / 35.6, 44.3 / 47.1, 55.8 / 61.0. By position: RB 27.2 / 28.3, TE 18.3 / 19.1, WR 19.8 / 21.4. The engine's TD chances run 1-5 points conservative.

## 9. Quarterbacks
- QB_EXIT, EXIT_SHARE (the QB who took the first snap, 5,489 games): he threw under 90% of the team's passes in 8.3% of games: 4.7% within 3 points, 5.3-5.5% at 4-14, 11% at 15-21, 15.6% at 22-28, 26% at 29-35, 44% beyond. His share when he exited: close games (injury, benching) deciles 0.0, 0.17, 0.30, 0.39, 0.48, 0.56, 0.64, 0.70, 0.77, 0.85, 0.90; blowouts (rest) 0.03, 0.33, 0.49, 0.64, 0.70, 0.77, 0.81, 0.84, 0.87, 0.88, 0.90. Full games: 99.4% of attempts.
- EXIT_TD_POW: in blowout exits he threw 67% of the attempts and 76% of the passing TDs (the TDs built the lead); in close-game exits 53% and 48%.
- Before this model the starter got every attempt, and QB attempts ran 2.4 too high and passing yards 17 too high in the 2025 pilot. With it, season-aware league norms and the market-quality term, the 2023-25 misses are +0.5 attempts and +1 passing yard.
- QB_RUN_CV (design 0.75, scramble 0.50): game plans swing a QB's designed runs far beyond the binomial (calibrated on 2023-25 QB rushing yards: 80% coverage went from 73% to 80%; designed-run counts given the team's runs were only 1.13x binomial, so most of it is game-plan variation in the share).

## 10. Weather, home field and the opponent
- Residuals beyond the closing lines, outdoor games 2016-26: wind 0-5 mph +8.8 passing yards, 5-10 -3.1, 10-15 -6.0, 15-20 -21.5 (rushing +3.0), 20+ -17.0 (rushing +15.9); temperature below 32 F -15.5 passing and +5.4 rushing, 32-45 -8.2 and +6.8, 75+ +4.5 and -5.1; domes and closed roofs +3.1 vs -1.3 outdoors. weather() turns these into multipliers (passing -0.85% per mph over 10, capped at 12; -6.4% below 32 F, -3.3% below 45 F, +1.6% at 75+; field goals -0.6% per mph over 10).
- Home field: passing yards -0.03 vs +0.03, rushing -0.47 vs +0.47 beyond the lines (nothing).
- Opponent: adding the opponent's season-to-date passing yards allowed to the market's view explained 0.19% more variance; rushing yards allowed 1.13%. Defense-vs-position: season-to-date share allowed correlated 0.071 (WR), 0.045 (TE) and 0.061 (RB) with the next game's. Not used as multipliers.

## 11. Kickers and defenders
- Kicking points by implied team total: 6.0 at 17 or less, 6.5 at 17-20, 7.1 at 20-23, 7.6 at 23-26, 8.1 at 26-29, 7.9 above (SD about 3.5); field-goal tries peak around 20-26 implied points.
- Tackles (combined) per game for 80%+ snap players: LB 7.33, S 5.59, CB 4.25, with variance/mean 1.15-1.18 around his own average; LB tackles are 0.116 per opponent play and their residual correlates 0.30 with opponent plays. The engine draws tackles from opponent plays with TKL_EXTRA 0.03 extra dispersion.

## 12. League norms drift (LG, 2023-26)
Neutral pass rate 0.54; sacks 6.4% of dropbacks; scrambles 5.9% of non-sack dropbacks (3.7% in 2016, 6.2% in 2025); interceptions 2.1% of attempts (2.3% before 2022); completion 64.5%; yards per completion 10.95 (11.35 in 2016); targets per attempt 0.953; QB share of designed runs 0.054; QB designed-run yards 3.1 (2.5 in 2026 to date); pass share of TDs 0.615 (0.64-0.66 in 2016-19).

## 13. Tested and not adopted
- Carrying the recent over/under drift into totals: 2024-26 games beat their closing totals by 0.5-0.7 points per team (in 2023-26: +2.0 points per game at spreads of 3-7, +2.5 at 7-10, +1.5 at 10+; in 2016-22 the sign flipped by era). Adding half or all of the trailing season's drift moved anytime-TD log loss from 0.4924 to 0.4920 and nothing else beyond noise. Not adopted; the calibration tripwire watches it.
- Market-quality adjustments to pass attempts, plays and rushing yards: fitted on 2020-22, they made 2023-25 worse (attempts +0.8-1.7% error) or changed nothing. Only the passing-efficiency term (IMP_EFF) is in.
- Opponent and defense-vs-position multipliers (section 10).
- Red-zone share as the TD driver (section 8).

## 14. Known gaps
- Passing TDs 5.5% under (12-16% under at 7+ point spreads) and anytime TDs 1-5 points conservative, both from 2023-25 scoring above the closing totals.
- QB rushing yards 5.8% high; rushing attempts for backs 3.3% low; TE receptions 3% low and WR receptions 2.5% high.
- The simulated margin and total run about 3% wider than real games; team yards per completion 12% narrow; passing-rushing yards correlation -0.08 vs -0.26 real.
- The QB-WR1 yards correlation is 0.49 vs 0.47 real, so the engine slightly overstates that pair's SGP lift.
- No historical prop prices: the backtest's lines are book-style proxies (the season average), so it shows the probabilities are honest, not that they beat the books. Tracked CLV and results do that (SKILL.md Step 15).

## 15. Reproduce
```
research/nfl/fetch_data.sh                 # nflverse play-by-play, player stats, snap counts, injuries, players, schedule
python research/nfl/data.py                # tables cached in data/cache/nfl/
research/nfl/run_all.sh                    # analyses 01-11, the passing calibration, the 2023-25 backtest and the audit
python research/nfl/backtest.py 2023 2025 2000 _final   # [first] [last] [sims] [tag]; NO_BUDGET=1 and DRIFT_K=0.5 run the experiments
python -m pytest -q tests
```
