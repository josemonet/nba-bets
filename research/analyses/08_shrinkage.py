import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
df = data.player_games()
p = df[df.played==1].copy().sort_values(['player_id','date','game_id'])
tp = p.groupby(['team_id','season'])['pace48'].transform('mean'); p['pf_'] = p.pace48/tp
p['fg2a'] = p.fga - p.fg3a
stats = ['pts','reb','ast','fg3m','fga','fg3a','fta','stl','blk','tov','oreb','dreb']
# previous-season per-minute rates (whole season, any team)
ps = p.groupby(['player_id','season'])[stats+['min']].sum()
prev = ps.copy(); prev.index = prev.index.set_levels(prev.index.levels[1]+1, level=1)
prev = prev.rename(columns=lambda c: 'prev_'+c)
p = p.join(prev, on=['player_id','season'])
g = p.groupby(['player_id','season'], sort=False)
cum_min = g['min'].cumsum() - p['min']
p['n_min'] = cum_min
for s in stats:
    p[f'cum_{s}'] = g[s].cumsum() - p[s]
# last-10 rates
for s in stats+['min']:
    p[f'l10_{s}'] = g[s].transform(lambda x: x.shift().rolling(10, min_periods=1).sum())
lg = p.groupby('season').apply(lambda d: d[stats].sum()/d['min'].sum(), include_groups=False)
ev = p[(p.season>=2012)&(p['min']>=10)].copy()
print('eval rows', len(ev))
out = {}
for s in stats:
    y = ev[s].values; mm = (ev['min']*ev.pf_).values
    obs = (ev[f'cum_{s}']/ev.n_min.replace(0, np.nan)).values
    n = ev.n_min.values
    has_prev = (ev.prev_min >= 300).values
    prior_prev = (ev[f'prev_{s}']/ev.prev_min).values
    prior_lg = lg.loc[ev.season, s].values
    prior = np.where(has_prev, prior_prev, prior_lg)
    best = None
    rows = []
    for k in (0, 100, 200, 300, 400, 600, 800, 1200, 1600, 2400, 3200):
        r = np.where(n > 0, (np.nan_to_num(obs)*n + k*prior)/(n + k + 1e-9), prior)
        e = y - r*mm; mse = np.nanmean(e**2)
        rows.append((k, mse))
        if best is None or mse < best[1]: best = (k, mse)
    # recency: blend in last-10 rate with weight w
    l10 = (ev[f'l10_{s}']/ev['l10_min'].replace(0, np.nan)).values
    k = best[0]; base = np.where(n > 0, (np.nan_to_num(obs)*n + k*prior)/(n + k + 1e-9), prior)
    l10m = ev['l10_min'].values
    rec = []
    for w in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
        r = np.where(np.isfinite(l10) & (l10m >= 60), (1-w)*base + w*np.nan_to_num(l10), base)
        rec.append((w, np.nanmean((y - r*mm)**2)))
    bw = min(rec, key=lambda t: t[1])
    # with-prior vs no-prior subset for players with a previous season
    out[s] = dict(best_k=best[0], mse=round(best[1],4), mse_k0=round(rows[0][1],4), best_w_l10=bw[0], gain_l10=round(rec[0][1]-bw[1],5))
    print(s, out[s], ' grid:', ' '.join(f'{k}:{m:.4f}' for k, m in rows))
