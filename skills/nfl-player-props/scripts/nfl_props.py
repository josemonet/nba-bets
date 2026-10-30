"""nfl_props: the NFL player prop engine. One shared game simulation prices every player prop, team total and same-game parlay.

Constants come from 2016-26 regular-season play-by-play (nflverse: 481,511 plays, 2,746 games with closing lines). The skill's
calibration reference (references/calibration.md, Appendix B in the single-file skill) lists every number, the test behind it, and
the walk-forward backtest against the old football_model (2023-25).
Usage: import nfl_props as m (copy this file next to your work).
"""
import itertools
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import brentq

VERSION = "1.0"

# ---- scoring: drives, TD and field-goal rates against the implied team total (fitted)
DRIVES, DRIVE_SLOPE = 11.09, -0.027      # drives per team-game; fewer when a team is expected to score more
DRIVE_SD_SHARED, DRIVE_SD_TEAM = 1.55, 0.65   # both teams' drive counts move together (correlation 0.85)
TD_RATE = (-0.0759, 0.01318)             # TD rate per drive = a + b x implied team points (solved exactly per game in drive_rates())
FGA_RATE = (0.1423, 0.00165)             # field-goal attempt rate per drive
FG_MAKE = 0.846
CONV = (0.906, 0.024)                    # extra points and two-point conversions made per TD
NONOFF_TD = 0.15                         # defensive and special-teams TDs per team-game
TD_VMR = (1.085, -0.0164)                # TD count variance/mean = a + b x implied points (0.83 at 16 implied, 0.61 at 29)
GAME_SHOCK = 0.10                        # shared game shock on both teams' TD rates (the two teams' scoring correlates about 0.035)
PTS_SD = 9.1                             # team points SD around the implied total: efficiency links are per SD of this surprise
EFF_LINK = dict(catch=0.047, ypcomp=0.079, ypc=0.051)   # log efficiency per SD of the team's own scoring surprise (fitted)
ATT_LINK = dict(ypcomp=-0.0236, ypc=-0.0585)            # log efficiency per SD of pass attempts beyond the score (fitted)
DEPTH_SD, DEPTH_CATCH = 0.14, -0.31                     # game-level passing depth: deeper means fewer catches, more yards per catch
YARD_COMP = 0.65                         # field constraint: a big catch ends a drive, so team catch-yard luck partly offsets across teammates
LINK_SCALE = 1.0                         # scale on the score-efficiency links (team level fit vs player level)
IMP_EFF = 0.0092                         # log yards per completion per implied point above the league's average team total: season-to-date
#   efficiency is shrunk toward the league, and the market knows which offenses are good (fitted on 2020-22 residuals; 2023-25 YPA error -3.7%)

# ---- volume (fitted on team-games against the closing lines and the realized score)
PLAYS = dict(total=0.120, margin=0.161, pace=0.389, opp_pace=0.020)   # expected_plays(): deviations from this season's league norms
LG_SEASON = dict(pace=62.3, total=45.3, npr=0.54)   # 2026 to date: league plays per team-game, closing total, neutral pass rate (update weekly)
QB_EXIT = ((0, 12, 15.5, 19, 24.5, 31.5, 40), (0.05, 0.055, 0.11, 0.112, 0.156, 0.263, 0.44))   # chance the starter throws under 90% of
#   the team's attempts, by |final margin| (fitted on the QB who took the first snap, 2016-26: 8.3% of games; injuries, benchings, rest)
EXIT_SHARE = dict(close=(0.0, 0.17, 0.3, 0.39, 0.48, 0.56, 0.64, 0.7, 0.77, 0.85, 0.9),     # his share of attempts when he exits: deciles
                  blowout=(0.03, 0.33, 0.49, 0.64, 0.7, 0.77, 0.81, 0.84, 0.87, 0.88, 0.9))  # (close games: early injuries; 21+ margins: rest late)
QB_FULL = 0.994                          # share of attempts when he plays it out (trick plays, a backup snap)
EXIT_TD_POW = dict(close=1.17, blowout=0.70)   # his share of the team's passing TDs = attempt share ** this: blowout exits come after
#   the TDs that built the lead (exits at 21+: 67% of attempts, 76% of passing TDs; close-game exits: 53% and 48%)
PLAYS_PTS, PLAYS_SD = 0.178, 8.14        # plays per point above the implied total; residual SD
PASS_RATE = dict(const=0.185, npr=0.780, exp_margin=0.0017, margin=-0.0049)         # dropback rate vs neutral pass rate and script
PASS_RATE_SD = 0.065                     # residual SD 0.085 net of the binomial noise of 63 plays (0.063), tuned to attempts SD 7.7
LG = dict(npr=0.54, sack=0.064, scramble=0.059, int=0.021, comp=0.645, ypcomp=10.95, tgt_per_att=0.953, pace=62.0,
          design_qb=0.054, ypc_rb=4.27, ypc_qb_design=3.1, ypc_qb_scramble=7.5, ypc_wr=5.81, pass_td_share=0.615)
# league norms 2023-26 (they drift: scrambles 3.7% of passes in 2016, 6.2% in 2025; QB designed runs 3.6 yards a carry before the
# sneak era, about 3.0 since; targets per attempt 0.98 to 0.95; plays per team-game 63.9 to 61.3). Use these as priors only.
PASS_TD_SLOPE = -0.0045                  # pass share of TDs per point of realized margin (trailing teams score through the air)
KNEELS = dict(lead=1.45, close=0.62, trail=0.18)   # kneel-downs per game by the final margin (each about -1 yard)
TKL_EXTRA = 0.03                         # tackles: variance/mean 1.15 around a defender's average, mostly from opponent plays
INT_TRAIL = 0.01                         # interception rate rises when trailing (per point behind, capped at 21)
QB_RUN_CV = dict(design=0.75, scramble=0.5)  # game-plan swing in a QB's designed-run share and scramble rate (log SD): calibrated so QB rushing-yard coverage is 52/80/90

# ---- player volume noise (fitted): Beta concentration of a player's share game to game, around a correct projection
TGT_KAPPA = dict(WR=117.0, TE=140.0, RB=122.0, FB=122.0, QB=122.0)   # x1.5 of the raw within-season fit once shares compete (calibrate_passing.py)
CAR_KAPPA = 12.0                          # carry shares swing far more (committees, script, in-game injuries)
SHARE_CV = 0.12                           # extra uncertainty in the projected share itself (0.08 settled, 0.12 normal, 0.20 new role)
EFF_CV = 0.08                             # uncertainty in projected efficiency (catch rate, yards per catch, yards per carry)

# ---- TDs: who scores them (fitted). Target share beat red-zone share as a predictor (log loss 0.385 vs 0.459).
REC_TD_W = (0.85, 0.15)                   # weight on target share and on inside-10 target share
REC_TD_POS = dict(WR=1.047, TE=1.157, RB=0.696, FB=0.9, QB=0.5)
RUSH_TD_W = (0.75, 0.25)                  # weight on carry share and on red-zone carry share
RUSH_TD_POS = dict(QB=1.206, RB=0.951, WR=1.049, TE=1.076, FB=1.711)

# ---- per-play shapes (fitted, 2016-25): catch yards as a multiple of the player's average catch, and carry yards
Q = np.array([0.0, 0.025, 0.05, 0.075, 0.1, 0.125, 0.15, 0.175, 0.2, 0.225, 0.25, 0.275, 0.3, 0.325,
              0.35, 0.375, 0.4, 0.425, 0.45, 0.475, 0.5, 0.525, 0.55, 0.575, 0.6, 0.625, 0.65, 0.675,
              0.7, 0.725, 0.75, 0.775, 0.8, 0.825, 0.85, 0.875, 0.9, 0.91, 0.92, 0.93, 0.94, 0.95,
              0.96, 0.97, 0.98, 0.99, 0.992, 0.994, 0.996, 0.998, 0.999, 0.9995, 1.0])
