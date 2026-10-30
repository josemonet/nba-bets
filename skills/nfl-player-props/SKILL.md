---
name: "nfl-player-props"
description: "Use for NFL player props (passing, rushing and receiving yards, receptions, attempts, completions, TDs, anytime and first TD, kicker and defensive props, alt lines): ranked straight bets plus a safe and a risky parlay, same-game or multi-game, from a player, screenshot or slate. Calibrated game simulation, profit gate, line shopping."
---

# NFL Player Props v1 (volume first, script first, logic first, price checked)

Goal: find the NFL player props most likely to hit and worth betting at their price, researched and modeled the way a professional prop shop works, and explain every choice in detail. Scan every posted prop, then go deep on a short list. Project volume first (team plays, pass rate, his share of targets or carries), then the game script that decides all three, then efficiency, shrunk hard. Price every prop in a game from one shared simulation (its plays, scoring, TD pool, script effects, starter exits and per-play yardage shapes are fitted on 481,511 real plays and backtested on every 2023-25 game), compare it with outside models, the sportsbooks and the exchanges, and test every claim so a popular story never makes a pick. Score each bet 1-10 by its chance to hit and the strength of the tested evidence, never by its price. Then check the price: a straight goes on the card only when it clears its breakeven (the profit gate) and is staked no bigger than the edge supports. Deliver the number of straight bets he asks for, ranked and priced -190 or better, and when he asks, two parlays (legs at any price, the ticket +EV): one safe and smart, one risky but smart.

