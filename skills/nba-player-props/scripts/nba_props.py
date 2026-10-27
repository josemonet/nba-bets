"""nba_props: the NBA player prop engine. One simulation prices every prop for a player or a whole game.

Constants marked (fitted) come from 2010-11 to 2023-24 regular-season box scores (351,409 player-games,
16,658 games). references/calibration.md lists every number, the test behind it and the old value it replaced.
Usage: import nba_props as m (copy this file next to your work, or add the skill's scripts/ folder to sys.path).
"""
import itertools
from collections import Counter, defaultdict

import numpy as np
from scipy.optimize import brentq
from scipy.stats import norm

VERSION = "2.0"

# ---- game script (fitted)
SIG = 13.0                       # SD of the final margin around the spread; 13 reproduces the 19% share of 20+ point games (12 gave 15%)
OT_PEAK, OT_WIDTH = 0.070, 11.5  # P(overtime) = OT_PEAK * exp(-m^2 / (2 OT_WIDTH^2)): 7.0% in pick'ems, 2.8% at 16-point spreads
OT_MORE = 0.138                  # chance an overtime game goes to another overtime
POSS_SD = 4.6                    # SD of game possessions around the pregame expectation (old value 3.5)
LG_PPP = 1.15                    # league points per possession; refresh from league ORtg/100 each month
BUCKETS = ((-99, -17.5, 'blowout loss'), (-17.5, -7.5, 'comfortable loss'), (-7.5, 7.5, 'close'),
           (7.5, 17.5, 'comfortable win'), (17.5, 99, 'blowout win'))

# ---- minutes (fitted). Role comes from projected competitive-game minutes unless p['role'] overrides it.
MKNOTS = np.array([0, 4.5, 7.5, 10.5, 13.5, 16.5, 19.5, 22.5, 25.5, 28.5, 32.5, 40.0])   # |final margin|
ROLE = dict(
    # dm: minutes vs his competitive-game average at each |margin| knot (wins and losses alike); ot: minutes per overtime;
    # sd, tail_p, tail_mean, tail_sign: normal core of the game-to-game noise plus a chance of a big swing (down for rotation players
    # and up: fouls, injury, short leash; up for the bench: extra run); reg: a recent-minutes projection's error toward the next game.
    # Noise fitted on 2014-24 games (2010-13 minutes were noisier); stars' recent minutes run 0.6 high.
    star=dict(floor=34.0, dm=(0.19, 0.08, -0.21, -1.04, -2.20, -3.27, -4.46, -5.48, -6.14, -6.60, -7.68, -8.59),
              ot=4.6, sd=3.07, tail_p=0.124, tail_mean=7.7, tail_sign=-1, reg=-0.63),
    starter=dict(floor=28.0, dm=(0.13, 0.09, -0.18, -0.72, -1.50, -2.38, -3.28, -3.65, -4.82, -4.92, -5.55, -6.25),
                 ot=4.0, sd=3.98, tail_p=0.211, tail_mean=6.6, tail_sign=-1, reg=-0.08),
    rotation=dict(floor=18.0, dm=(0.01, 0.04, -0.04, -0.15, -0.42, -0.61, -0.94, -1.05, -1.17, -1.22, -1.60, -1.70),
                  ot=2.1, sd=5.82, tail_p=0.049, tail_mean=8.4, tail_sign=-1, reg=-0.14),
    bench=dict(floor=0.0, dm=(-0.11, 0.08, 0.01, 0.29, 0.23, 0.32, 0.53, 1.04, 1.44, 1.84, 2.03, 2.78),
               ot=0.8, sd=4.81, tail_p=0.579, tail_mean=6.2, tail_sign=1, reg=0.37))
PF_KNOTS, PF_TAIL = (2.25, 2.75, 3.25, 3.75, 4.25, 4.75), (0.91, 1.06, 1.10, 1.32, 1.66, 1.90)  # fouls/36 -> tail multiplier (stars, starters)
MIN_HALFLIFE = 2.5               # games; a margin-adjusted EWMA beat last-5, last-10 and season averages (RMSE 5.96 vs 6.55-7.03)
MIN_PULL = 0.1                   # pull toward his margin-adjusted season average (best fit on 2014-20; halves the bias after a dip)
PROMOTED = ((12, 21, 27, 33), (11.5, 7.3, 5.05, 3.1), (5.6, 3.7, 3.3, 3.2))   # new starter: minutes gained and extra SD by recent average
DEMOTED = ((15, 21, 27, 33, 38), (-4.0, -4.4, -5.5, -6.3, -8.9), 2.0)          # starter sent to the bench: minutes lost, extra SD
TEAMMATE_OUT_MIN = ((14, 21, 27, 33, 38), (2.7, 1.7, 1.4, 0.6, 0.05))  # minutes gained by the others when a key player sits

# ---- per-minute rates (fitted)
STAB = dict(pts=200, reb=100, ast=100, fg3m=200, fga=100, fg3a=100, fta=200, stl=600, blk=200, tov=400,
            p3=750, p2=350, ft=200)  # minutes (attempts for shooting %) of weight on last season's rate
RECENT_W = dict(pts=0.2, reb=0.1, ast=0.3, fg3m=0.1, fga=0.3, fg3a=0.4, fta=0.2, stl=0.1, blk=0.1, tov=0.1)  # weight on the last-10 rate
DRIFT = dict(fga=1.008, fta=0.997, reb=0.995, ast=1.036, stl=0.984, blk=0.964, tov=0.975, s3=1.0, p2=1.006, p3=1.004, ft=1.005)
                                 # next-game rate / projected rate, 2014-24 (assists keep rising in-season every year: +2% to +6%;
                                 # the 3PA-share drift of the 2014-19 three-point boom faded to zero in 2020-24)
HOME = dict(fga=0.999, fta=1.014, reb=1.010, ast=1.020, stl=0.998, blk=1.032, tov=0.992, fg=1.008)  # home multiplier; away = 1/x
MATCH_K = dict(pts=40, fga=40, fta=40, reb=20, ast=20, fg3m=40, fg3a=5, stl=40, blk=20, tov=40)  # games of shrinkage, opponent factors