SHAPE = dict(
    catch_WR=[-1.757, 0.0, 0.142, 0.214, 0.269, 0.311, 0.349, 0.382, 0.412, 0.444, 0.472, 0.501, 0.532, 0.563,
              0.594, 0.626, 0.659, 0.69, 0.724, 0.757, 0.794, 0.83, 0.87, 0.911, 0.953, 1.0, 1.048, 1.1,
              1.155, 1.216, 1.282, 1.357, 1.441, 1.537, 1.658, 1.797, 1.992, 2.085, 2.196, 2.319, 2.457, 2.614,
              2.817, 3.093, 3.455, 4.049, 4.255, 4.515, 4.827, 5.452, 6.034, 6.517, 9.559],
    catch_TE=[-1.065, 0.0, 0.118, 0.208, 0.276, 0.323, 0.376, 0.408, 0.446, 0.478, 0.508, 0.544, 0.574, 0.6,
              0.629, 0.665, 0.694, 0.722, 0.758, 0.792, 0.827, 0.864, 0.9, 0.94, 0.981, 1.029, 1.075, 1.127,
              1.181, 1.239, 1.299, 1.371, 1.46, 1.55, 1.657, 1.794, 1.96, 2.041, 2.122, 2.216, 2.323, 2.451,
              2.594, 2.805, 3.088, 3.621, 3.779, 4.009, 4.379, 4.958, 5.531, 5.967, 8.198],
    catch_RB=[-3.333, -0.448, -0.191, 0.0, 0.0, 0.136, 0.206, 0.264, 0.317, 0.364, 0.407, 0.456, 0.496, 0.536,
              0.579, 0.622, 0.662, 0.699, 0.741, 0.784, 0.828, 0.871, 0.917, 0.967, 1.012, 1.059, 1.112, 1.176,
              1.233, 1.298, 1.371, 1.451, 1.543, 1.642, 1.754, 1.928, 2.118, 2.213, 2.325, 2.456, 2.595, 2.786,
              3.042, 3.322, 3.743, 4.572, 4.867, 5.276, 5.852, 6.735, 7.436, 8.447, 10.611],
    carry_RB=[-18.0, -3.0, -2.0, -1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0, 2.0, 2.0,
              2.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0, 4.0, 5.0,
              5.0, 5.0, 6.0, 6.0, 7.0, 7.0, 8.0, 9.0, 10.0, 10.0, 11.0, 12.0, 13.0, 14.0,
              15.0, 17.0, 21.0, 28.0, 31.0, 36.0, 43.0, 55.0, 66.0, 74.0, 99.0],
    carry_QB_design=[-12.0, -3.0, -2.0, -1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.35, 1.0, 1.0,
              1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 4.0,
              4.0, 4.0, 5.0, 6.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 11.0, 12.0, 13.0, 14.0,
              15.0, 17.0, 20.0, 27.0, 29.0, 32.68, 36.78, 45.89, 50.0, 63.12, 80.0],
    carry_QB_scramble=[-5.0, 1.0, 1.0, 1.0, 2.0, 2.0, 2.0, 3.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0,
              4.0, 5.0, 5.0, 5.0, 5.0, 6.0, 6.0, 6.0, 7.0, 7.0, 7.0, 8.0, 8.0, 8.0,
              9.0, 9.0, 10.0, 10.0, 11.0, 12.0, 12.0, 13.0, 15.0, 15.0, 16.0, 17.0, 18.0, 19.0,
              20.0, 22.0, 24.0, 29.0, 30.0, 33.0, 35.42, 40.71, 45.85, 50.28, 70.0],
    carry_WR=[-26.0, -6.0, -4.0, -3.0, -2.0, -1.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0, 2.0, 2.0,
              2.0, 3.0, 3.0, 3.0, 4.0, 4.0, 4.0, 5.0, 5.0, 5.0, 6.0, 6.0, 7.0, 7.0,
              8.0, 8.0, 9.0, 9.0, 10.0, 11.0, 12.0, 13.0, 15.0, 15.0, 16.0, 17.0, 18.0, 20.0,
              21.0, 24.02, 29.0, 38.0, 40.0, 45.0, 51.0, 60.0, 65.83, 69.83, 75.0])
SHAPE = {k: np.array(v) for k, v in SHAPE.items()}
SHAPE_MEAN = {k: float(np.trapezoid(v, Q)) for k, v in SHAPE.items()}
SPREAD = dict(catch=1.0, carry=0.9)        # per-play spread around the mean (calibrated so team yardage SDs match real games)

# ---- projections (fitted shrinkage and recency)
SHARE_HL = dict(tgt=4.0, car=2.0)          # half-life in games for the recency-weighted share
SHARE_K = dict(tgt=50.0, car=25.0)         # team targets or carries of weight on last season's share
# first game back (fitted 2016-26, players at 8%+ of targets or 20%+ of carries): usage comes in below the projection
RETURN_KEEP = dict(tgt=dict(opener=0.92, back1=0.88, back2=0.86, late_debut=0.60),   # opener: week 1 on last season's share alone;
                   car=dict(opener=0.92, back1=0.91, back2=0.88, late_debut=0.60))   # back1/back2: missed 1 or 2+ games; late_debut:
#   his first game of the season after missing the early weeks (IR, suspension). Normal weeks: 0.98-0.99.
EFF_K = dict(catch=40.0, ypt=80.0, ypc=100.0)   # targets, targets, carries of weight on last season (or the position norm)
QB_K = dict(comp=368.0, ypa=332.0, td=424.0, int=2490.0, sack=489.0, scramble=64.0,   # attempts or dropbacks (split-half reliability)
            design=21.0, ypc_design=18.0, ypc_scramble=101.0)   # QB rushing: team designed runs, his designed runs, his scrambles
NPR_K = 150.0                              # neutral plays of weight on the league neutral pass rate

# ---- weather (fitted residuals against the closing lines, outdoor games)
def weather(wind=0.0, temp=60.0, roof='outdoors'):
    """Multipliers on passing yards and rushing yards beyond what the closing lines price (wind 15-20 mph: about -9% passing)."""
    if roof in ('dome', 'closed'): return dict(pass_mult=1.019, rush_mult=1.0, fg_mult=1.0)
    w = max(float(wind or 0) - 10.0, 0.0); t = 60.0 if temp is None else float(temp)
    pm = 1.0 - 0.0085*min(w, 12.0) - (0.064 if t < 32 else 0.033 if t < 45 else 0.0) + (0.016 if t >= 75 else 0.0)
    rm = 1.0 + (0.045 if t < 32 else 0.064 if t < 45 else 0.0) - (0.05 if t >= 75 else 0.0) + 0.004*min(w, 12.0)
    fm = 1.0 - 0.006*min(w, 15.0)
    return dict(pass_mult=pm, rush_mult=rm, fg_mult=fm)


# ---- odds
def dec(a): return 1 + (a/100 if a > 0 else 100/-a)
def imp(a): return 1/dec(a)
def american(d): return int(round((d-1)*100)) if d >= 2 else int(round(-100/(d-1)))
def devig(prices, method='power'):
    q = np.array([imp(a) for a in prices])
    if method == 'mult': return q/q.sum()
    k = brentq(lambda k: (q**k).sum()-1, 0.2, 5.0); return q**k
def one_way_fair(price, margin=0.08): return imp(price)/(1+margin)   # one-sided price (alt ladder, milestone)
def td_fair(price, margin=0.20): return imp(price)/(1+margin)        # anytime-TD prices carry heavy hold; pass the book's overround if known
def ev(p, price, p_push=0.0): return p*(dec(price)-1)-(1-p-p_push)
def ev_line(p, price, p_push=0.0):
    e = ev(p, price, p_push); return f"EV {e*100:+.1f}% at {price:+d} ({'+EV' if e > 0 else '-EV'})"
def breakeven(price, p_push=0.0): return (1-p_push)/dec(price)
def edge(p, price, p_push=0.0): return p-breakeven(price, p_push)


# ---- projections
def implied(total, spread_a):
    """Team A's and B's implied points and A's expected margin from the total and A's spread (A favored by 3.5: spread_a = -3.5)."""
    m = -float(spread_a); return dict(A=round((total+m)/2, 2), B=round((total-m)/2, 2), exp_margin=m)
def ewm_share(vals, team_vals, hl):
    v, t = np.asarray(vals, float), np.asarray(team_vals, float); w = 0.5**(np.arange(len(v))[::-1]/hl)
    return float(np.sum(w*v)/max(np.sum(w*t), 1e-9))
def project_share(vals, team_vals, kind='tgt', prior=None):
    """A player's share of team targets ('tgt') or non-QB carries ('car') from his games this season (oldest first), shrunk toward
    last season's share (or the role norm) by SHARE_K units of team volume."""
    s = ewm_share(vals, team_vals, SHARE_HL[kind]) if len(vals) else (prior or 0.0)
    if prior is None or not len(vals): return round(float(s), 4)
    n = float(np.sum(team_vals)); return round(float((n*s+SHARE_K[kind]*prior)/(n+SHARE_K[kind])), 4)
SHARE_BUDGET = dict(tgt=(0.467, 0.456, 0.05), car=(0.664, 0.271, 0.08))   # (a, b, listing floor), fitted 2020-22, held up 2023-25
def share_budget(players, kind='tgt', lo=0.80, hi=1.25):
    """A team's listed players together get a + b x the sum of their projected shares, not the sum itself: projections that add up
    high come in lower (0.88 of targets at a sum of 0.95) and low sums come in higher (the listed players absorb what is missing).
    players: ALL of one team's players at 5%+ of targets ('tgt') or 8%+ of non-QB carries ('car'); returns rescaled copies."""
    a, b, floor = SHARE_BUDGET[kind]; L = [p for p in players if p.get(kind, 0) >= floor]; S = sum(p[kind] for p in L)
    if S <= 0: return [dict(p) for p in players]
    f = float(np.clip((a+b*S)/S, lo, hi))
    return [{**p, kind: round(p[kind]*f, 4)} if p.get(kind, 0) >= floor else dict(p) for p in players]
