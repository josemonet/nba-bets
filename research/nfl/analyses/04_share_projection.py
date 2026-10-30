# Best pregame projection of target share (WR/TE/RB) and carry share (RB): recency weighting, prior season, shrinkage.
import sys; sys.path.insert(0, 'research/nfl')
import numpy as np, pandas as pd, data
T = data.build(); pg = T['player_games'].copy()
pg = pg[pg.season.notna() & pg.position.isin(['WR', 'TE', 'RB'])]
tt = T['player_games'].assign(nq=lambda d: np.where(d.position == 'QB', 0, d.rush_att)).groupby(['game_id', 'team']).agg(
    team_tgt=('targets', 'sum'), team_nq=('nq', 'sum')).reset_index()
pg = pg.merge(tt, on=['game_id', 'team'])
pg = pg[(pg.offense_snaps > 0) | (pg.targets > 0) | (pg.rush_att > 0)].sort_values(['player_id', 'season', 'week'])
pg['nq_rush'] = pg.rush_att
# previous-season share for the same player (any team)
for y, n in (('targets', 'team_tgt'), ('nq_rush', 'team_nq')):
    s = pg.groupby(['player_id', 'season'])[[y, n]].sum(); s['sh'] = s[y]/s[n]; s['vol'] = s[n]
    prev = s[['sh', 'vol']].copy(); prev.index = prev.index.set_levels(prev.index.levels[1] + 1, level=1)
    pg = pg.join(prev.rename(columns={'sh': f'prev_sh_{y}', 'vol': f'prev_vol_{y}'}), on=['player_id', 'season'])
g = pg.groupby(['player_id', 'season'], sort=False)
pg['n_prior'] = g.cumcount()
def ewm_share(y, n, hl):
    num = g[y].transform(lambda x: x.shift().ewm(halflife=hl, ignore_na=True).mean() if hl else x.shift().expanding().mean())
    den = g[n].transform(lambda x: x.shift().ewm(halflife=hl, ignore_na=True).mean() if hl else x.shift().expanding().mean())
    return num/den.replace(0, np.nan)
res = {}
for y, n, pos, lab in (('targets', 'team_tgt', ['WR', 'TE', 'RB'], 'target share'), ('nq_rush', 'team_nq', ['RB'], 'RB carry share')):
    d0 = pg[pg.position.isin(pos)]
    for hl in (1, 2, 3, 4, 6, None):
        pg[f'e_{y}_{hl}'] = ewm_share(y, n, hl)
    ev = pg[pg.position.isin(pos) & (pg.n_prior >= 3) & (pg.season >= 2017)].copy()
    ev = ev[ev[f'e_{y}_None'] >= (0.05 if y == 'targets' else 0.15)]
    act = ev[y].values; vol = ev[n].values
    print(f'\n{lab}: {len(ev)} player-games (3+ prior games this season)')
    for hl in (1, 2, 3, 4, 6, None):
        pred = ev[f'e_{y}_{hl}'].values*vol; print(f'  EWMA half-life {hl}: RMSE {np.sqrt(np.nanmean((act-pred)**2)):.3f}')
    best = None
    cum_vol = g[n].transform(lambda x: x.shift().cumsum()).reindex(ev.index).values
    for hl in (2, 3, 4):
        for k in (0, 25, 50, 100, 200):
            prior = np.where(np.isfinite(ev[f'prev_sh_{y}']) & (ev[f'prev_vol_{y}'] >= 100), ev[f'prev_sh_{y}'], ev[f'e_{y}_None'])
            # recency-weighted share shrunk toward last season by k units of team volume
            sh = (ev[f'e_{y}_{hl}'].values*cum_vol + k*prior)/(cum_vol + k)
            r = np.sqrt(np.nanmean((act - sh*vol)**2))
            if best is None or r < best[2]: best = (hl, k, r)
    print(f'  best: half-life {best[0]}, prior weight {best[1]} team-{"targets" if y == "targets" else "carries"}: RMSE {best[2]:.3f}')
    res[y] = best
pd.to_pickle(res, 'data/cache/nfl/share_proj.pkl')
