# Minutes noise by role, fitted on 2014-24 games around the engine's own projection (margin-adjusted EWMA, half-life 2.5).
# Also the regression offsets and the role-change (promoted / demoted) effects. Needs 03_minutes_projection.py first.
import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, nba_props as m
from scipy.optimize import minimize
p = pd.read_pickle('data/cache/min_pred.pkl')
def role(b): return np.select([b>=34, b>=28, b>=18], ['star','starter','rotation'], 'bench')
p['role0'] = role(p.m_ewm4.fillna(0)); eff = np.zeros(len(p))
for r in ('star','starter','rotation','bench'):
    mk = (p.role0==r).values; eff[mk] = np.interp(p.am.values[mk], m.MKNOTS, m.ROLE[r]['dm']) + p.ot.values[mk]*m.ROLE[r]['ot']
p['min_adj'] = p['min'] - eff
g = p.groupby(['player_id','season'], sort=False); sha = g['min_adj'].shift()
p['ew'] = sha.groupby([p.player_id, p.season]).transform(lambda s: s.ewm(halflife=2.5, ignore_na=True).mean())
q = p[(p.n_prev>=10) & (p.season>=2014)].copy(); q['role'] = role(q['ew']); q['res0'] = q.min_adj - q['ew']
q['chg'] = np.select([(q.starter==1)&(q.st_prev5<=0.2), (q.starter==0)&(q.st_prev5>=0.8)], ['promoted','demoted'], 'same')
s = q[q.chg=='same']
reg = s.groupby('role')['res0'].mean().round(2).to_dict(); print('reg offsets', reg)
qs = np.array([.01,.05,.1,.25,.5,.75,.9,.95,.99])
rng = np.random.default_rng(0); Z = rng.standard_normal(400000); Ub = rng.random(400000); G = rng.gamma(2.0, 1.0, 400000)
def simq(par, sign=-1):
    sd, tp, ym = par; x = sd*Z + sign*(Ub < tp)*G*ym/2.0; x = x - x.mean(); return np.quantile(x, qs)
for r in ('star','starter','rotation','bench'):
    res = (s.res0[s.role==r] - reg[r]).values; emp = np.quantile(res - res.mean(), qs)
    sign = 1 if r == 'bench' else -1
    loss = lambda par: np.sum((simq(np.abs(par), sign) - emp)**2) if 0 < abs(par[1]) < 0.6 else 1e9
    best = min((minimize(loss, x0, method='Nelder-Mead', options=dict(xatol=1e-3, fatol=1e-5, maxiter=600)) for x0 in ([3,0.1,8],[4,0.2,6],[5,0.05,12])), key=lambda o: o.fun)
    sd, tp, ym = np.abs(best.x); print(r, len(res), 'sd %.2f tail_p %.3f tail_mean %.2f (sign %+d) resid_sd %.2f' % (sd, tp, ym, sign, res.std()))
for ch in ('promoted','demoted'):
    d = q[q.chg==ch]; e = d.min_adj - d['ew']
    print(ch, len(d), 'bias %.2f sd %.2f' % (e.mean(), e.std()))
    d = d.assign(e=e, b=pd.cut(d['ew'], [0, 18, 24, 30, 36, 48]))
    print(d.groupby('b', observed=True)['e'].agg(['mean','std','size']).round(2).to_string())
# era check: minutes were noisier in 2010-13
q2 = p[(p.n_prev>=10)].copy(); q2['role'] = role(q2['ew']); q2['res0'] = q2.min_adj - q2['ew']
q2['era'] = pd.cut(q2.season, [2009, 2013, 2017, 2020, 2023], labels=['10-13','14-17','18-20','21-23'])
print(q2[q2.role.isin(['star','starter','rotation'])].groupby(['role','era'], observed=True)['res0'].std().round(2).unstack().to_string())
