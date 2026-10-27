"""The v1 engine, copied verbatim from the original SKILL.md (Step 9), kept only so the backtest can compare old and new constants."""
import numpy as np, json, itertools
from collections import Counter, defaultdict
from scipy.stats import norm
from scipy.optimize import brentq
SIG = 12.0      # SD of the NBA final margin around the spread (Winston, about 12)
LG_PPP = 1.15   # league points per possession; refresh from league ORtg/100 each month
PHI = dict(fta=1.3, reb=1.0, ast=1.0, stl=1.0, blk=1.1, tov=1.0)  # variance/mean given minutes, pace and usage (<1 = steadier than Poisson)
SIG_U = 0.10   # game-to-game usage shock on shot volume (shared logic with same-game parlays)
KAPPA = dict(p2=150, p3=100, ft=150, mix=60)   # game-to-game noise in shooting % and 3PA share (Beta concentration)
ROLE = dict(star=dict(msd=2.2, cut25=7.0, close=1.5, phi_fga=0.35), starter=dict(msd=2.6, cut25=7.0, close=0.8, phi_fga=0.5),
            rotation=dict(msd=4.0, cut25=0.0, close=-0.5, phi_fga=0.7), bench=dict(msd=4.5, cut25=-5.0, close=-1.0, phi_fga=0.9))
# cut25 = minutes lost at a 25-point final margin (negative = minutes gained); close = minutes added when |margin| <= 5
BUCKETS = ((-99, -17.5, 'blowout loss'), (-17.5, -7.5, 'comfortable loss'), (-7.5, 7.5, 'close'),
           (7.5, 17.5, 'comfortable win'), (17.5, 99, 'blowout win'))
# ---- odds
def dec(a): return 1 + (a/100 if a > 0 else 100/-a)
def imp(a): return 1/dec(a)
def american(d): return int(round((d-1)*100)) if d >= 2 else int(round(-100/(d-1)))
def devig(prices, method='power'):                    # all outcomes of one market -> fair probabilities
    q = np.array([imp(a) for a in prices])
    if method == 'mult': return q/q.sum()
    k = brentq(lambda k: (q**k).sum()-1, 0.2, 5.0); return q**k
def one_way_fair(price, margin=0.08): return imp(price)/(1+margin)   # alt ladder or one-sided price
def ev(p, price): return p*(dec(price)-1)-(1-p)
def ev_line(p, price): e = ev(p, price); return f"EV {e*100:+.1f}% at {price:+d} ({'+EV' if e > 0 else '-EV'})"
# ---- game script
def p_ot(exp_margin): return float(np.clip(2.1*norm.pdf(exp_margin, 0, SIG), 0, 0.09))   # about 6% league-wide
def poss(total, ortg_a=None, drtg_a=None, ortg_b=None, drtg_b=None, lg=None):
    if None in (ortg_a, drtg_a, ortg_b, drtg_b): return total/(2*LG_PPP)
    lg = lg or 100*LG_PPP; pa = (ortg_a+drtg_b-lg)/100; pb = (ortg_b+drtg_a-lg)/100
    return total/(pa+pb)
def script_probs(exp_margin):                          # final-margin buckets for team A (exp_margin = -spread)
    po = p_ot(exp_margin); out = {n: (1-po)*(norm.cdf(h, exp_margin, SIG)-norm.cdf(l, exp_margin, SIG)) for l, h, n in BUCKETS}
    out['overtime'] = po; return {k: round(v, 3) for k, v in out.items()}
def draw_game(g, n=40000, seed=11):                    # shared draws for every player in one game (team A view)
    rng = np.random.default_rng(seed); ot = rng.random(n) < p_ot(g['exp_margin'])
    M = np.where(ot, rng.normal(0, 4, n), rng.normal(g['exp_margin'], SIG, n))
    pe = g.get('poss') or poss(g['total']); P = rng.normal(pe, 3.5, n)
    return dict(rng=rng, n=n, ot=ot, M=M, P=P)
def bucket(M, ot):
    lab = np.select([M <= -17.5, M <= -7.5, M < 7.5, M < 17.5], [b[2] for b in BUCKETS[:4]], 'blowout win')
    return np.where(ot, 'overtime', lab)
