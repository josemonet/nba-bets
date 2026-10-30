"""football_model.py from the sports-betting-research skill (Oct 23, 2026), copied verbatim as the NFL backtest baseline."""
# football_model.py: prices every CFB and NFL market for the sports-betting-research skill. Save it, import it, run it.
import numpy as np, itertools
from collections import Counter, defaultdict
from scipy.stats import norm, gamma, poisson
from scipy.optimize import brentq
# ---- key numbers, odds, de-vig
KEY_CFB = {1:.95,2:.95,3:2.4,4:1.15,5:.95,6:1.1,7:2.0,8:1.05,10:1.35,11:1.05,13:1.05,14:1.4,17:1.25,18:1.05,20:1.05,21:1.2,24:1.1,28:1.1}
KEY_NFL = {1:.73,2:.64,3:2.78,4:.98,5:.63,6:1.1,7:1.86,8:.69,9:.39,10:1.32,11:.57,12:.38,13:.66,14:1.36,16:.58,17:1.22,18:.57,20:.9,21:1.14,24:1.28}
def key_for(sport): return KEY_NFL if sport == 'nfl' else KEY_CFB
def dec(a): return 1+(a/100 if a > 0 else 100/-a)
def be(a): return 1/dec(a)                                   # break-even (implied) probability of a price
def american(d): return int(round((d-1)*100)) if d >= 2 else int(round(-100/(d-1)))
def nv(a, b): p, q = be(a), be(b); return p/(p+q)              # no-vig chance of side a (two-way, multiplicative)
def devig(prices, method='power'):                            # every outcome of one market -> fair probabilities
    q = np.array([be(a) for a in prices])
    if method == 'mult': return q/q.sum()
    k = brentq(lambda k: (q**k).sum()-1, 0.2, 5.0); return q**k
def one_way_fair(price, margin=0.06): return be(price)/(1+margin)   # one-sided price (alt ladder, milestone)
def ev(p, price, push=0.0): return p*(dec(price)-1)-(1-p-push)
def ev_line(p, price, push=0.0):                              # information only, never a gate
    e = ev(p, price, push); return f"EV {e*100:+.1f}% at {price:+d} ({'+EV' if e > 0 else '-EV'})"
# ---- full-game margin and total distributions (key-number weighted)
def msd(t, sport='cfb'): return 13.5 if sport == 'nfl' else min(max(0.25*t+2.5, 13.0), 16.5)   # margin SD
def tsd(t, sport='cfb'): return 13.0 if sport == 'nfl' else 0.24*t+3.5                           # game-total SD
def fpi(p, s=15.5): return s*norm.ppf(p)                     # win% -> margin (use msd(total) for s)
def mdist(mu, sd, sport='cfb'):
    ks = np.arange(-90, 91); ks = ks[ks != 0]; K = key_for(sport)
    w = norm.pdf(ks, mu, sd)*np.array([K.get(abs(k), 1.0) for k in ks]); return ks, w/w.sum()
def dmean(mu, sd, sport='cfb'): ks, w = mdist(mu, sd, sport); return float((ks*w).sum())
def mu_for_mean(m, sd, sport='cfb'): return brentq(lambda x: dmean(x, sd, sport)-m, m-25, m+25)
def mkt_mean(line, fav_p, dog_p, sd, sport='cfb'):           # one spread quote -> favorite's mean margin
    p = nv(fav_p, dog_p)
    def f(mu):
        ks, w = mdist(mu, sd, sport); pf = w[ks > line].sum(); pp = w[ks == line].sum(); return pf/(1-pp)-p
    return dmean(brentq(f, line-20, line+20), sd, sport)
def mkt_tot(line, po, pu, sport='cfb'):
    p = nv(po, pu); return brentq(lambda m: (1-norm.cdf((line-m)/tsd(m, sport)))-p, line-20, line+20)
def logic(research, models): return research if not models else 0.6*research+0.4*float(np.mean(models))
W = (0.25, 0.5, 1.0)   # market weight: final (logic-first), conservative check, market only (information)
def side(tot, quotes, logic_margin, bet, L, price, sport='cfb'):
    # quotes=[(fav_line, fav_price, dog_price)] with fav_line positive; logic_margin = favorite's margin; bet: fav|dog|favML|dogML
    sd = msd(tot, sport); mm = float(np.mean([mkt_mean(*q, sd, sport) for q in quotes])); out = []
    for w in W:
        ks, wt = mdist(mu_for_mean(w*mm+(1-w)*logic_margin, sd, sport), sd, sport)
        pf, pp = wt[ks > L].sum(), wt[ks == L].sum()
        p = {'fav': pf, 'dog': 1-pf-pp, 'favML': wt[ks > 0].sum(), 'dogML': wt[ks < 0].sum()}[bet]
        push = pp if bet in ('fav', 'dog') else 0.0
        out.append((w, round(float(p), 3), round(ev(p, price, push)*100, 1)))
    return round(mm, 2), out
def total(quotes, logic_total, line, price, under=True, sport='cfb'):   # quotes=[(line, over_price, under_price)]
    m = float(np.mean([mkt_tot(*q, sport) for q in quotes])); out = []
    for w in W:
        f = w*m+(1-w)*logic_total; pu = norm.cdf((line-f)/tsd(f, sport)); p = pu if under else 1-pu
        out.append((w, round(f, 1), round(float(p), 3), round(ev(p, price)*100, 1)))
    return round(m, 2), out
# ---- teasers and buying points (key numbers decide both)
def tease_leg(fav_margin, line, bet, pts=6.0, tot=45.0, sport='nfl'):
    # fav_margin = our favorite's mean margin; line = points laid (bet 'fav') or received (bet 'dog') before the tease
    sd = msd(tot, sport); ks, w = mdist(mu_for_mean(fav_margin, sd, sport), sd, sport)
    L = line-pts if bet == 'fav' else line+pts
    win = w[ks > L].sum() if bet == 'fav' else w[ks < L].sum(); push = w[ks == L].sum()
    return dict(teased_line=L, win=round(float(win), 3), push=round(float(push), 3))
