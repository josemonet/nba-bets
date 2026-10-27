# Does pulling the recent-weighted minutes toward his season average help? Fitted on 2014-20 (MIN_PULL = 0.1).
import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, nba_props as m
p = pd.read_pickle('data/cache/min_pred.pkl')
def role(b): return np.select([b>=34, b>=28, b>=18], ['star','starter','rotation'], 'bench')
p['role0'] = role(p.m_ewm4.fillna(0)); eff = np.zeros(len(p))
for r in ('star','starter','rotation','bench'):
    mk = (p.role0==r).values; eff[mk] = np.interp(p.am.values[mk], m.MKNOTS, m.ROLE[r]['dm']) + p.ot.values[mk]*m.ROLE[r]['ot']
p['min_adj'] = p['min'] - eff
g = p.groupby(['player_id','season'], sort=False); sha = g['min_adj'].shift()
p['ew'] = sha.groupby([p.player_id, p.season]).transform(lambda s: s.ewm(halflife=2.5, ignore_na=True).mean())
p['sa'] = sha.groupby([p.player_id, p.season]).transform(lambda s: s.expanding().mean())
q = p[(p.n_prev>=10)].copy()
q = q[~(((q.starter==1)&(q.st_prev5<=0.2)) | ((q.starter==0)&(q.st_prev5>=0.8)))]
tr = q[(q.season>=2014)&(q.season<=2020)]
for b in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
    proj = tr['ew'] + b*(tr['sa']-tr['ew']); proj = proj + np.select([proj>=34, proj>=28, proj>=18], [-0.63,-0.08,-0.14], 0.37)
    e = tr.min_adj - proj; print('pull', b, 'train RMSE %.4f' % np.sqrt((e**2).mean()))
d = tr.assign(gapb=pd.cut(tr['ew']-tr['sa'], [-40,-6,-3,-1,1,3,6,40]))
for b in (0.0, 0.1):
    proj = d['ew'] + b*(d['sa']-d['ew']); proj = proj + np.select([proj>=34, proj>=28, proj>=18], [-0.63,-0.08,-0.14], 0.37)
    print('pull', b, 'bias by recent-minus-season gap:', (d.min_adj - proj).groupby(d.gapb, observed=True).mean().round(2).to_dict())