# ---- one player
def cnt(mu, phi, rng):                                 # count with variance = phi*mean: binomial if phi<1, Poisson if 1, neg. binomial if >1
    mu = np.maximum(mu, 1e-9)
    if phi < 0.999:
        N = np.ceil(mu/(1-phi)).astype(int); return rng.binomial(N, mu/N)
    if phi <= 1.001: return rng.poisson(mu)
    r = mu/(phi-1); return rng.negative_binomial(r, r/(r+mu))
def bdraw(m, k, n, rng): return rng.beta(m*k, (1-m)*k, n)
def minutes(p, G):
    rng, n, ot = G['rng'], G['n'], G['ot']; r = ROLE[p['role']]
    M = G['M']*(1 if p.get('team', 'A') == 'A' else -1); a = np.abs(M)
    m = p['min'] - r['cut25']*np.clip((a-11)/14, 0, 1.6) + r['close']*(a <= 5) + rng.normal(0, np.hypot(r['msd'], p.get('min_sd_extra', 0.0)), n)
    big = p['role'] in ('star', 'starter')
    m = m + ot*np.where(big, rng.uniform(3.5, 5.0, n), rng.uniform(0, 1.5, n))
    pf = np.clip(0.02+0.05*(p.get('pf36', 3.0)-3.0), 0, 0.25)            # foul trouble
    m = m - (rng.random(n) < pf)*rng.uniform(3, 9, n)
    ex = rng.random(n) < p.get('p_exit', 0.008)                         # early exit: the bet still stands
    m = np.where(ex, m*rng.uniform(0.05, 0.8, n), m)
    return np.clip(m, 0, p.get('cap') or 53)
def calibrate_min(p, g, close_minutes, n=20000):         # set p['min'] so simulated minutes in games decided by under 10 match his real average there
    for _ in range(3):
        S = sim_player(p, g, n=n); mk = np.abs(S['M']) < 10
        p['min'] += close_minutes-float(S['MIN'][mk].mean())
    return round(p['min'], 1)
def sim_player(p, g, G=None, n=40000, seed=11, uz=None):
    # p: role, min (minutes in a normal competitive game), r36 per-36 rates (fga, fta, reb, ast, stl, blk, tov), s3 (3PA share of FGA),
    #    pct (p2, p3, ft), adj multipliers by r36 key, team 'A'/'B', team_poss, pf36, cap, q1_min, p_exit, rate_cv, min_sd_extra
    G = G or draw_game(g, n, seed); rng, n = G['rng'], G['n']; mins = minutes(p, G)
    f = G['P']/p.get('team_poss', g.get('team_poss', G['P'].mean()))
    uz = rng.lognormal(0, SIG_U, n) if uz is None else uz
    rc = p.get('rate_cv', 0.05)                                          # uncertainty in his true rates: 0.04 settled role, 0.08 10-20 games, 0.12 new role
    U = {k: rng.lognormal(-rc**2/2, rc, n) for k in ('vol', 'reb', 'ast')} if rc > 0 else defaultdict(lambda: 1.0)
    grp = dict(fga='vol', fta='vol', reb='reb', ast='ast', stl='vol', blk='reb', tov='vol')
    lam = lambda k: p['r36'][k]*p.get('adj', {}).get(k, 1.0)*mins/36*f*U[grp[k]]
    T = cnt(lam('fga')*uz, p.get('phi_fga', ROLE[p['role']]['phi_fga']), rng); fa = cnt(lam('fta')*uz, PHI['fta'], rng)
    a3 = rng.binomial(T, bdraw(p['s3'], KAPPA['mix'], n, rng)); a2 = T-a3
    m2 = rng.binomial(a2, bdraw(p['pct']['p2'], KAPPA['p2'], n, rng))
    m3 = rng.binomial(a3, bdraw(p['pct']['p3'], KAPPA['p3'], n, rng))
    mf = rng.binomial(fa, bdraw(p['pct']['ft'], KAPPA['ft'], n, rng))
    S = dict(MIN=mins, PTS=2*m2+3*m3+mf, FG3M=m3, FG3A=a3, FGA=T, FTM=mf, FGM=m2+m3)
    for k, K in (('reb', 'REB'), ('ast', 'AST'), ('stl', 'STL'), ('blk', 'BLK'), ('tov', 'TOV')): S[K] = cnt(lam(k), PHI[k], rng)
    S.update(PRA=S['PTS']+S['REB']+S['AST'], PR=S['PTS']+S['REB'], PA=S['PTS']+S['AST'], RA=S['REB']+S['AST'], STOCKS=S['STL']+S['BLK'])
    ten = (np.vstack([S['PTS'], S['REB'], S['AST'], S['STL'], S['BLK']]) >= 10).sum(0)
    S['DD'], S['TD'] = (ten >= 2).astype(float), (ten >= 3).astype(float)
    q1 = np.clip(rng.normal(p.get('q1_min', 9.0), 1.2, n), 0, 12); sh = np.clip(q1/np.maximum(mins, 1e-6), 0, 1)
    S['Q1_PTS'] = 2*rng.binomial(m2, sh)+3*rng.binomial(m3, sh)+rng.binomial(mf, sh)
    S['Q1_REB'], S['Q1_AST'] = rng.binomial(S['REB'], sh), rng.binomial(S['AST'], sh)
    S['M'] = G['M']*(1 if p.get('team', 'A') == 'A' else -1); S['OT'] = G['ot']
    return S