def teaser(legs_p, price):                                    # independent games; legs_p = each leg's win chance
    pj = float(np.prod(legs_p)); d = dec(price); n = len(legs_p)
    return dict(joint=round(pj, 3), breakeven_leg=round((1/d)**(1/n), 3), ev=round(pj*d-1, 4))
def wong_ok(line, bet, sport='nfl'):                          # classic NFL 6-point candidates: legs that cross both 3 and 7
    return sport == 'nfl' and ((bet == 'fav' and 7.5 <= line <= 8.5) or (bet == 'dog' and 1.5 <= line <= 2.5))
def buy_points(fav_margin, bet, line_a, price_a, line_b, price_b, tot=45.0, sport='nfl'):
    # compare the same side at two numbers (e.g. +2.5 -110 vs +3 -125): win, push and EV at each
    sd = msd(tot, sport); ks, w = mdist(mu_for_mean(fav_margin, sd, sport), sd, sport); out = []
    for L, pr in ((line_a, price_a), (line_b, price_b)):
        win = w[ks > L].sum() if bet == 'fav' else w[ks < L].sum(); push = w[ks == L].sum()
        out.append(dict(line=L, price=pr, win=round(float(win), 3), push=round(float(push), 3), ev=round(ev(win, pr, push)*100, 1)))
    return out
# ---- research inputs: opponent adjustment, regression, QB changes
def opp_adjust(rows, kind='off', avg=26.5, hfa=1.5, cap=20.0):
    # rows: (points scored or allowed, opponent's SP+ defense or offense rating, home True/False); returns per-game values and mean
    out = []
    for pts, opp, home in rows:
        h = hfa if home else -hfa
        v = pts-opp+avg-h if kind == 'off' else pts-opp+avg+h
        out.append(float(np.clip(v, avg-cap, avg+cap)))
    return out, round(float(np.mean(out)), 2)
def reg_weight(games, week=None):                            # share to pull toward the prior (league average or last season)
    if games <= 3: return 0.65
    if week is not None and week >= 8: return 0.30
    return 0.50
def regress(x, games, prior, week=None): r = reg_weight(games, week); return x+r*(prior-x)
def shrink(obs, n, prior, k): return (n*obs+k*prior)/(n+k)
def qb_blend(new_qb_avg, n_new, season_avg, k=4.0): return shrink(new_qb_avg, n_new, season_avg, k)   # 2 starts -> one third new QB
def team_pts(drives, off_ppd, def_ppd_allowed, lg_ppd=2.1): return drives*off_ppd*def_ppd_allowed/lg_ppd
def unit_avg(xs, lg, r=0.5): return float(np.mean(xs))+r*(lg-float(np.mean(xs)))
def team_yards(off, de, home, adj_rush=0, adj_pass=0, r_off=0.5, r_def=0.5, r_def_pass=None, lg_rush=155, lg_pass=230):
    rp = r_def if r_def_pass is None else r_def_pass; h = 3 if home else -3
    rush = unit_avg(off['orush'], lg_rush, r_off)+unit_avg(de['drush'], lg_rush, r_def)-lg_rush+h+adj_rush
    pas = unit_avg(off['opass'], lg_pass, r_off)+unit_avg(de['dpass'], lg_pass, rp)-lg_pass+h+adj_pass
    return rush, pas, rush+pas
def yards_fair(ours, line, w=0.4): return (1-w)*ours+w*line
def line_to_mean(line, cv): k = 1/cv**2; return line*k/gamma.median(k)   # yardage lines sit near the median
def offense_reaches(off_avg_regressed, line, over=True): return off_avg_regressed > line if over else off_avg_regressed < line
def p_yards_over(mu, line, kind): return 1-norm.cdf(line, mu, {'rush': 50, 'pass': 65, 'total': 80}[kind])
def p_gamma(mean, cv, line, side='under'): k = 1/cv**2; pu = gamma.cdf(line, k, scale=mean/k); return pu if side == 'under' else 1-pu
def p_pois(lam, line, side='over'): pu = poisson.cdf(np.floor(line), lam); return pu if side == 'under' else 1-pu
def p_prop(p_model, p_market, w=0.25): return (1-w)*p_model+w*p_market
def hit_rate(values, line, over=True):
    v = np.array(values, float); return round(float(((v > line) if over else (v < line)).mean()), 2), len(v)
def stat_cap(must_beat_own_avg, rank, games, n_teams=136):
    cap = 10
    if must_beat_own_avg and rank is not None:
        if rank > 0.75*n_teams: cap = 4
        elif rank > n_teams*2/3: cap = 5
    if games <= 3: cap = min(cap, 5)
    return cap
def under_cap(needs_offense_below_own_avg, def_rank, n_teams=136):   # the under/team-total-under twin of stat_cap (Oct 16, 2026)
    return 5 if needs_offense_below_own_avg and (def_rank is None or def_rank > n_teams/3) else 10
def momentum(games): return [round(y/15+s, 1) for y, s in games]      # (yards margin, closing spread, negative when favored)
# ---- book-style models
def spread_from_ratings(r_home, r_away, hfa=2.5, neutral=False): return (r_home-r_away)+(0 if neutral else hfa)
def sp_points(off, opp_def, avg=26.5, hfa=1.5, home=True): return off+opp_def-avg+(hfa if home else -hfa)   # SP+ unit ratings -> points
def massey(games, teams, prior=None, ridge=0.5, cap=28, hfa=2.5):
    idx = {t: i for i, t in enumerate(teams)}; X = []; y = []
    for h, a, m, neu in games:
        r = np.zeros(len(teams)); r[idx[h]] = 1; r[idx[a]] = -1; X.append(r); y.append(np.clip(m-(0 if neu else hfa), -cap, cap))
    X = np.array(X); y = np.array(y, float); p0 = np.array([(prior or {}).get(t, 0.0) for t in teams])
    sol = np.linalg.solve(X.T@X+ridge*np.eye(len(teams)), X.T@y+ridge*p0); return {t: round(sol[idx[t]], 1) for t in teams}