## About the user (read first)
- The user has ADHD. Every response follows the writing rules in Step 13d.
- He cares whether a bet hits (Oct 15, 2026) and wants the card to make money (Oct 27, 2026). Scores and verdicts come only from the chance to hit and the evidence (Step 10); price never moves a score. Then the profit gate (Step 11d) decides whether a scored bet is worth placing at its price, and a quarter-Kelly cap keeps thin edges small. A bet that hits 63% of the time loses money at -190 (breakeven 65.5%), so the card says so instead of listing it.
- Straight bets must be priced -190 or better (Oct 22, 2026): -190, -150, -110 and any plus price qualify; -195, -200, -250 and shorter don't. Parlay legs are exempt and can be any price. The cap decides whether a bet can be a straight, never its score (Step 11c).
- He wants picks that survive testing, not the popular narrative (Oct 21, 2026). Every claim behind a pick is tested (Steps 7 and 8). A claim that fails its test cannot support a pick.
- He wants the reasoning for every pick in great detail, the public's bets and money and the line movement as bullets, and no PDF; everything is delivered in chat.
- He bets in Tennessee: NFL player props are allowed (college player props aren't offered).
- Units, books, balance and bankroll: Step 0a. How many bets and which parlays: Step 0d. Game sides, totals and college bets belong to the sports-betting-research skill; NBA props to nba-player-props.

## Files in this skill
- SKILL.md: this workflow.
- scripts/nfl_props.py: the engine (Step 9). Copy it into the working directory and import it; never retype it from memory.
- scripts/nfl_inputs.py: the input builder. It downloads nflverse play-by-play, snap counts and the schedule with lines, and builds every engine input the way the backtest did (Step 3). Optional: when the download is blocked, build inputs by hand.
- references/calibration.md: every fitted constant, the data behind it, the old value it replaced, and the walk-forward backtest against the old football_model. Read it when a number in this file needs its source, or before changing the engine.
- references/sources.md: where to get data, odds, injuries, weather and news, the 30-day pulse rules, and the Dead ends list. Read it before fetching anything.
- references/markets.md: how every NFL prop settles (gross passing yards, kneel-downs, overtime, anytime-TD rules, voids, pushes, stat corrections) and the house rules that change a payout. Read it before pricing an unfamiliar market.

## Skills built into this one
This skill already contains what it needs from these, so don't load them separately unless the user asks (the xlsx file skill excepted).

| Skill | Step | What it does here |
|---|---|---|
| i-have-adhd (ayghri) | 13d | Answer first, numbered actions, a state line, short lists, real time estimates |
| humanizer (blader) | 13d | Plain human writing: no dashes, no "not X but Y", no hype words, no unnamed "experts" |
| superforecasting (deusyu) | 7 | Outside view first, three reference classes, factor bands, reasons it might be wrong, update triggers |
| bayesian-reasoning-calibration (lyndonkl) | 7 | Evidence weighed by how diagnostic it is, sensitivity analysis, no extreme probabilities without extreme evidence |
| verification-before-completion (obra/superpowers) | 8i | Evidence before claims: re-check every number a pick cites before sending |
| last30days (mvanhorn) | 3i | A 30-day pulse of beat writers, pressers, practice reports, Reddit and X on roles, health and mood |
| grilling (Matt Pocock) | 8d | Grill each thesis as a decision tree until no assumption is left unchecked |
| chief-of-staff (Matt Pocock, board protocol from alirezarezvani) | 0c, 8e, 15 | Week run-of-show and reminders, a desk board meeting on each pick, a dated season notebook |
| handoff (Matt Pocock) | 14 | A short game-day handoff so a new chat can pick up the card |
| anatomy (wheresryan22) | 8a, 13e | Bet anatomy, and an optional interactive "prop machine" whose every number comes from the model |
| teach (Matt Pocock) | 13f | One short lesson per card tied to a real pick, a glossary, retrieval questions |
| autoresearch (Karpathy) | 16 | Keep-or-discard model experiments against a fixed scorecard |
| skill-creator (Anthropic) | 17 | Test changes to this skill with saved prompts and pass/fail checks |
| retro and diagnosing-bugs (Matt Pocock) | 7d, 15 | Model tripwires that go red on known failure modes, and a short retro after each slate |
| betting and kalshi (machina-sports) | 6, 11d, 12 | De-vig, EV, Kelly, line shopping, parlay math and line moves; exchange ladders from the public API |
| deep-research (Anthropic), dispatching-parallel-agents (obra/superpowers) | 4 | Optional parallel research, one agent per game, on full Sunday slates |
| writing-for-agents (Matt Pocock) | every step | A "Done when" line ends each step so no step stops early |
| xlsx or Sheets | 15 | The tracker |

## Ground rules
1. Volume first. A prop is team plays x pass rate x his share x efficiency. Targets, carries, routes and attempts predict; catch rate, yards per carry and yards per attempt regress hard (Step 3b has the fitted weights). Never bet an over on efficiency alone.
2. Script before projection. The spread and total decide plays, the pass rate (trailing teams throw on 68% of plays, big leaders on 51%), kneel-downs, the QB's exit risk and who scores the TDs, so build the script (Step 5) before projecting.
3. One game, one simulation. Every prop in a game (both QBs, every receiver and back, every TD prop, the kicker, the defenders) comes from one run of sim_game(): shared plays, one TD pool, a passing game whose catches add up to the QB's yards. Never price two props in one game as independent.
4. Our number first. Build the projection before looking at the line or anyone's picks, so the market and the touts don't anchor the research.
5. Outside view before inside view. Start from the market's probability and the base rate, then move only as far as diagnostic evidence justifies (Step 7).
6. Every claim gets a test (Step 8b). "Smash spot", "worst defense against tight ends", "revenge game" and "he's due for a TD" are claims, not reasons, until a test passes. Defense-vs-position splits failed the test (Step 2c).
7. Small samples lie. Seventeen games is a small season: shrink every rate toward last season or the league by the fitted weights, and carry the leftover uncertainty into the simulation (share_cv, eff_cv).
8. Lines are medians. Yardage props are skewed right (a receiver's mean runs about 8% above his median), so a line is read through the simulated distribution, never against an average (Oct 15, 2026).
9. Lineups decide shares. Shares come from games with today's lineup; a teammate's absence (usage_shift_nfl()), a player's first game back (return_keep()) and the team's share budget (share_budget()) are fitted, so apply them before the simulation.
10. News is the edge and the risk. Practice reports, statuses and the inactives list 90 minutes before kickoff change everything, so nothing is final until the re-check (Step 14).
11. Fewer, better bets. Never force picks or parlay legs to fill a count.
12. Correlation discipline. Don't stack bets that need the same script or the same TDs unless they are priced together as one parlay (Step 12), and size same-game straights together (portfolio_scale()).
13. Truth and provenance. Every number carries its source and date. Never invent a stat; write "not found".
14. Price discipline. The chance to hit picks the bets; the price decides whether they are worth placing. Every straight clears its breakeven by 2 points and its conservative check clears breakeven (Step 11d). Shop every legal book he uses for the best number before placing.
15. Honest spreads. The engine's 50/80/90% ranges held their coverage across 2023-25 for every prop type (references/calibration.md). Never hand-narrow them: the old football_model's ranges held 56-74% at 80% for attempts, rushing and passing, and that is how a coin flip starts to look like a 65% bet.
16. The market is a strong forecaster. Our number moves off it only as far as sourced evidence justifies; the final blend gives the market 40% until our own tracked record measures the right weight (Step 15).

## Step 0: Before you start (~3 min)

### 0a. Setup
- Read memory for books, unit size and presentation preferences. Defaults: FanDuel is the main book and other legal books he uses are fine; Tennessee allows NFL player props; 1 unit = 25 USD; straight bets priced -190 or better, parlay legs at any price (Step 11c); the card goes out in chat, never as a PDF; the user has ADHD.
- Read the available balance from his screenshot when one is there. Never recommend more than it; when picks add up to more, give a priority order. After a settled slate, recompute the balance before sizing the next card.
- Bankroll for the Kelly cap (Step 11d): his betting bankroll in units (the balance divided by the unit size, unless he gives a separate bankroll). Unknown: use 40 units and say so.
- Open the tracker if one exists (Step 15) and run calib_tripwire() on the last 15 settled straights (Step 7e).
- Confirm today's date, the season and the NFL week (the 2026 regular season began Sep 9, 2026; week 8 runs Oct 29 to Nov 2). Searches often surface older seasons, so check the year on every number.
<!-- load -->
- Load the engine (once per session, about 1 min): copy scripts/nfl_props.py and scripts/nfl_inputs.py into the working directory and check the version (1.0). Find them with `find / -name nfl_props.py -path "*nfl-player-props*" 2>/dev/null | head -1`.
```bash
S=$(dirname "$(find / -name nfl_props.py -path '*nfl-player-props*' 2>/dev/null | head -1)") && cp "$S/nfl_props.py" "$S/nfl_inputs.py" . && python3 -c "import nfl_props as m; print('engine version', m.VERSION)"
```
<!-- /load -->
  Then `import nfl_props as m` (and `import nfl_inputs as d` for the data builder) in your own scripts.
- Load the data (about 1 min, about 40 MB the first time): `D = d.load(2026)`. If the download fails (no network to github.com), say so in one line and build inputs by hand (Step 3); everything else works the same.

### 0b. Market and house rules (checked Oct 2026; references/markets.md has the full list)
- Props settle on official NFL stats, overtime included. Passing yards are gross (sacks don't come off a QB's passing yards); rushing yards include scrambles and kneel-downs (each kneel loses about a yard); two-point tries never count; a spike is an incomplete pass attempt.
- Anytime TD: rushing, receiving and return TDs count for the player; a QB's passing TDs don't. A two-point conversion is not a TD.
- FanDuel voids a player prop when the player doesn't play a snap; once he plays one, the bet stands even after an early injury exit. Check the app for an injury-exit promotion before counting on one.
- A push on a whole-number line refunds a straight and drops that leg from a parlay, which reprices.
- Work only with what is posted, and never suggest a market his books don't offer.

### 0c. Run-of-show (chief-of-staff)
Write the week's timeline in one block (times CT):
- Lookahead lines the week before; openers Sunday night; props post Monday to Wednesday and fill in through the week (some only on game day).
- Practice reports Wednesday, Thursday and Friday (Monday, Tuesday and Wednesday for Thursday games; estimated reports on walk-through days), with game statuses (Out, Doubtful, Questionable) on the last report. Saturday and Monday games shift the schedule a day.
- Practice-squad elevations and roster moves by 3 p.m. CT the day before the game; questionable players often get an "expected to play" or "trending down" report from beat writers the night before or the morning of.
- Inactives 90 minutes before kickoff (10:30 a.m. CT for noon CT kickoffs, 1:55 p.m. CT for the 3:25 p.m. CT window). Weather the morning of the game and again 2 hours before.
- Our re-check times (Step 14).
- Offer one line: reminders for the re-checks, or a scheduled task for a Wednesday prop scan and a Sunday-morning re-check. Create them only after a yes.

### 0d. The order
- Read from his message: how many straight bets he wants (N), which games (the whole week, a window such as the Sunday early slate, or named games), whether he wants parlays, any stake limit, and any book besides FanDuel.
- No N given: ask one quick multiple-choice question (3, 5, 7 or 10 bets). If he doesn't answer or is away, use 5 and say so.
- Parlays: build the two parlays (Step 12) when he asks for parlays or a full card. Otherwise offer them in one line at the end.
- TD scorers: when he asks for anytime or first TD picks, build the long-shot list (Step 11e) besides the straight card.
- His overrides win: more or fewer legs, same-game only, multi-game only, a target payout, a specific game, or "turn off the profit gate" (then set m.REQUIRE_EDGE = False and label every straight's edge anyway).
- Never pad. When fewer than N bets reach a score of 5 and clear the profit gate, give the ones that do and say how many are missing. The best near-misses can follow, labeled "watch, not bets", each with the price that would make it a bet (bet_to()).

Done when: N, the games and the parlay request are known or defaulted and stated.

### 0e. Full prop menu (required before finalizing)
- List every posted market for each candidate, from his screenshots or the sources in references/sources.md: passing yards, completions, attempts, passing TDs, interceptions, longest completion, pass + rush yards; rushing yards, rushing attempts, longest rush; receptions, receiving yards, longest reception, rush + receiving yards; anytime TD, 2+ TDs, first TD; kicking points, field goals made, extra points; tackles + assists, sacks; alt lines and milestones (50+, 75+, 100+ yards, 250+ and 300+ passing yards); and the team markets that express the same script (team totals, team passing and rushing yards).
- Model every family from one simulation of the game (Step 9):
  - Yardage, receptions, attempts, completions, TDs, interceptions, longest plays, combos, kicking and defense: sim_game(), then final_probs() at the posted line (whole-number lines can push). Ladders and milestones: ladder().
  - Alt lines: final_probs() at the alt number with the main line's prices as the market (Step 6e).
  - Anytime TD and 2+ TDs: td_probs() (the simulated chance blended with the de-vigged menu price; TD menus carry 15-30% hold). First TD: first_td(), an approximation, with the menu's 25-40% hold.
  - Same-game legs: sgp() on leg_hits() from the same run, so shared plays, the TD pool, the script and a QB's yards being his receivers' yards are priced. Never treat same-game legs as independent.
  - One-sided prices (milestone ladders): one_way_fair().
  - No posted line yet: bet_zones() gives the median and the lines where each side reaches 55% and 60%. Share those zones, ask for a screenshot, and don't score or stake a bet until a line exists.
- Best expression of a thesis:
  - More volume (a teammate out, a promotion on the depth chart): receptions or rushing attempts isolate volume; yards add efficiency risk.
  - A big favorite expected to lead: its lead back's attempts over, the trailing QB's attempts and completions over, the favorite QB's attempts under.
  - A trailing team: its QB's attempts and completions, its slot receiver's receptions; its backs' carries under.
  - Wind 15+ mph or freezing temperatures not yet in the line: passing yards and longest-completion unders, the kicker's points under, rushing attempts over.
  - A deep threat with a low catch rate: receiving yards and longest reception carry his upside; receptions carry the floor of a possession receiver.
  - TD theses: a team TD pool split among teammates (TD props on one team compete for the same TDs; Step 8c test 12).
  - A combo that needs two stats to go right is a parlay in disguise; prefer the single stat when the thesis is about one.
  - Don't bet two props that need the same script; the second loses a point (Step 10).
  - Straights must be priced -190 or better (Step 11c) and clear the profit gate (Step 11d). When the safest number for a thesis (often an alt such as 3+ receptions or 40+ rushing yards) is priced shorter than -190 or fails the gate, the straight moves to the safest number that passes both (best_straight_line(..., min_edge=m.MIN_EDGE)), usually the main line, and the safer number stays available as a parlay leg.

Done when: every posted market for each candidate is listed and mapped to a model family.

## Step 1: Slate scan (the funnel, ~10 min per window)
1. Pull every posted prop for every game in scope: his screenshots first, then the line-shopping pages and exchange ladders (references/sources.md).
2. For each game, build inputs (d.game(), Step 3) at the market's spread and total, run m.sim_game(g, players, n=10000), and run screen(S, props) on every posted prop. It returns our quick chance, the sportsbook's no-vig probability where both prices exist, the gap, and the edge at the posted price.
3. Flag structural edges, the places NFL prop edges actually come from:
   - News the line hasn't absorbed: an inactive receiver or back, a QB change, a promotion on the depth chart. Re-posted lines move the obvious beneficiary and lag the second one (the TE when a WR sits, the RB2 when the RB1 sits). usage_shift_nfl() has the fitted split.
   - Script mismatches: a back's carries under on a team expected to trail big, a favorite QB's attempts over when his team should be running out the clock, a trailing QB's attempts under.
   - Medians: a yardage line set at a player's average instead of his median (his average is pulled up by long plays), usually an under edge on receivers.
   - Weather the line hasn't priced: wind of 15-20 mph took about 21 passing yards off a team beyond what the closing lines priced (2016-26).
   - Market budget: a team's receivers' yardage lines that add up to well more or less than its QB's passing line (market_budget()); the soft side is usually the one built from a different volume view.
   - Distribution edges: alt ladders and milestones whose tails disagree with our simulation or an exchange ladder; longest-play props (the engine samples real per-play shapes).
   - Disagreement between books on the line number. A different number changes the probability; a different price alone doesn't. Both feed best_offer().
   - Overreaction: a line moved after one big game built on one long catch or TD, with no role change.
4. Shortlist the top max(2N, 8) props by gap, edge and structural flags, at most 3 per game. Give unders the same look as overs; the public leans over. A prop priced shorter than -190 can't be a straight (Step 11c): shortlist its number priced -190 or better instead, and keep the shorter number on a separate parlay-leg list.
5. Props left off the shortlist get one line in "Other props considered" only when they came close.

Done when: every posted prop in scope has a quick probability and edge, and the shortlist is written with the reason each made it.

## Step 2: Game inputs and team sheets (~8 min per game)

### 2a. The market's game
- Spread, total and moneyline: opener and current at several books (his book first), plus the exchange price when one is liquid. nflverse's schedule (d.slate(D, week)) carries a recent consensus line, the roof and the listed QBs; confirm the live number at his book.
- implied(total, spread_a) gives each team's implied points and team A's expected margin (team A is the home team in d.game(); a 3.5-point home favorite has exp_margin 3.5).
- Expected plays: expected_plays(total, exp_margin, pace, opp_pace) from both teams' season paces and this season's league norms (fitted: a team's own pace carries most of the weight; each point of total adds 0.12 plays and each point of expected margin 0.16).

### 2b. Team sheet (both teams: value, league rank out of 32, games, last 3)
Plays per game, neutral pass rate (dropbacks per play when the win chance is 20-80%, first and second down, quarters 1-3) and pass rate over expected when quoted, sack rate, scramble rate, interception rate, completion %, yards per completion, explosive pass and run rates, red-zone trips and TD rate, the pass share of TDs, EPA per play and success rate on offense and defense, pressure rate, man and zone coverage shares, and run-defense yards before contact when quoted. team_profile() fills the volume and efficiency rows from the data; the rest come from sources.md.

### 2c. What the defense gives up, by prop type (tested; it is mostly already in the lines)
- Opponent "allowed" rates (yards per target, catch rate, yards per carry allowed) added only 0.2-1.2% of accuracy beyond the market's spread and total in 2016-26 data, and defense-vs-position splits correlated 0.04-0.07 with the next game. A matchup alone never carries a bet, and "worst defense against tight ends" fails the narrative audit unless the scheme explains it (a zone defense that lets the seam open every week, a linebacker injury).
- What does move props is volume, and the defense moves volume through the script: a defense that gives up long drives raises the opponent's plays; a pass rush raises sacks and lowers attempts; a bad run defense keeps a leading team running. Those effects flow through the spread, the total and the team inputs, so enter them there, not as a multiplier.
- Coverage scheme and the cornerback he'll face (a shadow corner, a slot mismatch) are context for the matchup desk (Step 8e); put a number on them only when a sourced, repeated pattern exists (5+ games).
- When the opponent changed a lot since its stats were built (a new coordinator, two starting corners out), its profile describes a different defense: say so and lean on the market.

### 2d. Weather (fitted; weather() applies it)
- Outdoor games, beyond what the closing lines already priced (2016-26): wind of 15-20 mph took about 21.5 passing yards off a team; below 32 F about 15.5 passing yards (rushing +5); domes and closed roofs about +4 passing yards; home field moved nothing beyond the lines. weather(wind, temp, roof) turns these into multipliers on passing yards, rushing yards and field-goal accuracy.
- The closing line already holds most of the weather effect, so only weather the line hasn't seen counts as an edge: a forecast that changed after the line settled, gusts the morning forecast missed.
- Get the game-time hourly forecast (sources.md) and re-check it the morning of the game: an early-week forecast can drag a total down and then clear (Oct 15, 2026, SEA-DEN).

Done when: both sheets show value, rank and games for every row, or "not found", and the weather line is written for outdoor games.

## Step 3: Player sheet (~6 min per shortlisted player)

### 3a. Inputs from the data (nfl_inputs.py: what the backtest used)
- g, players, notes = d.game(D, home, away, spread_home=..., total=..., wind=..., temp=..., out=[...], back=[...]) builds every input: team pace, neutral pass rate, sack, interception, completion and yards-per-completion rates, the pass share of TDs, the starting QB's own rushing profile, and every pass-catcher's and back's shares and efficiency, each shrunk by the fitted weights. Read every note it returns.
- Its default active list is everyone who played the team's last game. Then: out = confirmed inactives (a regular who played last week shifts usage to his teammates); back = players returning from a missed game (their usage is cut by return_keep() and their uncertainty raised); shares = a hand override for a role change the data can't see yet; extra = anyone with no game this season (an IR return: last season's share x 0.60).
- player_profiles(D, team) lists every player with his projected target and carry shares, last-3-game shares, snap share, games and games just missed. split_shares(D, team, with_=[...], without=[...]) gives the shares in games with a given lineup: use it when the lineup changed (a starter back from injury, a trade), because a season-long share mixes two offenses.
- Without the data (no network): take the same rows by hand from the sources (Step 4) and pass them as dicts (Step 9 example). Use project_share() and project_rate() with the weights below, never raw season averages.

### 3b. Volume and efficiency (fitted; references/calibration.md)
- Target share: a recency-weighted share (half-life 4 games) shrunk toward last season's share by 50 team targets of weight (best of the tested windows: error 2.39 points of share vs 2.44 for the season average). Carry share for backs: half-life 2 games, 25 team carries of weight (error 4.36 vs 4.64).
- Game to game, a share swings around its true value like a Beta with concentration 117 (WRs), 140 (TEs) or 122 (RBs) for targets and 12 for carries (committees and in-game script); the engine adds share_cv for the uncertainty in the projection itself: 0.10 for a settled role with last season behind him and 6+ games, 0.14 normal, 0.20 for under 3 games or a new role, 0.30 for a first game back.
- Efficiency, shrunk toward last season (or the position norm for rookies): catch rate by 40 targets of weight, yards per target by 80, yards per carry by 100. A back's 6.0 yards per carry over 60 carries is about 4.9 after shrinkage.
- QB rates, shrunk by the attempts it takes each to stabilize: completion % 368, yards per attempt 332, TD rate 424, interception rate 2,490 (interceptions are mostly noise), sack rate 489 dropbacks. His rushing: share of designed runs 21 team runs, scramble rate 64 passes, yards per designed run 18 runs, yards per scramble 101 scrambles.
- Team quality: season-to-date efficiency is shrunk toward the league, and the market knows which offenses are good, so the engine adds 0.9% to yards per completion per implied point above the league's average team total (IMP_EFF: a 28-point offense about +5%, a 17-point offense about -5%; it cut passing-yard error out of sample).
- Red-zone usage: target share predicted receiving TDs better than red-zone share (log loss 0.385 vs 0.459); the engine weights target share 85% and inside-10 share 15% for receivers, and carry share 75% and red-zone carry share 25% for backs, then the fitted position factors (TEs 1.16, WRs 1.05, RBs on receiving TDs 0.70; QBs on rushing TDs 1.21).

### 3c. The quarterback
- The starter: the schedule's listed QB, confirmed by news. A backup or a QB with 2 or fewer starts caps that team's passing and receiving props at 5 (new_qb), and his own rates start from his career and the league.
- Exit risk (fitted on the QB who took the first snap, 2016-26): the starter threw under 90% of his team's passes in 8.3% of games (5% in one-score games, 11% at 15-21 points, 16% at 21-28, 26% at 28-35, 44% beyond). When he exits in a close game it is usually early (injury or benching: his median share 0.56); in a blowout it is late rest (median 0.77). The engine draws it every simulated game. Set p['exit_mult'] to 1.5-2 for a QB playing through an injury or on a short leash.
- His rushing is his own: designed-run share, scramble rate and yards on each, from qb_profile(). Game plans swing QB designed runs a lot (the engine draws a 75% log-swing in the designed-run share and 50% in the scramble rate per game, calibrated so QB rushing-yard ranges hold coverage).

### 3d. Game logs and hit rates
The last 6-17 games in his current role with targets, routes or snaps, carries and the team's result. hit_rate() at the posted line counts only games in the role he has now (same QB, same teammates in or out).

### 3e. Availability (the NFL timeline)
- Practice participation Wednesday to Friday (DNP, limited, full), the game status on the final report (Out, Doubtful, Questionable), and the inactives 90 minutes before kickoff. A questionable starter changes every teammate's projection, so run both versions; when sources disagree, the official report wins, and until the inactives post, a questionable tag is unresolved (cap 4).
- Snap or pitch counts after injury: write "none announced as of [date]" when there isn't one, and treat the first game back as a reduced role (Step 3g).
- Practice-squad elevations and signings the day before can add a body that takes snaps; a new signing rarely plays much in his first week.

### 3f. Usage shifts when a teammate sits (fitted on 133 absences of 18%+ target-share pass-catchers and 99 lead backs, split-sample)
- usage_shift_nfl(out, mates) applies the measured rule: each remaining main target gains about 2-3 points of target share, mostly at the same position (WR out: other WRs +3.8 points, TEs +0.8, RBs +0.6; TE out: TEs +3.5, WRs +2.0; RB out: RBs +2.5, TEs +1.8, WRs +1.3), scaled by how big the missing player's share was. When the lead back sits, the next back goes from about 31% to 58% of the carries and the third from 19% to 34%: the backup does not take everything.
- In the 2025 test, active backs were projected 39% short when a lead back sat and nothing was shifted; with the shift they were projected as well as every other back (about 5% short, the overall level). The shift is required, never optional.
- A QB out: the backup's own profile replaces the starter's. The market's line move prices the team-level drop (team passing yards fell about 10% in QB-out games, and the closing lines already had it), so the edge is in the receivers' shares under the new QB, not the drop itself.
- share_budget() runs last (d.game() does it): a team's listed players together get a + b x the sum of their projected shares, not the sum itself (fitted on 2020-22 backtests, held up on 2023-25: every stat's error improved). Projections that add up high come in lower, and a thin list absorbs what's missing. It assumes the list holds every player at 5%+ of targets and 8%+ of carries.

### 3g. First game back (fitted, 2016-26)
- return_keep() cuts a returning player's projected share: targets x0.88 after one missed game and x0.86 after two or more; carries x0.91 and x0.88; a first game of the season after missing the early weeks (IR, suspension) x0.60; week 1 on last season's share alone x0.92, or after a team change x0.78 (WR), x0.76 (TE), x0.66 (RB targets) and x0.74 (carries) (return_keep(..., new_team=True, pos=...)). Players in their first game back were also more variable than their projections (80% ranges held 74%), so share_cv goes to 0.30 and the score caps at 5 (first_game_back).
- His teammates' recent shares were built without him: use split_shares() with him in the lineup when 2+ such games exist; otherwise trust share_budget() and say so.

### 3h. Matchup
Likely coverage (man or zone shares, a shadow corner), pass rush against his line (pressure rate vs pass-block win rate when quoted), the run defense's front and the box counts he faces, the opponent's injuries in the secondary or at linebacker. Context for the matchup desk; it changes the number only through a tested, repeated pattern.

### 3i. Chemistry, momentum and coaching
- Run the 30-day pulse (references/sources.md).
- Real momentum: routes, targets or carries rising because of a role change seen in 2+ games. Fake: one long catch, a TD streak, garbage-time production, a weak opponent.
- Coaching: the play-caller's pass rate over expected, tempo, fourth-down and two-point aggressiveness, how fast he goes to the run with a lead, how he uses the backs in the red zone, a coordinator change.

### 3j. Schedule and motivation
- Thursday games after Sunday games (short week), Monday night and the next Sunday, international games and the trip back, the second straight road game, byes (rest), cold-weather road trips for dome teams.
- Week 17-18: teams locked into their seed or eliminated rest starters, sometimes after a series or a half. Check the coach's statement and last year's habit; a starter with a rest risk is a minutes-risk prop (cap 5), and his backup's props may be the bet.
- Motivation counts only through a concrete behavior (a starter playing longer, a team running up a score); otherwise it's a narrative (Step 8b).

Done when: projected shares, rates and the QB profile, availability, and the three deciding factors are written with sources and dates.

## Step 4: Where to get it
Read references/sources.md: nflverse data (play-by-play, snap counts, rosters, injuries, the schedule with lines), the ESPN APIs, nfl.com stats and game logs, Next Gen Stats, EPA sites, injury reports and practice participation, weather, markets and line shopping (his screenshots, multi-book prop pages, sharp reference prices, exchanges), outside projections, the 30-day pulse rules, splits, parallel research, and the Dead ends list. Read the Dead ends before any fetch.

Done when: every source used is named with its date, and any source that failed is listed in the coverage line.

## Step 5: The game-script engine (~5 min per game)

### 5a. The market's script (fitted)
- The final margin lands around the spread with an SD of 12.7 points and the total around the closing total with an SD of 13.2 (2,746 games, 2016-26). Key margins: 3 (14.6% of games), 7 (8.6%), 6 (6.9%), 14 (5.0%), 10 (4.8%), 4 and 1 (4.6-4.7%). Overtime 5.6%; ties 0.4%. A team's points run about 9 points around its implied total, and the two teams' surprises barely move together (correlation 0.035).
- sim_game() reproduces these from drives, a TD count with the fitted variance, field goals, conversions and non-offensive scores, and reads each player's script from the same draw. bucket() names five final-margin buckets from his team's side: blowout loss (17+), two-score loss (8-16), one-score game, two-score win, blowout win.

### 5b. Our script
Adjust the market's script only for concrete reasons: injuries the line hasn't absorbed, a QB change, weather, a coach who runs out the clock early or keeps throwing with a lead, rest. Write each adjustment with its reason, then rerun the simulation at our numbers.

### 5c. Script archetypes and what they do to props (fitted where marked)

| Script | Signs | Helps | Hurts |
|---|---|---|---|
| One-score game | spread under 7 | both QBs' volume, both lead backs, closers, overtime upside on overs (5.6%) | blowout-dependent bets |
| Comfortable favorite | spread 6-10 | the favorite's carries (fitted: pass rate 0.56 when leading by 4-10), the dog's attempts | the favorite QB's fourth-quarter passing |
| Blowout | spread 10+ or a big talent gap | the leader's backs' carries, the trailer's attempts and garbage-time receiving yards | the leader's QB (8-44% exit risk by margin), the trailer's backs |
| Trailing team chases | an early deficit | the trailing QB's attempts and completions (pass rate 0.68 trailing by 10+), short and slot receivers, passing TDs (trailing teams score 68% of TDs through the air) | its backs' carries |
| Shootout | high total, two good offenses | passing yards, receivers, every TD prop, overs | unders |
| Grind | low total, two run-first teams | carries overs, unders on receivers, field goals | passing overs |
| Weather | 15+ mph wind or freezing | carries, short passes, unders on passing yards and the kicker | deep passing, long-completion overs, field goals |
| Pass-rush mismatch | top pressure defense vs a weak line | sacks, the QB's interceptions, quick-game receptions | deep targets, passing yards |
| Kneel-down finish | a favorite up late | nothing | the leading QB's rushing yards (1.45 kneels a game when leading, about -1 yard each) |
| Overtime | close spread | every over | every under |

### 5d. Quarter and half flow
First drives are scripted and the first quarter scores least; the second quarter scores most (two-minute drills); the fourth belongs to the leader's run game and the trailer's passing. Garbage time inflates trailing receivers' yards and deflates the leader's QB, so a projection built on garbage-time games overstates the next close game.

### 5e. Write the script
3-6 plain sentences: who controls tempo, where each team gains yards and scores, the key matchup, the weather, and what the fourth quarter looks like. Then the script-to-prop map (which props the story helps and hurts) and the kill switches (an early turnover or defensive score, a QB injury, a blowout, overtime, a weather shift, a special-teams TD), each with rough odds.

### 5f. Script dependency
script_table(hits, S[name]['MARGIN']) shows each script's weight and the bet's hit rate inside it. script_fit() returns 2 when the bet hits 55%+ in the likeliest script and 50%+ in the next one, 1 when only the likeliest script carries it, and 0 when it needs a minority script. It also flags a fragile bet: a script with 25%+ weight in which it hits under 40%.

Done when: each game has its script story, bucket odds and kill switches, and each shortlisted bet has its script table.

## Step 6: Build the numbers (~10 min)

### 6a. Our projection
- Inputs: g (exp_margin, total, weather, and per-team dicts 'A' and 'B') and players (Step 3). Run sim_game(g, players, n=20000) once per game (under a second). One run prices every player in the game.
- Read the median and the mean (bet_zones()): yardage lines sit near the median.
- sanity(S, g, team) flags plays outside 52-75, a dropback rate outside 0.40-0.75 and team points more than 0.8 off the implied total.

### 6b. Budget checks
- The simulation keeps every team's receiving yards equal to its QB's passing yards, targets to attempts, carries to rushes, and TDs to the team's TD count. When the book's lines disagree with each other, market_budget(qb_line, receiver_lines) shows the gap: receivers' lines are medians, so their sum should sit a few yards below the QB's line minus what unlisted players catch; a gap of 25+ yards points at the softer side.
- Shares: after usage shifts, share_budget() keeps the team's total realistic; never hand-add bumps that sum to more than the missing player's share.

### 6c. Outside models, book-style numbers and the exchange (compare, don't copy)
How books build NFL props:
1. A base projection (team plays x pass rate x share x efficiency) usually bought from a data feed, then set as a median.
2. Openers go up Monday to Wednesday with low limits; respected bettors and other books move them through the week; limits rise toward kickoff. The closing number is the market's best estimate.
3. The public bets overs on stars, primetime games and TD scorers, so retail books shade those overs (a higher line or extra juice).
4. Alt ladders and milestones come off the main line through an assumed distribution, so the tails can be off. ladder() shows where.
5. Anytime and first TD menus carry about 15-30% and 25-40% hold; same-game parlays carry heavy hold and a correlation model of their own.
6. News pulls props off the board; re-posted lines often move the obvious beneficiary and lag the second one.
7. Holds run about 4.5% on -110/-110 props. Winners on props get limited quickly.

Side by side for every shortlisted bet: our research number; the book-style number (his season share x the team volume the book can see); every outside projection (references/sources.md); the sportsbook-implied mean (market_mean(), from every posted line and both prices, with book names); and an exchange ladder's mean when one is liquid (fit_ladder()). compare_models() lists each gap in SD units (about 65 for passing yards, 25-35 for receiving and rushing yards, 1.5-2 for receptions) and flags gaps of 0.35 SD or more. For every flagged gap, write one line on why it differs (role, script, injury timing, weather). When you can't explain a gap in our favor, side with the consensus.

### 6d. Blends
- Logic mean = 60% ours + 40% the outside-model average (ours alone when none exist; say so).
- Market mean = market_mean(quotes): each book's line and both prices turned into an implied mean through our simulated shape, weighted by how sharp the book is (Pinnacle and Circa 3x, Bookmaker 2x, FanDuel and DraftKings 1x, slower books less; one-sided prices half), plus a liquid exchange ladder's mean through extra=[(mean, weight)].
- Final fair = 60% logic mean + 40% market mean (W_MKT = 0.40). final_probs() returns p_final, its chance to win at the posted line, and p_push on whole-number lines. Our inputs are public play-by-play, and the market also sees practice reports, injuries and sharp money, so the market keeps 40% until fit_blend() measures the right weight on 100+ settled bets (Step 15).
- Conservative check = 30% logic, 70% market (p_cons): does the bet still win more often than its breakeven?
- Anytime TD and 2+ TDs: td_probs(S, name, price, hold) blends the simulated chance with the menu's de-vigged chance (pass the book's real overround when you can compute it from the whole menu).

### 6e. Alt lines and milestones
Price every alt line off the main line's market: final_probs(x, alt_line, side, quotes=[(main_line, over, under, book)]). The alt's own one-sided price carries extra hold and isn't the market's view. Use an alt only when the logic points to that number or a parlay needs a safer leg (Step 12). A straight on an alt line must still be priced -190 or better (Step 11c) and clear the profit gate (Step 11d); safer alts that fail either are parlay legs only.

Done when: each shortlisted bet has our median and mean, every outside number, the book-style number, the market and exchange means, p_final, p_push, p_cons and the budget checks.

## Step 7: Forecasting discipline (superforecasting + Bayesian calibration)

### 7a. Outside view first
Write the base rate before any argument: the sportsbook's no-vig probability (and the exchange price) is the first reference class; his role-filtered hit rate at this line is the second; the league-wide rate for this kind of prop is the third (about 50% by construction, a bit under 50% for overs on yardage because lines are medians of a skewed stat). Every inside-view argument must explain why this week differs from all three.

### 7b. Evidence weighed by how diagnostic it is
For each piece of evidence, ask how much more likely it is if the bet wins than if it loses (the likelihood ratio). Near 1 means it moves nothing: "revenge game", a two-game TD streak, a head-to-head record, a defense-vs-position split, a primetime narrative. Strong: a confirmed inactive teammate (usage_shift_nfl()), a depth-chart promotion seen in practice reports and snaps, a QB change, a script shift the line hasn't absorbed, weather the line hasn't seen. Write each factor with its direction and size band (for example, the WR1 out = +3 to +5 points of target share for the WR2 = +6 to +10 points of probability on his receptions over) and make the final number add up from the base rate.

### 7c. Sensitivity
sensitivity(g, players, leg) reruns the game with the spread and total moved 3 points each way and every share moved 15%. A bet that drops under 50% when his share falls 15% is volume-fragile: say so, and cap it at 5 when the role is uncertain.

### 7d. Tripwires and the market guard (diagnosing-bugs: checks that go red)
- sanity() (plays, dropback rate, team points) and too_far(stat, ours, market) against TOO_FAR (passing yards 30, receiving yards 18, rushing yards 20, receptions 1.3, attempts 4, completions 3, rushing attempts 3.5, passing TDs 0.35, rush + receiving yards 22, tackles 1.6, kicking points 1.5).
- market_guard(p_final, p_mkt) flags a final probability more than 12 points away from the market's no-vig probability.
- A red flag needs a concrete, sourced reason the market hasn't priced (news in the last hour, a confirmed inactive, a QB change, a weather shift). Without one, cap the bet at 5 and lean on the conservative blend.

### 7e. Calibration humility and the tripwire
- No straight prop above about 75% to hit unless it's an alt line or confirmed news the line hasn't caught. Parlays inherit honest leg probabilities; nothing gets rounded up to make a ticket look better.
- calib_tripwire(rows) on the last 15 settled straights: when their stated chances average 10+ points above their actual hit rate, the tripwire is live. While it is live, every score is capped at 6 and every stake halved, and the retro (Step 15) looks for the cause before the next card.

### 7f. Why it might be wrong, and what would change it
Write 2-3 specific ways the forecast could be wrong and the update triggers: the news or line moves that would raise or lower the chance to hit (a teammate upgraded to active, the line moving past his median, the wind forecast dropping). These feed the "what would change my mind" bullet and the re-check in Step 14.

Done when: each shortlisted bet has its base rates, a weighed evidence list, a sensitivity line, any red flags resolved, and its update triggers.

## Step 8: Anatomy and the test battery (the anti-narrative layer)

### 8a. Bet anatomy (anatomy)
Break the bet into its working parts with numbers and name the one part that must go right, and how often it does:
- QB passing yards: plays x dropback rate, minus sacks and scrambles = attempts; attempts x completion % x yards per completion; his exit risk.
- Receptions and receiving yards: team attempts x his target share = targets; targets x catch rate; catches x yards per catch from his position's per-catch shape (most catches gain under his average, a few long ones pull it up).
- Rushing yards: the team's designed runs x his carry share = carries; carries x yards per carry, with one long run deciding many overs.
- Anytime TD: the team's TDs (from its implied total) x the pass or rush share x his share of those.
- Kicking points: field-goal tries x make rate x 3 + extra points; tackles: opponent plays x his tackle rate.

### 8b. Narrative audit
List every claim the pick leans on (ours, the media's, the public's). Test each one with data and tag it:
- Verified: a number supports it in two independent windows (this season and last, or the last 3 games and the season) or from two sources.
- Unverified: no test was possible. It adds nothing to the score.
- Refuted: the data says otherwise. If the pick relies on it, PASS.

Common narratives and their tests:
- "Smash spot against the worst pass defense", "worst against tight ends": defense-vs-position barely predicts the next game (correlation 0.04-0.07) and opponent rates add 0.2-1.2% beyond the lines. Refuted as a standalone reason.
- "He's due for a TD", "TD regression": TDs follow volume (target and carry share) and the team's implied points; a TD drought with steady volume means nothing, and a TD streak without volume means less.
- "Red-zone back": goal-line role is real but target and carry share predict TDs better than red-zone share alone; check his inside-10 share over 6+ games.
- "Revenge game", "primetime player", "always kills this team": usually noise; test the splits with enough games.
- "The game script says they'll throw": the trailing team's pass rate rises (fitted, already in the engine); the claim is verified only when the spread actually makes him the trailer.
- "Target hog", "alpha": target share and its trend over 3+ games with the same QB.
- "Usage bump with X out": usage_shift_nfl() gives the fitted bump; the with/without split from split_shares() over 3+ games is the check; the team budget must still add up.
- "The wind will kill it": the game-time hourly forecast, gusts, the stadium's orientation and whether the line already moved.
- "Everyone likes it": if every article and tout has the same prop, the price already has it. Treat it as the public side, and fade it only when the data supports the other side.

### 8c. Trap battery (answer every test; trap_flags() automates the numeric ones)
1. Public over: a star, primetime, a popular TD scorer, and the line won't move toward it.
2. Recency: the line jumped after 1-2 big games, or his last 3 games run 30%+ above his season, without more volume.
3. Blowout: a leading QB's over (exit risk, kneels, running clock) or a trailing back's carries over.
4. Status risk: questionable tag, limited practice all week, a pitch count, a first game back.
5. Usage overreaction: the line moved more than usage_shift_nfl() supports, or the bump goes to someone else.
6. Too good to be true: a line far from our number and the models with no news found. The book usually knows something.
7. Steam against: the line moved against us (5+ yards on receiving or rushing, 10+ on passing, a full reception) with no news.
8. Matchup mirage: the edge rests only on defense-vs-position splits or a single big game against this opponent.
9. Efficiency heater: an over built on yards per target or per carry, not volume.
10. Garbage-time inflation: averages padded by blowout production he won't get in a close game.
11. Weather: wind or cold already priced, or a forecast likely to change.
12. Correlation and the TD pool: two bets that need the same script, TD props competing for one team's TDs, or a receiver's over and his QB's under.

For every game on the card, also name the most popular public prop and say whether it's a trap and why. One failed test costs a point unless the research explains it away; two or more cap the bet at 4. A leg with any failed test stays out of parlays (Oct 20, 2026).

### 8d. Grill the thesis (grilling)
Map the thesis as a decision tree, in order: availability, role and share, team volume, script, efficiency, market, price. Ask each open question and answer it with a fact and a source; finding facts is your job, not the user's. A branch still unsettled when you score is an assumption: name it in the breakdown and cap the bet at 5 if it depends on it.

### 8e. Desk board meeting (chief-of-staff)
For each shortlisted bet, five desks give one line each, in one turn, with no back-and-forth:
- Volume desk: his projected share, the team's plays and pass rate, and the main risk to them.
- Matchup desk: his role against the opponent's scheme and personnel.
- Script desk: the likeliest script and how the bet does in the next one.
- Market desk: models, exchanges, line movement, splits, and the best available price.
- Skeptic: the strongest data-backed case for the other side.

Synthesis: what the desks agree on; the disagreement, named, with each side's reason; the one decision. Name conflicts instead of smoothing them over.

### 8f. Blind check (full cards)
When subagents are available and the card has 3+ bets, give a fresh subagent only the raw inputs (the shares and rates, team inputs, injuries, the line) and scripts/nfl_props.py, with no thesis, and ask for its projection and its best case against the bet. If its number differs from ours by more than TOO_FAR, find out why before scoring. Without subagents, re-derive the projection from the raw inputs before re-reading your earlier reasoning.

### 8g. Pre-mortem
1. Is my side the public side? What does the research show that the public misses?
2. Does our median sit on the line? Then it's a coin flip: WATCH or PASS.
3. What would cut his volume tonight (an inactive teammate returning, a script flip, an injury), and how likely is it?
4. Does the bet survive the second-likeliest script?
5. Any news since the line opened? Is any outside model stale?
6. Am I overreacting to his last game?
7. Is the obvious story already in the number?
8. What is the likeliest way this loses, and how often? If losing is as plausible as winning, drop a point.
9. Does another pick need the same script or the same TDs? Cap that script at 2u.
10. Is this the market that best isolates the thesis?
11. Is this the best price for it at any book he uses?

### 8h. Research coverage check
Mark each done or "not found": slate scan; game lines and opener; team sheets; weather; player sheet; injuries, practice reports and inactives; usage shifts and returns; lineup split; matchup; 30-day pulse; schedule spot; script; simulation; outside, book-style and exchange numbers; market mean and market budget; base rates and evidence weights; sensitivity; splits; line movement; line shopping; narrative audit; trap battery; board; profit gate. Give the user one line listing anything not found.

### 8i. Verify before sending (verification-before-completion)
Evidence before claims. Right before the card goes out: re-pull injuries, statuses and lines for every pick and parlay leg; re-check every number a breakdown cites against its source; re-run any projection whose inputs changed; re-run the profit gate at the current price. A number that couldn't be re-checked is labeled "not re-checked" in its bullet. Words like "should be fine" or "likely still" never stand in for a check.

Done when: every shortlisted bet has its anatomy, narrative audit, trap results and board synthesis, the coverage line is written, and every cited number was re-checked or labeled.

## Step 9: The engine (scripts/nfl_props.py v1.0, scripts/nfl_inputs.py)
Copy both files into the working directory and import them. Store each pick's inputs (g, players, name, stat, line, side, quotes, models) in the tracker so replay() can re-run them. Every fitted constant is listed with its data in references/calibration.md; the GitHub repo josemonet/nba-bets holds the research scripts, the backtest and the tests.

What it holds:
- Game and script: implied(), expected_plays(), weather(), sim_game(), bucket(), script_table(), script_fit().
- Inputs: project_share(), project_rate(), project_npr(), usage_shift_nfl(), return_keep() (with NEW_TEAM_KEEP), share_budget(); nfl_inputs: load(), league(), slate(), team_profile(), qb_profile(), starter(), player_profiles(), split_shares(), game().
- Simulation output S[name]: QB: ATT, CMP, PYDS, PTD, INT, SACKED, LONGCMP, RATT, RYDS, RTD, LONGRUSH, PRY (pass + rush yards), PASS_RUSH_TD, ANYTD. Receivers and backs: TGT, REC, RECYDS, LONGREC, RECTD, RATT, RYDS, LONGRUSH, RTD, TDS, ANYTD, RRY (rush + receiving yards), RR (receptions + rush attempts). K: FGA, FGM, XPM, KPTS. DEF: TKL (tackles + assists), SACKS. Every player also carries MARGIN (his team's final margin). Teams: S['A'] and S['B'] (PTS, TD, FGM, PLAYS, ATT, CMP, PASS_YDS, RUSH_YDS, PTD, RTD, INT, SACKS, KNEELS); S['game'] (MARGIN, TOTAL).
- Probabilities: p_hit() (half-point lines), p_outcomes() (win, push, loss), ladder(), bet_zones(), hits(), leg_hits(), sgp(), script_corr(), sensitivity().
- Market: devig(), one_way_fair(), td_fair(), mkt_mean(), market_mean(), final_probs(), event_final(), td_probs(), first_td(), fit_ladder(), kalshi_weight(), compare_models(), market_budget(), market_guard(), est_price().
- Checks: sanity(), too_far(), trap_flags(), hit_rate(), screen().
- Score and card: score(), verdict(), CAPS, pick_top(), straight_ok(), price_note(), best_straight_line().
- Profit: breakeven(), edge(), ev(), ev_line(), profit_gate(), min_edge_for() and SOFT_SPOTS, bet_to(), kelly(), stake_units(), portfolio_scale(), best_offer().
- Parlays: build_parlays(), joint_prob(), parlay_price(), parlay_ev(), house_edge(), implied_lift(), round_robin().
- Tracking: brier(), logloss(), calib(), calib_tripwire(), clv(), line_clv(), fit_blend(), replay(), autoresearch().

Example (by-hand inputs; d.game() builds the same dicts from the data):
```python
import nfl_props as m
g = dict(exp_margin=3.5, total=46.5, wind=9, temp=41, roof='outdoors',            # team A (home) favored by 3.5
         A=dict(pace=m.expected_plays(46.5, 3.5, 63.0, 61.5), npr=0.55, sack=0.058, int=0.021, comp=0.64, ypcomp=11.4,
                pass_td_share=0.66, design_qb=0.035, scramble=0.03, ypc_design=3.2, ypc_scramble=7.4),
         B=dict(pace=m.expected_plays(46.5, -3.5, 61.5, 63.0), npr=0.53, sack=0.07, int=0.024, comp=0.62, ypcomp=10.6))
players = [dict(name='QB A', team='A', pos='QB'), dict(name='QB B', team='B', pos='QB'),
           dict(name='WR1 A', team='A', pos='WR', tgt=0.24, i10=0.22, catch=0.64, ypr=13.5, share_cv=0.10),
           dict(name='TE A', team='A', pos='TE', tgt=0.17, catch=0.72, ypr=10.8, share_cv=0.10),
           dict(name='RB1 A', team='A', pos='RB', tgt=0.10, car=0.62, rz=0.70, catch=0.78, ypr=7.5, ypc=4.4, share_cv=0.10),
           dict(name='WR1 B', team='B', pos='WR', tgt=0.26, catch=0.63, ypr=12.6, share_cv=0.14),
           dict(name='RB1 B', team='B', pos='RB', tgt=0.09, car=0.70, catch=0.80, ypr=7.0, ypc=4.2, share_cv=0.10)]
players = m.share_budget(m.share_budget([p for p in players if p['team'] == 'A'], 'tgt'), 'car') + \
          m.share_budget(m.share_budget([p for p in players if p['team'] == 'B'], 'tgt'), 'car')
S = m.sim_game(g, players, n=20000)                                       # one shared game for every prop below
x = S['WR1 A']['RECYDS']; print(m.bet_zones(x))                           # median, mean, 55% and 60% lines
fp = m.final_probs(x, 64.5, 'under', quotes=[(64.5, -115, -105, 'fanduel'), (65.5, -110, -110, 'pinnacle')], models=[66.0, 61.5])
gate = m.profit_gate(fp['p_final'], fp['p_cons'], -105, fp['p_push'])       # ok, edge, breakeven
stake = m.stake_units(6, fp['p_final'], -105, bankroll_units=40)          # verdict stake capped at quarter Kelly
rows = m.script_table(m.hits(x, 64.5, 'under'), S['WR1 A']['MARGIN']); pts, fragile = m.script_fit(rows)
shop = m.best_offer(x, 'under', [('fanduel', 64.5, -105), ('draftkings', 66.5, -120)], c=fp['final_mean']/x.mean())
td = m.td_probs(S, 'RB1 A', price=-115)                                   # anytime TD: sim blended with the menu
sens = m.sensitivity(g, players, lambda S: m.hits(S['WR1 A']['RECYDS'], 64.5, 'under'))
leg = dict(id='WR1 A u64.5 rec yds', player='WR1 A', game='B@A', stat='RECYDS', side='under', p=fp['p_final'], p_cons=fp['p_cons'],
           score=6, price=-105, hits=m.leg_hits(S, 'WR1 A', 'RECYDS', 64.5, 'under'))
# card: m.pick_top(candidates, n); each candidate carries a posted price or m.est_price(); anything past -190 or failing the gate is skipped
# same-game stakes: m.portfolio_scale(stakes, [c['hits'] for c in card]); parlays: m.build_parlays(legs, 'safe') and (legs, 'risky')
```

## Step 10: Confidence score (1-10): how likely the bet is to hit
The score measures the logic: the chance to hit plus how strongly the tested evidence supports it. The price never raises or lowers it.

Chance to hit (0-2), from p_final at the posted line:
- 2: 60% or more
- 1: 55-59.9%
- 0: under 55%

Evidence (0-8):
- Role and volume (0-2): 2 = a secure role (stable share over 3+ games with the same QB and lineup, no tag, no pitch count) in the role the projection assumes; 1 = one real risk; 0 = uncertain role or availability.
- Matchup and volume (0-2): 2 = the team volume and his role both favor the bet, tested in Step 8b; 1 = one favors, the other is neutral; 0 = mixed or against.
- Game script (0-2): the script_fit() points.
- Models and market (0-1): 1 = most outside models, the market mean and any exchange sit on our side of the line, and no unexplained steam runs against us.
- Momentum, chemistry and situation (0-1): 1 = a verified 30-day signal, schedule or weather edge on our side; 0 = against, unknown or narrative only.

Caps and adjustments (CAPS in the code):
- Under 50% to hit: cap 3 (PASS). 50-54.9%: cap 4 (WATCH).
- Conservative check under 50%: cap 5.
- Unresolved status (questionable, game-time decision), his or a teammate's the bet depends on: cap 4 until it resolves, unless both versions are bets.
- Refuted claim the pick relies on: cap 3. Unverified claim the pick relies on: cap 5.
- First game back, a new QB (2 or fewer starts) for passing and receiving props, a fragile script, a volume-fragile bet with a real role risk, weather still moving on a passing or kicking prop, or a red tripwire with no sourced reason: cap 5.
- Under 3 games in his current role (new team, new depth-chart spot): cap 6.
- Two or more failed trap tests: cap 4. One: minus 1 unless the research explains it.
- Minus 1 if the bet repeats a higher-ranked bet's script in the same game.
- The calibration tripwire live (Step 7e): cap 6.
- Long shots (+250 or longer, most TD scorers) rarely reach 55% to hit, so they land at WATCH or PASS on the straight card; Step 11e has their own list.
- Price: no effect on the score. The profit gate (Step 11d) and the -190 cap (Step 11c) decide only whether a scored bet is placed and how big.

Anchors: 9-10 rare (major news the line hasn't caught); 7-8 strong; 6 solid; 5 small; 4 watch; 3 or less pass.

## Step 11: Straight bets: ranking, verdicts, the price checks and sizing (minimum baseline score = 5)

### 11a. Ranking the card
- pick_top(candidates, n) ranks by score, then chance to hit, then p_cons, then script fit; skips anything past -190 or failing the profit gate; allows at most 2 bets per game and one per player; and blocks a same-game bet whose hits correlate 0.25+ with a higher-ranked bet in the same simulation (a 0.10-0.25 link costs a point).
- Each pick carries a one-line rank reason: what puts it above the next one (higher chance, a sturdier role, a script it survives).

### 11b. Verdicts and stakes

| Score | Verdict | Stake (before the Kelly cap) |
|---|---|---|
| 8-10 | STRONG TAKE | 1.5u (max) |
| 6-7 | TAKE | 1u |
| 5 | TAKE SMALL | 0.5u |
| 4 | WATCH | no bet now; say what would make it a 5 (news, a different line number, a better price) |
| 0-3 | PASS | none |

- The stake is stake_units(score, p_final, price, bankroll_units): the verdict's stake, capped at a quarter of the Kelly stake for that edge, in 0.25u steps. A STRONG TAKE with a thin edge gets a small stake; the cap never raises a stake above the verdict's.
- Same-game straights that win together are one bigger bet: run portfolio_scale(stakes, hits) on the card, which cuts a stake by its strongest positive link (correlation above 0.25) to a larger stake in the same game.
- FADE means bet the other side. Recommend it only when the other side scores 6+ on its own and clears the gate.
- SKIP THE GAME: if nothing in a game scores 5+ and clears the gate, say "no bet on this game".
- Limits: at most 2u on one game script (straights and parlay legs together); at most 4u per day, parlays included, and never more than the balance; after a losing day keep the same unit size.
- Daily cap with a long card: when the bets he asked for add up to more than 4u, keep every bet and multiply every stake by the same factor (4u divided by the card's total), rounded down to the nearest 0.25u with a 0.25u floor, so every bet he asked for stays on the card. If the floor still runs past 4u, stake the top picks by rank and list the rest without a stake. Say so in one line of the stake plan; he can raise the cap any time.
- When the balance forces a priority order, fill it strictly by rank.
- If a line move could change the logic (a yardage line crossing his median, a receptions line moving a full catch), say which number would change the verdict.
- Straights priced from -150 to -190: add one line on what a loss costs.

### 11c. The -190 straight cap (Oct 22, 2026)
He won't place a straight bet at -200, so every straight on the card must be priced -190 or better. Parlay legs are exempt.
- What qualifies: -190, -175, -150, -110 and any plus price. What doesn't: anything shorter than -190 (-195, -200, -250, -400).
- Where it's checked: the price at the book he'll use, FanDuel first. Another legal book with the same number at -190 or better also works.
- Re-express before dropping. When the safest number for a thesis is priced shorter than -190 (common for alts like 3+ receptions or 40+ rushing yards), move to the safest number priced -190 or better that also clears the profit gate, usually the main line or the next alt up (best_straight_line(x, side, prices, min_edge=m.MIN_EDGE)). Run final_probs() at that number and score it on its own. If it scores 5+, hits 55%+ and clears the gate, it's the straight. If not, the thesis isn't a straight this week; keep the shorter number as a parlay leg.
- Never fill the count with weaker bets because of the cap. Give a shortfall line ("2 of 3 straights qualify under the -190 cap and the profit gate") and name the bets that moved to the parlay-leg list.
- No screenshot: estimate the price with est_price() from the blended market chance, and price alts off the books' main lines when they're posted. Mark estimates "about", and for any estimate from -175 to -190 add "place only if the app shows -190 or better" plus the fallback number (price_note()).
- Re-check (Step 14): if a straight's price moves past -190 before he bets, switch to its fallback number or drop it.
- The cap never changes a score or a verdict. A bet can be a STRONG TAKE on logic and still go only into a parlay because of its price.

### 11d. The profit gate, the bet-to price and line shopping (Oct 27, 2026)
- breakeven(price, p_push) is the chance to win a bet needs to break even: 52.4% at -110, 60.0% at -150, 65.5% at -190. profit_gate(p_final, p_cons, price, p_push) passes a straight only when p_final clears its breakeven by MIN_EDGE (2 points) and p_cons clears breakeven. The gate never changes a score; it decides whether a scored bet is placed.
- bet_to(p_final) is the shortest price at which the bet still passes: put it on the card ("bet to -135") so he can skip the bet if the app's price has moved past it.
- Known soft spots need a 4-point edge (min_edge_for(stat, side, p) returns it, pick_top() applies it, and bet_to(p, min_edge=0.04) prices it): receptions, receiving-yard and rush + receiving overs the model puts at 60%+ (in the 2023-25 backtest they hit 4-8 points under their stated chance), rushing-yard overs at 70%+, pass-attempt overs at 60%+ and passing-yard unders at 70%+. Unders on receivers and backs were calibrated within 1-2 points (references/calibration.md).
- A bet that scores 5+ but fails the gate is labeled HITS, NO VALUE AT THIS PRICE, with its bet-to price. It can still be a parlay leg if the ticket is +EV, or go on the watch list for a better number.
- Line shopping: before placing, run best_offer(x, side, [(book, line, price), ...], c=final_mean/sim_mean) across every legal book he uses and every posted number for that thesis. It ranks offers by EV with each one's chance, push chance and edge. A half yard rarely matters on a 65-yard line, but a full catch on receptions (3.5 vs 4.5), a full attempt on rushing attempts and 15 cents of price often are the whole edge.
- Thin edges stay small: the quarter-Kelly cap (Step 11b) sizes by edge, so a 2-point edge at -110 is about 0.25-0.5u on a 40-unit bankroll even when the score is 8.
- Honest expectations, as plain math: at -110, winning 55% of bets returns about 5% of what is staked and 58% about 10%; rates above that over hundreds of bets are rare, and losing weeks happen at either rate. The card says so when he asks how much to expect; it never promises a result.

### 11e. Long shots: TD scorers and plus-money ladders (when he asks)
- Anytime TD, 2+ TDs, first TD and long milestone ladders (100+ receiving yards, 300+ passing yards) rarely reach 55% to hit, so they never fill the straight card's count. When he asks for them, list them separately as LONG SHOTS, each with td_probs() or final_probs(), its breakeven, edge and bet-to price.
- A long shot makes the list only when it clears the profit gate with a 4-point edge (TD menus carry 15-30% hold, first-TD menus 25-40%) and its score on the rest of the rubric would be 5+. Stake 0.25u each, 1u for the whole list, inside the daily cap.
- TD scorers on one team share one pool: never list two from the same team without the joint chance from the simulation.

Done when: the card holds up to N ranked picks, each with verdict, stake, edge, bet-to price, best book and rank reason, inside the limits.

## Step 12: Parlays (when he asks)

### 12a. How parlay odds work
- Leg prices multiply as decimals: two -110 legs (1.909 each) pay 3.645, which is +264. parlay_price() does it; american() converts back.
- Fair odds are 1 divided by the joint chance to hit.
- The book's edge compounds with every leg. On coin-flip legs priced -110, the house edge is 8.9% for 2 legs, 13.0% for 3, 17.0% for 4, 20.8% for 5 and 24.4% for 6 (house_edge()). A parlay of good legs compounds the edge and a parlay of coin flips compounds the vig.
- Straights are still the core of the card: a parlay has a higher variance than straights on the same legs, and its stake stays smaller (Step 12e).

### 12b. Multi-game, same-game and SGP+
- Multi-game parlay: legs in different games are close to independent. The book multiplies the leg prices, and our joint chance is the product of the legs' p_final.
- Same-game parlay (SGP): legs share plays, the script, the TD pool and the passing game, so they're correlated. Our joint chance comes from the shared simulation: joint_prob() multiplies the legs' p_final and applies the lift from leg_hits() in the same run. Fitted links in the engine: a QB's passing yards and his WR1's receiving yards move together (correlation about 0.47 in real games and 0.49 in the engine, so it slightly overstates that pair's lift); two receivers on one team barely move together (-0.02) once the QB's volume is known; a team's passing and rushing yards move against each other; the trailing team throws more.
- Check every SGP price: implied_lift(app SGP price, leg chances) is the correlation the book is charging for; compare it with our lift. If the book charges more than our simulation supports, the ticket costs more than it's worth, so prefer legs from different games.
- SGP+ (FanDuel) combines SGPs from several games: each game's legs are priced as an SGP, then the games multiply.
- Books block legs that depend on the same outcome (a player's receiving yards and his rush + receiving yards) or force them into an SGP.

### 12c. Rules that change a parlay's payout
- FanDuel removes a voided leg (a player who didn't play) and recalculates the rest; if every leg is voided, the stake comes back. Check how the book grades a non-playing player inside an SGP before betting one with a questionable player.
- A push on a whole-number line drops that leg and reprices the ticket.
- Profit boosts raise the payout, never the chance to hit, so they never change which legs we pick. Show the boosted EV as information; a boost can turn a near-miss ticket +EV.
- Round robins: every combination of k legs from a list (4 legs by 2s = 6 tickets). round_robin() gives the chance at least one ticket cashes and the expected return.

### 12d. The logic of a parlay
1. Every leg stands alone. A leg that isn't a bet by itself never goes in to raise the price. Standing alone means it scores 5+ on logic. The -190 straight cap doesn't apply to legs, but a leg worse than -3% EV at its own price is dropped.
2. Independence or one shared script. Legs from different games fail independently. Same-game legs go together only when they need the same script and our lift is 1.0 or more: a trailing QB's attempts with his slot receiver's receptions; a favorite's back's carries with the dog QB's attempts. Never pair legs that need opposite scripts; build_parlays() rejects same-game pairs with a lift under 0.98.
3. The best leg from each game is the one with the highest chance to hit and the sturdiest script fit, often a slightly safer alt line priced off the main line (Step 6e).
4. The weakest leg decides the ticket. Name it, its chance and its kill switch.
5. Legs that all depend on one piece of news (a WR1 inactive) fail together; count them as one risk, not several.
6. No more than 2u on one game script across straights and parlays.
7. The ticket must be +EV on our joint chance at the app's price (build_parlays() enforces it at the multiplied price; recheck with the real SGP price).

### 12e. The two parlays (build_parlays(); his overrides win)
- SAFE & SMART: 2-3 legs, each 62%+ to hit and scored 6+, one leg per game, no status-risk legs, priced +100 to +400, +EV. Alt lines one step safer are welcome when they raise a leg's chance and the payout still clears +100. Aim for a 35-60% joint chance. Stake 0.5u.
- RISKY BUT SMART: 3-5 legs, each 55%+ and scored 5+, up to 2 legs per game when they share a script (lift 1.0+), priced +450 to +1500, +EV, and the highest joint chance available at that payout. Stake 0.25u.
- When nothing qualifies, build_parlays() loosens the legs in 2-point steps, never below 56% and a score of 5, and reports the level it used. If still nothing qualifies, say "no safe parlay today" or "no risky parlay today" instead of forcing one.
- The builder's price is the product of the leg prices. For any same-game pair, he reads the real SGP price in the app; recompute the joint EV line and implied_lift() with it, and drop the ticket if it turns -EV.

### 12f. What each parlay shows
- One line per leg: game, bet, leg chance to hit, price.
- The joint chance (our simulation), the app price and the fair price, the house edge, and the EV line.
- Why each leg is the best choice from its game, and why the other games' best legs didn't make it.
- How the legs relate: independent, same script, and the lift for any same-game pair.
- The weakest leg and its kill switch; void and push notes; the stake.

Done when: both parlays (or a plain "none qualifies") are built with joint chances, prices, EV and the leg-by-leg logic.

## Step 13: Present (the user's required format)

### 13a. Order of the response
1. The straight picks first, one line each in rank order: rank, verdict, score, chance to hit, edge, bet-to price, bet, odds, book, stake in USD and units. Example: "#1 TAKE, 7/10 (63% to hit, +5.5 edge, bet to -150): [Player] Over 4.5 receptions (-120, FanDuel), 1 unit (25 USD)". Every straight's price is -190 or better and clears the profit gate; an estimated price says "about" and carries the app check from price_note(). If fewer bets qualify than he asked for (including bets lost to the -190 cap or the gate), say so in one line instead of padding.
2. The parlays when requested, one headline each: "SAFE & SMART: 3 legs, 41% to hit, +240, +EV 9%, 0.5u" and "RISKY BUT SMART: 4 legs, 14% to hit, +780, +EV 9%, 0.25u", with the legs listed under each. Long shots (Step 11e) follow when he asked for them.
3. The next action with a time estimate ("Next (2 min): place #1 and #2").
4. State line: balance, bets placed, time to the first kickoff, next re-check (inactives at 10:30 a.m. CT for noon CT kickoffs).
5. Breakdowns, one per straight pick in rank order (13b), then each parlay's breakdown (13c).
6. Traps to avoid, HITS, NO VALUE AT THIS PRICE bets with their bet-to prices, other props considered, stake plan and coverage line.
7. The lesson of the week (13f) on full cards.
8. One concrete next action he can do in under 2 minutes.

### 13b. Each straight pick's breakdown (detailed, as long as it needs)
1. The bet, the score and the rank reason, on one line.
2. Why this bet, in detail. Each bullet starts with a bold label and carries numbers, ranks, sources and dates:
   - What has to happen and how often (the anatomy).
   - Role and volume: his share over the season and the last 3 games with the lineup behind it, snaps or routes, the team's plays and pass rate, the main risk, and the sensitivity line.
   - The game script: the story, the bet's hit rate in the likeliest and the next script, the kill switches.
   - Injuries, inactives, usage shifts and returns.
   - Matchup, weather and the schedule spot.
   - Chemistry, momentum and coaching from the 30-day pulse (with dates).
   - From the base rate to our number: the market's probability, his role-filtered hit rate, each factor that moved it and by how much, and the final chance to hit.
   - Our median and mean vs each outside model vs the book-style number vs the sportsbook and exchange markets.
   - Price: breakeven, edge, bet-to price, the best book and number from best_offer(), the Kelly-capped stake, and the EV line.
   - Tests: the narrative audit, the traps checked, the board's disagreement and how it was settled, and the blind check when one ran.
   - How it loses: the likeliest losing path and how often it happens.
   - What would change my mind: the update triggers from Step 7f.
   - The score in one line: chance, role, matchup, script, models and market, context, caps.
3. Why this bet and not the alternatives: his other props (why this stat and this number), the other side, his teammates' props, and the alt lines. When a safer number was over the -190 cap or failed the gate, say so and name the parlay it went into.
4. Public betting, as bullets (no table): % of bets and % of money on each side of the related game market with source and time, why the public is there, and what the money-vs-bets gap means. Label game-market splits and proxies as such.
5. Line movement, as bullets: opener, the current number at several books, when and why it moved, whether the move changes the logic, and whether to bet now or wait.

### 13c. Each parlay's breakdown
Everything in Step 12f, written out: the case for each leg in two or three lines (pointing to its straight breakdown when it's also on the card), why the legs belong together, the math, the weakest leg, and the rules that could change the payout.

### 13d. Writing rules (i-have-adhd + humanizer; every response)
1. Lead with the answer: the picks, the parlays and the next action come first. No preamble ("Let me", "Great question"), no recap of steps, no closing pleasantries.
2. Number anything he has to do, one action per step ("1. Open FanDuel 2. [Player], Receptions 3. Over 4.5, 1 unit").
3. Keep the top of the card scannable: the picks list, the parlay headlines and the next action stay short. The breakdowns underneath are long on purpose because he asked for great detail; bold labels keep them skimmable.
4. Restate state every turn: balance, bets placed, what's left, time to kickoff.
5. Give specific time estimates ("2 min", "re-check at 10:30 AM CT, 10 min").
6. After a slate, lead with the net result and each bet's win or loss on one line.
7. Cut tangents: model fixes, skill changes and side notes get one line at the end or a separate question.
8. State losses and mistakes matter-of-factly: cause and fix.
9. Short sentences, plain words, bold verdicts. Bold the breakdown labels and the verdicts, nothing else.
10. No em or en dashes; use commas, colons, periods or parentheses.
11. No "not X but Y" contrasts, no one-line closers that repeat the point, no staged openers ("Here's the thing").
12. No hype or stock AI words (crucial, pivotal, robust, elite as filler, delve, landscape, testament, showcase, lock, smash). Give the number instead.
13. No unnamed authorities ("sharps are on it", "experts say"): name the source and what it showed.
14. Keep a hedge only when it carries real uncertainty.
15. Pre-send check: if he reads only the first and last lines, does he know what to bet and what to do next?

### 13e. Optional prop machine (anatomy)
When he asks how a bet works, build a small interactive page as an artifact: a gauge-style machine where sliders for the team's plays, pass rate, his share and the script move the readout, and every number shown comes from the same formulas as the model (export the simulation's per-script numbers into the page). The readout must match the breakdown. Keep it a small figure, not a multi-hour build.

### 13f. Lesson of the week (teach)
End each full card with one short lesson (3-4 lines) tied to a real pick or parlay: one concept (volume vs efficiency, medians, the TD pool, script dependency, de-vigging, breakeven and edge, Kelly sizing, parlay hold, correlation, CLV), one high-quality source to read, and one retrieval question from an earlier lesson (its answer goes on the next card). Keep a glossary in the tracker's Notes tab and use the same terms every time. Skip the lesson on quick answers.

## Step 14: Game-day timeline, re-check and handoff
- Wednesday to Friday: practice reports; re-run any prop whose player or key teammate changed status. Friday: final statuses.
- The day before: elevations and signings (3 p.m. CT); beat writers' "expected to play" reports on questionable players.
- Morning of: the hourly weather for outdoor games, lines and splits.
- Inactives (90 minutes before kickoff): re-run every prop in that game with out= and back= set from the list, re-score every straight and parlay leg, and re-run the profit gate at the current price. Anything below 5 becomes PASS even if it was a TAKE earlier; a parlay that loses a leg is rebuilt or dropped. A straight whose price moved past -190 switches to its fallback number or drops (Step 11c); a bet whose price moved past its bet-to price drops to the watch list. Re-posted lines often lag the second beneficiary.
- Lead every update with what changed and what to do.
- When to bet: early in the week when the edge is information the market is slow on (a confirmed role change, a QB change), because that line will move; after the inactives when the bet depends on an unresolved status, unless both versions are bets; near kickoff for unders the public is pushing up. Note the number taken so CLV can be tracked.
- Handoff (handoff skill): after the card, keep a 5-line handoff in the tracker's Notes tab: bets placed, open re-checks with times, news to watch, parlay legs still live, the update triggers. A new chat reads it first, so nothing depends on this chat's memory.

## Step 15: Track, retro and notebook
- Tracker (a Sheets artifact when available, otherwise an .xlsx): every straight bet with date, week, player, prop, line, side, odds, book, score, p_final, p_push, p_cons, p_logic, p_mkt, edge, bet-to price, stake, model inputs (g and players as JSON), our median and mean, each outside model's number, the exchange mean, closing line and price, result, the actual stat, his targets or carries, the script that happened, and a one-line reason. Every parlay with its legs, joint chance, app price, EV and result.
- After each slate: lead with the net result in units and USD, then each bet with the stat that settled it and his volume, then the passed or downgraded picks that would have won or lost. Write a 3-line post-mortem for every loss, root cause first: what happened; where it broke (inputs, model, script, news, or variance: the bet's chance in the script that happened was high and it still lost); and what to change. No rule changes without a root cause. For a lost parlay, name the leg that failed and whether the legs failed together.
- CLV is the first scoreboard: run clv() on every straight with the closing price at the same number, and line_clv() in yards or catches (took 64.5, closed 61.5 on an under: +3). Hit rate needs hundreds of bets to mean anything; beating the close shows within 50-100 bets whether the process finds value.
- Calibration tripwire: calib_tripwire() after every slate (Step 7e).
- Outside models' record: log each model's projection next to the result; after 50 logged picks, weight models by their tracked error instead of equally.
- Market weight: at 100+ settled bets, run fit_blend(rows) on p_logic, p_mkt and results; if a different weight cuts log loss by 0.002 or more on held-out bets (Step 16), update W_MKT.
- Subgroup calibration (the NBA lesson: check every tier separately): every 50 settled bets, hit rate by score bucket (4, 5, 6-7, 8+), by chance-to-hit band with calib(), brier() and logloss(), by prop family (receptions, yardage, attempts, TDs), by over and under, and by share_cv tier. If 6+ scores aren't hitting more often than 5s, tighten the rubric; if 2-4 point edges lose money over 200+ bets, raise MIN_EDGE; if one family or tier runs 5+ points under its stated chance over 50+ bets, cap it at 5 until the engine is fixed.
- Retro (3 lines max per slate): a source that wasted time goes to Dead ends (references/sources.md); a mistake a check could have caught becomes a tripwire; missing information becomes a new source to find.
- Season notebook (the chief-of-staff wiki): dated claims only ("On 2026-10-29, X was named the starter with Y on IR"). Never write "currently"; mark a claim superseded instead of rewriting it. Keep it in the tracker's Notes tab, not in memory.

## Step 16: Autoresearch loop (model improvement)
Run it at 100+ settled bets and every 50 after, or when he asks.
1. The scorecard is fixed: log loss on settled bets (autoresearch()). Never change the scorecard or the logged results.
2. Run the baseline first: the current settings.
3. One idea per experiment, written as one line: a setting (W_MKT, MIN_EDGE, KELLY_FRAC, SHARE_CV, TGT_KAPPA, CAR_KAPPA, EFF_CV, QB_EXIT, SHARE_BUDGET, RETURN_KEEP, the weather multipliers, the parlay rules) or a scoring rule. Replay logged bets with replay(row, **changes) when the idea is a model setting.
4. Keep a change only if it improves held-out log loss by 0.002 or more without hurting the training part. Simpler wins ties, and deleting a rule with equal results is a win.
5. Log every experiment (setting, held-out log loss, change, keep or discard) in the tracker's Experiments tab.
6. The best kept change becomes the new baseline. Stop after 10 experiments in a chat session (a scheduled task can run longer), report the kept change in one line, and update scripts/nfl_props.py, references/calibration.md and the Lessons section.
7. Re-check a kept change on the next 50 bets; a change that only won on one sample is overfit.
8. Engine-level changes (new constants from play-by-play) go through the GitHub repo josemonet/nba-bets: rerun research/nfl/backtest.py, research/nfl/audit.py and the tests before shipping a new engine.

## Step 17: Changing this skill (skill-creator)
When lessons pile up or he asks for a change:
- Keep six saved test prompts: a Sunday slate from a screenshot with "give me 5 and two parlays"; a single-player question ("is [player] over 64.5 receiving yards a bet?"); a "give me 10" request with fewer than 10 qualifying bets; a week where a WR1 is ruled out after the lines posted (the shift must go to the right teammates and the re-check must re-score); a slate where a 62% bet is priced -190 (it must show as HITS, NO VALUE AT THIS PRICE with its bet-to price); and a results check.
- Checks that must pass: picks listed first and ranked; exactly the number asked for or a plain shortfall line; every straight priced -190 or better (or marked "about" with the app check and a fallback), clearing the profit gate, and showing its edge, bet-to price and Kelly-capped stake; parlay legs at any price with each ticket +EV; same-game props priced from one simulation; a script section and a "why not the alternatives" section in every breakdown; the trap battery answered; no pick resting on an unverified or refuted claim; both parlays with joint chances and leg-by-leg logic, or a plain "none qualifies"; public splits and line moves as bullets; no PDF; no em dashes; stakes within the balance and the daily cap.
- Run the new version on the prompts, compare it with the old one, and keep the change only if every check passes.
- Keep the description short and trigger-rich, and give the reason behind each new rule.

## Lessons
Carried over from the CFB/NFL skill (sports-betting-research):
- Oct 19, 2026 (MNF, 2-2): both TD props lost to the TD pool. Purdy Over 1.5 passing TDs (68%) lost when he threw for 264 yards and 1 TD while McCaffrey ran in two 1-yard TDs; Daniels Under 1.5 (64%) lost when both of Washington's TDs were passes. A team's TDs are shared, and a trailing team scores through the air (68% of its TDs vs 59% for a big leader, fitted). This engine prices every TD prop from one team TD pool.
- Oct 15, 2026: player yardage lines sit near the median. Treating them as the mean made every rushing and receiving under look better than it was.
- Oct 15, 2026: volume beats efficiency on RB props. J.K. Dobbins looked like an under on efficiency, but after Jonah Coleman went to IR his carries rose to 15.3 a game. Check the current carry share (last 3 games, injuries) first.
- Oct 15, 2026: an early-week forecast (rain, gusts to 34 mph) helped push the SEA-DEN total from 43.5 to 40.5; the game-day forecast was dry at 7 mph. Re-check weather on game day.
- Oct 13 and 16, 2026: same-script pairs lost together. Don't stack bets that need the same script; pick_top() blocks correlated same-game straights and portfolio_scale() sizes the rest.
- Oct 23, 2026: the straights since Oct 15 went 5-10 and the MNF and Tuesday cards averaged 69% stated and went 3-4. The calibration tripwire (Step 7e) exists for this.
Carried over from the NBA skill:
- Oct 27, 2026: he wants accuracy and profit. The profit gate, bet-to prices, line shopping and the quarter-Kelly cap (Step 11d), with the market at 40% of the blend until our tracked record measures it.
- In the NBA backtest one uncertainty tier (rate_cv 0.09: last season plus under 20 games) ran too wide while the overall numbers looked fine. Every uncertainty tier is checked separately here (Step 15, references/calibration.md).
NFL engine lessons from the calibration (Oct 29, 2026; references/calibration.md):
- The old football_model over-projected passing volume by 5.5 attempts and 35 passing yards per QB-game (it ignored sacks, scrambles, starter exits and the league's falling pass volume); its 80% ranges for attempts, rushing attempts and passing yards held 56-74% of games. v1.0 is within 0.6 attempts and 0.5 yards, with every range at 77-81%.
- League norms drift: scrambles went from 3.7% of passes (2016) to 6.2% (2025), QB designed runs from 3.6 to about 3.0 yards a carry (the sneak era), targets per attempt from 0.98 to 0.95, plays per team-game from 63.9 to 61.3. Priors come from the last three seasons, and this season's pace and totals update weekly (league()).
- A backtest that knows who played but ignores absences is wrong: active backs were projected 39% short when the lead back sat. usage_shift_nfl() and return_keep() are part of every projection.
- Shares built over a lineup change mislead: the listed players' projected shares that summed to 0.95+ came in 5-8% high, and thin lists came in low. share_budget() fixes the total (fitted on 2020-22, held on 2023-25).
- 2024-26 games went over the closing totals by about 0.5-0.7 points per team, and TD props hit about 4% more than the totals implied. It isn't built into the engine (the market should adjust); the calibration tripwire watches it.

## Maintenance
- Never put a dollar sign directly in front of digits in this file or the references. The skill loader treats it as an argument placeholder. Write amounts as "25 USD".
- The engine lives in scripts/nfl_props.py and the input builder in scripts/nfl_inputs.py. After an autoresearch run or any engine change, keep their constants, references/calibration.md and the Lessons section in sync, and run the tests in the GitHub repo (josemonet/nba-bets).
- Weekly: update LG_SEASON in nfl_props.py (league() computes it from the data) when working without the data builder.