# ---- game-to-game noise at fixed minutes and pace (fitted)
PHI = dict(fta=2.05, reb=1.08, ast=1.10, stl=1.04, blk=1.08, tov=1.0)  # variance / mean (old: fta 1.3, reb and ast 1.0)
FGA_D = (0.92, -0.0055)          # FGA variance/mean = 0.92 - 0.0055 x mean (old model: 0.35-0.9 by role)
SIG_U = 0.10                     # shot-competition shock on FGA; teammates' attempts correlate -0.03
KAPPA = dict(mix=160, ft=64)     # Beta concentration of game-to-game noise in 3PA share and FT%; 2P% and 3P% showed none beyond binomial
PCT_N = dict(p2=1500, p3=700)    # default effective attempts behind his 2P% and 3P% (estimate uncertainty, not game noise)
RATE_CV = dict(vol=2.8, three=2.0, reb=0.9, ast=1.4, stl=1.8, blk=1.8, tov=1.4)  # multipliers on rate_cv by stat group (tuned on
                                 # 2014-20 so 50/80/90% intervals hold their coverage)
RATE_RHO = 0.5                   # projection errors share a common part across his stats (a role change moves them together)
TEAM_FGM = 42.0                  # team field goals made per game; assists respond to teammates' makes in same-game sims
ASSIST_LINK = 0.65               # share of a teammate's extra makes that lift his assists; reproduces the 0.12 correlation of a
                                 # playmaker's assists with a scoring teammate's points


# ---- odds
def dec(a): return 1 + (a/100 if a > 0 else 100/-a)
def imp(a): return 1/dec(a)
def american(d): return int(round((d-1)*100)) if d >= 2 else int(round(-100/(d-1)))
def devig(prices, method='power'):                     # all outcomes of one market -> fair probabilities
    q = np.array([imp(a) for a in prices])
    if method == 'mult': return q/q.sum()
    k = brentq(lambda k: (q**k).sum()-1, 0.2, 5.0); return q**k
def one_way_fair(price, margin=0.08): return imp(price)/(1+margin)   # alt ladder or one-sided price
def ev(p, price, p_push=0.0): return p*(dec(price)-1)-(1-p-p_push)   # pushes refund the stake
def ev_line(p, price, p_push=0.0):
    e = ev(p, price, p_push); return f"EV {e*100:+.1f}% at {price:+d} ({'+EV' if e > 0 else '-EV'})"
def breakeven(price, p_push=0.0): return (1-p_push)/dec(price)       # chance to win needed to break even
def edge(p, price, p_push=0.0): return p-breakeven(price, p_push)


# ---- game script
def p_ot(exp_margin): return float(OT_PEAK*np.exp(-exp_margin**2/(2*OT_WIDTH**2)))
def poss(total, ortg_a=None, drtg_a=None, ortg_b=None, drtg_b=None, lg=None):
    if None in (ortg_a, drtg_a, ortg_b, drtg_b): return total/(2*LG_PPP)
    lg = lg or 100*LG_PPP; pa = (ortg_a+drtg_b-lg)/100; pb = (ortg_b+drtg_a-lg)/100
    return total/(pa+pb)
def script_probs(exp_margin):                           # final-margin buckets for team A (exp_margin = -spread)
    po = p_ot(exp_margin); out = {n: (1-po)*(norm.cdf(h, exp_margin, SIG)-norm.cdf(l, exp_margin, SIG)) for l, h, n in BUCKETS}
    out['overtime'] = po; return {k: round(float(v), 3) for k, v in out.items()}
def draw_game(g, n=40000, seed=11):                     # shared draws for every player in one game (team A view)
    rng = np.random.default_rng(seed); ot = rng.random(n) < p_ot(g['exp_margin'])
    ot_n = np.where(ot, rng.geometric(1-OT_MORE, n), 0)
    M = np.where(ot, rng.normal(0, 4, n), rng.normal(g['exp_margin'], SIG, n))
    pe = g.get('poss') or poss(g['total']); P = rng.normal(pe, POSS_SD, n)
    return dict(rng=rng, n=n, ot=ot, ot_n=ot_n, M=M, P=P, pe=pe)
def bucket(M, ot):
    lab = np.select([M <= -17.5, M <= -7.5, M < 7.5, M < 17.5], [b[2] for b in BUCKETS[:4]], 'blowout win')
    return np.where(ot, 'overtime', lab)


# ---- minutes
def role_for(minutes_): return next(k for k in ('star', 'starter', 'rotation', 'bench') if minutes_ >= ROLE[k]['floor'])
def minutes(p, G):
    rng, n = G['rng'], G['n']; role = p.get('role') or role_for(p['min']); r = ROLE[role]
    tp = r['tail_p']*(float(np.interp(p.get('pf36', 2.7), PF_KNOTS, PF_TAIL)) if role in ('star', 'starter') else 1.0)
    noise = (np.hypot(r['sd'], p.get('min_sd_extra', 0.0))*rng.standard_normal(n)
             + r['tail_sign']*((rng.random(n) < tp)*rng.gamma(2.0, max(r['tail_mean'], 1e-9)/2, n)-tp*r['tail_mean']))   # mean zero
    m = p['min'] + np.interp(np.abs(G['M']), MKNOTS, r['dm']) + G['ot_n']*r['ot'] + noise
    ex = rng.random(n) < p.get('p_exit', 0.0)                           # extra injury-exit risk; the bet still stands
    m = np.where(ex, m*rng.uniform(0.05, 0.8, n), m)
    return np.clip(m, 0, p.get('cap') or 53)
def calibrate_min(p, g, close_minutes, n=20000):        # set p['min'] so simulated minutes in games decided by under 10 match his real average
    for _ in range(3):
        S = sim_player(p, g, n=n); mk = np.abs(S['M']) < 10
        p['min'] += close_minutes-float(S['MIN'][mk].mean())
    return round(p['min'], 1)