def elo_prob(diff): return 1/(1+10**(-diff/400))
def elo_update(ra, rb, margin_a, home_a=0, hfa=55, k=20):
    d = ra-rb+hfa*home_a; win = 1.0 if margin_a > 0 else 0.0 if margin_a < 0 else 0.5
    mult = np.log(abs(margin_a)+1)*2.2/((d if margin_a > 0 else -d)*0.001+2.2); ch = k*mult*(win-elo_prob(d)); return ra+ch, rb-ch
def elo_spread(ra, rb, home_a=0, hfa=55): return (ra-rb+hfa*home_a)/25
def derivatives(spread_fav, total, sport='cfb'):              # rough book ratios used to hang derivative lines
    q1 = 0.21 if sport == 'nfl' else 0.23
    return {'1H_spread': round(spread_fav*0.55, 1), '1H_total': round(total*0.50, 1), '1Q_spread': round(spread_fav*0.28, 1),
            '1Q_total': round(total*q1, 1), 'fav_TT': round((total+spread_fav)/2, 1), 'dog_TT': round((total-spread_fav)/2, 1)}
def compare_models(ours, sd, models, market):                 # gaps in SD units; flag 0.35 SD or more
    rows = [(k, v, round((v-ours)/sd, 2)) for k, v in {**models, 'market': market}.items()]
    return sorted(rows, key=lambda t: -abs(t[2])), [k for k, v, z in rows if abs(z) >= 0.35]
# ---- exchanges (Kalshi, Polymarket via DeFi Rate): ladders -> market means
def kalshi_mid(bid, ask): return (bid+ask)/2
def kalshi_weight(bid, ask, volume=0): s = ask-bid; return 0.0 if s > 0.10 else (1.0 if s <= 0.03 and volume >= 500 else 0.5)
def fit_margin_ladder(ladder, tot, sport='cfb'):              # ladder={k: P(favorite wins by k or more)} -> favorite's mean margin
    sd = msd(tot, sport)
    def err(mu):
        ks, w = mdist(mu, sd, sport); return sum((w[ks >= k].sum()-p)**2 for k, p in ladder.items())
    mus = np.linspace(-30, 30, 601); mu = mus[int(np.argmin([err(m) for m in mus]))]; return round(dmean(mu, sd, sport), 2)
def fit_total_ladder(ladder, sport='cfb'):                    # ladder={line: P(over line)} -> mean total
    ts = np.linspace(20, 100, 801); e = [sum((1-norm.cdf((l-t)/tsd(t, sport))-p)**2 for l, p in ladder.items()) for t in ts]
    return round(float(ts[int(np.argmin(e))]), 1)
# ---- quarter and first-quarter helpers
def rates_for(target_pts, drives, fg=0.10, dtd_pts=0.4): return {'td': max(0.0, (target_pts-dtd_pts-3*fg*drives)/(6.96*drives)), 'fg': fg}
def price_game(S, spread_a=None, total=None, tt_a=None, tt_b=None, h1_spread_a=None, h1_total=None):
    # every game-level market from one sim_football() run (A = first team listed; spread_a = A's line, e.g. -3.5)
    A, B, G = S['A'], S['B'], S['game']; m, t = G['MARGIN'], G['TOTAL']; o = dict(A_pts=round(A['PTS'].mean(), 1), B_pts=round(B['PTS'].mean(), 1))
    o['A_win'] = round(float(((m > 0)+0.5*(m == 0)).mean()), 3)
    if spread_a is not None: o['A_cover'] = round(float((m+spread_a > 0).mean()), 3); o['push'] = round(float((m+spread_a == 0).mean()), 3)
    if total is not None: o['over'] = round(float((t > total).mean()), 3)
    if tt_a is not None: o['A_TT_over'] = round(float((A['PTS'] > tt_a).mean()), 3)
    if tt_b is not None: o['B_TT_over'] = round(float((B['PTS'] > tt_b).mean()), 3)
    h = G['H1_MARGIN']; o['1H_A_lead'] = round(float((h > 0).mean()), 3); o['1H_tie'] = round(float((h == 0).mean()), 3)
    if h1_spread_a is not None: o['1H_A_cover'] = round(float((h+h1_spread_a > 0).mean()), 3)
    if h1_total is not None: o['1H_over'] = round(float((G['H1_TOTAL'] > h1_total).mean()), 3)
    for q in range(4): o[f'Q{q+1}_tie'] = round(float((A['Q'][:, q] == B['Q'][:, q]).mean()), 3)
    o['1Q_total_mean'] = round(float(G['Q1_TOTAL'].mean()), 1); return o
def team1q(N, td, fg, xm=0.04, dtd=0.015):
    poss = {7: td*(1-xm), 6: td*xm, 3: fg, 0: 1-td-fg}; dist = defaultdict(float)
    for nn, pn in N.items():
        d = {0: 1.0}
        for _ in range(nn):
            nd = defaultdict(float)
            for s, p in d.items():
                for o, po in poss.items(): nd[s+o] += p*po
            d = nd
        for s, p in d.items(): dist[s] += pn*p
    out = defaultdict(float)
    for s, p in dist.items(): out[s] += p*(1-dtd); out[s+7] += p*dtd
    return out