NEW_TEAM_KEEP = dict(WR=0.78, TE=0.76, RB=0.66, FB=0.66, car=0.74)   # week 1 after a team change: last season's share carries over at this
def return_keep(kind='tgt', missed=0, first_of_season=False, week1=False, new_team=False, pos='WR'):
    """Multiplier on a projected share for a player's first game back: kind 'tgt' or 'car'; missed = team games he just sat out."""
    k = RETURN_KEEP[kind]
    if first_of_season and new_team and (week1 or missed == 0): return NEW_TEAM_KEEP['car'] if kind == 'car' else NEW_TEAM_KEEP.get(pos, 0.78)
    if first_of_season: return k['opener'] if week1 or missed == 0 else k['late_debut']
    return 1.0 if missed <= 0 else k['back1'] if missed == 1 else k['back2']
def project_rate(made, att, prior, key):
    """Efficiency shrunk toward last season or the position norm: catch rate (key 'catch'), yards per target ('ypt'), yards per carry
    ('ypc'), or QB rates ('comp', 'ypa', 'td', 'int', 'sack', 'scramble')."""
    k = EFF_K.get(key, QB_K.get(key)); return round(float((made+k*prior)/(att+k)), 4)
def project_npr(neutral_db, neutral_plays, prior=None):
    p0 = LG['npr'] if prior is None else prior; return round((neutral_db+NPR_K*p0)/(neutral_plays+NPR_K), 4)
def expected_plays(total, exp_margin, pace, opp_pace, lg_pace=None, lg_total=None):
    """A team's expected offensive plays: its own pace matters most; the game total and the spread add a little (fitted 2016-26)."""
    c = PLAYS; lp = LG_SEASON['pace'] if lg_pace is None else lg_pace; lt = LG_SEASON['total'] if lg_total is None else lg_total
    return lp+c['total']*(total-lt)+c['margin']*exp_margin+c['pace']*(pace-lp)+c['opp_pace']*(opp_pace-lp)
def usage_shift_nfl(out, mates):
    """A key player is out. out: dict(pos, tgt (target share), car (carry share)). mates: {name: player dict with pos, tgt, car}.
    Fitted on 133 absences of 18%+ target-share pass-catchers and 99 lead backs (split-sample): each remaining main target gains about
    2-3 points of target share, mostly at the same position (WR out: other WRs +3.8, TEs +0.8, RBs +0.6; TE out: TEs +3.5, WRs +2.0;
    RB out: RBs +2.5, TEs +1.8, WRs +1.3); when the lead back sits the next back goes from about 31% to 58% of carries, the third from 19%
    to 34%: the backup does not take everything."""
    gain = {('WR', 'WR'): 0.038, ('WR', 'TE'): 0.008, ('WR', 'RB'): 0.006, ('TE', 'TE'): 0.035, ('TE', 'WR'): 0.020, ('TE', 'RB'): 0.006,
            ('RB', 'RB'): 0.025, ('RB', 'TE'): 0.018, ('RB', 'WR'): 0.013}
    scale = out.get('tgt', 0.0)/0.24        # gains were measured for missing players averaging about 24% of targets
    new = {}
    ranked = sorted([k for k, v in mates.items() if v.get('pos') == 'RB'], key=lambda k: -mates[k].get('car', 0.0))
    car_gain = {0: 0.267, 1: 0.153, 2: 0.098}
    for name, p in mates.items():
        q = dict(p)
        if out.get('tgt', 0) > 0 and q.get('tgt', 0) > 0:
            q['tgt'] = q['tgt']+scale*gain.get((out.get('pos', 'WR'), q.get('pos', 'WR')), 0.005)
        if out.get('car', 0) >= 0.30 and q.get('pos') == 'RB' and name in ranked:
            q['car'] = q.get('car', 0.0)+car_gain.get(ranked.index(name), 0.05)*out['car']/0.55
        new[name] = q
    return new


# ---- the shared game simulation
def drive_rates(implied, drives, fg_rate=None):
    """TD and FG-attempt rates per drive that reproduce a team's implied points exactly (with conversions and non-offensive TDs)."""
    fga = FGA_RATE[0]+FGA_RATE[1]*implied if fg_rate is None else fg_rate
    conv = CONV[0]+2*CONV[1]
    td = (implied-NONOFF_TD*7.0-drives*fga*FG_MAKE*3.0)/(drives*(6.0+conv))
    return float(np.clip(td, 0.02, 0.6)), float(np.clip(fga, 0.03, 0.4))
def _qdraw(shape, u):
    v = np.interp(u, Q, SHAPE[shape]); lam = SPREAD['catch' if shape.startswith('catch') else 'carry']
    return v if lam == 1.0 else SHAPE_MEAN[shape]+lam*(v-SHAPE_MEAN[shape])
def _beta(m, k, n, rng): m = np.clip(m, 1e-4, 1-1e-4); return rng.beta(m*k, (1-m)*k, n)
def _split(total, shares, rng):
    """Split a count among players by per-sim shares (the rest go to 'others'); totals are preserved."""
    left = total.copy(); pl = np.ones_like(total, dtype=float); out = []
    for s in shares:
        x = rng.binomial(left, np.clip(s/np.maximum(pl, 1e-9), 0, 1)); out.append(x); left = left-x; pl = pl-s
    return out, left
def _sum_draws(count, shape, scale, rng, cap=40):
    """Sum of `count` per-play draws from a shape scaled by `scale` (per sim), plus the longest single play."""
    m = int(min(max(int(count.max()), 1), cap)); u = rng.random((len(count), m))
    sc = np.broadcast_to(np.asarray(scale, float), count.shape)
    v = _qdraw(shape, u)*sc[:, None]; ok = np.arange(m)[None, :] < count[:, None]
    v = np.where(ok, v, 0.0); longest = np.where(ok, v, -99.0).max(1); longest = np.where(count > 0, longest, 0.0)
    return v.sum(1), longest