def project_minutes(mins, margins=None, ots=None, role_change=None, halflife=MIN_HALFLIFE):
    """Competitive-game minutes for sim_player from his game log in his current role this season (oldest first; 5+ games,
    the whole log is best). margins: his team's final margins in those games; ots: overtime periods.
    role_change: 'promoted' or 'demoted' tonight (confirmed lineup)."""
    m = np.asarray(mins, float); r = ROLE[role_for(float(np.mean(m)))]
    if margins is not None: m = m-np.interp(np.abs(np.asarray(margins, float)), MKNOTS, r['dm'])
    if ots is not None: m = m-np.asarray(ots, float)*r['ot']
    w = 0.5**(np.arange(len(m))[::-1]/halflife); base = float(np.sum(w*m)/np.sum(w))
    base += MIN_PULL*(float(m.mean())-base)
    base += ROLE[role_for(base)]['reg']; extra = 0.0
    if role_change == 'promoted': extra = float(np.interp(base, PROMOTED[0], PROMOTED[2])); base += float(np.interp(base, *PROMOTED[:2]))
    elif role_change == 'demoted': extra = DEMOTED[2]; base += float(np.interp(base, *DEMOTED[:2]))
    return dict(min=round(base, 1), min_sd_extra=extra, role=role_for(base))


# ---- rates
def shrink(obs, n, prior, k): return (n*obs+k*prior)/(n+k)
def project_rate(stat, season_total, season_min, prev_total=None, prev_min=None, l10_total=None, l10_min=None, league36=None):
    """Per-36 rate: this season shrunk toward last season by STAB minutes, then RECENT_W of the last-10 rate blended in."""
    prior = 36*prev_total/prev_min if prev_min and prev_min >= 300 else league36
    obs = 36*season_total/season_min if season_min else None
    if obs is None: r = prior
    elif prior is None: r = obs
    else: r = shrink(obs, season_min, prior, STAB[stat])
    if l10_min and l10_min >= 60 and r is not None:
        r = (1-RECENT_W.get(stat, 0.1))*r+RECENT_W.get(stat, 0.1)*36*l10_total/l10_min
    return None if r is None else round(float(r*DRIFT.get(stat, 1.0)), 3)
def project_pct(made, att, prior_pct, key):                # shooting % shrunk toward his career (or last season) mark
    return round(float((made+STAB[key]*prior_pct)/(att+STAB[key])*DRIFT.get(key, 1.0)), 4)
def project_share(fg3a, fga, prior_share, k=100):          # 3PA share of FGA, shrunk toward last season by 100 attempts
    return round(float(min((fg3a+k*prior_share)/(fga+k)*DRIFT['s3'], 0.95)), 4)
def matchup_adj(opp_allowed, league_avg, games, stat=None, k=None, cap=0.15):   # regressed opponent multiplier for one stat
    k = k or MATCH_K.get(stat, 20); return float(1+np.clip((opp_allowed/league_avg-1)*games/(games+k), -cap, cap))
def wowy_bump(with_avg, without_avg, n_without, k=8): return (without_avg-with_avg)*n_without/(n_without+k)
def usage_shift(out, mates):
    """A key player sits. out: his r36 (fga, ast, reb). mates: {name: player dict}; set promoted=True on whoever takes his
    starting spot. Returns new player dicts. Fitted on 1,490 absences (split-sample): every remaining player's FGA/36 rises by
    0.135 x (out FGA/36 - 10.6), about +1.1 when a 19-FGA star sits, similar for stars and role players; assists rise 17% when
    he is a playmaker (7+ AST/36); rebounds 4.5% when he is a big (10+ REB/36); stars gain almost no minutes."""
    d_fga = 0.135*max(out.get('fga', 0.0)-10.6, 0.0)
    ast_m = 1.17 if out.get('ast', 0.0) >= 7 else 1+0.0098*out.get('ast', 0.0)
    reb_m = 1.045 if out.get('reb', 0.0) >= 10 else 1.0
    new = {}
    for name, p in mates.items():
        q = {**p, 'r36': dict(p['r36'])}; f0 = q['r36']['fga']
        q['r36']['fga'] = f0+d_fga
        q['r36']['fta'] = q['r36'].get('fta', 0.0)*(q['r36']['fga']/max(f0, 1e-9))
        q['r36']['ast'] = q['r36'].get('ast', 0.0)*ast_m; q['r36']['reb'] = q['r36'].get('reb', 0.0)*reb_m
        if p.get('promoted'):
            q['min'] = p['min']+float(np.interp(p['min'], *PROMOTED[:2]))
            q['min_sd_extra'] = max(p.get('min_sd_extra', 0.0), float(np.interp(p['min'], PROMOTED[0], PROMOTED[2])))
        else:
            q['min'] = p['min']+float(np.interp(p['min'], *TEAMMATE_OUT_MIN))
        new[name] = q
    return new
def usage_bumps(out_fga, mates, **_):                    # v1 name kept: FGA multipliers per teammate from usage_shift's fitted rule
    d = 0.135*max(out_fga-10.6, 0.0); return {k: round(1+d/max(v, 1e-9), 3) for k, v in mates.items()}


# ---- one player
def cnt(mu, phi, rng):                                  # count with variance = phi*mean: binomial if phi<1, Poisson if 1, neg. binomial if >1
    mu = np.maximum(mu, 1e-9)
    if phi < 0.999:
        N = np.ceil(mu/(1-phi)).astype(int); return rng.binomial(N, np.minimum(mu/N, 1.0))
    if phi <= 1.001: return rng.poisson(mu)
    r = mu/(phi-1); return rng.negative_binomial(r, r/(r+mu))
def bdraw(m, k, n, rng): m = np.clip(m, 1e-4, 1-1e-4); return rng.beta(m*k, (1-m)*k, n)
def fga_phi(mu): return float(np.clip(FGA_D[0]+FGA_D[1]*mu-mu*SIG_U**2, 0.3, 1.0))
def _home(p, k):
    h = p.get('home'); return 1.0 if h is None else (HOME[k] if h else 1/HOME[k])