def q1_tie(N, a, b, haircut=0.8): A, B = team1q(N, *a), team1q(N, *b); return haircut*sum(A[k]*B.get(k, 0) for k in A)
TIE_HAIRCUT = 0.9   # sim_football's 1Q tie rate runs 1-3 points above the CFB record (17-18%, about 20% low-scoring pick'ems): multiply by this
# ---- the shared football simulation: one game draw prices sides, totals, halves, team totals, team yards and NFL props together
FB = dict(nfl=dict(drives=10.8, fg=0.15, ppd=6.0, rush_sd=6.0, s_eff=0.10, pr_slope=0.06, dtd=0.012, xp=0.95, two=0.07, gs=0.05, shared=0.03, dsd=0.05, q_share=(.21, .29, .21, .29)),
          cfb=dict(drives=12.5, fg=0.10, ppd=5.8, rush_sd=6.8, s_eff=0.15, pr_slope=0.07, dtd=0.015, xp=0.97, two=0.07, gs=0.05, shared=0.03, dsd=0.05, q_share=(.23, .27, .24, .26)))
TEAM0 = dict(nfl=dict(pass_rate=0.58, comp=0.65, ypcomp=10.9, ypc=4.4, sack=0.065, int_rate=0.022, pass_td=0.60, qb_rush=0.14),
             cfb=dict(pass_rate=0.48, comp=0.62, ypcomp=11.4, ypc=4.9, sack=0.065, int_rate=0.025, pass_td=0.55, qb_rush=0.16))
BUCKETS = ((-99, -16.5, 'blowout loss'), (-16.5, -7.5, 'two-score loss'), (-7.5, 7.5, 'one-score game'), (7.5, 16.5, 'two-score win'), (16.5, 99, 'blowout win'))
def _seq_split(total_n, shares, rng):                         # split a count among players by shares (rest go to 'others'), sums preserved
    left = total_n.copy(); pl = 1.0; out = []
    for s in shares:
        x = rng.binomial(left, float(np.clip(s/pl, 0, 1)) if pl > 1e-9 else 0.0); out.append(x); left = left-x; pl -= s
    return out