# ---- probabilities, scripts, market
def p_hit(x, line, side='over', c=1.0):                # integer stats, half-point lines; c rescales the distribution smoothly
    po = float(np.clip(x+0.5-line/c, 0, 1).mean()); return po if side == 'over' else 1-po
def ladder(S, stat, ks): return {k: round(float((S[stat] >= k).mean()), 3) for k in ks}   # P(k+) for alt milestones
def bet_zones(x, levels=(0.55, 0.60)):                 # no posted line yet: the lines where each side reaches 55% and 60%
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
def _scale_for(x, line, q, side):
    lo, hi = 0.2, 4.0
    for _ in range(50):
        c = (lo+hi)/2; pv = p_hit(x, line, side, c)
        if (pv < q) == (side == 'over'): lo = c
        else: hi = c
    return (lo+hi)/2
def mkt_mean(x, line, over_price, under_price=None, method='power'):   # market-implied mean, using our distribution's shape
    q = devig([over_price, under_price], method)[0] if under_price is not None else one_way_fair(over_price)
    return float(x.mean()*_scale_for(x, line, q, 'over'))
def logic_mean(ours, models): return ours if not models else 0.6*ours+0.4*float(np.mean(models))
def at_mean(x, line, side, target): return p_hit(x, line, side, target/max(x.mean(), 1e-9))
def final_probs(x, line, side, quotes, models=()):      # quotes=[(line, over_price, under_price)], models=outside projections (means)
    ours = float(x.mean()); lm = logic_mean(ours, list(models))
    mm = float(np.mean([mkt_mean(x, l, o, u) for l, o, u in quotes]))
    pf = lambda w: round(at_mean(x, line, side, (1-w)*lm+w*mm), 3)
    return dict(ours=round(ours, 2), logic=round(lm, 2), market=round(mm, 2), p_logic=pf(0), p_final=pf(0.25), p_cons=pf(0.5), p_mkt=pf(1.0))
def event_final(p_model, p_mkt, w=0.25): return (1-w)*p_model+w*p_mkt   # double-doubles, triple-doubles
def compare_models(ours, sd, models, market):           # models={'SportsLine': 24.1, ...}; flags anything 0.35 SD or more from us
    rows = [(k, v, round((v-ours)/sd, 2)) for k, v in {**models, 'market': market}.items()]
    return sorted(rows, key=lambda t: -abs(t[2])), [k for k, v, z in rows if abs(z) >= 0.35]
# ---- same-game parlays: one shared game draw so minutes, pace, margin and OT correlate legs
def sim_game_players(players, g, n=40000, seed=11, rho=0.5):   # every player in one game from one shared draw (teammates compete for shots)
    G = draw_game(g, n, seed); rng = G['rng']; u = [rng.normal(0, SIG_U, n) for _ in players]; uz = []
    for i, p in enumerate(players):
        mates = [u[j] for j, q in enumerate(players) if q.get('team', 'A') == p.get('team', 'A')]
        uz.append(np.exp(u[i]-rho*np.mean(mates, axis=0)) if len(mates) > 1 else np.exp(u[i]))
    return [sim_player(p, g, G, uz=uz[i]) for i, p in enumerate(players)]