def sim_player(p, g, G=None, n=40000, seed=11, uz=None):
    # p: min (competitive-game minutes, project_minutes()), r36 per-36 rates (fga, fta, reb, ast, stl, blk, tov), s3 (3PA share of FGA),
    #    pct (p2, p3, ft). Optional: role, team 'A'/'B', home True/False, team_poss, adj (opponent multipliers by r36 key), pf36, cap,
    #    q1_min, starter, rate_cv (0.05 settled, 0.09 for 10-20 games, 0.13 new role or team), min_sd_extra, p_exit, pct_n (p2, p3)
    G = G or draw_game(g, n, seed); rng, n = G['rng'], G['n']; mins = minutes(p, G)
    f = G['P']/p.get('team_poss', g.get('team_poss', G['pe']))
    rc = p.get('rate_cv', 0.05); zc = rng.standard_normal(n)
    U = {k: np.exp(rc*w*(np.sqrt(RATE_RHO)*zc+np.sqrt(1-RATE_RHO)*rng.standard_normal(n))-(rc*w)**2/2)
         for k, w in RATE_CV.items()} if rc > 0 else defaultdict(lambda: 1.0)
    grp = dict(fga='vol', fta='vol', reb='reb', ast='ast', stl='stl', blk='blk', tov='tov'); adj = p.get('adj', {})
    lam = lambda k: p['r36'][k]*adj.get(k, 1.0)*_home(p, k)*mins/36*f*U[grp[k]]
    uz = rng.lognormal(-SIG_U**2/2, SIG_U, n) if uz is None else uz
    mu = lam('fga'); T = cnt(mu*uz, fga_phi(float(mu.mean())), rng); fa = cnt(lam('fta'), PHI['fta'], rng)
    a3 = rng.binomial(T, bdraw(p['s3']*U['three'], KAPPA['mix'], n, rng)) if p['s3'] > 0 else np.zeros(n, int); a2 = T-a3
    pn = {**PCT_N, **p.get('pct_n', {})}; hf = _home(p, 'fg')
    m2 = rng.binomial(a2, np.clip(bdraw(p['pct']['p2'], pn['p2'], n, rng)*hf, 0, 1))
    m3 = rng.binomial(a3, np.clip(bdraw(p['pct']['p3'], pn['p3'], n, rng)*hf, 0, 1))
    mf = rng.binomial(fa, bdraw(p['pct']['ft'], KAPPA['ft'], n, rng))
    S = dict(MIN=mins, PTS=2*m2+3*m3+mf, FG3M=m3, FG3A=a3, FGA=T, FGM=m2+m3, FTA=fa, FTM=mf, _lam_ast=lam('ast'))
    for k, K in (('reb', 'REB'), ('ast', 'AST'), ('stl', 'STL'), ('blk', 'BLK'), ('tov', 'TOV')): S[K] = cnt(lam(k), PHI[k], rng)
    starter = p.get('starter', (p.get('role') or role_for(p['min'])) in ('star', 'starter'))
    q1 = np.clip(rng.normal(p.get('q1_min', min(10.0, (0.27 if starter else 0.10)*p['min'])), 1.2, n), 0, 12)
    S['_q1sh'] = np.clip(q1/np.maximum(mins, 1e-6), 0, 1)
    S['Q1_PTS'] = 2*rng.binomial(m2, S['_q1sh'])+3*rng.binomial(m3, S['_q1sh'])+rng.binomial(mf, S['_q1sh'])
    S['Q1_REB'] = rng.binomial(S['REB'], S['_q1sh'])
    S['M'] = G['M']*(1 if p.get('team', 'A') == 'A' else -1); S['OT'] = G['ot']
    _combos(S, rng); return S
def _combos(S, rng):
    S.update(PRA=S['PTS']+S['REB']+S['AST'], PR=S['PTS']+S['REB'], PA=S['PTS']+S['AST'], RA=S['REB']+S['AST'], STOCKS=S['STL']+S['BLK'])
    ten = (np.vstack([S['PTS'], S['REB'], S['AST'], S['STL'], S['BLK']]) >= 10).sum(0)
    S['DD'], S['TD'] = (ten >= 2).astype(float), (ten >= 3).astype(float)
    S['Q1_AST'] = rng.binomial(S['AST'], S['_q1sh'])


# ---- probabilities, scripts, market
def p_hit(x, line, side='over', c=1.0):                 # integer stats, half-point lines; c rescales the distribution smoothly
    po = float(np.clip(x+0.5-line/c, 0, 1).mean()); return po if side == 'over' else 1-po
def p_outcomes(x, line, side='over', c=1.0):            # win, push and loss chances; whole-number lines can push
    if float(line) % 1:
        w = p_hit(x, line, side, c); return dict(win=w, push=0.0, loss=1-w)
    hi, lo = p_hit(x, line+0.5, 'over', c), p_hit(x, line-0.5, 'over', c)   # P(X >= L+1), P(X >= L)
    win = hi if side == 'over' else 1-lo; push = lo-hi
    return dict(win=win, push=push, loss=1-win-push)
def ladder(S, stat, ks): return {k: round(float((S[stat] >= k).mean()), 3) for k in ks}   # P(k+) for alt milestones
def bet_zones(x, levels=(0.55, 0.60)):                  # no posted line yet: the lines where each side reaches 55% and 60%
    ls = np.arange(0.5, 80.5, 1.0); out = {}
    for t in levels:
        ov = [l for l in ls if p_hit(x, l, 'over') >= t]; un = [l for l in ls if p_hit(x, l, 'under') >= t]
        out[f'over {int(t*100)}%'] = max(ov) if ov else None; out[f'under {int(t*100)}%'] = min(un) if un else None
    return {'median': float(np.median(x)), **out}
def script_table(S, stat, line, side='over'):
    b = bucket(S['M'], S['OT']); rows = []
    for name in [x[2] for x in BUCKETS]+['overtime']:
        mk = b == name; w = float(mk.mean())
        ph = p_hit(S[stat][mk], line, side) if mk.any() else float('nan')
        rows.append((name, round(w, 3), round(ph, 3), round(w*ph, 3) if mk.any() else 0.0))
    return rows
def script_fit(rows):                                   # 2 robust, 1 needs the likeliest script, 0 needs a minority script
    r = sorted([x for x in rows if x[1] > 0.02], key=lambda t: -t[1]); p1, p2 = r[0][2], r[1][2]
    pts = 2 if (p1 >= 0.55 and p2 >= 0.50) else 1 if p1 >= 0.55 else 0
    fragile = any(w >= 0.25 and ph < 0.40 for _, w, ph, _ in rows if ph == ph)
    return pts, fragile