def sim_football(g, players=(), n=40000, seed=7):
    # g: sport ('nfl'|'cfb'), exp_margin (team A minus team B, A = the team you list first), total, optional drives/fg,
    #    A/B team dicts overriding TEAM0 (pass_rate neutral, comp, ypcomp = yards per completion, ypc, sack per dropback, int_rate, pass_td share, qb_rush share)
    # players: name, team 'A'/'B', pos QB|RB|WR|TE, tgt (share of team attempts), catch, ypr, car (share of non-QB carries), ypc, rz_rec, rz_rush, cv (share uncertainty)
    sp = g.get('sport', 'cfb'); c = FB[sp]; rng = np.random.default_rng(seed); d = g.get('drives', c['drives']); fg = g.get('fg', c['fg'])
    D = np.maximum(np.round(d*rng.lognormal(0, c['dsd'], n)), 6).astype(int)   # possessions alternate: both teams get about the same count
    kk = dict(A=D, B=np.maximum(D+rng.integers(-1, 2, n), 5)); shared = rng.lognormal(-c['shared']**2/2, c['shared'], n); S = {}; tm = {}
    for T, sign in (('A', 1), ('B', -1)):
        tgt_pts = (g['total']+sign*g['exp_margin'])/2; td0 = rates_for(tgt_pts, d, fg, 7*4*c['dtd'])['td']
        e = rng.lognormal(-c['s_eff']**2/2, c['s_eff'], n)*shared; k = kk[T]; m = int(k.max())
        tm[T] = dict(e=e, drives=k, td=np.clip(td0*e, 0, 0.75), u=rng.random((n, m)), ok=np.arange(m)[None, :] < k[:, None],
                     q=np.searchsorted(np.cumsum(c['q_share'])[:-1], (np.arange(m)[None, :]+rng.random((n, m)))/k[:, None], side='right'),
                     xp=np.where(rng.random((n, m)) < c['two'], 2*(rng.random((n, m)) < 0.48), rng.random((n, m)) < c['xp']), dst=rng.binomial(4, c['dtd'], n), dq=rng.integers(0, 4, n))
    def outcome(x, td):
        fr = np.minimum(fg, 0.95-td); return (x['u'] < td[:, None]) & x['ok'], (x['u'] >= td[:, None]) & (x['u'] < (td+fr)[:, None]) & x['ok']
    for x in tm.values(): x['isTD'], x['isFG'] = outcome(x, x['td'])
    p3 = {T: ((x['isTD']*(6+x['xp'])+x['isFG']*3)*(x['q'] < 3)).sum(1)+7*x['dst']*(x['dq'] < 3) for T, x in tm.items()}
    for T, O in (('A', 'B'), ('B', 'A')):   # 4th quarter: leaders milk the clock, trailers press (mean-preserving)
        x = tm[T]; z = np.clip((p3[T]-p3[O])/14, -1.5, 1.5); t4, f4 = outcome(x, np.clip(x['td']*(1-c['gs']*(z-z.mean())), 0, 0.75))
        late = x['q'] == 3; x['isTD'] = np.where(late, t4, x['isTD']); x['isFG'] = np.where(late, f4, x['isFG'])
    for x in tm.values():
        dp = x['isTD']*(6+x['xp'])+x['isFG']*3; Q = np.stack([(dp*(x['q'] == i)).sum(1) for i in range(4)], 1).astype(float)
        Q[np.arange(n), x['dq']] += 7*x['dst']; x.update(Q=Q, PTS=Q.sum(1), TD=x['isTD'].sum(1))
        for key in ('u', 'ok', 'q', 'xp', 'isTD', 'isFG', 'dq'): x.pop(key)
    for T, O in (('A', 'B'), ('B', 'A')):
        t = {**TEAM0[sp], **g.get(T, {})}; x = tm[T]; e = x['e']; marg = x['PTS']-tm[O]['PTS']
        plays = np.maximum(np.round(x['drives']*c['ppd']*rng.lognormal(0, 0.07, n)), 1).astype(int)
        pr = np.clip(t['pass_rate']-c['pr_slope']*np.clip(marg/14, -1.5, 1.5), 0.25, 0.85)
        db = rng.binomial(plays, pr); sk = rng.binomial(db, t['sack']); att = db-sk; ratt = plays-db
        qbr = rng.binomial(ratt, t['qb_rush']); nqr = ratt-qbr
        cmp_ = rng.binomial(att, np.clip(t['comp']*e**0.18, 0.3, 0.85))
        pyds = np.where(cmp_ > 0, rng.gamma(np.maximum(cmp_, 1)/0.81, t['ypcomp']*e**0.6*0.81), 0.0)*(cmp_ > 0)
        ryds = rng.normal(ratt*t['ypc']*e**0.6, np.sqrt(np.maximum(ratt, 1))*c['rush_sd'])
        ptd_sh = np.clip(t['pass_td']+0.08*np.clip(-marg/14, -1, 1), 0.2, 0.9); ptd = rng.binomial(x['TD'], ptd_sh); rtd = x['TD']-ptd
        ints = rng.poisson(att*t['int_rate']*e**-0.75)
        sky = sk*6.5   # official team stats: CFB counts sacks as rushes, the NFL takes them off team passing; total yards lose them either way
        x.update(MARGIN=marg, PLAYS=plays, ATT=att, CMP=cmp_, PYDS=pyds, RATT=ratt, QB_RATT=qbr, NQ_RATT=nqr, RYDS=ryds, PTD=ptd, RTD=rtd,
                 INT=ints, SACKS=sk, TEAM_RUSH=ryds-(sp == 'cfb')*sky, TEAM_PASS=pyds-(sp == 'nfl')*sky, TYDS=pyds+ryds-sky,
                 H1=x['Q'][:, 0]+x['Q'][:, 1], H2=x['Q'][:, 2]+x['Q'][:, 3], Q1=x['Q'][:, 0])
    for T in ('A', 'B'):
        x = tm[T]; e = x['e']; ps = [p for p in players if p.get('team', 'A') == T]
        recs = [p for p in ps if p['pos'] != 'QB']; rush = [p for p in ps if p.get('rz_rush', 0) > 0]
        rec_td = dict(zip([p['name'] for p in recs], _seq_split(x['PTD'], [p.get('rz_rec', 0.0) for p in recs], rng)))
        rsh_td = dict(zip([p['name'] for p in rush], _seq_split(x['RTD'], [p['rz_rush'] for p in rush], rng)))
        for p in ps:
            P = {}; sh = rng.lognormal(-p.get('cv', 0.15)**2/2, p.get('cv', 0.15), n)
            if p['pos'] == 'QB':
                P.update(ATT=x['ATT'], CMP=x['CMP'], PYDS=x['PYDS'], PTD=x['PTD'], INT=x['INT'], RATT=x['QB_RATT'])
                P['RYDS'] = rng.normal(x['QB_RATT']*p.get('ypc', 5.0), np.sqrt(np.maximum(x['QB_RATT'], 1))*c['rush_sd'])*(x['QB_RATT'] > 0)
                P['REC'] = np.zeros(n); P['RECYDS'] = np.zeros(n)
            else:
                tg = rng.binomial(x['ATT'], np.clip(p.get('tgt', 0)*sh, 0, 0.6)); rc = rng.binomial(tg, p.get('catch', 0.65))
                cvr = 1.0 if p['pos'] == 'WR' else 0.85
                P['TGT'], P['REC'] = tg, rc
                P['RECYDS'] = np.where(rc > 0, rng.gamma(np.maximum(rc, 1)/cvr**2, p.get('ypr', 11.0)*e**0.45*cvr**2), 0.0)*(rc > 0)
                car = rng.binomial(x['NQ_RATT'], np.clip(p.get('car', 0)*sh, 0, 0.95)); P['RATT'] = car
                P['RYDS'] = rng.normal(car*p.get('ypc', 4.3)*e**0.45, np.sqrt(np.maximum(car, 1))*c['rush_sd'])*(car > 0)
            P['RTD'] = rsh_td.get(p['name'], np.zeros(n, int)); P['RECTD'] = rec_td.get(p['name'], np.zeros(n, int))
            P['TDS'] = P['RTD']+P['RECTD']; P['ANYTD'] = (P['TDS'] >= 1).astype(float); P['RRY'] = P['RYDS']+P['RECYDS']
            S[p['name']] = P
    A, B = tm['A'], tm['B']
    S['game'] = dict(MARGIN=A['PTS']-B['PTS'], TOTAL=A['PTS']+B['PTS'], H1_MARGIN=A['H1']-B['H1'], H1_TOTAL=A['H1']+B['H1'],
                     Q1_MARGIN=A['Q1']-B['Q1'], Q1_TOTAL=A['Q1']+B['Q1'])
    S['A'], S['B'] = A, B; return S
def bucket(margin):
    lab = np.select([margin <= -16.5, margin <= -7.5, margin < 7.5, margin < 16.5], [b[2] for b in BUCKETS[:4]], 'blowout win'); return lab
def p_hit(x, line, side='over', c=1.0):                       # continuous stats: direct; integer stats with half-point lines: smoothed so scaling stays smooth
    x = np.asarray(x, float)
    if np.allclose(x, np.round(x)): po = float(np.clip(x*c+0.5-line, 0, 1).mean()) if c != 1.0 else float((x > line).mean())
    else: po = float((x*c > line).mean())
    return po if side == 'over' else 1-po
def hits(x, line, side='over'): x = np.asarray(x, float); return (x > line) if side == 'over' else (x < line)
def script_table(hit, margin):                               # margin from the bet team's view; hit = boolean array from the shared sim
    b = bucket(margin); rows = []
    for name in [z[2] for z in BUCKETS]:
        mk = b == name; w = float(mk.mean()); ph = float(hit[mk].mean()) if mk.any() else float('nan')
        rows.append((name, round(w, 3), round(ph, 3), round(w*ph, 3) if mk.any() else 0.0))
    return rows
