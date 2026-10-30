# Markets: how NFL props settle, and the rules that change a payout (checked Oct 29, 2026)

Books grade props on the league's official stats. The rules below are the common ones; anything marked "check the house rules" varies by book, so read the book's NFL rules page (FanDuel: Help, then House Rules, then NFL) before betting a market that depends on it. When a screenshot shows a rule that differs from this file, the screenshot wins; note it in the tracker.

## What counts in each stat (official NFL stats; the engine uses the same conventions)
- Passing yards: gross. Yards lost on sacks are not taken off a QB's passing yards (they come off the team's net passing yards, which is why team passing props and QB props differ). Laterals after a catch count for the receiver, not the QB.
- Pass attempts: every pass, including spikes (incomplete) and throwaways; sacks and two-point tries are not attempts. A pass that draws defensive pass interference with no catch is no attempt (the play is a penalty).
- Completions: every caught forward pass.
- Passing TDs: thrown TDs only. Interceptions: thrown interceptions, including Hail Marys.
- Rushing attempts and yards: every designed run, scramble and kneel-down. A kneel-down is a rush for about -1 yard, so a leading QB's late kneels cut his rushing yards; a fumbled snap recovered by the QB can count as a rush.
- Receptions and receiving yards: official catches. A backward pass (a pitch or a lateral) is officially a rush for the player who catches it, not a reception; most screens are forward passes and count as catches.
- Longest reception, rush and completion: the single longest play, TDs included; a play that ends in a fumble still counts its yards up to the fumble.
- Rush + receiving yards and pass + rush yards: the plain sums. Two-point conversions never count toward any stat.
- Kicking points: field goals made x 3 + extra points made; missed kicks and two-point tries add nothing.
- Tackles + assists: the official combined tackles (solo + assisted); special-teams tackles count at most books (check the house rules). Sacks: official sacks, with half sacks.
- Overtime counts for every full-game prop unless the market says regulation only.

## TD markets
- Anytime TD: rushing, receiving, and kick, punt, fumble or interception return TDs count for the player who scores; a QB's passing TDs don't. A two-point conversion is not a TD.
- 2+ TDs: the same TDs, twice or more.
- First TD scorer: the first TD of the game by anyone. If it is scored by a player not listed, a defense or special teams, every player bet loses unless the book offers that option. A player who doesn't play, or who first enters after the first TD, is void at some books and a loss at others (check the house rules).
- TD menus carry about 15-30% hold (anytime) and 25-40% (first TD). td_fair(price, hold) divides the implied chance by 1 + hold. Estimate the book's hold for the game: the sum of the menu's implied anytime chances for the players you simulated, divided by the sum of their simulated chances, minus 1.

## Voids, pushes and corrections
- A player prop is void when the player doesn't play a snap (FanDuel); once he plays one, it stands even after an early injury exit. Check the app for any injury-exit promotion before counting on one.
- A whole-number line can push: a straight is refunded, and a parlay drops the leg and reprices. Half-point lines can't push.
- Stat corrections after the game: books usually grade on the official stats at the end of the game and don't regrade for later corrections (check the house rules). A borderline catch or a lateral can be reclassified days later; don't bet a ticket expecting a correction.
- Postponed or moved games: books void props when the game isn't played within a set time (often 24-48 hours), and keep them when only the venue changes (check the house rules).
- Ties: a tie doesn't affect player props.

## Parlays and same-game parlays
- FanDuel removes a voided leg and recalculates the rest; if every leg is voided, the stake comes back. Check how a non-playing player is graded inside an SGP before betting one with a questionable player.
- A push on a whole-number line drops that leg and reprices.
- Books block or force into an SGP legs that depend on the same outcome (receiving yards and rush + receiving yards for one player, a QB's passing TDs and his receiver's TD); some books don't allow same-player multi-under combinations.
- SGP prices include a correlation model and extra hold; implied_lift(app price, leg chances) shows the correlation the book charged.
- Profit boosts raise the payout, never the chance to hit.

## Tennessee
- NFL player props are allowed; college player props aren't offered.
- Bet only through the books legal in Tennessee that he uses; FanDuel first.
