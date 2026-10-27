---
name: "nba-player-props"
description: "Use for NBA player props (points, rebounds, assists, threes, combos, alt lines): any number of ranked straight bets plus a safe and a risky parlay, same-game or multi-game, from a player, screenshot or slate. Calibrated simulation, profit gate, line shopping."
---

# NBA Player Props v2 (minutes first, script first, logic first, price checked)

Goal: find the NBA player props most likely to hit and worth betting at their price, researched and modeled the way a professional prop shop works, and explain every choice in detail. Scan every posted prop, then go deep on a short list. Project minutes first, then role and volume, then the game script that decides both. Price every prop from one calibrated simulation (its noise, blowout cuts and usage shifts are fitted on 351,409 real player-games), compare it with outside models, the sportsbooks and the Kalshi exchange, and test every claim so a popular story never makes a pick. Score each bet 1-10 by its chance to hit and the strength of the tested evidence, never by its price. Then check the price: a straight goes on the card only when it clears its breakeven (the profit gate) and is staked no bigger than the edge supports. Deliver the number of straight bets he asks for, ranked and priced -190 or better, and when he asks, two parlays (legs at any price, the ticket +EV): one safe and smart, one risky but smart.

## About the user (read first)
- The user has ADHD. Every response follows the writing rules in Step 13d.
- He cares whether a bet hits (Oct 15, 2026) and wants the card to make money (Oct 27, 2026). Scores and verdicts come only from the chance to hit and the evidence (Step 10); price never moves a score. Then the profit gate (Step 11d) decides whether a scored bet is worth placing at its price, and a quarter-Kelly cap keeps thin edges small. A bet that hits 63% of the time loses money at -190 (breakeven 65.5%), so the card says so instead of listing it.
- Straight bets must be priced -190 or better (Oct 22, 2026): -190, -150, -110 and any plus price qualify; -195, -200, -250 and shorter don't, because he won't place a straight bet at -200. Parlay legs are exempt and can be any price. It decides whether a bet can be a straight, never its score (Step 11c).
- He wants picks that survive testing, not the general narrative (Oct 21, 2026). Every claim behind a pick is tested (Steps 7 and 8). A claim that fails its test cannot support a pick.
- He wants the reasoning for every pick in great detail, and no PDF; everything is delivered in chat (Oct 21, 2026).
- Units, books, balance and bankroll: Step 0a. How many bets and which parlays: Step 0d.

## Files in this skill
- SKILL.md: this workflow.
- scripts/nba_props.py: the engine (Step 9). Copy it into the working directory and import it; never retype it from memory. Find it with `find / -name nba_props.py -path "*nba-player-props*" 2>/dev/null | head -1`.
- references/calibration.md: every fitted constant, the data behind it, the old value it replaced, and the backtest against the v1 engine. Read it when a number in this file needs its source, or before changing the engine.
- references/sources.md: where to get data, odds and news, the 30-day pulse rules, and the Dead ends list. Read it before fetching anything.

## Skills built into this one
This skill already contains what it needs from these, so don't load them separately unless the user asks (the xlsx file skill excepted).

| Skill | Step | What it does here |
|---|---|---|
| i-have-adhd (ayghri) | 13d | Answer first, numbered actions, a state line, short lists, real time estimates |
| humanizer (blader) | 13d | Plain human writing: no dashes, no "not X but Y", no hype words, no unnamed "experts" |
| superforecasting (deusyu) | 7 | Outside view first, three reference classes, factor bands, reasons it might be wrong, update triggers |
| bayesian-reasoning-calibration (lyndonkl) | 7 | Evidence weighed by how diagnostic it is, sensitivity analysis, no extreme probabilities without extreme evidence |
| verification-before-completion (obra/superpowers) | 8i | Evidence before claims: re-check every number a pick cites before sending |
| last30days (mvanhorn) | 4 | A 30-day pulse of beat writers, pressers, Reddit, X and YouTube on roles, chemistry and mood |
| grilling (Matt Pocock) | 8d | Grill each thesis as a decision tree until no assumption is left unchecked |
| chief-of-staff (Matt Pocock, board protocol from alirezarezvani) | 0c, 8e, 15 | Slate run-of-show and reminders, a desk board meeting on each pick, a dated season notebook |
| handoff (Matt Pocock) | 14 | A short game-day handoff so a new chat can pick up the card |
| anatomy (wheresryan22) | 8a, 13e | Bet anatomy, and an optional interactive "prop machine" whose every number comes from the model |
| teach (Matt Pocock) | 13f | One short lesson per card tied to a real pick, a glossary, retrieval questions |
| autoresearch (Karpathy) | 16 | Keep-or-discard model experiments against a fixed scorecard |
| skill-creator (Anthropic) | 17 | Test changes to this skill with saved prompts and pass/fail checks |
| retro and diagnosing-bugs (Matt Pocock) | 7d, 15 | Model tripwires that go red on known failure modes, and a short retro after each slate |
| betting and kalshi (machina-sports) | 4, 6c, 11d, 12 | De-vig, EV, Kelly, line shopping, parlay math and line moves; Kalshi player-prop ladders from the public API |
| deep-research (Anthropic), dispatching-parallel-agents (obra/superpowers) | 4 | Optional parallel research, one agent per game, on full slates |
| writing-for-agents (Matt Pocock) | every step | A "Done when" line ends each step so no step stops early |
| xlsx or Sheets | 15 | The tracker |

## Ground rules
1. Minutes first. A prop is minutes times a rate. Most prop losses come from minutes (blowouts, foul trouble, injury exits, rotation changes), so project minutes before anything else and let the simulation price those risks.
2. Volume beats efficiency. Attempts (FGA, 3PA, FTA), touches, potential assists and rebound chances predict; shooting percentages regress. Game-to-game shooting showed no hot or cold streak beyond plain chance in 14 seasons of data, so never bet a threes over on a hot streak without the attempts behind it.
3. Script before projection. Spread and total decide minutes, pace and shot mix, so build the script (Step 5) before projecting.
4. Our number first. Build the projection before looking at the line or anyone's picks, so the market and the touts don't anchor the research.
5. Outside view before inside view. Start from the market's probability and the base rate, then move only as far as diagnostic evidence justifies (Step 7).
6. Every claim gets a test (Step 8b). "Revenge game", "always scores against them", "pace-up spot" and "worst defense against point guards" are claims, not reasons, until a test passes.
7. Small samples lie. Shrink rates toward a prior by sample size and carry the leftover uncertainty into the simulation (Step 6a). With/without splits under 5 games are mostly noise.
8. Wide net, deep dive. Scan every posted prop (Step 1), then research the short list in full. The best picks come from coverage plus depth, not from the first idea.
9. News is the edge and the risk. Injury reports, rest and lineups change in the last hour, so nothing is final until the re-check (Step 14).
10. Fewer, better bets. Never force picks or parlay legs to fill a count.
11. Correlation discipline. Don't stack bets that need the same script unless they are priced together as one parlay (Step 12).
12. Truth and provenance. Every number carries its source and date. Never invent a stat; write "not found".
13. Price discipline. The chance to hit picks the bets; the price decides whether they are worth placing. Every straight clears its breakeven by 2 points and its conservative check clears breakeven (Step 11d). Shop every legal book he uses for the best number before placing.
14. Honest spreads. The engine's minutes noise, blowout cuts, stat variance and usage shifts are fitted on real games, and its 50/80/90% ranges held their coverage in a 41,000-game backtest (references/calibration.md). Never hand-narrow them: the v1 spreads were too tight, and that is how a coin flip starts to look like a 65% bet.
15. The market is a strong forecaster. Our number moves off it only as far as sourced evidence justifies; the final blend gives the market 40% until our own tracked record measures the right weight (Step 15).

## Step 0: Before you start (~3 min)

