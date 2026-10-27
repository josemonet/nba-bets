import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
df = data.player_games()
p = df[df.played==1].copy().sort_values(['player_id','date','game_id'])
p['am'] = p.margin.abs()
# empirical margin effect table (role by projected minutes), deltas relative to competitive base
knots = np.array([0, 4.5, 7.5, 10.5, 13.5, 16.5, 19.5, 22.5, 25.5, 28.5, 32.5, 40])
tab = {'star':     [0.19,0.08,-0.21,-1.04,-2.20,-3.27,-4.46,-5.48,-6.14,-6.60,-7.68,-8.59],
       'starter':  [0.13,0.09,-0.18,-0.72,-1.50,-2.38,-3.28,-3.65,-4.82,-4.92,-5.55,-6.25],
       'rotation': [0.01,0.04,-0.04,-0.15,-0.42,-0.61,-0.94,-1.05,-1.17,-1.22,-1.60,-1.70],
       'bench':    [-0.11,0.08,0.01,0.29,0.23,0.32,0.53,1.04,1.44,1.84,2.03,2.78]}
otadd = {'star':4.6,'starter':4.0,'rotation':2.1,'bench':0.8}
g = p.groupby(['player_id','season'], sort=False)
p['n_prev'] = g.cumcount()
sh = g['min'].shift()
p['m_season'] = sh.groupby([p.player_id, p.season]).transform(lambda s: s.expanding().mean())
for k in (3,5,10):
    p[f'm_last{k}'] = sh.groupby([p.player_id, p.season]).transform(lambda s: s.rolling(k, min_periods=1).mean())
for hl in (2,4,6,10):
    p[f'm_ewm{hl}'] = sh.groupby([p.player_id, p.season]).transform(lambda s: s.ewm(halflife=hl, ignore_na=True).mean())
p['st_prev5'] = g['starter'].shift().groupby([p.player_id, p.season]).transform(lambda s: s.rolling(5, min_periods=1).mean())
p['m_prev1'] = sh
p.to_pickle('data/cache/min_pred.pkl')
q = p[(p.n_prev>=10)].copy()
def role(b): return np.select([b>=34, b>=28, b>=18], ['star','starter','rotation'], 'bench')
q['role'] = role(q.m_ewm4)
eff = np.zeros(len(q))
for r in tab:
    m = (q.role==r).values
    eff[m] = np.interp(q.am.values[m], knots, tab[r]) + q.ot.values[m]*otadd[r]
q['min_adj'] = q['min'] - eff
print('rows', len(q))
for c in ['m_prev1','m_last3','m_last5','m_last10','m_season','m_ewm2','m_ewm4','m_ewm6','m_ewm10']:
    e = q.min_adj - q[c]
    print(f'{c:9s} RMSE {np.sqrt((e**2).mean()):.3f}  MAE {e.abs().mean():.3f}  bias {e.mean():+.3f}')
# role change: starter now vs previous starts
q['st_change'] = np.select([(q.starter==1)&(q.st_prev5<=0.2), (q.starter==0)&(q.st_prev5>=0.8)], ['promoted','demoted'], 'same')
print(q.groupby('st_change').apply(lambda d: pd.Series({'n':len(d),'bias_ewm4':(d.min_adj-d.m_ewm4).mean(),'sd':(d.min_adj-d.m_ewm4).std()}), include_groups=False).round(2))
# linear blend fit on 'same' rows, by role, with starter flag
from numpy.linalg import lstsq
s = q[q.st_change=='same']
X = np.c_[s.m_ewm4, s.m_season, s.m_last10, np.ones(len(s))]
b, *_ = lstsq(X, s.min_adj.values, rcond=None); e = s.min_adj.values - X@b
print('blend ewm4/season/last10/const', b.round(3), 'RMSE', np.sqrt((e**2).mean()).round(3))
# residual SD by role around best simple predictor (ewm4) for 'same'
s = s.assign(res=s.min_adj - s.m_ewm4)
print(s.groupby('role')['res'].describe(percentiles=[.01,.05,.1,.25,.5,.75,.9,.95,.99]).round(2).to_string())
print('share res < -8', s.groupby('role')['res'].apply(lambda x: (x<-8).mean()).round(3).to_dict())
print('share res < -15', s.groupby('role')['res'].apply(lambda x: (x<-15).mean()).round(3).to_dict())
# rest (back-to-back) effect on minutes residual
s2 = s[s.rest.notna()].assign(b2b=(s.rest==1))
print('B2B minutes effect by role', s2.groupby(['role','b2b'])['res'].mean().unstack().round(2).to_string())
# recent volatility: does a player's own recent minutes SD predict residual size?
s['vol'] = s.groupby(['player_id','season'])['min'].transform(lambda x: x.shift().rolling(10, min_periods=5).std())
s['vb'] = pd.qcut(s.vol, 5)
print(s.groupby(['role','vb'], observed=True)['res'].std().unstack().round(2).to_string())