def sim_game(g, players=(), n=20000, seed=7):
    """g: exp_margin (team A minus team B: A is the team you list first), total; optional per team 'A'/'B' dicts:
         pace (expected plays from expected_plays(), default from the total), npr (neutral pass rate), sack, scramble, int,
         comp (completion %), ypcomp (yards per completion), design_qb (QB share of designed runs), ypc_design, ypc_scramble,
         pass_td_share, fg_make; weather: wind, temp, roof.
       players: dicts with name, team 'A'/'B', pos QB|RB|WR|TE|FB|K|DEF; receivers: tgt (target share), i10 (inside-10 target share),
         catch (catch rate), ypr (yards per catch); rushers: car (share of non-QB designed carries), rz (red-zone carry share), ypc;
         share_cv / eff_cv (projection uncertainty); DEF: tkl (tackles per opponent play), sack_sh (share of team sacks);
         K: fg_make. QBs take the team inputs. Returns a dict keyed by player name plus 'A', 'B' and 'game'."""
    rng = np.random.default_rng(seed); W = weather(g.get('wind', 0.0), g.get('temp', 60.0), g.get('roof', 'outdoors'))
    imp = {'A': (g['total']+g['exp_margin'])/2, 'B': (g['total']-g['exp_margin'])/2}
    shared = rng.normal(0, DRIVE_SD_SHARED, n); gs = np.exp(GAME_SHOCK*rng.standard_normal(n)-GAME_SHOCK**2/2); T = {}
    for t in ('A', 'B'):
        dm = DRIVES+DRIVE_SLOPE*(imp[t]-22.8)
        D = np.maximum(np.round(dm+shared+rng.normal(0, DRIVE_SD_TEAM, n)), 6).astype(int)
        td_r, fga_r = drive_rates(imp[t], dm)
        mu = td_r*dm*gs                                                    # expected TDs this sim
        r = float(np.clip(TD_VMR[0]+TD_VMR[1]*imp[t]-td_r*dm*GAME_SHOCK**2, 0.35, 0.95))   # binomial variance/mean before the shock
        q = 1.0-r; N = mu/q; Ni = np.floor(N).astype(int)+(rng.random(n) < N-np.floor(N))
        TD = rng.binomial(Ni, q); FGA = rng.binomial(np.maximum(D-TD, 0), np.clip(fga_r/(1-td_r), 0, 0.9))
        tm = {**g.get(t, {})}
        FGM = rng.binomial(FGA, np.clip(tm.get('fg_make', FG_MAKE)*W['fg_mult'], 0.3, 0.99))
        XP = rng.binomial(TD, CONV[0]); TWO = rng.binomial(TD-XP, CONV[1]/max(1-CONV[0], 1e-9))
        NO = rng.poisson(NONOFF_TD, n)
        PTS = 6*TD+XP+2*TWO+3*FGM+7*NO
        T[t] = dict(D=D, TD=TD, FGA=FGA, FGM=FGM, XP=XP, PTS=PTS, NONOFF=NO, zs=(PTS-imp[t])/PTS_SD, tm=tm)
    for t, o in (('A', 'B'), ('B', 'A')):
        x = T[t]; tm = x['tm']; M = x['PTS']-T[o]['PTS']; x['MARGIN'] = M; sign = 1 if t == 'A' else -1
        pace = tm.get('pace', expected_plays(g['total'], sign*g['exp_margin'], LG_SEASON['pace'], LG_SEASON['pace']))
        plays = np.maximum(np.round(pace+PLAYS_PTS*(x['PTS']-imp[t])+rng.normal(0, PLAYS_SD, n)), 35).astype(int)
        pr = (PASS_RATE['const']+PASS_RATE['npr']*tm.get('npr', LG['npr'])+PASS_RATE['exp_margin']*sign*g['exp_margin']
              +PASS_RATE['margin']*np.clip(M, -28, 28)+rng.normal(0, PASS_RATE_SD, n))
        pr = np.clip(pr, 0.3, 0.85)
        qv = lambda k: np.exp(QB_RUN_CV[k]*rng.standard_normal(n)-QB_RUN_CV[k]**2/2)
        db = rng.binomial(plays, pr); sk = rng.binomial(db, tm.get('sack', LG['sack']))
        scr = rng.binomial(db-sk, np.clip(tm.get('scramble', LG['scramble'])*qv('scramble'), 0, 0.5))
        att = db-sk-scr
        lead, close = M > 3, np.abs(M) <= 3
        kn = rng.poisson(np.where(lead, KNEELS['lead'], np.where(close, KNEELS['close'], KNEELS['trail'])))
        kn = np.minimum(kn, plays-db); des = plays-db-kn                     # kneel-downs are rush plays too
        qbd = rng.binomial(des, np.clip(tm.get('design_qb', LG['design_qb'])*qv('design'), 0, 0.9)); nq = des-qbd
        tgts = rng.binomial(att, LG['tgt_per_att'])
        cm = np.clip(M, -14, 14); cm_w = float((x['TD']*cm).sum()/max(x['TD'].sum(), 1))   # centered TD-weighted: the share holds on average
        ptd_sh = np.clip(tm.get('pass_td_share', LG['pass_td_share'])+PASS_TD_SLOPE*(cm-cm_w), 0.2, 0.95)
        PTD = rng.binomial(x['TD'], ptd_sh); RTD = x['TD']-PTD
        x.update(PLAYS=plays, DB=db, SACKS=sk, SCR=scr, ATT=att, DES=des, KNEELS=kn, QB_DES=qbd, NQ=nq, TGTS=tgts, PTD=PTD, RTD=RTD,
                 INT=rng.binomial(att, np.clip(tm.get('int', LG['int'])*np.exp(INT_TRAIL*np.clip(-M, 0, 21)), 0.001, 0.1)),
                 cat_eff=np.exp(EFF_LINK['catch']*x['zs']))
        az = (att-att.mean())/max(att.std(), 1e-9); dz = DEPTH_SD*rng.standard_normal(n)
        x['cat_eff'] = np.exp(LINK_SCALE*EFF_LINK['catch']*x['zs']+DEPTH_CATCH*dz)
        x['pass_eff'] = np.exp(LINK_SCALE*EFF_LINK['ypcomp']*x['zs']+ATT_LINK['ypcomp']*az+dz
                               +IMP_EFF*(imp[t]-LG_SEASON['total']/2))*W['pass_mult']
        x['rush_eff'] = np.exp(EFF_LINK['ypc']*x['zs']+ATT_LINK['ypc']*az)*W['rush_mult']
    S = {}
    for t, o in (('A', 'B'), ('B', 'A')):
        x = T[t]; tm = x['tm']; ps = [p for p in players if p.get('team', 'A') == t]
        recv = [p for p in ps if p.get('tgt', 0) > 0 and p['pos'] not in ('K', 'DEF')]
        rush = [p for p in ps if p.get('car', 0) > 0 and p['pos'] not in ('QB', 'K', 'DEF')]
        tshares = [np.clip(_beta(p['tgt'], TGT_KAPPA.get(p['pos'], 80.0), n, rng)*np.exp(p.get('share_cv', SHARE_CV)*rng.standard_normal(n)
                           - p.get('share_cv', SHARE_CV)**2/2), 0, 0.6) for p in recv]
        if recv:                                                           # receivers compete: shares are normalized with the rest of the team
            rest = float(np.clip(1.0-sum(p['tgt'] for p in recv), 0.03, 0.97))
            oth = _beta(rest, TGT_KAPPA['WR']*0.5, n, rng); tot = np.sum(tshares, axis=0)+oth
            tshares = [s/tot for s in tshares]
        # backs compete for the same carries: gamma draws normalized with the rest of the team (each share keeps its Beta(kappa) spread)
        cg = [rng.gamma(max(p['car'], 1e-4)*CAR_KAPPA, 1.0, n)*np.exp(p.get('share_cv', SHARE_CV)*rng.standard_normal(n)
              - p.get('share_cv', SHARE_CV)**2/2) for p in rush]
        if rush:
            c_oth = rng.gamma(float(np.clip(1.0-sum(p['car'] for p in rush), 0.03, 0.97))*CAR_KAPPA, 1.0, n)
            ctot = np.sum(cg, axis=0)+c_oth; cshares = [np.clip(s/ctot, 0, 0.98) for s in cg]
        else: cshares = []
        tg_named, tg_oth = _split(x['TGTS'], tshares, rng); car_named, car_oth = _split(x['NQ'], cshares, rng)
        # receivers: catches and yards from the position's per-catch shape, scaled to each player's yards per catch
        exp_cmp_named = sum(p['tgt']*p.get('catch', 0.62) for p in recv); exp_tg_named = sum(p['tgt'] for p in recv)
        comp_team = tm.get('comp', LG['comp']); ypcomp_team = tm.get('ypcomp', LG['ypcomp'])
        cr_oth = float(np.clip((comp_team/LG['tgt_per_att']-exp_cmp_named)/max(1-exp_tg_named, 0.05), 0.35, 0.9))
        yds_named_exp = sum(p['tgt']*p.get('catch', 0.62)*p.get('ypr', 10.0) for p in recv)
        ypr_oth = float(np.clip((comp_team/LG['tgt_per_att']*ypcomp_team-yds_named_exp)/max(cr_oth*max(1-exp_tg_named, 0.05), 0.02), 5.0, 16.0))
        team_cmp = np.zeros(n, int); team_yds = np.zeros(n); team_long = np.zeros(n); rec_by = {}
        for p, tg_ in zip(recv, tg_named):
            ecv = p.get('eff_cv', EFF_CV); u = np.exp(ecv*rng.standard_normal(n)-ecv**2/2)
            cr = np.clip(p.get('catch', 0.62)*u**0.5*x['cat_eff'], 0.05, 0.98)
            rc = rng.binomial(tg_, cr); shape = f"catch_{p['pos'] if p['pos'] in ('WR', 'TE', 'RB') else 'WR'}"
            yds, lg_ = _sum_draws(rc, shape, p.get('ypr', 10.0)*u**0.5*x['pass_eff']/SHAPE_MEAN[shape], rng)
            rec_by[p['name']] = dict(TGT=tg_, REC=rc, RECYDS=np.round(yds), LONGREC=np.round(lg_))
            team_cmp = team_cmp+rc; team_yds = team_yds+yds; team_long = np.maximum(team_long, lg_)
        rc_o = rng.binomial(tg_oth, np.clip(cr_oth*x['cat_eff'], 0.05, 0.98))
        y_o, l_o = _sum_draws(rc_o, 'catch_WR', ypr_oth*x['pass_eff']/SHAPE_MEAN['catch_WR'], rng)
        team_cmp = team_cmp+rc_o; team_yds = team_yds+y_o; team_long = np.maximum(team_long, l_o)
        if YARD_COMP > 0:                                                  # compress team catch-yard luck toward its expectation
            exp_y = sum(rec_by[p['name']]['REC']*p.get('ypr', 10.0) for p in recv)+rc_o*ypr_oth
            f = np.clip((np.maximum(exp_y*x['pass_eff'], 1.0)/np.maximum(team_yds, 1.0))**YARD_COMP, 0.5, 2.0)
            f = np.where(team_cmp > 0, f, 1.0); team_yds = team_yds*f
            for p in recv: rec_by[p['name']]['RECYDS'] = np.round(rec_by[p['name']]['RECYDS']*f)
        x.update(CMP=team_cmp, PASS_YDS=np.round(team_yds), LONG_CMP=np.round(team_long))
        # rushers
        run_by = {}
        for p, c_ in zip(rush, car_named):
            ecv = p.get('eff_cv', EFF_CV); u = np.exp(ecv*rng.standard_normal(n)-ecv**2/2)
            shape = 'carry_WR' if p['pos'] in ('WR', 'TE') else 'carry_RB'
            yds, lg_ = _sum_draws(c_, shape, p.get('ypc', LG['ypc_rb'])*u*x['rush_eff']/SHAPE_MEAN[shape], rng, cap=45)
            run_by[p['name']] = dict(RATT=c_, RYDS=np.round(yds), LONGRUSH=np.round(lg_))
        y_or, _ = _sum_draws(car_oth, 'carry_RB', x['rush_eff'], rng, cap=45)
        # QB rushing: designed runs + scrambles + kneels
        qb = next((p for p in ps if p['pos'] == 'QB'), None)
        yd_d, l_d = _sum_draws(x['QB_DES'], 'carry_QB_design', tm.get('ypc_design', LG['ypc_qb_design'])*x['rush_eff']/SHAPE_MEAN['carry_QB_design'], rng)
        yd_s, l_s = _sum_draws(x['SCR'], 'carry_QB_scramble', tm.get('ypc_scramble', LG['ypc_qb_scramble'])/SHAPE_MEAN['carry_QB_scramble'], rng)
        qb_ratt = x['QB_DES']+x['SCR']+x['KNEELS']; qb_ryds = np.round(yd_d+yd_s-x['KNEELS'])
        x['RUSH_YDS'] = qb_ryds+sum(v['RYDS'] for v in run_by.values())+np.round(y_or)
        # TDs: each team TD goes to one player with probability = his realized share of that sim's targets (receiving) or rushes
        # (rushing), times the fitted position factor and a small red-zone tilt; unlisted players take the rest
        tg_all = np.maximum(x['TGTS'], 1)
        rw = [REC_TD_POS.get(p['pos'], 1.0)*(REC_TD_W[0]+REC_TD_W[1]*p.get('i10', p['tgt'])/max(p['tgt'], 1e-9))*rec_by[p['name']]['TGT']/tg_all
              for p in recv]
        rec_td, _ = _alloc(x['PTD'], rw, rng)
        ru_all = np.maximum(x['DES']+x['SCR'], 1)
        uw = [RUSH_TD_POS.get(p['pos'], 1.0)*(RUSH_TD_W[0]+RUSH_TD_W[1]*p.get('rz', p['car'])/max(p['car'], 1e-9))*run_by[p['name']]['RATT']/ru_all
              for p in rush]
        qbw = RUSH_TD_POS['QB']*(x['QB_DES']+x['SCR'])/ru_all if qb else None
        rush_td, _ = _alloc(x['RTD'], uw+([qbw] if qb else []), rng)
        names_r = [p['name'] for p in rush]+(['__QB__'] if qb else [])
        rtd_by = dict(zip(names_r, rush_td)); rtd_by.setdefault('__QB__', np.zeros(n, int))
        for p, td in zip(recv, rec_td): rec_by[p['name']]['RECTD'] = td
        for p in ps:
            P = {}; nm = p['name']
            if p['pos'] == 'QB':
                # the starter throws everything unless he exits (injury, benching, blowout rest): fitted by |final margin|
                ma = np.abs(x['MARGIN']); ex = rng.random(n) < np.clip(np.interp(ma, *QB_EXIT)*p.get('exit_mult', 1.0), 0, 1)
                u = rng.random(n); dq = np.linspace(0, 1, 11)
                sh = np.where(ex, np.where(ma >= 21, np.interp(u, dq, EXIT_SHARE['blowout']), np.interp(u, dq, EXIT_SHARE['close'])), QB_FULL)
                att_q = rng.binomial(x['ATT'], sh); f = att_q/np.maximum(x['ATT'], 1)
                f_td = np.where(ex, f**np.where(ma >= 21, EXIT_TD_POW['blowout'], EXIT_TD_POW['close']), f)
                P.update(ATT=att_q, CMP=rng.binomial(x['CMP'], f), PYDS=np.round(x['PASS_YDS']*f), PTD=rng.binomial(x['PTD'], f_td), INT=rng.binomial(x['INT'], f),
                         SACKED=rng.binomial(x['SACKS'], f), LONGCMP=x['LONG_CMP'], RATT=np.round(qb_ratt*f).astype(int), RYDS=np.round(qb_ryds*f),
                         RTD=rng.binomial(rtd_by['__QB__'], f), LONGRUSH=np.round(np.maximum(l_d, l_s)))
                P['PRY'] = P['PYDS']+P['RYDS']; P['TDS'] = P['RTD']; P['ANYTD'] = (P['RTD'] > 0).astype(float)
                P['PASS_RUSH_TD'] = P['PTD']+P['RTD']
            elif p['pos'] == 'K':
                P.update(FGA=x['FGA'], FGM=x['FGM'], XPM=x['XP'], KPTS=3*x['FGM']+x['XP'])
            elif p['pos'] == 'DEF':
                opp = T[o]; mu = opp['PLAYS']*p.get('tkl', 0.10)
                r = mu/TKL_EXTRA; P['TKL'] = rng.negative_binomial(np.maximum(r, 1e-6), r/(r+np.maximum(mu, 1e-9)))   # opponent plays add the rest
                P['SACKS'] = rng.binomial(opp['SACKS'], np.clip(p.get('sack_sh', 0.15), 0, 1))
            else:
                z0 = np.zeros(n, int)
                rb, ru = rec_by.get(nm, {}), run_by.get(nm, {})
                P.update(TGT=rb.get('TGT', z0), REC=rb.get('REC', z0), RECYDS=rb.get('RECYDS', z0*1.0), LONGREC=rb.get('LONGREC', z0*1.0),
                         RECTD=rb.get('RECTD', z0), RATT=ru.get('RATT', z0), RYDS=ru.get('RYDS', z0*1.0), LONGRUSH=ru.get('LONGRUSH', z0*1.0),
                         RTD=rtd_by.get(nm, z0))
                P['TDS'] = P['RECTD']+P['RTD']; P['ANYTD'] = (P['TDS'] > 0).astype(float); P['RRY'] = P['RECYDS']+P['RYDS']
                P['RR'] = P['REC']+P['RATT']
            P['MARGIN'] = x['MARGIN']; S[nm] = P
    A, B = T['A'], T['B']
    for x in (A, B): x.pop('tm', None)
    S['A'], S['B'] = A, B
    S['game'] = dict(MARGIN=A['PTS']-B['PTS'], TOTAL=A['PTS']+B['PTS'])
    return S