def leg_hits(S, stat, line, side='over'): return (S[stat] > line) if side == 'over' else (S[stat] < line)
def sgp(players, g, legs, n=40000, seed=11, rho=0.5):   # legs=[(player_index, stat, line, side)]
    sims = sim_game_players(players, g, n, seed, rho)
    hits = [leg_hits(sims[i], s, l, sd) for i, s, l, sd in legs]
    joint = float(np.mean(np.all(hits, axis=0))); indep = float(np.prod([h.mean() for h in hits]))
    return dict(joint=round(joint, 3), independent=round(indep, 3), lift=round(joint/max(indep, 1e-9), 3))
# ---- inputs: shrinkage, with/without, hit rates, team budget
STAB = dict(pts36=300, reb36=250, ast36=250, fg3a36=300, stl36=800, blk36=500, tov36=500, p3=750, p2=350, ft=200)  # minutes or attempts; starting values
def shrink(obs, n, prior, k): return (n*obs+k*prior)/(n+k)
def wowy_bump(with_avg, without_avg, n_without, k=8): return (without_avg-with_avg)*n_without/(n_without+k)
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
# ---- forecasting discipline: sensitivity, market distance, matchup and usage helpers
def sensitivity(p, g, stat, line, side='over', dmin=3.0, dposs=3.0, dspread=5.0, n=20000):   # how fragile is the chance to hit?
    pe = g.get('poss') or poss(g['total']); out = {'base': round(p_hit(sim_player(p, g, n=n)[stat], line, side), 3)}
    for lab, pp, gg in ((f'min -{dmin:g}', {**p, 'min': p['min']-dmin}, g), (f'min +{dmin:g}', {**p, 'min': p['min']+dmin}, g),
                        (f'poss -{dposs:g}', p, {**g, 'poss': pe-dposs}), (f'poss +{dposs:g}', p, {**g, 'poss': pe+dposs}),
                        (f'margin -{dspread:g}', p, {**g, 'exp_margin': g['exp_margin']-dspread}), (f'margin +{dspread:g}', p, {**g, 'exp_margin': g['exp_margin']+dspread})):
        out[lab] = round(p_hit(sim_player(pp, gg, n=n)[stat], line, side), 3)
    return out
def market_guard(p_final, p_mkt, gap=0.12): return abs(p_final-p_mkt) > gap   # True = needs a sourced reason or shrink toward the market
def matchup_adj(opp_allowed, league_avg, games, k=20, cap=0.15):            # regressed opponent multiplier for one stat
    return float(1+np.clip((opp_allowed/league_avg-1)*games/(games+k), -cap, cap))
def usage_bumps(out_fga, mates, repl_fga=0.0, keep=0.85, tilt=1.5):       # missing shots per game -> FGA multipliers for teammates (fga per game)
    pool = max(out_fga*keep-repl_fga, 0.0); wts = {k: v**tilt for k, v in mates.items()}; tw = sum(wts.values())
    return {k: round(1+pool*wts[k]/tw/max(v, 1e-9), 3) for k, v in mates.items()}
# ---- slate scan, ranking and the straight-bet card
def screen(props, n=6000):                               # quick pass over every posted prop; deep research goes to the top of this list
    rows = []
    for r in props:
        S = sim_player(r['p'], r['g'], n=n); ph = p_hit(S[r['stat']], r['line'], r['side'])
        pm = devig([r['over'], r['under']])[0 if r['side'] == 'over' else 1] if r.get('over') is not None and r.get('under') is not None else None
        rows.append(dict(id=r['id'], p_quick=round(ph, 3), p_mkt=None if pm is None else round(float(pm), 3), gap=round(ph-(0.5 if pm is None else pm), 3)))
    return sorted(rows, key=lambda t: -t['gap'])
MAX_STRAIGHT_PRICE = -190   # straights must be priced -190 or better (Oct 22, 2026); parlay legs are exempt
def straight_ok(price, cap=MAX_STRAIGHT_PRICE): return price is not None and (price > 0 or price >= cap)   # -190, -150, +120 pass; -195, -250 fail
def est_price(p_mkt, hold=0.05): return american(1/min(p_mkt+hold, 0.97))   # no screenshot: book-style price from the market's chance (alt ladders carry 0.05-0.08 hold)
def price_note(price, est=False, cap=MAX_STRAIGHT_PRICE, near=15):   # the card's price check for one straight
    if price is None: return 'price not found: estimate it with est_price() before the bet goes on the card'
    if not straight_ok(price, cap): return f'{price:+d} is past {cap}: not a straight, use the fallback number or keep it as a parlay leg'
    if est and price < 0 and price <= cap+near: return f'about {price:+d}: place only if the app shows {cap} or better'
    return ''
