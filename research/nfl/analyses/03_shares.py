# Player volume shares: game-to-game dispersion (beyond binomial) and the best pregame projection (recency, prior season).
import sys; sys.path.insert(0, 'research/nfl')
import numpy as np, pandas as pd, data
T = data.build(); pg = T['player_games'].copy()
pg = pg[pg.season.notna()]
pg['is_qb'] = (pg.position == 'QB')
pg['nq_rush'] = np.where(pg.is_qb, 0, pg.rush_att)
tt = pg.groupby(['game_id', 'team']).agg(team_tgt=('targets', 'sum'), team_nq=('nq_rush', 'sum'), team_rz_tgt=('rz_tgt', 'sum'),
                                          team_rz_car=('rz_car', 'sum'), team_gl_car=('gl_car', 'sum'), team_air=('air_yds', 'sum'),
                                          team_rec_td=('rec_td', 'sum'), team_rush_td_nq=('rush_td', lambda x: x.sum())).reset_index()
pg = pg.merge(tt, on=['game_id', 'team'])
pg = pg.sort_values(['player_id', 'season', 'week'])
pg.to_pickle('data/cache/nfl/pg_shares.pkl')
def bb_kappa(y, n, p):
    ok = (n > 1) & (p > 0) & (p < 1); y, n, p = y[ok], n[ok], p[ok]
    num = ((y - n*p)**2).sum() - (n*p*(1-p)).sum(); den = (n*(n-1)*p*(1-p)).sum(); rho = num/den
    return rho, (1/rho - 1) if rho > 0 else np.inf
# dispersion within player-season (leave-one-out share), players with a real role
for lab, ycol, ncol, filt in (('targets (WR/TE/RB)', 'targets', 'team_tgt', pg.position.isin(['WR', 'TE', 'RB'])),
                              ('WR targets', 'targets', 'team_tgt', pg.position == 'WR'), ('TE targets', 'targets', 'team_tgt', pg.position == 'TE'),
                              ('RB targets', 'targets', 'team_tgt', pg.position == 'RB'), ('RB carries', 'nq_rush', 'team_nq', pg.position == 'RB')):
    d = pg[filt].copy(); key = ['player_id', 'season', 'team']
    gb = d.groupby(key); S, N, C = gb[ycol].transform('sum'), gb[ncol].transform('sum'), gb[ycol].transform('size')
    d['p_loo'] = (S - d[ycol])/(N - d[ncol]).replace(0, np.nan)
    d = d[(C >= 8) & (S/N >= 0.08)]
    rho, kap = bb_kappa(d[ycol].values.astype(float), d[ncol].values.astype(float), d.p_loo.values)
    print(f'{lab:20s} beta-binomial rho {rho:.4f} kappa {kap:.1f}  (n={len(d)})')