def _alloc(k, weights, rng):
    """Give each of k TDs (per sim) to one player with probability proportional to his per-sim weight; the rest go to others."""
    n = len(k); W = np.vstack(weights) if weights else np.zeros((0, n))
    tot = W.sum(0); oth = np.clip(1.0-tot, 0.02, None); P = np.vstack([W, oth]); P = P/P.sum(0)
    out = np.zeros((W.shape[0]+1, n), int); kmax = int(k.max()) if len(k) else 0; cum = np.cumsum(P, 0)
    for i in range(kmax):
        u = rng.random(n); idx = (u[None, :] > cum).sum(0); live = k > i
        np.add.at(out, (idx[live], np.nonzero(live)[0]), 1)
    return [out[i] for i in range(W.shape[0])], out[-1]


# ---- probabilities, scripts, market
BUCKETS = ((-99, -16.5, 'blowout loss'), (-16.5, -7.5, 'two-score loss'), (-7.5, 7.5, 'one-score game'), (7.5, 16.5, 'two-score win'),
           (16.5, 99, 'blowout win'))
def bucket(margin): return np.select([margin <= -16.5, margin <= -7.5, margin < 7.5, margin < 16.5], [b[2] for b in BUCKETS[:4]], 'blowout win')
def p_hit(x, line, side='over', c=1.0):
    x = np.asarray(x, float); po = float(np.clip(x+0.5-line/c, 0, 1).mean()); return po if side == 'over' else 1-po
def p_outcomes(x, line, side='over', c=1.0):
    if float(line) % 1:
        w = p_hit(x, line, side, c); return dict(win=w, push=0.0, loss=1-w)
    hi, lo = p_hit(x, line+0.5, 'over', c), p_hit(x, line-0.5, 'over', c)
    win = hi if side == 'over' else 1-lo; push = lo-hi
    return dict(win=win, push=push, loss=1-win-push)
def ladder(x, ks): x = np.asarray(x, float); return {k: round(float((x >= k).mean()), 3) for k in ks}
def bet_zones(x, levels=(0.55, 0.60), step=1.0):
    x = np.asarray(x, float); ls = np.arange(0.5, max(float(np.quantile(x, 0.995)), 2.0)+step, step); out = {}
    for t in levels:
        ov = [l for l in ls if p_hit(x, l, 'over') >= t]; un = [l for l in ls if p_hit(x, l, 'under') >= t]
        out[f'over {int(t*100)}%'] = max(ov) if ov else None; out[f'under {int(t*100)}%'] = min(un) if un else None
    return {'median': float(np.median(x)), 'mean': round(float(x.mean()), 2), **out}