def _scale_for(x, line, q):                             # scale c so the no-push chance of the over equals q
    lo, hi = 0.2, 4.0
    for _ in range(50):
        c = (lo+hi)/2; o = p_outcomes(x, line, 'over', c); pv = o['win']/max(o['win']+o['loss'], 1e-12)
        if pv < q: lo = c
        else: hi = c
    return (lo+hi)/2
def mkt_mean(x, line, over_price, under_price=None, method='power'):   # market-implied mean, using our distribution's shape
    q = devig([over_price, under_price], method)[0] if under_price is not None else one_way_fair(over_price)
    return float(x.mean()*_scale_for(x, line, q))
BOOK_W = dict(pinnacle=3.0, circa=3.0, bookmaker=2.0, betonline=1.5, kalshi=1.0, fanduel=1.0, draftkings=1.0, betmgm=0.8,
              caesars=0.8, fanatics=0.8, espnbet=0.8, betrivers=0.7, hardrock=0.7)   # sharper books count more in the market mean
def market_mean(x, quotes, extra=()):                   # quotes=[(line, over, under[, book])]; extra=[(mean, weight)], e.g. a liquid Kalshi fit
    ms, ws = [], []
    for q in quotes:
        l, o, u = q[:3]; b = (q[3] if len(q) > 3 else '').lower().replace(' ', '')
        ms.append(mkt_mean(x, l, o, u)); ws.append(BOOK_W.get(b, 1.0)*(1.0 if u is not None else 0.5))
    for mean_, w in extra: ms.append(mean_); ws.append(w)
    return float(np.average(ms, weights=ws))
W_MODELS = 0.40     # outside-model average inside the logic mean
W_MKT = 0.40        # market weight in p_final (v1 used 0.25); autoresearch tunes it from logged bets with fit_blend()
W_MKT_CONS = 0.70   # the conservative check leans on the market
def logic_mean(ours, models): return ours if not models else (1-W_MODELS)*ours+W_MODELS*float(np.mean(models))
def at_mean(x, line, side, target): return p_hit(x, line, side, target/max(x.mean(), 1e-9))
def final_probs(x, line, side, quotes, models=(), extra=(), w_mkt=None):   # quotes=[(line, over, under[, book])], models=outside means
    w_mkt = W_MKT if w_mkt is None else w_mkt
    ours = float(x.mean()); lm = logic_mean(ours, list(models)); mm = market_mean(x, quotes, extra)
    o = lambda w: p_outcomes(x, line, side, ((1-w)*lm+w*mm)/max(ours, 1e-9))
    f = o(w_mkt)
    return dict(ours=round(ours, 2), logic=round(lm, 2), market=round(mm, 2), final_mean=round((1-w_mkt)*lm+w_mkt*mm, 2),
                p_logic=round(o(0)['win'], 3), p_final=round(f['win'], 3), p_push=round(f['push'], 3),
                p_cons=round(o(W_MKT_CONS)['win'], 3), p_mkt=round(o(1.0)['win'], 3))
def event_final(p_model, p_mkt, w=W_MKT): return (1-w)*p_model+w*p_mkt   # double-doubles, triple-doubles
def compare_models(ours, sd, models, market):            # models={'SportsLine': 24.1, ...}; flags anything 0.35 SD or more from us
    rows = [(k, v, round((v-ours)/sd, 2)) for k, v in {**models, 'market': market}.items()]
    return sorted(rows, key=lambda t: -abs(t[2])), [k for k, v, z in rows if abs(z) >= 0.35]


# ---- same game: one shared draw so minutes, pace, margin and overtime correlate; teammates compete for shots and feed assists
def sim_game_players(players, g, n=40000, seed=11, rho=0.5):
    G = draw_game(g, n, seed); rng = G['rng']; u = [rng.normal(0, SIG_U, n) for _ in players]; uz = []
    for i, p in enumerate(players):
        mates = [u[j] for j, q in enumerate(players) if q.get('team', 'A') == p.get('team', 'A')]
        uz.append(np.exp(u[i]-rho*np.mean(mates, axis=0)-SIG_U**2/2) if len(mates) > 1 else np.exp(u[i]-SIG_U**2/2))
    sims = [sim_player(p, g, G, uz=uz[i]) for i, p in enumerate(players)]
    for i, p in enumerate(players):                      # each assist rides on a teammate's make
        mates = [j for j, q in enumerate(players) if j != i and q.get('team', 'A') == p.get('team', 'A')]
        if not mates: continue
        dev = sum(sims[j]['FGM']-sims[j]['FGM'].mean() for j in mates)
        mult = np.clip(1+ASSIST_LINK*dev/max(g.get('team_fgm', TEAM_FGM)-sims[i]['FGM'].mean(), 10.0), 0.3, 3.0)
        lam = sims[i]['_lam_ast']; phi = max(PHI['ast']-float(lam.mean()*mult.var()), 1.0)   # keep his assist variance at the fitted level
        sims[i]['AST'] = cnt(lam*mult, phi, rng); _combos(sims[i], rng)
    return sims
def leg_hits(S, stat, line, side='over'): return (S[stat] > line) if side == 'over' else (S[stat] < line)
def sgp(players, g, legs, n=40000, seed=11, rho=0.5):    # legs=[(player_index, stat, line, side)]
    sims = sim_game_players(players, g, n, seed, rho)
    hits = [leg_hits(sims[i], s, l, sd) for i, s, l, sd in legs]
    joint = float(np.mean(np.all(hits, axis=0))); indep = float(np.prod([h.mean() for h in hits]))
    return dict(joint=round(joint, 3), independent=round(indep, 3), lift=round(joint/max(indep, 1e-9), 3))


# ---- inputs: hit rates, team budget
def hit_rate(values, line, side='over'):
    v = np.array(values, float); return round(float(((v > line) if side == 'over' else (v < line)).mean()), 2), len(v)
def team_budget(proj_pts, implied_team_total): s = float(sum(proj_pts)); return round(s, 1), round(s-implied_team_total, 1)


