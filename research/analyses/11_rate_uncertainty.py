import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
df = data.player_games()
p = df[df.played==1].copy().sort_values(['player_id','date','game_id'])
tp = p.groupby(['team_id','season'])['pace48'].transform('mean'); p['pf_'] = p.pace48/tp
stats = ['pts','reb','ast','fg3m','fga','fta','stl','blk','tov']
K = dict(pts=200, reb=100, ast=100, fg3m=200, fga=100, fta=200, stl=600, blk=200, tov=400)
W10 = dict(pts=0.2, reb=0.1, ast=0.3, fg3m=0.1, fga=0.3, fta=0.2, stl=0.1, blk=0.1, tov=0.1)
D = dict(pts=2.2, reb=1.08, ast=1.10, fg3m=1.0, fga=0.86, fta=2.05, stl=1.04, blk=1.08, tov=1.0)
ps = p.groupby(['player_id','season'])[stats+['min']].sum()
prev = ps.copy(); prev.index = prev.index.set_levels(prev.index.levels[1]+1, level=1); prev = prev.rename(columns=lambda c: 'prev_'+c)
p = p.join(prev, on=['player_id','season'])
g = p.groupby(['player_id','season'], sort=False)
p['n_min'] = g['min'].cumsum() - p['min']; p['n_g'] = g.cumcount()
lg = p.groupby('season').apply(lambda d: d[stats].sum()/d['min'].sum(), include_groups=False)
for s in stats+['min']:
    p[f'l10_{s}'] = g[s].transform(lambda x: x.shift().rolling(10, min_periods=1).sum())
ev = p[(p.season>=2012)&(p['min']>=12)].copy()
ev['has_prev'] = ev.prev_min >= 300
ev['nb'] = pd.cut(ev.n_g, [-1, 4, 9, 19, 39, 90], labels=['0-4','5-9','10-19','20-39','40+'])
# pace elasticity check: regress log((y+0.5)/(base+0.5)) on log(pf)
for s in stats:
    cum = g[s].cumsum() - p[s]; obs = (cum/p.n_min.replace(0, np.nan)).reindex(ev.index)
    prior = np.where(ev.has_prev, ev[f'prev_{s}']/ev.prev_min, lg.loc[ev.season, s].values)
    base = np.where(ev.n_min > 0, (np.nan_to_num(obs)*ev.n_min + K[s]*prior)/(ev.n_min + K[s]), prior)
    l10 = ev[f'l10_{s}']/ev['l10_min'].replace(0, np.nan)
    rate = np.where(np.isfinite(l10) & (ev.l10_min >= 60), (1-W10[s])*base + W10[s]*np.nan_to_num(l10), base)
    mu = rate*ev['min'].values*ev.pf_.values
    y = ev[s].values
    out = []
    for (hp, nb), idx in ev.groupby(['has_prev','nb'], observed=True).indices.items():
        m_, y_ = mu[idx], y[idx]
        ex = np.mean((y_-m_)**2) - D[s]*np.mean(m_)
        cv2 = ex/np.mean(m_**2)
        out.append(f"{'prev' if hp else 'new '} {nb}: cv={np.sqrt(max(cv2,0)):.3f} bias={np.mean(y_-m_)/np.mean(m_):+.3f}")
    # pace elasticity
    ok = (mu > 1)
    X = np.log(ev.pf_.values[ok]); Y = np.log((y[ok]+0.5)/(mu[ok]/ev.pf_.values[ok]+0.5))
    slope = np.polyfit(X, Y, 1)[0]
    print(s, f'pace elasticity {slope:.2f} |', ' | '.join(out))