def script_table(hit, margin):
    b = bucket(margin); rows = []
    for name in [z[2] for z in BUCKETS]:
        mk = b == name; w = float(mk.mean()); ph = float(np.asarray(hit)[mk].mean()) if mk.any() else float('nan')
        rows.append((name, round(w, 3), round(ph, 3), round(w*ph, 3) if mk.any() else 0.0))
    return rows
def script_fit(rows):
    r = sorted([z for z in rows if z[1] > 0.02], key=lambda t: -t[1]); p1, p2 = r[0][2], r[1][2]
    pts = 2 if (p1 >= 0.55 and p2 >= 0.50) else 1 if p1 >= 0.55 else 0
    return pts, any(w >= 0.25 and ph < 0.40 for _, w, ph, _ in rows if ph == ph)
def hits(x, line, side='over'): x = np.asarray(x, float); return (x > line) if side == 'over' else (x < line)
def _scale_for(x, line, q):
    lo, hi = 0.2, 4.0
    for _ in range(50):
        c = (lo+hi)/2; o = p_outcomes(x, line, 'over', c); pv = o['win']/max(o['win']+o['loss'], 1e-12)
        if pv < q: lo = c
        else: hi = c
    return (lo+hi)/2
def mkt_mean(x, line, over_price, under_price=None, method='power'):
    q = devig([over_price, under_price], method)[0] if under_price is not None else one_way_fair(over_price)
    return float(np.asarray(x, float).mean()*_scale_for(x, line, q))
BOOK_W = dict(pinnacle=3.0, circa=3.0, bookmaker=2.0, betonline=1.5, kalshi=1.0, fanduel=1.0, draftkings=1.0, betmgm=0.8,
              caesars=0.8, fanatics=0.8, espnbet=0.8, betrivers=0.7, hardrock=0.7, underdog=0.8, prizepicks=0.8)
def market_mean(x, quotes, extra=()):
    ms, ws = [], []
    for q in quotes:
        l, o, u = q[:3]; b = (q[3] if len(q) > 3 else '').lower().replace(' ', '')
        ms.append(mkt_mean(x, l, o, u)); ws.append(BOOK_W.get(b, 1.0)*(1.0 if u is not None else 0.5))
    for mean_, w in extra: ms.append(mean_); ws.append(w)
    return float(np.average(ms, weights=ws))
W_MODELS, W_MKT, W_MKT_CONS = 0.40, 0.40, 0.70
def logic_mean(ours, models): return ours if not models else (1-W_MODELS)*ours+W_MODELS*float(np.mean(models))
def final_probs(x, line, side, quotes, models=(), extra=(), w_mkt=None):
    """Our simulated distribution, re-centered on the blend of logic and market means; quotes=[(line, over, under[, book])]."""
    x = np.asarray(x, float); w_mkt = W_MKT if w_mkt is None else w_mkt
    ours = float(x.mean()); lm = logic_mean(ours, list(models)); mm = market_mean(x, quotes, extra) if quotes or extra else lm
    o = lambda w: p_outcomes(x, line, side, ((1-w)*lm+w*mm)/max(ours, 1e-9))
    f = o(w_mkt)
    return dict(ours=round(ours, 2), median=float(np.median(x)), logic=round(lm, 2), market=round(mm, 2), final_mean=round((1-w_mkt)*lm+w_mkt*mm, 2),
                p_logic=round(o(0)['win'], 3), p_final=round(f['win'], 3), p_push=round(f['push'], 3), p_cons=round(o(W_MKT_CONS)['win'], 3),
                p_mkt=round(o(1.0)['win'], 3))
def event_final(p_model, p_mkt, w=W_MKT): return (1-w)*p_model+w*p_mkt     # anytime TD, 2+ TDs, first-drive markets
def td_probs(S, name, price=None, hold=0.20, w=W_MKT):
    """Anytime TD: the simulated chance blended with the book's de-vigged chance (TD menus carry about 15-30% hold)."""
    p = float(S[name]['ANYTD'].mean()); pm = td_fair(price, hold) if price is not None else p
    return dict(p_model=round(p, 3), p_mkt=round(pm, 3), p_final=round(event_final(p, pm, w), 3), p_cons=round(event_final(p, pm, W_MKT_CONS), 3))
def first_td(S, name):
    """First TD scorer: each of the game's TDs (both teams, defense and special teams included) is equally likely to come first.
    An approximation (it ignores who gets the ball first); these menus carry 25-40% hold, so they rarely clear the gate."""
    tot = S['A']['TD']+S['B']['TD']+S['A']['NONOFF']+S['B']['NONOFF']; mine = np.asarray(S[name].get('TDS', S[name].get('RTD', 0)), float)
    return round(float(np.where(tot > 0, mine/np.maximum(tot, 1), 0.0).mean()), 4)
def kalshi_weight(bid, ask, volume=0):
    """Tight, traded exchange markets count; wide or empty ones don't (prices in dollars read as probabilities)."""
    sp = ask-bid; return 0.0 if sp > 0.10 else (1.0 if sp <= 0.03 and volume >= 500 else 0.5)
def fit_ladder(x, ladder, w=None):
    """ladder={k: P(k or more)} from an exchange or milestone menu: scales our simulated shape to the market's ladder -> its mean."""
    x = np.asarray(x, float); w = w or {k: 1.0 for k in ladder}; ks = [k for k in ladder if w.get(k, 0) > 0]
    if not ks: return None
    cs = np.linspace(0.5, 2.0, 151); err = [sum(w[k]*(p_hit(x, k-0.5, 'over', c)-ladder[k])**2 for k in ks) for c in cs]
    c = float(cs[int(np.argmin(err))])
    return dict(mean=round(float(x.mean()*c), 2), scale=round(c, 3), fit={k: round(p_hit(x, k-0.5, 'over', c), 3) for k in ks})
def compare_models(ours, sd, models, market):
    rows = [(k, v, round((v-ours)/sd, 2)) for k, v in {**models, 'market': market}.items()]
    return sorted(rows, key=lambda t: -abs(t[2])), [k for k, v, z in rows if abs(z) >= 0.35]
def market_budget(qb_yds_line, receiver_lines, others=0.0):
    """Sum of a team's receiving-yard lines vs its QB's passing-yard line. Receivers' lines are medians, so their sum should sit a few
    yards below the QB line minus what unlisted players catch; a gap of 25+ yards points at the softer side."""
    s = float(sum(receiver_lines)); return dict(receivers=s, qb=qb_yds_line, gap=round(qb_yds_line-s-others, 1))


def market_guard(p_final, p_mkt, gap=0.12): return abs(p_final-p_mkt) > gap   # True: needs a sourced reason, or lean on p_cons
def hit_rate(values, line, side='over'):
    v = np.asarray(values, float); return round(float(((v > line) if side == 'over' else (v < line)).mean()), 2), len(v)
def screen(S, props):
    """Slate scan: props = [(id, name, stat, line, side, over_price, under_price)] priced off one game's sim. Sorted by the gap
    between our chance and the no-vig chance; the deep research goes to the top of this list."""
    rows = []
    for pid, name, stat, line, side, op, up in props:
        ph = p_outcomes(S[name][stat], line, side)['win']; price = op if side == 'over' else up
        pm = devig([op, up])[0 if side == 'over' else 1] if op is not None and up is not None else None
        rows.append(dict(id=pid, p_sim=round(ph, 3), p_mkt=None if pm is None else round(float(pm), 3), gap=round(float(ph-(0.5 if pm is None else pm)), 3),
                         edge=None if price is None else round(edge(ph, price), 3)))
    return sorted(rows, key=lambda r: -r['gap'])


# ---- same game: correlation from the shared simulation
def leg_hits(S, name, stat, line, side='over'):
    x = np.asarray(S[name][stat], float); return (x > line) if side == 'over' else (x < line)
def sgp(leg_hits):
    H = np.vstack([np.asarray(h, bool) for h in leg_hits]); joint = float(H.all(0).mean()); ind = float(np.prod(H.mean(1)))
    return dict(joint=round(joint, 3), independent=round(ind, 3), lift=round(joint/max(ind, 1e-9), 3))
def script_corr(a, b):
    x, y = np.asarray(a, float), np.asarray(b, float)
    return 0.0 if x.std() == 0 or y.std() == 0 else float(np.corrcoef(x, y)[0, 1])