# ---- red-capable checks and trap flags
TOO_FAR = dict(PTS=3.5, REB=1.8, AST=1.6, FG3M=0.8, PRA=4.5, PR=3.5, PA=3.5, RA=2.5, STL=0.5, BLK=0.5, TOV=0.7)
def sanity(S, p, g, stat=None, market=None):
    fl = []; m = float(S['MIN'].mean()); pf = (g.get('poss') or poss(g['total']))/p.get('team_poss', g.get('team_poss', 99))
    if m > 40.5: fl.append(f'minutes {m:.1f}: check role and blowout inputs')
    if m < 12: fl.append(f'minutes {m:.1f}: low-minute prop, unders may be restricted')
    if not 0.92 <= pf <= 1.08: fl.append(f'pace factor {pf:.2f}: check total and team_poss')
    if stat and market is not None and abs(S[stat].mean()-market) > TOO_FAR.get(stat, 1e9):
        fl.append(f'{stat}: ours {S[stat].mean():.1f} vs market {market:.1f}: find the reason or treat it as a model error')
    return fl
def trap_flags(t):                                       # t: dict of facts; returns failed tests
    f = []; side = t.get('side', 'over')
    if t.get('l3') and t.get('season') and t['l3'] >= 1.25*t['season'] and side == 'over': f.append('recency: last 3 games far above season')
    if side == 'over' and t.get('role') in ('star', 'starter') and t.get('exp_margin', 0) >= 10: f.append('blowout: big favorite starter over')
    if t.get('move_against', 0) >= t.get('move_tol', 1.0) and not t.get('news'): f.append('steam against us with no news')
    if t.get('status') in ('Q', 'GTD', 'Doubtful') or t.get('cap'): f.append('minutes risk: status or restriction')
    if t.get('stat') == 'FG3M' and side == 'over' and t.get('exp_3pa', 9) < 6: f.append('threes over on low volume')
    if t.get('public_pct', 0) >= 65 and t.get('public_side') == side and t.get('line_moved_with_public') is False: f.append('public side, line not moving with it')
    if t.get('dvp_only'): f.append('defense-vs-position split only, no play-type or archetype support')
    if t.get('usage_line_move', 0) > t.get('usage_fair_move', 1e9) and side == 'over': f.append('usage overreaction: line moved more than the fitted bump')
    return f


# ---- score (logic first; price never enters)
def hit_pts(p): return 2 if p >= 0.60 else 1 if p >= 0.55 else 0
CAPS = dict(status_unresolved=4, refuted_claim=3, two_trap_fails=4, minutes_restriction=5, low_minutes=5, script_fragile=5,
            low_3pa=5, unverified_claim=5, too_far_no_news=5, early_season_role=6)
def score(p, minutes_role, matchup_volume, script_pts, models_market, context, p_cons=None, caps=(), duplicate=False):
    s = hit_pts(p)+minutes_role+matchup_volume+script_pts+models_market+context-int(duplicate)
    cap = min([10]+[CAPS.get(c, c) if isinstance(c, str) else c for c in caps])
    if p < 0.50: cap = min(cap, 3)
    elif p < 0.55: cap = min(cap, 4)
    if p_cons is not None and p_cons < 0.50: cap = min(cap, 5)
    return max(0, min(s, cap))
def verdict(s): return ('STRONG TAKE', 1.5) if s >= 8 else ('TAKE', 1.0) if s >= 6 else ('TAKE SMALL', 0.5) if s == 5 else ('WATCH', 0) if s == 4 else ('PASS', 0)


# ---- profit layer: the price decides whether a scored bet is worth placing and how big
REQUIRE_EDGE = True   # a straight needs p_final at least MIN_EDGE above breakeven and p_cons at or above breakeven
MIN_EDGE = 0.02
KELLY_FRAC = 0.25     # quarter Kelly caps the score-based stake
def profit_gate(p_final, p_cons, price, p_push=0.0, min_edge=MIN_EDGE):
    be = breakeven(price, p_push)
    return dict(breakeven=round(be, 3), edge=round(p_final-be, 3), cons_edge=round(p_cons-be, 3),
                ok=bool(p_final-be >= min_edge and p_cons >= be))
def bet_to(p, p_push=0.0, min_edge=MIN_EDGE):           # the shortest price that still clears the gate ("bet to -135")
    q = p-min_edge; return None if q <= 0 else american((1-p_push)/q) if q < 1-p_push else None
def kelly(p, price, p_push=0.0): b = dec(price)-1; return max((b*p-(1-p-p_push))/b, 0.0)
def stake_units(score_, p, price, bankroll_units, p_push=0.0, frac=KELLY_FRAC):
    """Score-based stake (verdict) capped by fractional Kelly on the bankroll, in 0.25u steps."""
    base = verdict(score_)[1]; k = frac*kelly(p, price, p_push)*bankroll_units; s = min(base, k)
    if base == 0 or k < 0.125: return 0.0
    return max(0.25, float(np.floor(s*4)/4))
def best_offer(x, side, offers, c=1.0):                  # offers=[(book, line, price)]; c = final mean / simulated mean
    rows = []
    for book, line, price in offers:
        o = p_outcomes(x, line, side, c)
        rows.append(dict(book=book, line=line, price=price, p=round(o['win'], 3), push=round(o['push'], 3),
                         ev=round(ev(o['win'], price, o['push']), 4), edge=round(edge(o['win'], price, o['push']), 3),
                         straight_ok=straight_ok(price)))
    return sorted(rows, key=lambda r: -r['ev'])


# ---- tracking, calibration, autoresearch
def brier(p, y): p, y = np.asarray(p, float), np.asarray(y, float); return float(((p-y)**2).mean())
def logloss(p, y):
    p = np.clip(np.asarray(p, float), 1e-4, 1-1e-4); y = np.asarray(y, float); return float(-(y*np.log(p)+(1-y)*np.log(1-p)).mean())
def calib(p, y, edges=(0.5, 0.55, 0.6, 0.65, 1.01)):
    p, y = np.asarray(p, float), np.asarray(y, float); out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi)
        if m.any(): out.append((f'{lo:.2f}-{hi:.2f}', int(m.sum()), round(float(p[m].mean()), 3), round(float(y[m].mean()), 3)))
    return out
def clv(price_taken, close_over, close_under, side='over'):      # same line: closing fair prob x taken payout - 1
    q = devig([close_over, close_under])[0 if side == 'over' else 1]; return round(q*dec(price_taken)-1, 4)