def script_fit(rows):                                        # 2 robust, 1 needs the likeliest script, 0 needs a minority script
    r = sorted([z for z in rows if z[1] > 0.02], key=lambda t: -t[1]); p1, p2 = r[0][2], r[1][2]
    pts = 2 if (p1 >= 0.55 and p2 >= 0.50) else 1 if p1 >= 0.55 else 0
    return pts, any(w >= 0.25 and ph < 0.40 for _, w, ph, _ in rows if ph == ph)
def _scale_for(x, line, q, side):
    lo, hi = 0.2, 4.0
    for _ in range(50):
        c = (lo+hi)/2; pv = p_hit(x, line, side, c)
        if (pv < q) == (side == 'over'): lo = c
        else: hi = c
    return (lo+hi)/2
def mkt_mean_x(x, line, over_price, under_price=None):        # market-implied mean of a sim stat, using our distribution's shape
    q = nv(over_price, under_price) if under_price is not None else one_way_fair(over_price)
    return float(np.asarray(x, float).mean()*_scale_for(x, line, q, 'over'))
def final_probs(x, line, side, quotes, models=()):            # quotes=[(line, over_price, under_price)], models = outside projections (means)
    ours = float(np.asarray(x, float).mean()); lm = logic(ours, list(models)); mm = float(np.mean([mkt_mean_x(x, l, o, u) for l, o, u in quotes]))
    pf = lambda w: round(p_hit(x, line, side, ((1-w)*lm+w*mm)/max(ours, 1e-9)), 3)
    return dict(ours=round(ours, 2), logic=round(lm, 2), market=round(mm, 2), p_logic=pf(0), p_final=pf(0.25), p_cons=pf(0.5), p_mkt=pf(1.0))
def event_final(p_model, p_mkt, w=0.25): return (1-w)*p_model+w*p_mkt   # anytime TDs, interceptions
def sgp(hit_list):                                            # legs priced from ONE shared sim_football() run
    H = np.vstack(hit_list); joint = float(H.all(0).mean()); ind = float(np.prod(H.mean(1)))
    return dict(joint=round(joint, 3), independent=round(ind, 3), lift=round(joint/max(ind, 1e-9), 3))
def sensitivity(g, players, leg, n=15000, seed=7, d_spread=3.0, d_total=4.0, d_pr=0.05):
    # leg(S) -> boolean hits; reruns the shared sim with the spread, total and both teams' pass rates moved
    base = float(leg(sim_football(g, players, n, seed)).mean()); out = {'base': round(base, 3)}; T0 = TEAM0[g.get('sport', 'cfb')]
    for lab, gg in ((f'margin -{d_spread:g}', {**g, 'exp_margin': g['exp_margin']-d_spread}), (f'margin +{d_spread:g}', {**g, 'exp_margin': g['exp_margin']+d_spread}),
                    (f'total -{d_total:g}', {**g, 'total': g['total']-d_total}), (f'total +{d_total:g}', {**g, 'total': g['total']+d_total}),
                    (f'pass rate -{d_pr:g}', {**g, 'A': {**T0, **g.get('A', {}), 'pass_rate': {**T0, **g.get('A', {})}['pass_rate']-d_pr}}),
                    (f'pass rate +{d_pr:g}', {**g, 'A': {**T0, **g.get('A', {}), 'pass_rate': {**T0, **g.get('A', {})}['pass_rate']+d_pr}})):
        out[lab] = round(float(leg(sim_football(gg, players, n, seed)).mean()), 3)
    return out
# ---- tripwires, traps and scoring
TOO_FAR = dict(side=7.0, total=8.0, team_total=5.0, half=4.5, pass_yds=30.0, rush_yds=25.0, rec_yds=20.0, rec=1.5, att=4.0, tds=0.35, team_yds=40.0)
def too_far(kind, ours, market): return abs(ours-market) > TOO_FAR[kind]
def market_guard(p_final, p_mkt, gap=0.12): return abs(p_final-p_mkt) > gap   # True = needs a sourced reason, or lean on the conservative blend
def sanity(S, g, team='A'):                                  # red flags on the shared sim's inputs
    x = S[team]; fl = []; pl = float(x['PLAYS'].mean()); pr = float((x['ATT']+x['SACKS']).mean()/max(pl, 1e-9)); lo, hi = (52, 75) if g.get('sport') == 'nfl' else (58, 90)
    tgt = (g['total']+(1 if team == 'A' else -1)*g['exp_margin'])/2
    if not lo <= pl <= hi: fl.append(f'{team} plays {pl:.0f}: check drives and plays per drive')
    if not 0.35 <= pr <= 0.75: fl.append(f'{team} pass rate {pr:.2f}: check pass_rate and the script slope')
    if abs(float(x['PTS'].mean())-tgt) > 0.6: fl.append(f'{team} points {x["PTS"].mean():.1f} vs target {tgt:.1f}: recheck rates')
    return fl
def trap_flags(t):                                           # t: dict of facts for one bet; returns the failed numeric tests (Step 8c)
    f = []; side = t.get('side')
    if t.get('public_pct', 0) >= 65 and t.get('public_side') == side and t.get('line_moved_toward_other', False): f.append('public side: 65%+ of tickets with us and the line moving the other way')
    if t.get('money_minus_bets', 0) <= -15 and t.get('line_moved_against', False): f.append('bigger bettors against us and the line moving away')
    if t.get('steam_against', 0) >= t.get('steam_tol', 1.0) and not t.get('news'): f.append('steam against us with no news')
    if t.get('move_after_one_game', 0) >= 2: f.append('recency: the line moved 2+ after one result')
    if t.get('needs_bottom_third_unit_over'): f.append('bad-at-it: a bottom-third unit must beat its own average')
    if t.get('needs_offense_below_avg') and not t.get('def_top_third'): f.append('under mirror: an offense must finish below its own average without a top-third defense')
    if t.get('qb_starts', 9) <= 2 or t.get('games', 9) <= 3: f.append('small sample: QB with 2 or fewer starts in this role, or a unit with 3 or fewer FBS games')
    if t.get('key_hook'): f.append('key number: laying the hook past 3 or 7 (10 or 14 in CFB), or a better number elsewhere')
    if t.get('wind', 0) >= 15 and side == 'over' and not t.get('weather_priced'): f.append('weather: 15+ mph wind on an over or a passing over')
    if t.get('too_far') and not t.get('news'): f.append('too good to be true: far from the market and the models with no news')
    if t.get('td_pool_split'): f.append('TD pool: this TD leg competes with another TD leg on the same team')
    return f