# ---- checks, traps, score
TOO_FAR = dict(PYDS=30.0, RYDS=20.0, RECYDS=18.0, REC=1.3, ATT=4.0, CMP=3.0, RATT=3.5, PTD=0.35, RRY=22.0, PRY=32.0, TKL=1.6, KPTS=1.5, INT=0.3)
def sanity(S, g, team='A'):
    x = S[team]; fl = []; pl = float(x['PLAYS'].mean()); pr = float(x['DB'].mean()/max(pl, 1e-9))
    tgt = (g['total']+(1 if team == 'A' else -1)*g['exp_margin'])/2
    if not 52 <= pl <= 75: fl.append(f'{team} plays {pl:.0f}: check pace')
    if not 0.40 <= pr <= 0.75: fl.append(f'{team} dropback rate {pr:.2f}: check npr and the script')
    if abs(float(x['PTS'].mean())-tgt) > 0.8: fl.append(f'{team} points {x["PTS"].mean():.1f} vs implied {tgt:.1f}')
    return fl
def too_far(stat, ours, market): return abs(ours-market) > TOO_FAR.get(stat, 1e9)
def trap_flags(t):
    f = []; side = t.get('side', 'over')
    if t.get('public_pct', 0) >= 65 and t.get('public_side') == side and t.get('line_moved_with_public') is False: f.append('public side, line not moving with it')
    if t.get('move_against', 0) >= t.get('move_tol', 1.0) and not t.get('news'): f.append('steam against us with no news')
    if t.get('l3_over_season', 1.0) >= 1.30 and side == 'over': f.append('recency: last 3 games far above season')
    if t.get('status') in ('Q', 'Questionable', 'Doubtful', 'GTD'): f.append('unresolved status')
    if t.get('wind', 0) >= 15 and side == 'over' and t.get('stat') in ('PYDS', 'RECYDS', 'CMP', 'LONGREC') and not t.get('weather_priced'):
        f.append('wind 15+ mph on a passing over')
    if t.get('dvp_only'): f.append('defense-vs-position split only (it barely predicts the next game)')
    if t.get('rz_only'): f.append('red-zone share only (target share predicts TDs better)')
    if t.get('efficiency_only') and side == 'over': f.append('efficiency heater without more volume')
    if t.get('td_pool_split'): f.append('TD pool: this TD leg competes with another TD leg on the same team')
    if t.get('too_far') and not t.get('news'): f.append('too good to be true: far from the market and the models with no news')
    return f
def hit_pts(p): return 2 if p >= 0.60 else 1 if p >= 0.55 else 0
CAPS = dict(status_unresolved=4, refuted_claim=3, unverified_claim=5, two_trap_fails=4, script_fragile=5, sens_fragile=5, new_qb=5,
            small_sample=6, too_far_no_news=5, new_role=6, first_game_back=5, weather_unsettled=5)
def score(p, role, matchup_volume, script_pts, models_market, context, p_cons=None, caps=(), duplicate=False):
    s = hit_pts(p)+role+matchup_volume+script_pts+models_market+context-int(duplicate)
    cap = min([10]+[CAPS.get(c, c) if isinstance(c, str) else c for c in caps])
    if p < 0.50: cap = min(cap, 3)
    elif p < 0.55: cap = min(cap, 4)
    if p_cons is not None and p_cons < 0.50: cap = min(cap, 5)
    return max(0, min(s, cap))
def verdict(s): return ('STRONG TAKE', 1.5) if s >= 8 else ('TAKE', 1.0) if s >= 6 else ('TAKE SMALL', 0.5) if s == 5 else ('WATCH', 0) if s == 4 else ('PASS', 0)


# ---- profit layer
REQUIRE_EDGE, MIN_EDGE, KELLY_FRAC = True, 0.02, 0.25
# soft spots (2023-25 backtest at book-style lines): the model's confident receiving overs hit 4-8 points under their stated chance, as did
# 70%+ rushing-yard overs, 60-70% attempt overs and 70%+ passing-yard unders. Those bets need a 4-point edge. (stat: side, from p, edge)
SOFT_SPOTS = dict(REC=('over', 0.60, 0.04), RECYDS=('over', 0.60, 0.04), RRY=('over', 0.60, 0.04), RYDS=('over', 0.70, 0.04),
                  ATT=('over', 0.60, 0.04), PYDS=('under', 0.70, 0.04))
def min_edge_for(stat, side, p):
    sp = SOFT_SPOTS.get(stat); return sp[2] if sp and sp[0] == side and p >= sp[1] else MIN_EDGE
def profit_gate(p_final, p_cons, price, p_push=0.0, min_edge=MIN_EDGE):
    be = breakeven(price, p_push)
    return dict(breakeven=round(be, 3), edge=round(p_final-be, 3), cons_edge=round(p_cons-be, 3), ok=bool(p_final-be >= min_edge and p_cons >= be))
def bet_to(p, p_push=0.0, min_edge=MIN_EDGE):
    q = p-min_edge; return None if q <= 0 else american((1-p_push)/q) if q < 1-p_push else None
def kelly(p, price, p_push=0.0): b = dec(price)-1; return max((b*p-(1-p-p_push))/b, 0.0)
def stake_units(score_, p, price, bankroll_units, p_push=0.0, frac=KELLY_FRAC):
    base = verdict(score_)[1]; k = frac*kelly(p, price, p_push)*bankroll_units; s = min(base, k)
    if base == 0 or k < 0.125: return 0.0
    return max(0.25, float(np.floor(s*4)/4))
def portfolio_scale(stakes, hit_arrays, cap_corr=0.25):
    """Same-game bets that win together are one bigger bet: scale each stake down by its strongest positive link to a larger stake."""
    out = list(stakes)
    for i in range(len(stakes)):
        for j in range(len(stakes)):
            if j != i and stakes[j] >= stakes[i] and hit_arrays[i] is not None and hit_arrays[j] is not None:
                r = script_corr(hit_arrays[i], hit_arrays[j])
                if r > cap_corr: out[i] = min(out[i], float(np.floor(stakes[i]*(1-r)*4)/4))
    return out
def best_offer(x, side, offers, c=1.0):
    rows = []
    for book, line, price in offers:
        o = p_outcomes(x, line, side, c)
        rows.append(dict(book=book, line=line, price=price, p=round(o['win'], 3), push=round(o['push'], 3), ev=round(ev(o['win'], price, o['push']), 4),
                         edge=round(edge(o['win'], price, o['push']), 3), straight_ok=straight_ok(price)))
    return sorted(rows, key=lambda r: -r['ev'])
MAX_STRAIGHT_PRICE = -190
def straight_ok(price, cap=MAX_STRAIGHT_PRICE): return price is not None and (price > 0 or price >= cap)
def est_price(p_mkt, hold=0.045): return american(1/min(p_mkt+hold, 0.97))
def price_note(price, est=False, cap=MAX_STRAIGHT_PRICE, near=15):
    if price is None: return 'price not found: estimate it with est_price() before the bet goes on the card'
    if not straight_ok(price, cap): return f'{price:+d} is past {cap}: not a straight, use the fallback number or keep it as a parlay leg'
    if est and price < 0 and price <= cap+near: return f'about {price:+d}: place only if the app shows {cap} or better'
    return ''
def best_straight_line(x, side, line_prices, cap=MAX_STRAIGHT_PRICE, c=1.0, min_edge=None):
    ok = {}
    for l, pr in line_prices.items():
        if not straight_ok(pr, cap): continue
        o = p_outcomes(x, l, side, c)
        if min_edge is not None and edge(o['win'], pr, o['push']) < min_edge: continue
        ok[l] = (pr, o['win'])
    if not ok: return None
    l = max(ok, key=lambda k: ok[k][1]); return dict(line=l, price=ok[l][0], p_sim=round(ok[l][1], 3))
def pick_top(cands, n, max_per_game=2, block=0.25, warn=0.10, cap=MAX_STRAIGHT_PRICE, require_edge=None):
    """cands: id, game, player, score, p, p_cons, fit, price, stat, side, optional p_push and hits (bool array from the game's shared sim);
    the gate's edge comes from min_edge_for(stat, side, p) unless the candidate carries min_edge.
    Skips straights past -190 or failing the profit gate, blocks same-game bets whose hits correlate 0.25+, one bet per player."""
    require_edge = REQUIRE_EDGE if require_edge is None else require_edge
    gate = lambda c: profit_gate(c['p'], c.get('p_cons', c['p']), c['price'], c.get('p_push', 0.0),
                                 c.get('min_edge', min_edge_for(c.get('stat'), c.get('side'), c['p'])))
    left = [{**c, 'gate': gate(c)} for c in cands if straight_ok(c.get('price'), cap)]
    if require_edge: left = [c for c in left if c['gate']['ok']]
    chosen = []; pg = Counter(); pp = Counter()
    link = lambda c: max([abs(script_corr(c['hits'], d['hits'])) for d in chosen if d['game'] == c['game'] and c.get('hits') is not None
                          and d.get('hits') is not None] or [0.0])
    while left and len(chosen) < n:
        eff = lambda c: c['score']-(1 if link(c) >= warn else 0)
        left.sort(key=lambda c: (-eff(c), -c['p'], -c.get('p_cons', 0), -c.get('fit', 0))); c = left.pop(0)
        if eff(c) < 5 or c['p'] < 0.55: break
        if pg[c['game']] >= max_per_game or link(c) >= block or (c.get('player') and pp[c['player']] >= 1): continue
        chosen.append({**c, 'eff_score': eff(c), 'link': round(link(c), 2)}); pg[c['game']] += 1
        if c.get('player'): pp[c['player']] += 1
    return chosen