def fit_blend(rows, grid=np.linspace(0, 1, 21)):         # rows: settled picks with p_logic, p_mkt, y; log loss by market weight
    pl = np.array([r['p_logic'] for r in rows]); pm = np.array([r['p_mkt'] for r in rows]); y = np.array([r['y'] for r in rows])
    res = [(round(float(w), 2), round(logloss((1-w)*pl+w*pm, y), 4)) for w in grid]
    return min(res, key=lambda t: t[1]), res
def replay(row, **over):                                 # re-run a logged pick with changed settings; row holds p, g, stat, line, side, quotes, models
    saved = {k: globals()[k] for k in over}; globals().update(over)
    try:
        S = sim_player(row['p'], row['g']); return final_probs(S[row['stat']], row['line'], row['side'], row['quotes'], row.get('models', ()))
    finally: globals().update(saved)
def autoresearch(rows, experiments, holdout=0.3, min_gain=0.002):
    # rows: settled picks in date order, each with y (1 win, 0 loss) and p_final; experiments: name -> function(row) -> new p
    ys = np.array([r['y'] for r in rows], float); cut = int(len(rows)*(1-holdout)); res = []
    base = np.array([r['p_final'] for r in rows]); b_tr, b_te = logloss(base[:cut], ys[:cut]), logloss(base[cut:], ys[cut:])
    res.append(('baseline', round(b_te, 4), 0.0, 'keep'))
    for name, fn in experiments.items():
        pe = np.array([fn(r) for r in rows]); tr, te = logloss(pe[:cut], ys[:cut]), logloss(pe[cut:], ys[cut:])
        keep = (b_te-te) >= min_gain and tr <= b_tr                       # must help on held-out picks and not hurt the rest
        res.append((name, round(te, 4), round(b_te-te, 4), 'keep' if keep else 'discard'))
    return res


# ---- exchange ladders (Kalshi): market-implied distribution from "N+" prices
def kalshi_mid(bid, ask): return (bid+ask)/2
def kalshi_weight(bid, ask, volume=0):                   # tight, traded markets count; wide or empty ones don't
    s = ask-bid; return 0.0 if s > 0.10 else (1.0 if s <= 0.03 and volume >= 500 else 0.5)
def fit_ladder(x, ladder, w=None):                       # ladder={k: P(k+)}; scales our distribution's shape to the market's ladder
    w = w or {k: 1.0 for k in ladder}; ks = [k for k in ladder if w.get(k, 0) > 0]
    if not ks: return None
    cs = np.linspace(0.5, 2.0, 151); err = [sum(w[k]*(p_hit(x, k-0.5, 'over', c)-ladder[k])**2 for k in ks) for c in cs]
    c = float(cs[int(np.argmin(err))])
    return dict(mean=round(float(x.mean()*c), 2), scale=round(c, 3), fit={k: round(p_hit(x, k-0.5, 'over', c), 3) for k in ks})


# ---- forecasting discipline: sensitivity and market distance
def sensitivity(p, g, stat, line, side='over', dmin=3.0, dposs=3.0, dspread=5.0, n=20000):   # how fragile is the chance to hit?
    pe = g.get('poss') or poss(g['total']); out = {'base': round(p_hit(sim_player(p, g, n=n)[stat], line, side), 3)}
    for lab, pp, gg in ((f'min -{dmin:g}', {**p, 'min': p['min']-dmin}, g), (f'min +{dmin:g}', {**p, 'min': p['min']+dmin}, g),
                        (f'poss -{dposs:g}', p, {**g, 'poss': pe-dposs}), (f'poss +{dposs:g}', p, {**g, 'poss': pe+dposs}),
                        (f'margin -{dspread:g}', p, {**g, 'exp_margin': g['exp_margin']-dspread}), (f'margin +{dspread:g}', p, {**g, 'exp_margin': g['exp_margin']+dspread})):
        out[lab] = round(p_hit(sim_player(pp, gg, n=n)[stat], line, side), 3)
    return out
def market_guard(p_final, p_mkt, gap=0.12): return abs(p_final-p_mkt) > gap   # True = needs a sourced reason or shrink toward the market


# ---- slate scan, ranking and the straight-bet card
def screen(props, n=6000):                               # quick pass over every posted prop; deep research goes to the top of this list
    rows = []
    for r in props:
        S = sim_player(r['p'], r['g'], n=n); ph = p_hit(S[r['stat']], r['line'], r['side'])
        pm = devig([r['over'], r['under']])[0 if r['side'] == 'over' else 1] if r.get('over') is not None and r.get('under') is not None else None
        price = r.get('over' if r['side'] == 'over' else 'under')
        rows.append(dict(id=r['id'], p_quick=round(ph, 3), p_mkt=None if pm is None else round(float(pm), 3),
                         gap=round(ph-(0.5 if pm is None else pm), 3), edge=None if price is None else round(edge(ph, price), 3)))
    return sorted(rows, key=lambda t: -t['gap'])
MAX_STRAIGHT_PRICE = -190   # straights must be priced -190 or better (Oct 22, 2026); parlay legs are exempt
def straight_ok(price, cap=MAX_STRAIGHT_PRICE): return price is not None and (price > 0 or price >= cap)   # -190, -150, +120 pass; -195, -250 fail
def est_price(p_mkt, hold=0.05): return american(1/min(p_mkt+hold, 0.97))   # no screenshot: book-style price from the market's chance
def price_note(price, est=False, cap=MAX_STRAIGHT_PRICE, near=15):   # the card's price check for one straight
    if price is None: return 'price not found: estimate it with est_price() before the bet goes on the card'
    if not straight_ok(price, cap): return f'{price:+d} is past {cap}: not a straight, use the fallback number or keep it as a parlay leg'
    if est and price < 0 and price <= cap+near: return f'about {price:+d}: place only if the app shows {cap} or better'
    return ''
def best_straight_line(x, side, line_prices, cap=MAX_STRAIGHT_PRICE, c=1.0, min_edge=None):
    """The safest number priced at the cap or better; with min_edge set, only numbers that also clear the profit gate."""
    ok = {}
    for l, pr in line_prices.items():
        if not straight_ok(pr, cap): continue
        o = p_outcomes(x, l, side, c)
        if min_edge is not None and edge(o['win'], pr, o['push']) < min_edge: continue
        ok[l] = (pr, o['win'])
    if not ok: return None
    l = max(ok, key=lambda k: ok[k][1]); return dict(line=l, price=ok[l][0], p_sim=round(ok[l][1], 3))