def hit_pts(p): return 2 if p >= 0.60 else 1 if p >= 0.55 else 0
CAPS = dict(status_unresolved=4, refuted_claim=3, unverified_claim=5, two_trap_fails=4, script_fragile=5, sens_fragile=5, new_qb=5, small_sample=5,
            red_tripwire=5, bottom_third=5, bottom_quarter=4, under_vs_avg_defense=5, yardage_short=5, too_far_no_news=5)
def score(p, matchup, script_pts, players, models_market, mom_chem, situ, p_cons=None, caps=(), duplicate=False):
    # chance 0-2 + matchup 0-2 + script 0-2 + players 0-1 + models and market 0-1 + momentum/chemistry/coaching 0-1 + situation/weather 0-1 = 10
    # price never enters; while calib_tripwire() is live, pass p_cons as p
    s = hit_pts(p)+matchup+script_pts+players+models_market+mom_chem+situ-int(duplicate)
    cap = min([10]+[CAPS.get(c, c) if isinstance(c, str) else c for c in caps])
    if p < 0.50: cap = min(cap, 3)
    elif p < 0.55: cap = min(cap, 4)
    if p_cons is not None and p_cons < 0.50: cap = min(cap, 5)
    return max(0, min(s, cap))
def verdict(s): return ('STRONG TAKE', 1.5) if s >= 8 else ('TAKE', 1.0) if s >= 6 else ('TAKE SMALL', 0.5) if s == 5 else ('WATCH', 0) if s == 4 else ('PASS', 0)
def read_split(bets, money, line_moved_toward_this_side):
    gap = money-bets; tags = []
    if bets >= 65: tags.append('public side')
    if gap >= 15: tags.append('bigger bettors here')
    if gap <= -15: tags.append('small bettors only')
    if bets < 50 and line_moved_toward_this_side: tags.append('reverse line movement')
    return ', '.join(tags) or 'balanced'
def calib_tripwire(rows, n=15, gap=0.10):                    # rows: settled straights in date order with p_final and y (1 win, 0 loss)
    r = rows[-n:]
    if len(r) < n: return dict(live=False, n=len(r))
    st = float(np.mean([x['p_final'] for x in r])); ac = float(np.mean([x['y'] for x in r]))
    return dict(live=st-ac >= gap, n=n, stated=round(st, 3), actual=round(ac, 3))
# ---- straight card: the -190 cap, correlation blocks and ranking
MAX_STRAIGHT_PRICE = -190   # straights must be priced -190 or better (Oct 22, 2026); parlay and teaser legs are exempt
def straight_ok(price, cap=MAX_STRAIGHT_PRICE): return price is not None and (price > 0 or price >= cap)   # -190, -150, +120 pass; -195, -430 fail
def est_price(p_mkt, hold=0.045): return american(1/min(p_mkt+hold, 0.97))   # no screenshot: a book-style price from the market's chance (alt ladders: hold 0.05-0.08)
def price_note(price, est=False, cap=MAX_STRAIGHT_PRICE, near=15):
    if price is None: return 'price not found: estimate it with est_price() before the bet goes on the card'
    if not straight_ok(price, cap): return f'{price:+d} is past {cap}: not a straight; re-express it (spread, alt spread, team total, first half) or keep it as a parlay leg'
    if est and price < 0 and price <= cap+near: return f'about {price:+d}: place only if the app shows {cap} or better'
    return ''
def best_straight_line(p_at, line_prices, cap=MAX_STRAIGHT_PRICE):   # p_at(line) -> chance at that number; line_prices={line: price} for one side
    ok = {l: pr for l, pr in line_prices.items() if straight_ok(pr, cap)}
    if not ok: return None
    l = max(ok, key=p_at); return dict(line=l, price=ok[l], p=round(float(p_at(l)), 3))
def script_corr(a, b):                                       # phi between two bets' hit arrays from one shared sim; same script label = 1
    if a.get('hits') is not None and b.get('hits') is not None:
        x, y = np.asarray(a['hits'], float), np.asarray(b['hits'], float)
        return 0.0 if x.std() == 0 or y.std() == 0 else float(np.corrcoef(x, y)[0, 1])
    return 1.0 if a.get('script') and a.get('script') == b.get('script') else 0.0
def pick_top(cands, n, max_per_game=2, block=0.25, warn=0.10, cap=MAX_STRAIGHT_PRICE):
    # cands: id, game, score, p, p_cons, fit, price, player (props only), hits (bool array from the game's shared sim) or a script label
    left = [c for c in cands if straight_ok(c.get('price'), cap)]; chosen = []; pg = Counter(); pp = Counter()
    link = lambda c: max([abs(script_corr(c, d)) for d in chosen if d['game'] == c['game']] or [0.0])
    while left and len(chosen) < n:
        eff = lambda c: c['score']-(1 if link(c) >= warn else 0)
        left.sort(key=lambda c: (-eff(c), -c['p'], -c.get('p_cons', 0), -c.get('fit', 0))); c = left.pop(0)
        if eff(c) < 5 or c['p'] < 0.55: break
        if pg[c['game']] >= max_per_game or link(c) >= block or (c.get('player') and pp[c['player']] >= 1): continue
        chosen.append({**c, 'eff_score': eff(c), 'link': round(link(c), 2)}); pg[c['game']] += 1
        if c.get('player'): pp[c['player']] += 1
    return chosen
