import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
df = data.player_games()
key = ['team_id','season']
# team-game list
tg = df[['game_id','team_id','season','date']].drop_duplicates(['game_id','team_id'])
pl = df[df.played==1]
# key players: >=20 games and >=26 mpg for the team-season
agg = pl.groupby(['player_id','team_id','season']).agg(gp=('min','size'), mpg=('min','mean'), fga=('fga','sum'), ast=('ast','sum'), reb=('reb','sum'), M=('min','sum'),
        first=('date','min'), last=('date','max'))
agg['fga36'] = agg.fga/agg.M*36; agg['ast36'] = agg.ast/agg.M*36; agg['reb36'] = agg.reb/agg.M*36
keyp = agg[(agg.gp>=20)&(agg.mpg>=26)].reset_index()
print('key player-seasons', len(keyp))
# for each key player: team games in tenure window where he did not play
played = set(zip(pl.player_id, pl.game_id))
rows = []
tg_by = {k: v for k, v in tg.groupby(['team_id','season'])}
for r in keyp.itertuples():
    games = tg_by[(r.team_id, r.season)]
    games = games[(games.date>=r.first)&(games.date<=r.last)]
    for gid in games.game_id.values:
        rows.append((r.player_id, r.team_id, r.season, gid, int((r.player_id, gid) in played)))
st = pd.DataFrame(rows, columns=['x_id','team_id','season','game_id','x_played'])
print('key player team-games', len(st), 'out share', round(1-st.x_played.mean(),3))
# teammates' lines in those games
tm = pl[['player_id','team_id','season','game_id','min','fga','fta','fg3a','ast','reb','pts','starter']]
m = st.merge(tm, on=['team_id','season','game_id'])
m = m[m.player_id != m.x_id]
# per (x, teammate, season): totals in X-in vs X-out games
g = m.groupby(['x_id','player_id','team_id','season','x_played']).agg(n=('min','size'), M=('min','sum'), fga=('fga','sum'), fta=('fta','sum'), ast=('ast','sum'), reb=('reb','sum'), pts=('pts','sum'), st=('starter','mean'))
w = g.unstack('x_played')
w.columns = [f'{a}_{"in" if b==1 else "out"}' for a, b in w.columns]
w = w.dropna()
w = w[(w.n_out>=3)&(w.n_in>=10)&(w.M_in/w.n_in>=10)]
for s in ('fga','fta','ast','reb','pts'):
    w[f'{s}36_in'] = w[f'{s}_in']/w.M_in*36; w[f'{s}36_out'] = w[f'{s}_out']/w.M_out*36
w['mpg_in'] = w.M_in/w.n_in; w['mpg_out'] = w.M_out/w.n_out
w = w.reset_index().merge(keyp[['player_id','team_id','season','fga36','ast36','reb36','mpg']].rename(columns={'player_id':'x_id','fga36':'x_fga36','ast36':'x_ast36','reb36':'x_reb36','mpg':'x_mpg'}), on=['x_id','team_id','season'])
print('pairs', len(w))
# 1) minutes redistribution by teammate base minutes
w['mb'] = pd.cut(w.mpg_in, [10,18,24,30,36,48])
w['d_min'] = w.mpg_out - w.mpg_in
w['started_more'] = (w.st_out - w.st_in) > 0.5
print(w.groupby(['mb','started_more'], observed=True)['d_min'].agg(['mean','size']).round(2).to_string())
# 2) rate ratios out/in by teammate rate level (weighted by out-minutes)
for s in ('fga','ast','reb','pts','fta'):
    w[f'r_{s}'] = w[f'{s}36_out']/w[f'{s}36_in']
wt = np.minimum(w.M_out, 400)
for s in ('fga','ast','reb','pts'):
    w['lvl'] = pd.qcut(w[f'{s}36_in'], 5)
    t = w.groupby('lvl', observed=True).apply(lambda d: pd.Series({'ratio': np.average(d[f'r_{s}'], weights=np.minimum(d.M_out,400)), 'n': len(d)}), include_groups=False)
    print(s, 'rate ratio (X out / X in) by teammate rate quintile:', ' '.join(f'{i.left:.1f}-{i.right:.1f}:{v:.3f}' for i, v in zip(t.index, t.ratio)))
# 3) keep: how much of X's per-game FGA is absorbed through teammates' higher per-minute rates
# per (x, game set): sum_j mpg_out_j * (fga36_out - fga36_in)/36 vs X's fga per game
w['abs_fga'] = w.mpg_out*(w.fga36_out - w.fga36_in)/36
w['abs_ast'] = w.mpg_out*(w.ast36_out - w.ast36_in)/36
w['abs_reb'] = w.mpg_out*(w.reb36_out - w.reb36_in)/36
xs = w.groupby(['x_id','team_id','season']).agg(abs_fga=('abs_fga','sum'), abs_ast=('abs_ast','sum'), abs_reb=('abs_reb','sum'), x_fga36=('x_fga36','first'), x_ast36=('x_ast36','first'), x_reb36=('x_reb36','first'), x_mpg=('x_mpg','first'), k=('abs_fga','size'))
xs['x_fga_pg'] = xs.x_fga36*xs.x_mpg/36; xs['x_ast_pg'] = xs.x_ast36*xs.x_mpg/36; xs['x_reb_pg'] = xs.x_reb36*xs.x_mpg/36
for s in ('fga','ast','reb'):
    print(s, 'absorbed via teammates rate increase / X per game: median %.2f  mean %.2f (n=%d)' % ((xs[f'abs_{s}']/xs[f'x_{s}_pg']).median(), (xs[f'abs_{s}'].sum()/xs[f'x_{s}_pg'].sum()), len(xs)))
# by X usage level
xs['xb'] = pd.qcut(xs.x_fga36, 4)
print(xs.groupby('xb', observed=True).apply(lambda d: d.abs_fga.sum()/d.x_fga_pg.sum(), include_groups=False).round(3).to_string())
# 4) tilt fit: bump-1 = c * fga36^(tilt-1); choose tilt minimizing weighted SSE within each X-set
best = []
for tilt in (0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0, 2.5):
    sse = 0
    for _, d in w.groupby(['x_id','team_id','season']):
        if len(d) < 3: continue
        y = d.r_fga.values - 1; xv = d.fga36_in.values**(tilt-1); wts = np.minimum(d.M_out.values, 400)
        c = np.sum(wts*xv*y)/np.sum(wts*xv*xv)
        sse += np.sum(wts*(y - c*xv)**2)
    best.append((tilt, sse))
print('tilt SSE', [(t, round(s, 1)) for t, s in best])
w.to_pickle('data/cache/usage_pairs.pkl')