def pick_top(cands, n, max_per_game=2, max_per_player=1, cap=MAX_STRAIGHT_PRICE, require_edge=None):
    # cands: id, player, game, script, score, p, p_cons, fit, price (posted or est_price()), optional p_push
    require_edge = REQUIRE_EDGE if require_edge is None else require_edge
    gate = lambda c: profit_gate(c['p'], c.get('p_cons', c['p']), c['price'], c.get('p_push', 0.0))
    left = [{**c, 'gate': gate(c)} for c in cands if straight_ok(c.get('price'), cap)]
    if require_edge: left = [c for c in left if c['gate']['ok']]
    chosen = []; pg = Counter(); pp = Counter(); used = set()
    while left and len(chosen) < n:
        eff = lambda c: c['score']-(1 if (c['game'], c.get('script')) in used else 0)
        left.sort(key=lambda c: (-eff(c), -c['p'], -c.get('p_cons', 0), -c.get('fit', 0)))
        c = left.pop(0)
        if eff(c) < 5 or c['p'] < 0.55: break
        if pg[c['game']] >= max_per_game or pp[c['player']] >= max_per_player: continue
        chosen.append({**c, 'eff_score': eff(c)}); pg[c['game']] += 1; pp[c['player']] += 1; used.add((c['game'], c.get('script')))
    return chosen


# ---- parlays: pricing, house edge, correlation and the two-parlay builder
def parlay_dec(prices): return float(np.prod([dec(a) for a in prices]))
def parlay_price(prices): return american(parlay_dec(prices))
def parlay_ev(p_joint, price): return round(p_joint*dec(price)-1, 4)
def house_edge(fair_ps, prices): return round(1-float(np.prod([q*dec(a) for q, a in zip(fair_ps, prices)])), 4)
def implied_lift(sgp_price, leg_ps): return round((1/dec(sgp_price))/float(np.prod(leg_ps)), 3)   # correlation the book charges for (vs our sgp() lift)
def round_robin(ps, prices, size):                       # independent legs: every combo of `size`, 1 unit each
    n = len(ps); combos = list(itertools.combinations(range(n), size)); ret = 0.0; p_any = 0.0
    for out in itertools.product([0, 1], repeat=n):
        pr = float(np.prod([ps[i] if o else 1-ps[i] for i, o in enumerate(out)]))
        won = [c for c in combos if all(out[i] for i in c)]
        ret += pr*sum(parlay_dec([prices[i] for i in c]) for c in won); p_any += pr*(len(won) > 0)
    return dict(tickets=len(combos), p_any_win=round(p_any, 3), exp_return=round(ret/len(combos)-1, 4))
def joint_prob(legs):                                    # p_final per leg; same-game legs get the correlation lift from their shared simulation
    by = defaultdict(list); out = 1.0; lifts = {}
    for L in legs: by[L['game']].append(L)
    for gm, Ls in by.items():
        base = float(np.prod([L['p'] for L in Ls]))
        if len(Ls) > 1:
            H = float(np.all([L['hits'] for L in Ls], axis=0).mean()); ind = float(np.prod([L['hits'].mean() for L in Ls])); lift = H/max(ind, 1e-9)
        else: lift = 1.0
        out *= min(base*lift, min(L['p'] for L in Ls)); lifts[gm] = round(lift, 3)
    return out, lifts
def parlay_ok(legs, max_per_game):
    pl = Counter((L['player'], L['side']) for L in legs)
    if any(L['side'] == 'under' and pl[(L['player'], 'under')] > 1 for L in legs): return False   # same-player multi-unders are restricted
    if len({(L['player'], L['stat']) for L in legs}) < len(legs): return False                    # one line per player-stat
    if any(c > max_per_game for c in Counter(L['game'] for L in legs).values()): return False
    return len({L['player'] for L in legs if L['side'] == 'over'} & {L['player'] for L in legs if L['side'] == 'under'}) == 0
PARLAY = dict(safe=dict(legs=(2, 3), min_p=0.62, min_score=6, max_per_game=1, min_price=100, max_price=400, min_ev=0.0, leg_ev=-0.03),
              risky=dict(legs=(3, 5), min_p=0.55, min_score=5, max_per_game=2, min_price=450, max_price=1500, min_ev=0.0, leg_ev=-0.03))
def build_parlays(legs, kind='safe', top=3, relax=True, **over):   # legs: id, player, game, stat, side, p, score, price, hits (shared-game bool array)
    c = {**PARLAY[kind], **over}; res = _search(legs, c, kind, top)
    while relax and not res and round(c['min_p']-0.02, 2) >= 0.56:  # loosen in small steps, never below a 5-score, 56% leg
        c = {**c, 'min_p': round(c['min_p']-0.02, 2), 'min_score': max(5, c['min_score']-1)}; res = _search(legs, c, kind, top)
    for r in res: r['level'] = f"legs {c['min_p']:.0%}+ and score {c['min_score']}+"
    return res
def _search(legs, c, kind, top):
    pool = [L for L in legs if L['p'] >= c['min_p'] and L['score'] >= c['min_score'] and ev(L['p'], L['price']) >= c['leg_ev']]; out = []
    for k in range(c['legs'][0], c['legs'][1]+1):
        for combo in itertools.combinations(pool, k):
            if not parlay_ok(combo, c['max_per_game']): continue
            price = parlay_price([L['price'] for L in combo])
            if price < c['min_price'] or price > c['max_price']: continue
            j, lifts = joint_prob(combo)
            if any(v < 0.98 for v in lifts.values()): continue          # never pair same-game legs that work against each other
            if parlay_ev(j, price) < c['min_ev']: continue              # a parlay must be +EV on our joint chance
            out.append(dict(kind=kind, legs=[L['id'] for L in combo], joint=round(j, 3), price=price, fair=american(1/j), lifts=lifts,
                            sgp=any(v != 1.0 for v in lifts.values()), weakest=min(combo, key=lambda L: L['p'])['id'], ev=parlay_ev(j, price)))
    return sorted(out, key=lambda r: (-r['joint'], -r['price']))[:top]