# ---- parlays: pricing, house edge, correlation and the two-parlay builder
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
def joint_prob(legs):                                         # p_final per leg; same-game legs take the lift from their shared sim
    by = defaultdict(list); out = 1.0; lifts = {}
    for L in legs: by[L['game']].append(L)
    for gm, Ls in by.items():
        base = float(np.prod([L['p'] for L in Ls]))
        if len(Ls) > 1:
            H = float(np.all([L['hits'] for L in Ls], axis=0).mean()); ind = float(np.prod([L['hits'].mean() for L in Ls])); lift = H/max(ind, 1e-9)
        else: lift = 1.0
        out *= min(base*lift, min(L['p'] for L in Ls)); lifts[gm] = round(lift, 3)
    return out, lifts
def parlay_ok(legs, max_per_game):                           # market: 'side' (spread or ML), 'total', 'tt_A', 'tt_B', '1h_side', '1h_total', 'prop:{player}:{stat}'
    if len({(L['game'], L['market']) for L in legs}) < len(legs): return False   # one leg per market per game, never both sides
    return all(c <= max_per_game for c in Counter(L['game'] for L in legs).values())
PARLAY = dict(safe=dict(legs=(2, 3), min_p=0.62, min_score=6, max_per_game=1, min_price=100, max_price=400),
              risky=dict(legs=(3, 5), min_p=0.55, min_score=5, max_per_game=2, min_price=450, max_price=1500))
def build_parlays(legs, kind='safe', top=3, relax=True, **over):   # legs: id, game, market, side, p, score, price, hits (bool array from the game's shared sim)
    c = {**PARLAY[kind], **over}; res = _search(legs, c, kind, top)
    while relax and not res and round(c['min_p']-0.02, 2) >= 0.56:
        c = {**c, 'min_p': round(c['min_p']-0.02, 2), 'min_score': max(5, c['min_score']-1)}; res = _search(legs, c, kind, top)
    for r in res: r['level'] = f"legs {c['min_p']:.0%}+ and score {c['min_score']}+"
    return res
def _search(legs, c, kind, top):
    pool = [L for L in legs if L['p'] >= c['min_p'] and L['score'] >= c['min_score'] and not L.get('traps')]; out = []   # a trap-flagged leg never goes in (Oct 20, 2026)
    for k in range(c['legs'][0], c['legs'][1]+1):
        for combo in itertools.combinations(pool, k):
            if not parlay_ok(combo, c['max_per_game']): continue
            price = parlay_price([L['price'] for L in combo])
            if price < c['min_price'] or price > c['max_price']: continue
            j, lifts = joint_prob(combo)
            if any(v < 0.98 for v in lifts.values()): continue
            out.append(dict(kind=kind, legs=[L['id'] for L in combo], joint=round(j, 3), price=price, fair=american(1/j), lifts=lifts,
                            sgp=any(v > 1 for v in Counter(L['game'] for L in combo).values()), weakest=min(combo, key=lambda L: L['p'])['id'], ev=parlay_ev(j, price)))
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
def clv(price_taken, close_side, close_other): q = nv(close_side, close_other); return round(q*dec(price_taken)-1, 4)   # same number: closing fair chance x payout - 1
def line_clv(taken, closed, kind='side'): return round((closed-taken) if kind == 'over' else (taken-closed), 1)   # points beaten; sides signed from the bettor's view (laid -2.5, closed -4 -> +1.5)
def autoresearch(rows, experiments, holdout=0.3, min_gain=0.002):
    ys = np.array([r['y'] for r in rows], float); cut = int(len(rows)*(1-holdout)); res = []
    base = np.array([r['p_final'] for r in rows]); b_tr, b_te = logloss(base[:cut], ys[:cut]), logloss(base[cut:], ys[cut:])
    res.append(('baseline', round(b_te, 4), 0.0, 'keep'))
    for name, fn in experiments.items():
        pe = np.array([fn(r) for r in rows]); tr, te = logloss(pe[:cut], ys[:cut]), logloss(pe[cut:], ys[cut:])
        res.append((name, round(te, 4), round(b_te-te, 4), 'keep' if (b_te-te) >= min_gain and tr <= b_tr else 'discard'))
    return res
def model_checks(n=20000):                                    # run after any change to this file; each check guards a failure we hit in Oct 2026
    out = []; G = sim_football(dict(sport='nfl', exp_margin=3, total=44), (), n)['game']
    if not (12.8 <= G['MARGIN'].std() <= 14.2 and 13.2 <= G['TOTAL'].std() <= 14.8): out.append('NFL margin or total SD off the key-number model')
    G = sim_football(dict(sport='cfb', exp_margin=-0.5, total=51.2), (), n)['game']
    if not (14.5 <= G['MARGIN'].std() <= 16.3 and 15.0 <= G['TOTAL'].std() <= 16.8): out.append('CFB margin or total SD off the key-number model')
    pl = [dict(name='QB', team='A', pos='QB'), dict(name='RB', team='A', pos='RB', car=0.6, rz_rush=0.55)]
    S = sim_football(dict(sport='nfl', exp_margin=7, total=48), pl, n); k = S['A']['TD'] == 3
    if np.corrcoef(S['QB']['PTD'][k], S['RB']['RTD'][k])[0, 1] > -0.3: out.append('TD pool: QB passing TDs and RB rushing TDs must compete for the team TDs')
    S = sim_football(dict(sport='cfb', exp_margin=3, total=52), (), n)
    if script_corr({'hits': S['game']['MARGIN'] > 0}, {'hits': S['B']['PTS'] < 24.5}) < 0.25: out.append('same-script block: a moneyline and the opponent team-total under must correlate 0.25+')
    if straight_ok(-195) or not straight_ok(-190) or not straight_ok(120): out.append('-190 straight cap')
    return out or ['all checks pass']
