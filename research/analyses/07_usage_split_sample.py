import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
df = data.player_games()
pl = df[df.played==1]
tg = df[['game_id','team_id','season','date']].drop_duplicates(['game_id','team_id'])
agg = pl.groupby(['player_id','team_id','season']).agg(gp=('min','size'), mpg=('min','mean'), fga=('fga','sum'), ast=('ast','sum'), reb=('reb','sum'), pts=('pts','sum'), M=('min','sum'), first=('date','min'), last=('date','max'))
for s in ('fga','ast','reb','pts'): agg[s+'36'] = agg[s]/agg.M*36
keyp = agg[(agg.gp>=20)&(agg.mpg>=26)].reset_index()
played = set(zip(pl.player_id, pl.game_id))
tg_by = {k: v for k, v in tg.groupby(['team_id','season'])}
rows = []
for r in keyp.itertuples():
    games = tg_by[(r.team_id, r.season)]; games = games[(games.date>=r.first)&(games.date<=r.last)]
    for gid in games.game_id.values: rows.append((r.player_id, r.team_id, r.season, gid, int((r.player_id, gid) in played)))
st = pd.DataFrame(rows, columns=['x_id','team_id','season','game_id','x_played'])
tm = pl[['player_id','team_id','season','game_id','date','min','fga','ast','reb','pts','starter']]
m = st.merge(tm, on=['team_id','season','game_id']); m = m[m.player_id != m.x_id].sort_values('date')
# split X-in games alternately into A (classify) and B (baseline)
m['k'] = m.groupby(['x_id','player_id','team_id','season','x_played']).cumcount()
m['part'] = np.where(m.x_played==0, 'out', np.where(m.k % 2 == 0, 'A', 'B'))
g = m.groupby(['x_id','player_id','team_id','season','part']).agg(n=('min','size'), M=('min','sum'), fga=('fga','sum'), ast=('ast','sum'), reb=('reb','sum'), pts=('pts','sum'), st=('starter','mean')).unstack('part')
g.columns = [f'{a}_{b}' for a, b in g.columns]; g = g.dropna()
g = g[(g.n_out>=3)&(g.n_A>=6)&(g.n_B>=6)&(g.M_A/g.n_A>=10)&(g.M_B/g.n_B>=10)].reset_index()
g = g.merge(keyp[['player_id','team_id','season','fga36','ast36','reb36','pts36','mpg']].rename(columns=lambda c: 'x_'+c if c not in ('team_id','season') else c).rename(columns={'x_player_id':'x_id'}), on=['x_id','team_id','season'])
print('pairs', len(g))
res = {}
for s in ('fga','ast','reb','pts'):
    g[f'{s}36_A'] = g[f'{s}_A']/g.M_A*36; g[f'{s}36_B'] = g[f'{s}_B']/g.M_B*36; g[f'{s}36_out'] = g[f'{s}_out']/g.M_out*36
    wts = np.minimum(g.M_out, 400)
    g['lvl'] = pd.qcut(g[f'{s}36_A'], 5, duplicates='drop')
    t = g.groupby('lvl', observed=True).apply(lambda d: pd.Series({
        'ratio': np.average(d[f'{s}36_out'], weights=np.minimum(d.M_out,400))/np.average(d[f'{s}36_B'], weights=np.minimum(d.M_out,400)),
        'abs': np.average(d[f'{s}36_out']-d[f'{s}36_B'], weights=np.minimum(d.M_out,400)), 'n': len(d)}), include_groups=False)
    print(s, 'split-sample out/in by teammate level: ' + ' | '.join(f'{i.left:.1f}-{i.right:.1f}: x{v['ratio']:.3f} ({v['abs']:+.2f}/36)' for i, v in t.iterrows()))
# by X usage quartile: absolute per-36 increase of teammates and the total absorbed share
g['xq'] = pd.qcut(g.x_fga36, 4)
t = g.groupby('xq', observed=True).apply(lambda d: pd.Series({'d_fga36': np.average(d.fga36_out-d.fga36_B, weights=np.minimum(d.M_out,400)),
     'd_ast36': np.average(d.ast36_out-d.ast36_B, weights=np.minimum(d.M_out,400)), 'd_pts36': np.average(d.pts36_out-d.pts36_B, weights=np.minimum(d.M_out,400)),
     'x_fga36': d.x_fga36.mean(), 'n': len(d)}), include_groups=False)
print(t.round(3).to_string())
# teammates' absolute per-36 bump as a fraction of X's per-36 rate, by X's usage share: d_fga36_j / x_fga36 ~ const?
g['f_fga'] = (g.fga36_out - g.fga36_B)/g.x_fga36
g['f_ast'] = (g.ast36_out - g.ast36_B)/g.x_ast36
print('per-teammate per-36 bump as share of X per-36 rate: fga %.4f  ast %.4f' % (np.average(g.f_fga, weights=np.minimum(g.M_out,400)), np.average(g.f_ast, weights=np.minimum(g.M_out,400))))
# assists: does the bump concentrate on playmakers? classify by teammate ast36_A
g['alvl'] = pd.qcut(g.ast36_A, 4)
print(g.groupby('alvl', observed=True).apply(lambda d: pd.Series({'d_ast36': np.average(d.ast36_out-d.ast36_B, weights=np.minimum(d.M_out,400)), 'n': len(d)}), include_groups=False).round(3).to_string())
# assists when X is a primary playmaker (x_ast36 >= 7)
pm = g[g.x_ast36>=7]
print('X playmaker (ast36>=7):', len(pm), 'teammate ast36 bump by level:')
print(pm.groupby('alvl', observed=True).apply(lambda d: pd.Series({'d_ast36': np.average(d.ast36_out-d.ast36_B, weights=np.minimum(d.M_out,400)), 'ratio': np.average(d.ast36_out, weights=np.minimum(d.M_out,400))/np.average(d.ast36_B, weights=np.minimum(d.M_out,400)), 'n': len(d)}), include_groups=False).round(3).to_string())
# rebounds when X is a big (x_reb36 >= 10)
bg = g[g.x_reb36>=10]; bg = bg.assign(rlvl=pd.qcut(bg.reb36_A, 4))
print('X big (reb36>=10):', len(bg))
print(bg.groupby('rlvl', observed=True).apply(lambda d: pd.Series({'d_reb36': np.average(d.reb36_out-d.reb36_B, weights=np.minimum(d.M_out,400)), 'ratio': np.average(d.reb36_out, weights=np.minimum(d.M_out,400))/np.average(d.reb36_B, weights=np.minimum(d.M_out,400)), 'n': len(d)}), include_groups=False).round(3).to_string())
g.to_pickle('data/cache/usage_split.pkl')
