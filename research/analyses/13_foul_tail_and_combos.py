import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
p = pd.read_pickle('data/cache/min_pred.pkl')
df = data.player_games()
knots = np.array([0, 4.5, 7.5, 10.5, 13.5, 16.5, 19.5, 22.5, 25.5, 28.5, 32.5, 40])
tab = {'star':[0.19,0.08,-0.21,-1.04,-2.20,-3.27,-4.46,-5.48,-6.14,-6.60,-7.68,-8.59],'starter':[0.13,0.09,-0.18,-0.72,-1.50,-2.38,-3.28,-3.65,-4.82,-4.92,-5.55,-6.25],
       'rotation':[0.01,0.04,-0.04,-0.15,-0.42,-0.61,-0.94,-1.05,-1.17,-1.22,-1.60,-1.70],'bench':[-0.11,0.08,0.01,0.29,0.23,0.32,0.53,1.04,1.44,1.84,2.03,2.78]}
otadd = {'star':4.6,'starter':4.0,'rotation':2.1,'bench':0.8}
def role(b): return np.select([b>=34, b>=28, b>=18], ['star','starter','rotation'], 'bench')
p['role0'] = role(p.m_ewm4.fillna(0)); eff = np.zeros(len(p))
for r in tab:
    m = (p.role0==r).values; eff[m] = np.interp(p.am.values[m], knots, tab[r]) + p.ot.values[m]*otadd[r]
p['min_adj'] = p['min'] - eff
g = p.groupby(['player_id','season'], sort=False)
sha = g['min_adj'].shift()
p['proj'] = sha.groupby([p.player_id, p.season]).transform(lambda s: s.ewm(halflife=2.5, ignore_na=True).mean())
p['pf36_prev'] = g['pf'].transform(lambda x: x.shift().expanding().sum()) / g['min'].transform(lambda x: x.shift().expanding().sum()) * 36
q = p[(p.n_prev>=10)].copy(); q['role'] = role(q.proj); q['res'] = q.min_adj - q.proj
q = q[~(((q.starter==1)&(q.st_prev5<=0.2)) | ((q.starter==0)&(q.st_prev5>=0.8)))]
q['pfb'] = pd.cut(q.pf36_prev, [0, 2.5, 3.0, 3.5, 4.0, 4.5, 9])
t = q[q.role.isin(['star','starter','rotation'])].groupby(['role','pfb'], observed=True)['res'].agg(tail8=lambda s: (s < -8).mean(), sd='std', n='size').round(3)
print(t.to_string())
# home/away per-minute factors for each stat: weighted geometric mean of each player-season's home rate / road rate
pl = df[df.played==1]
key = ['player_id','season','team_id']
out = {}
for s in ('pts','reb','ast','fg3m','fg3a','fga','fta','stl','blk','tov'):
    r = pl.groupby(key+['home'])[[s,'min']].sum().unstack('home').dropna()
    h, a = r[(s,1)], r[(s,0)]; mh, ma = r[('min',1)], r[('min',0)]
    ok = (h > 0) & (a > 0) & (mh > 300) & (ma > 300)
    lr = np.log((h[ok]/mh[ok])/(a[ok]/ma[ok])); w = np.minimum(mh[ok], ma[ok])
    out[s] = round(float(np.exp(np.average(lr, weights=w)/2)), 4)
print('home multiplier (away = 1/x):', out)
# variance/mean of fg3m and pra at fixed minutes (LOO season rates) for engine checks
pp = pl.copy(); tp = pp.groupby(['team_id','season'])['pace48'].transform('mean'); pp['pf_'] = pp.pace48/tp
pp['pra'] = pp.pts+pp.reb+pp.ast; pp['pr'] = pp.pts+pp.reb; pp['pa'] = pp.pts+pp.ast; pp['ra'] = pp.reb+pp.ast
gb = pp.groupby(key); pp['n_g'] = gb['min'].transform('size'); pp['M'] = gb['min'].transform('sum')
pp = pp[(pp.n_g>=40)&(pp.M/pp.n_g>=15)&(pp['min']>=6)]
for s in ('fg3m','pra','pr','pa','ra'):
    S = pp.groupby(key)[s].transform('sum'); mu = (S - pp[s])/(pp.M - pp['min'])*pp['min']*pp.pf_
    b = pd.qcut(mu, 5); t = pd.DataFrame({'mu':mu,'r2':(pp[s]-mu)**2}).groupby(b, observed=True).agg(mu=('mu','mean'), v=('r2','mean'))
    print(s, 'variance/mean by mu quintile:', ' '.join(f'{a:.1f}:{v/a:.2f}' for a, v in zip(t.mu, t.v)))