# ---- parlays
def parlay_dec(prices): return float(np.prod([dec(a) for a in prices]))
def parlay_price(prices): return american(parlay_dec(prices))
def parlay_ev(p_joint, price): return round(p_joint*dec(price)-1, 4)
def house_edge(fair_ps, prices): return round(1-float(np.prod([q*dec(a) for q, a in zip(fair_ps, prices)])), 4)
def implied_lift(sgp_price, leg_ps): return round((1/dec(sgp_price))/float(np.prod(leg_ps)), 3)
def round_robin(ps, prices, size):
    n = len(ps); combos = list(itertools.combinations(range(n), size)); ret = 0.0; p_any = 0.0
    for out in itertools.product([0, 1], repeat=n):
        pr = float(np.prod([ps[i] if o else 1-ps[i] for i, o in enumerate(out)])); won = [c for c in combos if all(out[i] for i in c)]
        ret += pr*sum(parlay_dec([prices[i] for i in c]) for c in won); p_any += pr*(len(won) > 0)
    return dict(tickets=len(combos), p_any_win=round(p_any, 3), exp_return=round(ret/len(combos)-1, 4))
def joint_prob(legs):
    by = defaultdict(list); out = 1.0; lifts = {}
    for L in legs: by[L['game']].append(L)
    for gm, Ls in by.items():
        base = float(np.prod([L['p'] for L in Ls]))
        if len(Ls) > 1:
            H = float(np.all([L['hits'] for L in Ls], axis=0).mean()); ind = float(np.prod([np.mean(L['hits']) for L in Ls])); lift = H/max(ind, 1e-9)
        else: lift = 1.0
        out *= min(base*lift, min(L['p'] for L in Ls)); lifts[gm] = round(lift, 3)
    return out, lifts
def parlay_ok(legs, max_per_game):
    if len({(L['game'], L.get('market', L['id'])) for L in legs}) < len(legs): return False
    pl = Counter((L.get('player'), L.get('side')) for L in legs if L.get('player'))
    if any(L.get('side') == 'under' and pl[(L.get('player'), 'under')] > 1 for L in legs if L.get('player')): return False
    return all(c <= max_per_game for c in Counter(L['game'] for L in legs).values())
PARLAY = dict(safe=dict(legs=(2, 3), min_p=0.62, min_score=6, max_per_game=1, min_price=100, max_price=400, min_ev=0.0, leg_ev=-0.03),
              risky=dict(legs=(3, 5), min_p=0.55, min_score=5, max_per_game=2, min_price=450, max_price=1500, min_ev=0.0, leg_ev=-0.03))
def build_parlays(legs, kind='safe', top=3, relax=True, **over):
    c = {**PARLAY[kind], **over}; res = _search(legs, c, kind, top)
    while relax and not res and round(c['min_p']-0.02, 2) >= 0.56:
        c = {**c, 'min_p': round(c['min_p']-0.02, 2), 'min_score': max(5, c['min_score']-1)}; res = _search(legs, c, kind, top)
    for r in res: r['level'] = f"legs {c['min_p']:.0%}+ and score {c['min_score']}+"
    return res
def _search(legs, c, kind, top):
    pool = [L for L in legs if L['p'] >= c['min_p'] and L['score'] >= c['min_score'] and not L.get('traps') and ev(L['p'], L['price']) >= c['leg_ev']]
    out = []
    for k in range(c['legs'][0], c['legs'][1]+1):
        for combo in itertools.combinations(pool, k):
            if not parlay_ok(combo, c['max_per_game']): continue
            price = parlay_price([L['price'] for L in combo])
            if price < c['min_price'] or price > c['max_price']: continue
            j, lifts = joint_prob(combo)
            if any(v < 0.98 for v in lifts.values()): continue
            if parlay_ev(j, price) < c['min_ev']: continue
            out.append(dict(kind=kind, legs=[L['id'] for L in combo], joint=round(j, 3), price=price, fair=american(1/j), lifts=lifts,
                            weakest=min(combo, key=lambda L: L['p'])['id'], ev=parlay_ev(j, price)))
    return sorted(out, key=lambda r: (-r['joint'], -r['price']))[:top]


# ---- tracking, calibration, autoresearch
def brier(p, y): p, y = np.asarray(p, float), np.asarray(y, float); return float(((p-y)**2).mean())
def logloss(p, y):
    p = np.clip(np.asarray(p, float), 1e-4, 1-1e-4); y = np.asarray(y, float); return float(-(y*np.log(p)+(1-y)*np.log(1-p)).mean())
def calib(p, y, edges=(0.5, 0.55, 0.6, 0.65, 1.01)):
    p, y = np.asarray(p, float), np.asarray(y, float); out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mk = (p >= lo) & (p < hi)
        if mk.any(): out.append((f'{lo:.2f}-{hi:.2f}', int(mk.sum()), round(float(p[mk].mean()), 3), round(float(y[mk].mean()), 3)))
    return out
def calib_tripwire(rows, n=15, gap=0.10):
    r = rows[-n:]
    if len(r) < n: return dict(live=False, n=len(r))
    st = float(np.mean([x['p_final'] for x in r])); ac = float(np.mean([x['y'] for x in r]))
    return dict(live=st-ac >= gap, n=n, stated=round(st, 3), actual=round(ac, 3))
def clv(price_taken, close_side, close_other): q = devig([close_side, close_other])[0]; return round(q*dec(price_taken)-1, 4)
def line_clv(taken, closed, side='over'): return round((closed-taken) if side == 'over' else (taken-closed), 1)
def fit_blend(rows, grid=np.linspace(0, 1, 21)):
    pl = np.array([r['p_logic'] for r in rows]); pm = np.array([r['p_mkt'] for r in rows]); y = np.array([r['y'] for r in rows])
    res = [(round(float(w), 2), round(logloss((1-w)*pl+w*pm, y), 4)) for w in grid]
    return min(res, key=lambda t: t[1]), res
def autoresearch(rows, experiments, holdout=0.3, min_gain=0.002):
    ys = np.array([r['y'] for r in rows], float); cut = int(len(rows)*(1-holdout)); res = []
    base = np.array([r['p_final'] for r in rows]); b_tr, b_te = logloss(base[:cut], ys[:cut]), logloss(base[cut:], ys[cut:])
    res.append(('baseline', round(b_te, 4), 0.0, 'keep'))
    for name, fn in experiments.items():
        pe = np.array([fn(r) for r in rows]); tr, te = logloss(pe[:cut], ys[:cut]), logloss(pe[cut:], ys[cut:])
        res.append((name, round(te, 4), round(b_te-te, 4), 'keep' if (b_te-te) >= min_gain and tr <= b_tr else 'discard'))
    return res
def replay(row, **over):
    """Re-run a logged pick with changed engine settings: row holds g, players, name, stat, line, side, quotes, models."""
    saved = {k: globals()[k] for k in over}; globals().update(over)
    try:
        S = sim_game(row['g'], row['players'], n=row.get('n', 20000))
        return final_probs(S[row['name']][row['stat']], row['line'], row['side'], row.get('quotes', []), row.get('models', ()))
    finally: globals().update(saved)
def sensitivity(g, players, leg, n=8000, seed=7, d_spread=3.0, d_total=3.0, d_share=0.15):
    """leg(S) -> boolean hits. Reruns the shared sim with the spread and total moved and every named share moved 15%."""
    base = float(np.mean(leg(sim_game(g, players, n, seed)))); out = {'base': round(base, 3)}
    for lab, gg, pl in ((f'margin -{d_spread:g}', {**g, 'exp_margin': g['exp_margin']-d_spread}, players),
                        (f'margin +{d_spread:g}', {**g, 'exp_margin': g['exp_margin']+d_spread}, players),
                        (f'total -{d_total:g}', {**g, 'total': g['total']-d_total}, players), (f'total +{d_total:g}', {**g, 'total': g['total']+d_total}, players),
                        ('shares -15%', g, [{**p, 'tgt': p.get('tgt', 0)*(1-d_share), 'car': p.get('car', 0)*(1-d_share)} for p in players]),
                        ('shares +15%', g, [{**p, 'tgt': p.get('tgt', 0)*(1+d_share), 'car': p.get('car', 0)*(1+d_share)} for p in players])):
        out[lab] = round(float(np.mean(leg(sim_game(gg, pl, n, seed)))), 3)
    return out
