# Per-play outcome distributions (the source of yardage-prop skew), game-level overdispersion of yards given volume,
# and shrinkage of efficiency (catch rate, yards per catch, yards per carry).
import sys; sys.path.insert(0, 'research/nfl')
import numpy as np, pandas as pd, data
T = data.build(); p = T['plays']; pg = T['player_games']
pos = pg.drop_duplicates('player_id').set_index('player_id').position
s = p[~p.two_point_attempt]
tg = s[(s.pass_attempt == 1) & (s.sack == 0) & s.receiver_player_id.notna()].copy()
tg['pos'] = tg.receiver_player_id.map(pos)
tg['ry'] = np.where(tg.complete_pass == 1, tg.receiving_yards.fillna(tg.yards_gained), 0.0)
tg['ay'] = tg.air_yards.fillna(0)
tg['ab'] = pd.cut(tg.ay, [-99, 0, 4, 8, 12, 18, 99])
print('per-target outcomes by air-yards bucket (all receivers):')
t = tg.groupby('ab', observed=True).apply(lambda d: pd.Series({'n': len(d), 'catch': d.complete_pass.mean(), 'ypc_mean': d.ry[d.complete_pass == 1].mean(),
    'ypc_med': d.ry[d.complete_pass == 1].median(), 'p20': (d.ry >= 20).mean(), 'p40': (d.ry >= 40).mean()}), include_groups=False)
print(t.round(3).to_string())
# yards per catch distribution normalized by the player-season mean (shape for simulation)
c = tg[tg.complete_pass == 1].copy()
key = ['receiver_player_id', 'season']
c['ypr_ps'] = c.groupby(key)['ry'].transform('mean'); c['n_ps'] = c.groupby(key)['ry'].transform('size')
cc = c[c.n_ps >= 25]
z = cc.ry/cc.ypr_ps
print('normalized yards-per-catch quantiles (catch yards / his season mean):', dict(zip([.05, .1, .25, .5, .75, .9, .95, .99], np.quantile(z, [.05, .1, .25, .5, .75, .9, .95, .99]).round(3))))
print('  CV of yards per catch by position:', cc.groupby(cc.receiver_player_id.map(pos)).apply(lambda d: round(float((d.ry/d.ypr_ps).std()), 3), include_groups=False).to_dict())
# game-level overdispersion: Var(game receiving yards | targets) vs i.i.d. per-target variance
gy = tg.groupby(['game_id', 'receiver_player_id', 'season']).agg(t=('ry', 'size'), y=('ry', 'sum'), yy=('ry', lambda x: (x**2).sum())).reset_index()
ps = gy.groupby(['receiver_player_id', 'season']).agg(nt=('t', 'sum'), ny=('y', 'sum'), nyy=('yy', 'sum'), ng=('t', 'size'))
gy = gy.join(ps, on=['receiver_player_id', 'season'])
gy = gy[(gy.ng >= 8) & (gy.nt >= 50)]
mu = (gy.ny - gy.y)/(gy.nt - gy.t); m2 = (gy.nyy - gy.yy)/(gy.nt - gy.t); var1 = m2 - mu**2
ratio = ((gy.y - gy.t*mu)**2).sum()/(gy.t*var1).sum()
print('receiving yards: observed game variance / i.i.d. per-target variance = %.3f (n=%d player-games)' % (ratio, len(gy)))
# rushing per carry
ru = s[(s.rush_attempt == 1) & s.rusher_player_id.notna() & (s.qb_kneel == 0)].copy(); ru['pos'] = ru.rusher_player_id.map(pos)
ru['y'] = ru.rushing_yards.fillna(ru.yards_gained)
for ps_ in ('RB', 'QB', 'WR'):
    d = ru[ru.pos == ps_].y
    print(f'{ps_} carries: n {len(d)} mean {d.mean():.2f} median {d.median():.0f} sd {d.std():.2f} P(<0) {(d < 0).mean():.3f} P(10+) {(d >= 10).mean():.3f} P(20+) {(d >= 20).mean():.3f} P(40+) {(d >= 40).mean():.4f}')
gr = ru[ru.pos == 'RB'].groupby(['game_id', 'rusher_player_id', 'season']).agg(t=('y', 'size'), y=('y', 'sum'), yy=('y', lambda x: (x**2).sum())).reset_index()
psr = gr.groupby(['rusher_player_id', 'season']).agg(nt=('t', 'sum'), ny=('y', 'sum'), nyy=('yy', 'sum'), ng=('t', 'size'))
gr = gr.join(psr, on=['rusher_player_id', 'season']); gr = gr[(gr.ng >= 8) & (gr.nt >= 80)]
mu = (gr.ny - gr.y)/(gr.nt - gr.t); m2 = (gr.nyy - gr.yy)/(gr.nt - gr.t); var1 = m2 - mu**2
print('RB rushing yards: observed game variance / i.i.d. per-carry variance = %.3f (n=%d)' % (((gr.y - gr.t*mu)**2).sum()/(gr.t*var1).sum(), len(gr)))
# efficiency shrinkage: predict rest-of-season efficiency from season-to-date + prior season (empirical Bayes k in plays)
def shrink_k(df, key_player, val, w, prior_col, ks):
    out = []
    for k in ks:
        pred = (df.cum_v + k*df[prior_col])/(df.cum_w + k)
        e = df[val]/df[w] - pred; out.append((k, float(np.average(e**2, weights=df[w]))))
    return min(out, key=lambda t: t[1]), out
# catch rate, yards per target (receivers) and yards per carry (RBs) at the player-game level
pgx = pg[pg.season.notna()].sort_values(['player_id', 'season', 'week']).copy()
for v, w, pos_, lab, ks in (('rec', 'targets', ['WR', 'TE', 'RB'], 'catch rate', (0, 20, 40, 80, 160, 320)),
                            ('rec_yds', 'targets', ['WR', 'TE', 'RB'], 'yards per target', (0, 20, 40, 80, 160, 320)),
                            ('rush_yds', 'rush_att', ['RB'], 'yards per carry', (0, 25, 50, 100, 200, 400, 800))):
    d = pgx[pgx.position.isin(pos_)].copy()
    gs = d.groupby(['player_id', 'season'])
    d['cum_v'] = gs[v].cumsum() - d[v]; d['cum_w'] = gs[w].cumsum() - d[w]
    seas = d.groupby(['player_id', 'season'])[[v, w]].sum(); seas['r'] = seas[v]/seas[w].replace(0, np.nan)
    prev = seas[['r', w]].copy(); prev.index = prev.index.set_levels(prev.index.levels[1] + 1, level=1)
    d = d.join(prev.rename(columns={'r': 'prev_r', w: 'prev_w'}), on=['player_id', 'season'])
    lg = (d[v].sum()/d[w].sum())
    d['prior'] = np.where(d.prev_w >= (30 if w == 'targets' else 50), d.prev_r, lg)
    d = d[(d[w] > 0) & (d.cum_w >= 10)]
    best, grid = shrink_k(d, 'player_id', v, w, 'prior', ks)
    print(f'{lab}: best prior weight k={best[0]} {w} (weighted MSE {best[1]:.4f}) | grid', [(k, round(m, 4)) for k, m in grid])