def best_straight_line(x, side, line_prices, cap=MAX_STRAIGHT_PRICE):   # line_prices={line: price} for one side; the safest number priced at the cap or better
    ok = {l: pr for l, pr in line_prices.items() if straight_ok(pr, cap)}
    if not ok: return None
    l = max(ok, key=lambda k: p_hit(x, k, side)); return dict(line=l, price=ok[l], p_sim=round(p_hit(x, l, side), 3))
def pick_top(cands, n, max_per_game=2, max_per_player=1, cap=MAX_STRAIGHT_PRICE):   # cands: id, player, game, script, score, p, p_cons, fit, price (posted or est_price())
    left = [c for c in cands if straight_ok(c.get('price'), cap)]; chosen = []; pg = Counter(); pp = Counter(); used = set()
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
def parlay_ev(p_joint, price): return round(p_joint*dec(price)-1, 4)     # information only
def house_edge(fair_ps, prices): return round(1-float(np.prod([q*dec(a) for q, a in zip(fair_ps, prices)])), 4)
def implied_lift(sgp_price, leg_ps): return round((1/dec(sgp_price))/float(np.prod(leg_ps)), 3)   # correlation the book charges for (vs our sgp() lift)
def round_robin(ps, prices, size):                     # independent legs: every combo of `size`, 1 unit each
    n = len(ps); combos = list(itertools.combinations(range(n), size)); ret = 0.0; p_any = 0.0
    for out in itertools.product([0, 1], repeat=n):
        pr = float(np.prod([ps[i] if o else 1-ps[i] for i, o in enumerate(out)]))
        won = [c for c in combos if all(out[i] for i in c)]
        ret += pr*sum(parlay_dec([prices[i] for i in c]) for c in won); p_any += pr*(len(won) > 0)
    return dict(tickets=len(combos), p_any_win=round(p_any, 3), exp_return=round(ret/len(combos)-1, 4))
def joint_prob(legs):                                   # p_final per leg; same-game legs get the correlation lift from their shared simulation
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
PARLAY = dict(safe=dict(legs=(2, 3), min_p=0.62, min_score=6, max_per_game=1, min_price=100, max_price=400),
              risky=dict(legs=(3, 5), min_p=0.55, min_score=5, max_per_game=2, min_price=450, max_price=1500))
def build_parlays(legs, kind='safe', top=3, relax=True, **over):   # legs: id, player, game, stat, side, p, score, price, hits (shared-game bool array)
    c = {**PARLAY[kind], **over}; res = _search(legs, c, kind, top)
    while relax and not res and round(c['min_p']-0.02, 2) >= 0.56:  # loosen in small steps, never below a 5-score, 56% leg
        c = {**c, 'min_p': round(c['min_p']-0.02, 2), 'min_score': max(5, c['min_score']-1)}; res = _search(legs, c, kind, top)
    for r in res: r['level'] = f"legs {c['min_p']:.0%}+ and score {c['min_score']}+"
    return res
def _search(legs, c, kind, top):
    pool = [L for L in legs if L['p'] >= c['min_p'] and L['score'] >= c['min_score']]; out = []
    for k in range(c['legs'][0], c['legs'][1]+1):
        for combo in itertools.combinations(pool, k):
            if not parlay_ok(combo, c['max_per_game']): continue
            price = parlay_price([L['price'] for L in combo])
            if price < c['min_price'] or price > c['max_price']: continue
            j, lifts = joint_prob(combo)
            if any(v < 0.98 for v in lifts.values()): continue          # never pair same-game legs that work against each other
            out.append(dict(kind=kind, legs=[L['id'] for L in combo], joint=round(j, 3), price=price, fair=american(1/j), lifts=lifts,
                            sgp=any(v != 1.0 for v in lifts.values()), weakest=min(combo, key=lambda L: L['p'])['id'], ev=parlay_ev(j, price)))
    return sorted(out, key=lambda r: (-r['joint'], -r['price']))[:top]