### 0a. Setup
- Read memory for books, unit size and presentation preferences. Defaults: FanDuel is the main book and other legal books he uses are fine; Tennessee allows pro player props (college props aren't offered); 1 unit = 25 USD; straight bets priced -190 or better, parlay legs at any price (Step 11c); the card goes out in chat, never as a PDF; the user has ADHD.
- Read the available balance from his screenshot when one is there. Never recommend more than it; when picks add up to more, give a priority order. After a settled slate, recompute the balance before sizing the next card.
- Bankroll for the Kelly cap (Step 11d): his betting bankroll in units (the balance divided by the unit size, unless he gives a separate bankroll). Unknown: use 40 units and say so.
- Open the tracker if one exists (Step 15).
- Confirm today's date and season (the 2026-27 regular season began Oct 20, 2026). Searches often surface older seasons, so check the year on every number.
- Load the engine: copy scripts/nba_props.py into the working directory and `import nba_props as m`.

### 0b. 2026-27 market rules
- Reported Oct 16-19, 2026 (ESPN via Deseret News; Legal Sports Report; Front Office Sports; Casino.org): partner sportsbooks dropped or restricted parlays that combine several unders on one player, "first" markets (first basket, first three, first rebound, assist, steal or block), opening-tip bets, bets on a player missing specific shots, unders on players projected under 12 minutes, and higher-payout alternate under lines. Earlier rules still limit bets on short-contract players and some turnover, foul and missed-free-throw markets.
- Prediction markets aren't covered. Kalshi lists player thresholds (25+ points, 10+ rebounds) priced in dollars that read as probabilities before fees (references/sources.md).
- FanDuel voids a prop when the player doesn't play. Once he takes the court the bet stands, even after an early injury exit (Bet Protect covers some first-quarter exits: Step 12c).
- Work only with what is posted, and never suggest a restricted market.

### 0c. Run-of-show (chief-of-staff)
- Write the slate timeline in one block: tip times (CT); referee assignments (about 9 a.m. ET); the game-day injury report (due 11 a.m. to 1 p.m. local, or 8 to 10 a.m. local for tips at 5 p.m. or earlier; the second night of a back-to-back reports by 1 p.m. local); starting lineups (submitted 30 minutes before tip); and our re-check times (Step 14).
- Offer one line: reminders for the re-checks, or a scheduled task for a morning slate scan. Create them only after a yes.

### 0d. The order
- Read from his message: how many straight bets he wants (N), which games (the whole slate or named games), whether he wants parlays, any stake limit, and any book besides FanDuel.
- No N given: ask one quick multiple-choice question (3, 5, 7 or 10 bets). If he doesn't answer or is away, use 5 and say so.
- Parlays: build the two parlays (Step 12) when he asks for parlays or a full card. Otherwise offer them in one line at the end.
- His overrides win: more or fewer legs, same-game only, multi-game only, a target payout, a specific game, or "turn off the profit gate" (then set m.REQUIRE_EDGE = False and label every straight's edge anyway).
- Never pad. When fewer than N bets reach a score of 5 and clear the profit gate, give the ones that do and say how many are missing. The best near-misses can follow, labeled "watch, not bets", each with the price that would make it a bet (bet_to()).

Done when: N, the games and the parlay request are known or defaulted and stated.

### 0e. Full prop menu (required before finalizing)
- List every posted market for each candidate, from his screenshots or the sources in references/sources.md: points, rebounds, assists, threes made, PRA, points+rebounds, points+assists, rebounds+assists, steals, blocks, steals+blocks, turnovers, double-double, triple-double, alt lines and milestones (20+, 25+), first-quarter points, rebounds and assists, first-half props, player head-to-heads, and the team markets that express the same script (team totals, quarter totals).
- Model every family from one simulation (Step 9):
  - Points, rebounds, assists, threes, combos, steals, blocks, turnovers and first-quarter props: sim_player(), then p_outcomes() at the posted line (whole-number lines can push). Alt ladders and milestones: ladder().
  - Alt lines: final_probs() at the alt number with the main line's prices as the market (Step 6e).
  - Double-doubles and triple-doubles: the simulation's DD and TD rates, blended with event_final().
  - Same-game legs: sim_game_players() or sgp(), so shared minutes, pace, margin, overtime, teammates competing for shots and assists riding on teammates' makes are priced. Never treat same-game legs as independent.
  - One-sided prices (milestone ladders): one_way_fair().
  - No posted line yet: bet_zones() gives the median and the lines where each side reaches 55% and 60%. Share those zones, ask for a screenshot, and don't score or stake a bet until a line exists.
- Best expression of a thesis:
  - More minutes (a confirmed promotion to the starting five, a teammate out): PRA or points+rebounds spreads the bet over several stats and is steadier than points alone.
  - Extra possessions: rebounds and assists for high-touch players; overtime risk helps every over.
  - A brick-heavy game (two poor-shooting teams, a low total from bad offense rather than slow pace): rebounds over.
  - A star facing traps or double teams: his assists, not his points.
  - An opponent that allows lots of threes: a threes over only with 6+ projected attempts. 3PA allowed is the most real defensive trait in the data; 3P% allowed is noise.
  - Blowout script: unders on the favorite's starters. Bench overs are fragile (bench players gain only 1-3 minutes even in 25+ point games).
  - A combo that needs two stats to go right is a parlay in disguise; prefer the single stat when the thesis is about one.
  - Don't bet two props that need the same script; the second loses a point (Step 10).
  - Straights must be priced -190 or better (Step 11c) and clear the profit gate (Step 11d). When the safest number for a thesis (often an alt such as 6+ assists or 8+ rebounds) is priced shorter than -190 or fails the gate, the straight moves to the safest number that passes both (best_straight_line(..., min_edge=m.MIN_EDGE)), usually the main line, and the safer number stays available as a parlay leg.

Done when: every posted market for each candidate is listed and mapped to a model family.

## Step 1: Slate scan (the funnel, ~10 min)
1. Pull every posted prop for every game in scope: his screenshots, Kalshi ladders, the line-shopping pages and preview articles that list lines (references/sources.md).
2. Give each player a quick input (project_minutes() on his recent log, project_rate() per-36 rates, pace) and run screen() on every prop at its line. It returns our quick chance, the sportsbook's no-vig probability where both prices exist, the gap, and the edge at the posted price.
3. Flag structural edges, the places NBA prop edges actually come from:
   - News the line hasn't absorbed: a late scratch, a starter returning, a minutes limit lifted. Re-posted lines often move the obvious beneficiary and lag the second one. The data backs this: when a high-usage player sits, every teammate's shot rate rises by a similar amount and stars gain almost no minutes, while the player who takes the starting spot gains 5-11 minutes (usage_shift()). His props, and role players' volume props, are usually where the value is.
   - Role changes: a new starter, a trade, a coaching change, a shrinking rotation, minutes up 4+ over the last 3 games for a reason.
   - Script mismatches: a star's over on a 12-point favorite (blowout risk), or an under on a closer in a pick'em.
   - Distribution edges: alt ladders and milestones whose tails disagree with our simulation or the Kalshi ladder; combos priced off a different minutes view than the single stats.
   - Disagreement between books or with Kalshi on the line number. A different number changes the probability; a different price alone doesn't. Both feed best_offer().
   - Overreaction: a line moved 2+ after one big game with no role change.
4. Shortlist the top max(2N, 8) props by gap, edge and structural flags, at most 3 per game. Give unders the same look as overs; the public leans over. A prop priced shorter than -190 can't be a straight (Step 11c): shortlist its number priced -190 or better instead, and keep the shorter number on a separate parlay-leg list.
5. Props left off the shortlist get one line in "Other props considered" only when they came close.

Done when: every posted prop in scope has a quick probability and edge, and the shortlist is written with the reason each made it.

## Step 2: Game inputs and team sheets (~8 min per game)

### 2a. The market's game
- Spread, total and moneyline: opener and current (ESPN summary pickcenter, a DraftKings feed) plus his book's number.
- Implied team totals, with the spread as a positive number: favorite = (total + spread)/2, underdog = (total - spread)/2. Expected margin for team A = minus its spread (a 4.5-point favorite has exp_margin 4.5).
- Possessions: poss() from the total and both teams' ratings, or total / (2 x league points per possession). Points rise about 1.3 times as fast as expected pace (fast games are also efficient games), so read a points thesis off the implied team total, not pace alone.
- Power-rating check: ESPN BPI from the summary endpoint, Basketball-Reference adjusted ratings, DRatings, and any rating quoted in previews. Convert a win probability to a margin with 13 x norm.ppf(p).

### 2b. Team sheet (both teams: value, league rank out of 30, games, last 10)
Offensive and defensive rating, net rating, pace, effective FG%, turnover rate, offensive and defensive rebound rates, free-throw rate, 3PA rate, rim attempt share and assist rate, for and against; fouls per game; bench minutes share; starters' minutes; close-game record (context only); home and road splits; rest.

### 2c. What the defense gives up, by prop type (matchup_adj(allowed, league_avg, games, stat) regresses it; fitted)
- Shrinkage is fitted (MATCH_K): 20 games of weight for rebounds, assists and blocks allowed; 40 for points, threes, steals and turnovers; 5 for 3PA allowed (the most stable defensive trait). Capped at 15%. Team-level factors cut next-game error by 0.1-1.4% in 2012-24 data: real but small, so a matchup alone never carries a bet.
- Rebounds: the misses the opponent creates (FGA x (1 - FG%)) and its defensive rebound rate; rebounds allowed per game.
- Assists: assist rate allowed and scheme (switching teams cut pick-and-roll assists; trapping teams raise the handler's assists).
- Threes: 3PA allowed is real; 3P% allowed is mostly noise.
- Points: rim protection, fouls and FTA allowed, points by play type or archetype. Defense-vs-position added 0.00-0.13% on top of the team factor across 126,000 starter games, so it is never a reason (trap test 8).
- Steals and turnovers: forced turnover rate. Blocks: the opponent's rim attempt share.
- Home court is fitted into the engine (set p['home']): home players get +2.0% assists and +3.2% blocks (scorekeeping), +1.4% free-throw attempts, +1.0% rebounds and +0.8% shooting; road players the reverse.
- When the opponent's rotation changed a lot since last season (trades, a new coach, a rookie starter), last season's profile describes a different team: regress it 50% or more and say so.

Done when: both sheets show value, rank and games for every row, or "not found".

## Step 3: Player sheet (~6 min per shortlisted player)

### 3a. Minutes and role (fitted; references/calibration.md)
- project_minutes(minutes, margins, ots) on his last 5-15 games in his current role, oldest first, with his team's final margins and overtime periods. It adds back minutes lost to blowouts, weights recent games with a 2.5-game half-life and applies the role regression (stars' recent minutes run 0.6 high). In 2014-24 data it beat a last-5 average (error 6.55 minutes), last-10 (6.59) and the season average (7.03) at 5.96. Its output is the "min" input: minutes in a competitive game.
- A confirmed lineup change tonight: role_change='promoted' adds about 11.5 minutes to a 12-minute bench player, 7.3 to a 21-minute one, 5 to a 27-minute one and 3 to a 33-minute one, with extra uncertainty; 'demoted' takes 4-9 (more from bigger roles).
- When a key teammate sits, stars gain almost nothing (+0.6 for 30-36 minute players, about 0 above 36); the player who takes the starting spot gains 5-11 and other rotation players 1-3 (usage_shift()).
- Blowouts (fitted, by final margin): stars lose about 1 minute at 10-12 points, 4.5 at 18-21, 6 at 24-27 and 8.6 at 35+; starters lose 3.3, 4.8 and 6.3 at the same margins; rotation players about 1-2; bench players gain 1-3. Close games add only 0.1-0.2 minutes. Overtime adds 4.6 minutes per period for stars, 4.0 for starters, 2.1 for rotation players.
- Foul rate (pf36) drives the chance of a big minutes loss for stars and starters: at 4.5+ fouls per 36 it is about double the rate at 2.5.
- Minutes restrictions: set cap. Returning from injury with no announced limit: write "none announced as of [date]" and add min_sd_extra of 3.
- Back-to-backs barely matter once he plays: stars and starters lose 0.2-0.3 minutes, bench players gain 0.4-1.0 when others rest, and per-minute output moves under 1.5%. The real back-to-back risk is a rest day, which voids the prop.
- Preseason minutes don't count (starters often play a half); use preseason only for who starts and who closes.

### 3b. Volume
Usage rate; FGA, 3PA and FTA per 36; 3PA share of FGA (project_share()); touches and time of possession; potential assists; rebound chances; rebounds and assists per 36.

### 3c. Rates (fitted)
- project_rate(stat, season total, season minutes, last-season total, last-season minutes, last-10 total, last-10 minutes) for fga, fta, reb, ast, stl, blk and tov. It shrinks this season toward last season by fitted minutes of weight (STAB: 100 for rebounds, assists and shot attempts; 200 for points, threes, FTA and blocks; 400-600 for turnovers and steals), blends in 10-40% of the last-10 rate (30% for assists, 40% for 3PA), and applies the in-season drift correction (assists and 3PA share keep rising during a season: +3.4% and +1.9%).
- Shooting percentages: project_pct(made, attempts, prior %, key) with about 350 attempts of weight for 2P%, 750 for 3P%, 200 for FT%.
- No last season (rookies, long injuries): pass the league per-36 rate for his role as league36 and use rate_cv 0.13.

### 3d. Game logs and hit rates
The last 10-20 games in his current role with minutes and opponent. hit_rate() at the posted line counts only games in the role he has now (same teammates in or out).

### 3e. Availability
Official status (Out, Doubtful, Questionable, Probable, Available), return-from-injury limits, rest on back-to-backs, G League assignments, personal leave. A questionable star changes every teammate's projection, so run both versions. When sources disagree on a status, the league's official report wins; until it posts, the status is unresolved. For a player back from surgery, look for an announced minutes limit and write "none announced as of [date]" when there isn't one.

### 3f. Usage shifts when teammates sit (fitted on 1,490 key-player absences, split-sample)
- usage_shift(out player's r36, teammates) applies the measured rule: every remaining player's FGA per 36 rises by 0.135 x (the missing player's FGA per 36 minus 10.6), about +1.1 when a 19-FGA star sits and nothing when a low-usage starter sits, and the rise is similar for stars and role players; assists rise 17% across the board when the missing player is a playmaker (7+ AST per 36); rebounds rise 4.5% when he is a big (10+ REB per 36); minutes move as in 3a (mark the new starter promoted=True).
- With/without splits from StatMuse ("{player} stats when {teammate} did not play this season") are a check, shrunk with wowy_bump() (8 games of weight). When a split disagrees with usage_shift() by more than its sampling noise, find the reason (a scheme change, a different fifth starter) before trusting it.
- The team budget (Step 6b) must still add up.

### 3g. Matchup
Likely primary defender and scheme (drop, switch, blitz, zone), size and rebounding matchups, the opponent's rim protector and his foul trouble.

### 3h. Chemistry, momentum and coaching
- Run the 30-day pulse (references/sources.md).
- Real momentum: minutes, usage or efficiency rising because of a role change seen in 2+ games. Fake: shooting heaters, garbage-time lines, weak opponents.
- Coaching: rotation changes, a new coach, how fast he pulls starters in blowouts.

### 3i. Schedule and motivation
- Second night of a back-to-back, 3 games in 4 nights, the end of a long road trip, altitude (Denver, Utah), time-zone travel, national TV. A road team on the second night of a back-to-back has played about 1-3 points per 100 possessions worse (Grantland, 2010-12 data); the bigger prop effect is rest decisions and minutes limits.
- NBA Cup group nights in 2026: Oct 30; Nov 6, 13, 20, 24, 25 and 27. Point differential is the first tiebreaker after head-to-head, so a favorite may keep starters in longer. Check the coach's past Cup blowouts before applying the normal garbage-time cut.
- Late season: playoff seeding, rest, and the 65-game award rule (a game counts with 20+ minutes, plus up to two games of 15-19 minutes; Adam Silver said in Oct 2026 the league is happy with it). New 2026-27 lottery rules (reconfigured odds, no back-to-back lottery wins, no top-five pick three drafts in a row, a "relegation zone") should cut late-season tanking; teams that don't own their 2027 first may still lose on purpose (TSN, Oct 6, 2026).

Done when: projected minutes, projected per-36 rates, availability and the three deciding factors are written with sources and dates.

## Step 4: Where to get it
Read references/sources.md: data (StatMuse, the ESPN APIs, Basketball-Reference ratings, the official injury report and lineups), markets and line shopping (his screenshots, Kalshi, multi-book odds pages, sharp reference prices), outside models, the 30-day pulse rules, splits, parallel research, and the Dead ends list. Read the Dead ends before any fetch.

Done when: every source used is named with its date, and any source that failed is listed in the coverage line.

## Step 5: The game-script engine (~5 min per game)

### 5a. The market's script (fitted)
script_probs(exp_margin) gives the chance of each final-margin bucket (blowout loss, comfortable loss, close, comfortable win, blowout win) and of overtime, from a normal margin with an SD of 13 points around the spread. SD 13 reproduces the 19% share of 20+ point games in 2021-24 (the v1 value of 12 gave 15% and underpriced blowouts). Overtime: 7.0% in pick'ems, falling to 2.8% at a 16-point spread; 14% of overtime games go to a second overtime. Possessions come from the total, with an SD of 4.6 per game.

### 5b. Our script
Adjust the market's script only for concrete reasons: injuries the line hasn't absorbed, a coach who pulls starters early or rides them, a team that routinely blows out weak opponents, rest, the Cup tiebreaker. Write each adjustment with its reason.

### 5c. Script archetypes and what they do to props

| Script | Signs | Helps | Hurts |
|---|---|---|---|
| Close game | spread under 5, good closers | no blowout cut for starters; overtime upside (7%) | bench minutes |
| Comfortable favorite | spread 6-10 | | favorite starters lose about 1-2 minutes on average |
| Blowout risk | spread 10+, or a big net-rating gap | favorite starters' unders | starters' points and PRA overs (stars lose 5.5 minutes at a 22-point margin) |
| Trailing team chases | a big early deficit | trailing team's 3PA, garbage-time bench stats | trailing starters' minutes once it gets out of hand |
| Pace-up shootout | high total, two fast teams, weak defenses | counting stats, assists | unders |
| Grind | low total from slow pace | volume unders | |
| Brick fest | low total from poor shooting at normal pace | rebounds (more misses) | points, assists |
| Whistle-heavy | a high-foul crew, two high free-throw-rate teams | free-throw-driven scorers | bigs in foul trouble |
| Star trapped or doubled | the opponent blitzes pick-and-roll or doubles the post | his assists, the roll man, spot-up threes | his points |
| Switch-everything defense | | isolation attempts | pick-and-roll assists |
| Drop coverage | | handlers' pull-up shots | the roll man's rim attempts |
| Overtime | close spread | every over | every under |

### 5d. Quarter flow
Starters usually play about 8-10 of the first 12 minutes, stars sit early in the second quarter, the third mirrors the first, and the fourth belongs to closers in a close game or the bench in garbage time. Cleaning the Glass defines garbage time as the 4th quarter with a lead of 25+ from 12:00 to 9:00, 20+ from 9:00 to 6:00 or 10+ under 6:00, with two or fewer starters on the floor. First-quarter props depend on starters' first-quarter minutes, so blowouts barely touch them.

### 5e. Write the script
3-6 plain sentences: who controls tempo, where each team scores, the key matchup, and what the 4th quarter looks like. Then the script-to-prop map (which props the story helps and hurts) and the kill switches (early fouls, an injury exit, a blowout, overtime, a hot or cold shooting night by one team), each with rough odds.

### 5f. Script dependency
script_table() shows each script's weight and the bet's hit rate inside it. script_fit() returns 2 when the bet hits 55%+ in the likeliest script and 50%+ in the next one, 1 when only the likeliest script carries it, and 0 when it needs a minority script. It also flags a fragile bet: a script with 25%+ weight in which it hits under 40%.

Done when: each game has its script story, bucket odds and kill switches, and each shortlisted bet has its script table.

## Step 6: Build the numbers (~10 min)

### 6a. Our projection
- Inputs per player: min and min_sd_extra (project_minutes()), r36 per-36 rates (project_rate()), s3 the 3PA share of FGA (project_share()), pct with p2, p3 and ft (project_pct()), home (True, False or None for neutral), pf36, his team's average possessions (team_poss), first-quarter minutes (q1_min, optional), matchup multipliers (adj, from matchup_adj()), a minutes cap if restricted, and rate_cv. The role (star, starter, rotation, bench) comes from projected minutes (34+, 28+, 18+); pass role only to override.
- rate_cv is how unsure we are of his true rates: 0.05 for a settled role with last season behind him and 20+ games this season, 0.09 for 10-20 games or no last season, 0.13 for a new role or team. The engine multiplies it per stat group (tuned so the 50/80/90% ranges held their coverage on 2014-20 data) and correlates the errors across his stats.
- Run sim_player() (40,000 games). One run prices every prop for that player. For several players in one game, sim_game_players() runs them from one shared game draw.
- calibrate_min(p, g, close-game average) still works when all you have is his average minutes in games decided by under 10.

### 6b. Budget checks
- Team points: the rotation's projected points vs the implied team total (team_budget()). More than 4 points off means a projection or the total is wrong; say which.
- Usage: shots added to teammates after an injury follow usage_shift(); the bumps can't add up to more than the missing player's shots.
- Minutes: the rotation adds to 240 (265 with overtime).

### 6c. Outside models, book-style numbers and the exchange (compare, don't copy)
How books build NBA props:
1. A base projection (recent minutes x per-minute rates, often bought from a data feed), shaded toward demand.
2. A few market-making books post first with low limits; others copy. Limits are low, so modest money moves lines.
3. The public bets overs on stars and national-TV games, so retail books shade those overs (a higher line or extra juice).
4. Alt ladders and milestones come off the main line through an assumed distribution, so the tails can be off. ladder() shows where.
5. Combos and same-game parlays are priced with correlation assumptions and heavy hold.
6. News pulls props off the board; re-posted lines often move the obvious beneficiary and lag the second one.
7. Holds run about 7% on -115/-115 props and much more on parlays. Winners on props get limited quickly.

Side by side for every shortlisted bet: our research number; the book-style number (his season per-minute rate x the minutes the book can see); every outside projection (references/sources.md); the sportsbook-implied mean (market_mean(), from every posted line and both prices, with book names); and the Kalshi-implied mean (fit_ladder() on the liquid thresholds of his ladder). compare_models() lists each gap in SD units and flags gaps of 0.35 SD or more. For every flagged gap, write one line on why it differs (minutes, role, pace, injury timing). When you can't explain a gap in our favor, side with the consensus.

### 6d. Blends
- Logic mean = 60% ours + 40% the outside-model average (ours alone when none exist; say so).
- Market mean = market_mean(quotes): each book's line and both prices turned into an implied mean, weighted by how sharp the book is (Pinnacle and Circa 3x, Bookmaker 2x, FanDuel and DraftKings 1x, slower books less; one-sided prices half), plus a liquid Kalshi ladder's fitted mean through extra=[(mean, weight)].
- Final fair = 60% logic mean + 40% market mean (W_MKT = 0.40; v1 used 25%). final_probs() returns p_final, its chance to win at the posted line, and p_push on whole-number lines. The weight moved toward the market on Oct 27, 2026: the engine is now calibrated, but its inputs are public box scores and the market also sees injury news, lineups and sharp money. fit_blend() resets it once 100+ settled bets are logged (Step 15).
- Conservative check = 30% logic, 70% market (p_cons): does the bet still win more often than its breakeven?
- Double-doubles and triple-doubles: event_final(model probability, market no-vig probability).

### 6e. Alt lines
Price every alt line off the main line's market: final_probs(x, alt_line, side, quotes=[(main_line, over, under, book)]). The alt's own one-sided price carries extra hold and isn't the market's view. Use an alt only when the logic points to that number or a parlay needs a safer leg (Step 12). A straight on an alt line must still be priced -190 or better (Step 11c) and clear the profit gate (Step 11d); safer alts that fail either are parlay legs only.

Done when: each shortlisted bet has our mean, every outside number, the book-style number, the market and Kalshi means, p_final, p_push, p_cons and the budget checks.

## Step 7: Forecasting discipline (superforecasting + Bayesian calibration)

### 7a. Outside view first
Write the base rate before any argument: the sportsbook's no-vig probability (and the Kalshi price) is the first reference class; his role-filtered hit rate at this line is the second; the league-wide rate for this kind of prop is the third (about 50% by construction). Every inside-view argument must explain why tonight differs from all three.

### 7b. Evidence weighed by how diagnostic it is
For each piece of evidence, ask how much more likely it is if the bet wins than if it loses (the likelihood ratio). Near 1 means it moves nothing: "revenge game", a two-game shooting streak, a head-to-head record, a defense-vs-position split. Strong: a confirmed role change with 4+ more minutes, a teammate's absence (usage_shift(), checked against a with/without sample of 5+ games), a script shift the line hasn't absorbed. Write each factor with its direction and size band (for example, minutes up 3 = +6 to +9 points of probability) and make the final number add up from the base rate.

### 7c. Sensitivity
sensitivity() shows how the chance to hit moves with 3 minutes less or more, 3 possessions less or more, and a 5-point swing in the expected margin. A bet that drops under 50% with 3 fewer minutes is minutes-fragile: say so, and cap it at 5 when there is a real minutes risk.

### 7d. Tripwires and the market guard (diagnosing-bugs: checks that go red)
- sanity() flags projected minutes above 40.5 or below 12, a pace factor outside 0.92-1.08, and our mean beyond TOO_FAR from the market (points 3.5, rebounds 1.8, assists 1.6, threes 0.8, PRA 4.5).
- market_guard() flags a final probability more than 12 points away from the market's no-vig probability.
- A red flag needs a concrete, sourced reason the market hasn't priced (news in the last hour, a confirmed role change). Without one, cap the bet at 5 and lean on the conservative blend.

### 7e. Calibration humility
No straight prop above about 75% to hit unless it's an alt line or a confirmed role change the line hasn't caught. Parlays inherit honest leg probabilities; nothing gets rounded up to make a ticket look better.

### 7f. Why it might be wrong, and what would change it
Write 2-3 specific ways the forecast could be wrong and the update triggers: the news or line moves that would raise or lower the chance to hit (he's ruled questionable, the line moves past his median, a teammate is upgraded to available). These feed the "what would change my mind" bullet and the re-check in Step 14.

Done when: each shortlisted bet has its base rates, a weighed evidence list, a sensitivity line, any red flags resolved, and its update triggers.

## Step 8: Anatomy and the test battery (the anti-narrative layer)

### 8a. Bet anatomy (anatomy)
Break the bet into its working parts with numbers: minutes x attempts per minute x conversion, plus free throws. For rebounds: the misses available x his share of them. For assists: potential assists x conversion. Name the one part that must go right and how often it does.

### 8b. Narrative audit
List every claim the pick leans on (ours, the media's, the public's). Test each one with data and tag it:
- Verified: a number supports it in two independent windows (this season and last, or the last 10 and the season) or from two sources.
- Unverified: no test was possible. It adds nothing to the score.
- Refuted: the data says otherwise. If the pick relies on it, PASS.

Common narratives and their tests:
- "Revenge game", "loves playing at home": his splits with enough games. Usually noise. Home court itself is real but small and already in the engine (Step 2c).
- "Always kills this team": head-to-head samples are tiny. Find out whether it's the matchup (scheme, size) or luck.
- "Pace-up spot": compare projected possessions with his team's average. Under 2% is nothing.
- "Worst defense against point guards": check who played those minutes and the play-type data. Defense-vs-position alone fails (tested: it adds 0.00-0.13% to the team factor).
- "He's hot": rising volume (FGA, 3PA, minutes) passes; rising percentages alone fail (no game-level shooting streaks in 14 seasons).
- "Usage bump with X out": usage_shift() gives the fitted bump; with/without data over 5+ games, shrunk, is the check; the team budget must still add up.
- "More minutes with X out" for a star: refuted in general (stars gain 0-0.6 minutes); it needs a coach's quote or a 3+ game pattern.
- "Everyone likes it": if every article and tout has the same prop, the price already has it. Treat it as the public side, and fade it only when the data supports the other side.

### 8c. Trap battery (answer every test; trap_flags() automates the numeric ones)
1. Public over: a popular star, national TV, an over the public is hammering, and the line won't move toward it.
2. Recency: the line jumped after 1-3 big games, or his last 3 games run 25%+ above his season.
3. Blowout: a starter's over on a 10+ point favorite, or the underdog's star in a mismatch.
4. Minutes risk: questionable tag, restriction, back-to-back, or a foul-prone big against a foul-drawing frontcourt.
5. Usage overreaction: the line moved more than the bump usage_shift() supports, or the bump goes to someone else.
6. Too good to be true: a line far from our number and the models with no news found. The book usually knows something.
7. Steam against: the line moved 1+ point against us (0.5 for rebounds, assists and threes) with no news.
8. Defense-vs-position mirage: the matchup edge rests only on position splits.
9. Shooting heater: a points or threes over built on percentages, not attempts.
10. Garbage-time inflation: averages padded by blowout minutes he won't get tonight.
11. Early-season role: a new team or coach, or under 5 games in his current role.
12. Correlation: two bets on one game that need the same script.

For every game on the card, also name the most popular public prop and say whether it's a trap and why. One failed test costs a point unless the research explains it away; two or more cap the bet at 4.

### 8d. Grill the thesis (grilling)
Map the thesis as a decision tree, in order: minutes, role, script, volume, conversion, market, price. Ask each open question and answer it with a fact and a source; finding facts is your job, not the user's. A branch still unsettled when you score is an assumption: name it in the breakdown and cap the bet at 5 if it depends on it.

### 8e. Desk board meeting (chief-of-staff)
For each shortlisted bet, five desks give one line each, in one turn, with no back-and-forth:
- Minutes desk: projected minutes and the main risk to them.
- Matchup desk: his volume against the opponent's profile.
- Script desk: the likeliest script and how the bet does in the next one.
- Market desk: models, Kalshi, line movement, splits, and the best available price.
- Skeptic: the strongest data-backed case for the other side.

Synthesis: what the desks agree on; the disagreement, named, with each side's reason; the one decision. Name conflicts instead of smoothing them over.

### 8f. Blind check (full cards)
When subagents are available and the card has 3+ bets (the user asked for this testing on Oct 21, 2026), give a fresh subagent only the raw inputs (minutes log with margins, rates, pace, injuries, the line) and scripts/nba_props.py, with no thesis, and ask for its projection and its best case against the bet. If its number differs from ours by more than TOO_FAR, find out why before scoring. Without subagents, re-derive the projection from the raw inputs before re-reading your earlier reasoning.

### 8g. Pre-mortem
1. Is my side the public side? What does the research show that the public misses?
2. Does our number sit on the line? Then it's a coin flip: WATCH or PASS.
3. What would cost him 4+ minutes tonight, and how likely is it?
4. Does the bet survive the second-likeliest script?
5. Any news since the line opened? Is any outside model stale?
6. Am I overreacting to his last game?
7. Is the obvious story already in the number?
8. What is the likeliest way this loses, and how often? If losing is as plausible as winning, drop a point.
9. Does another pick need the same script? Cap that script at 2u.
10. Is this the market that best isolates the thesis?
11. Is this the best price for it at any book he uses?

### 8h. Research coverage check
Mark each done or "not found": slate scan; game lines and opener; team sheets; opponent prop profile; player sheet; injuries and statuses; usage shifts; matchup; 30-day pulse; schedule spot; script; simulation; outside, book-style and Kalshi numbers; market mean; base rates and evidence weights; sensitivity; splits; line movement; line shopping; narrative audit; trap battery; board; profit gate. Give the user one line listing anything not found.

### 8i. Verify before sending (verification-before-completion)
Evidence before claims. Right before the card goes out: re-pull injuries and lines for every pick and parlay leg; re-check every number a breakdown cites against its source; re-run any projection whose inputs changed; re-run the profit gate at the current price. A number that couldn't be re-checked is labeled "not re-checked" in its bullet. Words like "should be fine" or "likely still" never stand in for a check.

Done when: every shortlisted bet has its anatomy, narrative audit, trap results and board synthesis, the coverage line is written, and every cited number was re-checked or labeled.

## Step 9: The engine (scripts/nba_props.py, v2)
Copy scripts/nba_props.py into the working directory and import it. Store each pick's inputs (p, g, stat, line, side, quotes, models) in the tracker so autoresearch can replay them. Every fitted constant is listed with its data in references/calibration.md; the GitHub repo josemonet/nba-bets holds the research scripts, the backtest and the tests.

What it holds:
- Game: script_probs(), draw_game(), p_ot(), poss().
- Minutes: project_minutes(), calibrate_min(), role_for().
- Rates and usage: project_rate(), project_pct(), project_share(), matchup_adj(), usage_shift(), wowy_bump().
- Simulation: sim_player(), sim_game_players(), sgp(). Stats: MIN, PTS, REB, AST, FG3M, FG3A, FGA, FGM, FTA, FTM, STL, BLK, TOV, PRA, PR, PA, RA, STOCKS, DD, TD, Q1_PTS, Q1_REB, Q1_AST.
- Probabilities: p_hit() (half-point lines), p_outcomes() (win, push, loss), ladder(), bet_zones(), script_table(), script_fit(), sensitivity().
- Market: devig(), mkt_mean(), market_mean(), final_probs(), fit_ladder(), kalshi_weight(), compare_models(), event_final(), one_way_fair(), est_price().
- Checks: sanity(), trap_flags(), market_guard(), team_budget(), hit_rate().
- Score and card: score(), verdict(), pick_top(), straight_ok(), price_note(), best_straight_line().
- Profit: breakeven(), edge(), ev_line(), profit_gate(), bet_to(), kelly(), stake_units(), best_offer().
- Parlays: build_parlays(), joint_prob(), parlay_price(), house_edge(), implied_lift(), round_robin().
- Tracking: brier(), logloss(), calib(), clv(), fit_blend(), replay(), autoresearch().

Example:
```python
import nba_props as m
g = dict(exp_margin=4.5, total=231.5, team_poss=99.0)                       # team A favored by 4.5
pm = m.project_minutes([35, 37, 31, 36, 34], margins=[4, -2, 24, 7, 1])      # last 5 games, oldest first
star = dict(min=pm['min'], min_sd_extra=pm['min_sd_extra'], home=True, pf36=2.4, team_poss=99.0, rate_cv=0.05, s3=0.40,
            r36=dict(fga=20.0, fta=7.5, reb=5.0, ast=7.0, stl=1.3, blk=0.4, tov=3.2), pct=dict(p2=0.53, p3=0.36, ft=0.86))
big = dict(star, min=31, pf36=3.8, s3=0.04, r36=dict(fga=11.5, fta=4.5, reb=12.0, ast=3.0, stl=0.8, blk=1.8, tov=2.0),
           pct=dict(p2=0.62, p3=0.30, ft=0.70))
S_star, S_big = m.sim_game_players([star, big], g)                          # one shared game draw
fp = m.final_probs(S_star['PTS'], 26.5, 'over', quotes=[(26.5, -115, -105, 'fanduel'), (26.5, -110, -110, 'pinnacle')],
                   models=[27.2, 26.0])
gate = m.profit_gate(fp['p_final'], fp['p_cons'], -115, fp['p_push'])        # ok, edge, breakeven
stake = m.stake_units(7, fp['p_final'], -115, bankroll_units=40)             # verdict stake capped at quarter Kelly
shop = m.best_offer(S_star['PTS'], 'over', [('fanduel', 26.5, -115), ('draftkings', 25.5, -140)], c=fp['final_mean']/S_star['PTS'].mean())
rows = m.script_table(S_star, 'PTS', 26.5); pts, fragile = m.script_fit(rows)
flags = m.sanity(S_star, star, g, 'PTS', fp['market']); sens = m.sensitivity(star, g, 'PTS', 26.5)
kal = m.fit_ladder(S_star['PTS'], {25: 0.60, 30: 0.33})                      # Kalshi mids for 25+ and 30+
leg = dict(id='star o26.5 pts', player='star', game='G1', stat='PTS', side='over', p=fp['p_final'], score=6, price=-115,
           hits=m.leg_hits(S_star, 'PTS', 26.5, 'over'))
# card: m.pick_top(candidates, n); each candidate carries a posted price or m.est_price(); anything past -190 or failing the gate is skipped
# parlays: m.build_parlays(legs, 'safe') and m.build_parlays(legs, 'risky'); legs can be any price, the ticket must be +EV
```

## Step 10: Confidence score (1-10): how likely the bet is to hit
The score measures the logic: the chance to hit plus how strongly the tested evidence supports it. The price never raises or lowers it.

Chance to hit (0-2), from p_final at the posted line:
- 2: 60% or more
- 1: 55-59.9%
- 0: under 55%

Evidence (0-8):
- Minutes and role (0-2): 2 = secure minutes (stable role, no tag or restriction, low foul risk) in the role the projection assumes; 1 = one real risk; 0 = uncertain minutes or role.
- Matchup and volume (0-2): 2 = his volume and the opponent's profile both favor the bet, tested in Step 8b, 5+ games each; 1 = one favors, the other is neutral; 0 = mixed or against.
- Game script (0-2): the script_fit() points.
- Models and market (0-1): 1 = most outside models, the market mean and Kalshi sit on our side of the line, and no unexplained steam runs against us.
- Momentum, chemistry and situation (0-1): 1 = a verified 30-day signal or schedule edge on our side; 0 = against, unknown or narrative only.

Caps and adjustments (CAPS in the code):
- Under 50% to hit: cap 3 (PASS). 50-54.9%: cap 4 (WATCH).
- Conservative check under 50%: cap 5.
- Unresolved status (questionable, game-time decision): cap 4 until it resolves.
- Refuted claim the pick relies on: cap 3. Unverified claim the pick relies on: cap 5.
- Minutes restriction, projected minutes under 24, a fragile script, a minutes-fragile bet with real minutes risk, a threes over under 6 projected attempts, or a red tripwire with no sourced reason: cap 5.
- Under 5 games in his current role: cap 6.
- Two or more failed trap tests: cap 4. One: minus 1 unless the research explains it.
- Minus 1 if the bet repeats a higher-ranked bet's script in the same game.
- Long shots (+300 or longer) rarely reach 55% to hit, so they usually land at WATCH or PASS. That's intended.
- Price: no effect on the score. The profit gate (Step 11d) and the -190 cap (Step 11c) decide only whether a scored bet is placed and how big.

Anchors: 9-10 rare (major news the line hasn't caught); 7-8 strong; 6 solid; 5 small; 4 watch; 3 or less pass.

## Step 11: Straight bets: ranking, verdicts, the price checks and sizing (minimum baseline score = 5)

### 11a. Ranking the card
- pick_top(candidates, N) skips any candidate priced shorter than -190 (Step 11c) or failing the profit gate (Step 11d), then ranks by score (after the same-script penalty), then chance to hit, then the conservative check, then script fit. It keeps at most 2 bets per game and 1 per player (2 only for clearly separate theses, and never two that need the same script), and stops at N or when scores drop under 5 or the chance to hit under 55%.
- Each pick carries a one-line rank reason: what puts it above the next one (higher chance, sturdier minutes, a script it survives).

### 11b. Verdicts and stakes

| Score | Verdict | Stake (before the Kelly cap) |
|---|---|---|
| 8-10 | STRONG TAKE | 1.5u (max) |
| 6-7 | TAKE | 1u |
| 5 | TAKE SMALL | 0.5u |
| 4 | WATCH | no bet now; say what would make it a 5 (news, a different line number, a better price) |
| 0-3 | PASS | none |

- The stake is stake_units(score, p_final, price, bankroll_units): the verdict's stake, capped at a quarter of the Kelly stake for that edge, in 0.25u steps. A STRONG TAKE with a thin edge gets a small stake; the cap never raises a stake above the verdict's.
- FADE means bet the other side. Recommend it only when the other side scores 6+ on its own and clears the gate.
- SKIP THE GAME: if nothing in a game scores 5+ and clears the gate, say "no bet on this game".
- Limits: at most 2u on one game script (straights and parlay legs together); at most 4u per day, parlays included, and never more than the balance; after a losing night keep the same unit size.
- Daily cap with a long card: when the bets he asked for add up to more than 4u, keep every bet and multiply every stake by the same factor (4u divided by the card's total), rounded down to the nearest 0.25u with a 0.25u floor, so every bet he asked for stays on the card. If the floor still runs past 4u, stake the top picks by rank and list the rest without a stake. Say so in one line of the stake plan; he can raise the cap any time.
- When the balance forces a priority order, fill it strictly by rank.
- If a line move could change the logic (a points line crossing his median, a rebounds line moving a full board), say which number would change the verdict.
- Straights priced from -150 to -190: add one line on what a loss costs.
- A long shot that scores 5+ gets half the stake (max 0.5u).

### 11c. The -190 straight cap (Oct 22, 2026)
He won't place a straight bet at -200, so every straight on the card must be priced -190 or better. Parlay legs are exempt.
- What qualifies: -190, -175, -150, -110 and any plus price. What doesn't: anything shorter than -190 (-195, -200, -250, -400).
- Where it's checked: the price at the book he'll use, FanDuel first. Another legal book with the same number at -190 or better also works.
- Re-express before dropping. When the safest number for a thesis is priced shorter than -190 (common for safe alts like 6+ assists or 8+ rebounds), move to the safest number priced -190 or better that also clears the profit gate, usually the main line or the next alt up (best_straight_line(x, side, prices, min_edge=m.MIN_EDGE)). Run final_probs() at that number and score it on its own. If it scores 5+, hits 55%+ and clears the gate, it's the straight. If not, the thesis isn't a straight that night; keep the shorter number as a parlay leg.
- Never fill the count with weaker bets because of the cap. Give a shortfall line ("2 of 3 straights qualify under the -190 cap and the profit gate") and name the bets that moved to the parlay-leg list.
- No screenshot: estimate the price with est_price() from the blended market chance, and price alts off the books' main lines when they're posted. Estimates from Kalshi mids alone came out too long on Oct 22, 2026: Harden 6+ assists looked like -250, but BetMGM's 6.5 line at -140 put it near -300. Mark estimates "about", and for any estimate from -175 to -190 add "place only if the app shows -190 or better" plus the fallback number (price_note()).
- Re-check (Step 14): if a straight's price moves past -190 before he bets, switch to its fallback number or drop it.
- The cap never changes a score or a verdict. A bet can be a STRONG TAKE on logic and still go only into a parlay because of its price.

### 11d. The profit gate, the bet-to price and line shopping (Oct 27, 2026)
- breakeven(price, p_push) is the chance to win a bet needs to break even: 52.4% at -110, 60.0% at -150, 65.5% at -190. profit_gate(p_final, p_cons, price, p_push) passes a straight only when p_final clears its breakeven by MIN_EDGE (2 points) and p_cons clears breakeven. The gate never changes a score; it decides whether a scored bet is placed.
- bet_to(p_final) is the shortest price at which the bet still passes: put it on the card ("bet to -135") so he can skip the bet if the app's price has moved past it.
- Two known soft spots need a 4-point edge (profit_gate(..., min_edge=0.04) and bet_to(p, min_edge=0.04)): threes overs the model puts at 60-70%, which hit about 3 points less in the backtest, and points or PRA unders it puts near 60-64%, which hit 3-4 points less (references/calibration.md).
- A bet that scores 5+ but fails the gate is labeled HITS, NO VALUE AT THIS PRICE, with its bet-to price. It can still be a parlay leg if the ticket is +EV, or go on the watch list for a better number.
- Line shopping: before placing, run best_offer(x, side, [(book, line, price), ...], c=final_mean/sim_mean) across every legal book he uses and every posted number for that thesis. It ranks offers by EV with each one's chance, push chance and edge. Recommend the best one; a half point or 15 cents of price is often the whole edge.
- Thin edges stay small: the quarter-Kelly cap (Step 11b) sizes by edge, so a 2-point edge at -110 is about 0.25-0.5u on a 40-unit bankroll even when the score is 8.
- Honest expectations, as plain math: at -110, winning 55% of bets returns about 5% of what is staked and 58% about 10%; rates above that over hundreds of bets are rare, and losing weeks happen at either rate. The card says so when he asks how much to expect; it never promises a result.

Done when: the card holds up to N ranked picks, each with verdict, stake, edge, bet-to price, best book and rank reason, inside the limits.

## Step 12: Parlays (when he asks)

### 12a. How parlay odds work
- Leg prices multiply as decimals: two -110 legs (1.909 each) pay 3.645, which is +264. parlay_price() does it; american() converts back.
- Fair odds are 1 divided by the joint chance to hit.
- The book's edge compounds with every leg. On coin-flip legs priced -110, the house edge is 8.9% for 2 legs, 13.0% for 3, 17.0% for 4, 20.8% for 5 and 24.4% for 6 (house_edge()). The breakeven per leg stays 52.4%, so a parlay of good legs compounds the edge and a parlay of coin flips compounds the vig (Establish The Run).
- Straights are still the core of the card: a parlay has a higher variance than straights on the same legs, and its stake stays smaller (Step 12e).

### 12b. Multi-game, same-game and SGP+
- Multi-game parlay: legs in different games are close to independent. The book multiplies the leg prices, and our joint chance is the product of the legs' p_final.
- Same-game parlay (SGP): legs share minutes, pace, margin and overtime, so they're correlated. Books price SGPs with a correlation model and add extra margin; one industry write-up (DeucesCracked) puts SGP holds around 8-12% for 2 legs, 12-18% for 3 and 18-30% for 4+, higher for prop-heavy tickets. Treat those as rough.
- Our same-game joint chance comes from the shared simulation: joint_prob() multiplies the legs' p_final and applies the lift from sim_game_players(). Fitted links: teammates' shot attempts move against each other (-0.03 to -0.05 correlation at fixed minutes); a playmaker's assists move with a scoring teammate's points (+0.12); everyone shares minutes, pace and overtime. Two stars' overs on opposite teams both gain from close games and overtime.
- Check every SGP price: implied_lift(app SGP price, leg chances) is the correlation the book is charging for; compare it with our lift. If the book charges more than our simulation supports, the ticket costs more than it's worth, so prefer legs from different games.
- SGP+ (FanDuel) combines SGPs from several games: each game's legs are priced as an SGP, then the games multiply.
- Restrictions: same-player multi-under parlays are banned for 2026-27, and books block or force into an SGP legs that depend on the same outcome (a player's points and his PRA).

### 12c. Rules that change a parlay's payout
- FanDuel removes a voided leg and recalculates the rest; if every leg is voided, the stake comes back. A player who doesn't play voids his single prop; check how the book grades a non-playing player inside an SGP before betting one with a questionable player.
- A push on a whole-number line drops that leg and reprices the ticket.
- FanDuel Bet Protect (NBA): an injury exit in the first quarter on a pre-game, full-game player prop removes that leg from straights, parlays and SGP/+ and reprices the rest; it pays in bonus bets, and only when the injured leg was the only loser. Bet Protect+ (3% fee, full game, cash, launched April 2026) isn't offered in Tennessee.
- DraftKings Early Exit (since Aug 2025): a starter's first-quarter injury exit in the NBA regular season removes the leg and reprices the parlay; unders are excluded.
- Profit boosts raise the payout, never the chance to hit, so they never change which legs we pick. Show the boosted EV as information; a boost can turn a near-miss ticket +EV.
- Round robins: every combination of k legs from a list (4 legs by 2s = 6 tickets). round_robin() gives the chance at least one ticket cashes and the expected return. Offer one when he wants partial wins from a strong list; it costs a stake per ticket.

### 12d. The logic of a parlay
1. Every leg stands alone. A leg that isn't a bet by itself never goes in to raise the price. Standing alone means it scores 5+ on logic. The -190 straight cap doesn't apply to legs, so a safe alt priced past -190 can be a leg (Oct 22, 2026), but a leg worse than -3% EV at its own price is dropped: heavy juice on a leg that doesn't earn it drags the whole ticket.
2. Independence or one shared script. Legs from different games fail independently, so one bad script kills one leg, not the ticket. Same-game legs go together only when they need the same script and our lift is 1.0 or more: both stars' overs in a close, fast game; a center's rebounds when the opponent bricks; a point guard's assists with his roll man's points. Never pair legs that need opposite scripts (a favorite star's over with that team's bench over); build_parlays() rejects same-game pairs with a lift under 0.98.
3. The best leg from each game is the one with the highest chance to hit and the sturdiest script fit, often a slightly safer alt line priced off the main line (Step 6e).
4. The weakest leg decides the ticket. Name it, its chance and its kill switch.
5. Legs that all depend on one piece of news (a star sitting) fail together; count them as one risk, not several.
6. No more than 2u on one game script across straights and parlays.
7. The ticket must be +EV on our joint chance at the app's price (build_parlays() enforces it at the multiplied price; recheck with the real SGP price).

### 12e. The two parlays (build_parlays(); his overrides win)
- SAFE & SMART: 2-3 legs, each 62%+ to hit and scored 6+, one leg per game, no minutes-risk legs, priced +100 to +400, +EV. Alt lines one step safer are welcome when they raise a leg's chance and the payout still clears +100. Aim for a 35-60% joint chance. Stake 0.5u.
- RISKY BUT SMART: 3-5 legs, each 55%+ and scored 5+, up to 2 legs per game when they share a script (lift 1.0+), priced +450 to +1500, +EV, and the highest joint chance available at that payout. Stake 0.25u.
- When nothing qualifies, build_parlays() loosens the legs in 2-point steps, never below 56% and a score of 5, and reports the level it used. If still nothing qualifies, say "no safe parlay today" or "no risky parlay today" instead of forcing one.
- The builder's price is the product of the leg prices. For any same-game pair, he reads the real SGP price in the app; recompute the joint EV line and implied_lift() with it, and drop the ticket if it turns -EV.

### 12f. What each parlay shows
- One line per leg: game, bet, leg chance to hit, price.
- The joint chance (our simulation), the app price and the fair price, the house edge, and the EV line.
- Why each leg is the best choice from its game, and why the other games' best legs didn't make it.
- How the legs relate: independent, same script, and the lift for any same-game pair.
- The weakest leg and its kill switch; void, push and Bet Protect notes; the stake.

Done when: both parlays (or a plain "none qualifies") are built with joint chances, prices, EV and the leg-by-leg logic.

## Step 13: Present (the user's required format)

### 13a. Order of the response
1. The straight picks first, one line each in rank order: rank, verdict, score, chance to hit, edge, bet-to price, bet, odds, book, stake in USD and units. Example: "#1 TAKE, 7/10 (63% to hit, +5.5 edge, bet to -150): [Player] Over 6.5 assists (-120, FanDuel), 1 unit (25 USD)". Every straight's price is -190 or better and clears the profit gate; an estimated price says "about" and carries the app check from price_note(). If fewer bets qualify than he asked for (including bets lost to the -190 cap or the gate), say so in one line instead of padding.
2. The parlays when requested, one headline each: "SAFE & SMART: 3 legs, 41% to hit, +240, +EV 9%, 0.5u" and "RISKY BUT SMART: 4 legs, 14% to hit, +780, +EV 9%, 0.25u", with the legs listed under each.
3. The next action with a time estimate ("Next (2 min): place #1 and #2").
4. State line: balance, bets placed, time to the first tip, next re-check.
5. Breakdowns, one per straight pick in rank order (13b), then each parlay's breakdown (13c).
6. Traps to avoid, HITS, NO VALUE AT THIS PRICE bets with their bet-to prices, other props considered, stake plan and coverage line.
7. The lesson of the night (13f) on full cards.
8. One concrete next action he can do in under 2 minutes.

### 13b. Each straight pick's breakdown (detailed, as long as it needs)
1. The bet, the score and the rank reason, on one line.
2. Why this bet, in detail. Each bullet starts with a bold label and carries numbers, ranks, sources and dates:
   - What has to happen and how often (the anatomy).
   - Minutes and role, with the main risk and the sensitivity line.
   - Volume against the opponent's profile, with ranks.
   - The game script: the story, the bet's hit rate in the likeliest and the next script, the kill switches.
   - Injuries and usage shifts.
   - Chemistry, momentum and coaching from the 30-day pulse (with dates), and the schedule spot.
   - From the base rate to our number: the market's probability, his role-filtered hit rate, each factor that moved it and by how much, and the final chance to hit.
   - Our number vs each outside model vs the book-style number vs the sportsbook and Kalshi markets.
   - Price: breakeven, edge, bet-to price, the best book and number from best_offer(), the Kelly-capped stake, and the EV line.
   - Tests: the narrative audit, the traps checked, the board's disagreement and how it was settled, and the blind check when one ran.
   - How it loses: the likeliest losing path and how often it happens.
   - What would change my mind: the update triggers from Step 7f.
   - The score in one line: chance, minutes, matchup, script, models and market, context, caps.
3. Why this bet and not the alternatives: his other props (why this stat and this number), the other side, his teammates' props, and the alt lines. When a safer number was over the -190 cap or failed the gate, say so and name the parlay it went into.
4. Public betting, as bullets (no table): % of bets and % of money on each side of the related game market with source and time, why the public is there, and what the money-vs-bets gap means. Label game-market splits and proxies as such.
5. Line movement, as bullets: opener, the current number at several books and on Kalshi, when and why it moved, whether the move changes the logic, and whether to bet now or wait.

### 13c. Each parlay's breakdown
Everything in Step 12f, written out: the case for each leg in two or three lines (pointing to its straight breakdown when it's also on the card), why the legs belong together, the math, the weakest leg, and the rules that could change the payout.

### 13d. Writing rules (i-have-adhd + humanizer; every response)
1. Lead with the answer: the picks, the parlays and the next action come first. No preamble ("Let me", "Great question"), no recap of steps, no closing pleasantries.
2. Number anything he has to do, one action per step ("1. Open FanDuel 2. [Player], Assists 3. Over 6.5, 1 unit").
3. Keep the top of the card scannable: the picks list, the parlay headlines and the next action stay short. The breakdowns underneath are long on purpose because he asked for great detail; bold labels keep them skimmable.
4. Restate state every turn: balance, bets placed, what's left, time to tip.
5. Give specific time estimates ("2 min", "re-check at 5:30 PM CT, 10 min").
6. After a slate, lead with the net result and each bet's win or loss on one line.
7. Cut tangents: model fixes, skill changes and side notes get one line at the end or a separate question.
8. State losses and mistakes matter-of-factly: cause and fix.
9. Short sentences, plain words, bold verdicts. Bold the breakdown labels and the verdicts, nothing else.
10. No em or en dashes; use commas, colons, periods or parentheses.
11. No "not X but Y" contrasts, no one-line closers that repeat the point, no staged openers ("Here's the thing").
12. No hype or stock AI words (crucial, pivotal, robust, elite as filler, delve, landscape, testament, showcase, lock). Give the number instead.
13. No unnamed authorities ("sharps are on it", "experts say"): name the source and what it showed.
14. Keep a hedge only when it carries real uncertainty.
15. Pre-send check: if he reads only the first and last lines, does he know what to bet and what to do next?

### 13e. Optional prop machine (anatomy)
When he asks how a bet works, build a small interactive page as an artifact: a gauge-style machine where sliders for minutes, pace, usage and the script move the readout, and every number shown comes from the same formulas as the model (export the simulation's per-script numbers into the page). The readout must match the breakdown. Keep it a small figure, not a multi-hour build.

### 13f. Lesson of the night (teach)
End each full card with one short lesson (3-4 lines) tied to a real pick or parlay: one concept (minutes risk, regression, script dependency, de-vigging, breakeven and edge, Kelly sizing, parlay hold, correlation, CLV), one high-quality source to read, and one retrieval question from an earlier lesson (its answer goes on the next card). Keep a glossary in the tracker's Notes tab and use the same terms every time. Skip the lesson on quick answers.

## Step 14: Game-day timeline, re-check and handoff
- Morning: lines post. Read the previous evening's injury report.
- About 9 a.m. ET: referee assignments. Check the crew's free-throw and foul rates only when a pick depends on them.
- The game-day injury report window (Step 0c), plus shootaround news.
- 60-90 minutes before tip: re-pull injuries, lineups, lines and Kalshi prices, re-run any changed projection, and re-score every straight and parlay leg. Anything below 5 becomes PASS even if it was a TAKE earlier; a parlay that loses a leg is rebuilt or dropped. A straight whose price moved past -190 switches to its fallback number or drops (Step 11c). Re-run the profit gate at the current price: a bet whose price moved past its bet-to price drops to the watch list.
- 30 minutes before tip: lineups are in. A late scratch changes his teammates' projections, so re-run them with usage_shift() and project_minutes(role_change=...). Re-posted lines often lag the second beneficiary.
- Lead every update with what changed and what to do.
- When to bet: early when the edge is information the market is slow on (a confirmed role or minutes change), because that line will move; after the report when the bet depends on unresolved news (a questionable teammate), unless both versions are bets; near tip for unders the public is pushing up. Note the number taken so CLV can be tracked.
- Handoff (handoff skill): after the card, keep a 5-line handoff in the tracker's Notes tab: bets placed, open re-checks with times, news to watch, parlay legs still live, the update triggers. A new chat reads it first, so nothing depends on this chat's memory.

## Step 15: Track, retro and notebook
- Tracker (a Sheets artifact when available, otherwise an .xlsx): every straight bet with date, player, prop, line, side, odds, book, score, p_final, p_push, p_cons, p_logic, p_mkt, edge, bet-to price, stake, model inputs (JSON), our mean, each outside model's number, the Kalshi mean, closing line and price, result, the actual stat, minutes played, the script that happened, and a one-line reason. Every parlay with its legs, joint chance, app price, EV and result.
- After each slate: lead with the net result in units and USD, then each bet with the stat that settled it and his minutes, then the passed or downgraded picks that would have won or lost. Write a 3-line post-mortem for every loss: what happened, whether it was the logic (minutes, script, role, model) or variance, and what to change. For a lost parlay, name the leg that failed and whether the legs failed together.
- CLV is the first scoreboard: run clv() on every straight with the closing price, and track line CLV (took 24.5, closed 25.5). Hit rate needs hundreds of bets to mean anything; beating the close shows within 50-100 bets whether the process finds value.
- Outside models' record: log each model's projection next to the result; after 50 logged picks, weight models by their tracked error instead of equally.
- Market weight: at 100+ settled bets, run fit_blend(rows) on p_logic, p_mkt and results; if a different weight cuts log loss by 0.002 or more on held-out bets (Step 16), update W_MKT.
- Retro (3 lines max per slate): a source that wasted time goes to Dead ends (references/sources.md); a mistake a check could have caught becomes a tripwire; missing information becomes a new source to find.
- Season notebook (the chief-of-staff wiki): dated claims only ("On 2026-10-21, X started at power forward with Y out"). Never write "currently"; mark a claim superseded instead of rewriting it. Keep it in the tracker's Notes tab, not in memory.
- Every 50 settled bets: hit rate by score bucket (4, 5, 6-7, 8+) and chance-to-hit band with calib(), brier() and logloss(), plus parlays' joint-chance bands against their hit rate, and units won by edge band. If 6+ scores aren't hitting more often than 5s, tighten the rubric; if 2-4 point edges lose money over 200+ bets, raise MIN_EDGE.

## Step 16: Autoresearch loop (model improvement)
Run it at 100+ settled bets and every 50 after, or when he asks.
1. The scorecard is fixed: log loss on settled bets (autoresearch()). Never change the scorecard or the logged results.
2. Run the baseline first: the current settings.
3. One idea per experiment, written as one line: a setting (W_MKT, MIN_EDGE, KELLY_FRAC, SIG, a ROLE table, PHI, SIG_U, RATE_CV, STAB, KAPPA, MATCH_K, the parlay rules) or a scoring rule. Replay logged bets with replay(row, **changes) when the idea is a model setting.
4. Keep a change only if it improves held-out log loss by 0.002 or more without hurting the training part. Simpler wins ties, and deleting a rule with equal results is a win.
5. Log every experiment (setting, held-out log loss, change, keep or discard) in the tracker's Experiments tab.
6. The best kept change becomes the new baseline. Stop after 10 experiments in a chat session (a scheduled task can run longer), report the kept change in one line, and update scripts/nba_props.py, references/calibration.md and the Lessons section.
7. Re-check a kept change on the next 50 bets; a change that only won on one sample is overfit.
8. Engine-level changes (new constants from box-score data) go through the GitHub repo josemonet/nba-bets: rerun research/backtest.py and the tests before shipping a new engine.

## Step 17: Changing this skill (skill-creator)
When lessons pile up or he asks for a change:
- Keep six saved test prompts: a full slate from a screenshot with "give me 5 and two parlays", a single-player question, a "give me 10" request with fewer than 10 qualifying bets, a slate where the safest number for a strong thesis is priced past -190 (the straight must move to a number priced -190 or better, and the safer number may appear only as a parlay leg), a slate where a 62% bet is priced -190 (it must show as HITS, NO VALUE AT THIS PRICE with its bet-to price), and a results check.
- Checks that must pass: picks listed first and ranked; exactly the number asked for or a plain shortfall line; every straight priced -190 or better (or marked "about" with the app check and a fallback), clearing the profit gate, and showing its edge, bet-to price and Kelly-capped stake; parlay legs at any price with each ticket +EV; a script section and a "why not the alternatives" section in every breakdown; the trap battery answered; no pick resting on an unverified or refuted claim; both parlays with joint chances and leg-by-leg logic, or a plain "none qualifies"; public splits and line moves as bullets; no PDF; no em dashes; stakes within the balance and the daily cap.
- Run the new version on the prompts, compare it with the old one, and keep the change only if every check passes.
- Keep the description short and trigger-rich, and give the reason behind each new rule.

## Lessons
Carried over from the CFB/NFL skill:
- Volume beats efficiency. Check the current role (minutes, attempts, teammates out) before efficiency (Oct 15, 2026).
- Prop lines sit near the median, not the mean. The simulation prices the full distribution, so don't compare a line with an average (Oct 15, 2026).
- Don't stack bets that need the same script; two bets on one script lost together (Oct 13, 2026).
- Logic leads. The old market-anchored method produced thin price edges instead of strong reasons. Logic still picks the bets; since Oct 27, 2026 the price decides whether they are worth placing.
- Re-check game-day news; early information can be stale (Oct 15, 2026).
- Explanations show the stats and ranks in plain English, with splits and line moves as bullets (Oct 15, 2026).
NBA lessons (add new ones with dates):
- Oct 21, 2026 dry run (Jaren Jackson Jr., Utah at Memphis, the opener against his old team): the "revenge game" claim had no data and no known grudge, so it stayed unverified and added nothing; the "pace-up" claim was +1.8% possessions, under the 2% bar; his 4.4 fouls per 36 is a real minutes risk the simulation prices. Preseason minutes (about 18, one half) were useless for projection. A beat report listed a frontcourt player out who wasn't on ESPN's injury list, so the official report decides.
- Oct 21, 2026 check: Kalshi's ladder for Luka Doncic (25+ at 86.5%, 30+ 63.5%, 35+ 39.5%, 40+ 22.5%) matched our star simulation within 2 points from 30+ up, but sat about 5 points higher at 25+. Our left tail (early exits, foul trouble, blowouts) may run fat for stars; track it before changing anything. Oct 27 note: the v2 minutes tail is fitted on 2014-24 data and its 50/80/90% minutes ranges held coverage in the backtest, so recheck this against v2 before acting.
- Oct 22, 2026: he won't place a straight shorter than -190, so Step 11c was added. That night's top straight, Harden 6+ assists (near -300 by BetMGM's 6.5 line), moved to Harden over 6.5 assists (-140 at BetMGM): 63% to hit instead of 76%, still 8/10. The 6+ number stayed usable as a parlay leg.
- Oct 27, 2026 calibration (references/calibration.md): fitted on 351,409 player-games and backtested on 41,382 held-out 2021-24 player-games. The v1 engine's minutes spread was about half of reality (its 80% minutes range held 64% of games) and its points and PRA ranges were too narrow; the close-game minutes bonus was 6-8x too big; starters' blowout cuts were too big; the usage bump went mostly to the next star when the data spreads it across teammates; 2P% and 3P% showed no game-to-game streaks; home court and in-season drift were missing; the margin SD was 12 when the data says 13. v1 also crashed on players who never shoot threes. All fixed in v2.
- Oct 27, 2026: he wants accuracy and profit. The profit gate, bet-to prices, line shopping and the quarter-Kelly cap were added (Step 11d), and the market's weight in the final blend went from 25% to 40% until our tracked record measures it.

## Maintenance
- Never put a dollar sign directly in front of digits in this file or the references. The skill loader treats it as an argument placeholder. Write amounts as "25 USD".
- The engine lives in scripts/nba_props.py. After an autoresearch run or any engine change, keep its constants, references/calibration.md and the Lessons section in sync, and run the tests in the GitHub repo (josemonet/nba-bets).
