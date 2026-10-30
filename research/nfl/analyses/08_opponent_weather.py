# Opponent defense (team level and by position), weather and home field: what moves player volume and efficiency beyond the market lines.
import sys; sys.path.insert(0, 'research/nfl')
import numpy as np, pandas as pd, data
T = data.build(); tg = pd.read_pickle('data/cache/nfl/team_view2.pkl'); pg = T['player_games']
tg = tg.sort_values(['season', 'week'])
# defense season-to-date per-game allowed (passing yards, rushing yards, pass attempts faced), with games played, before this game
allowed = tg[['game_id', 'season', 'week', 'opp', 'pass_yds', 'rush_yds', 'pass_att', 'rush_att', 'sacks', 'dropbacks']].rename(columns={'opp': 'defense'})
allowed = allowed.sort_values(['defense', 'season', 'week'])
gd = allowed.groupby(['defense', 'season'])
for c in ('pass_yds', 'rush_yds', 'pass_att', 'sacks', 'dropbacks'):
    allowed[f'a_{c}'] = (gd[c].cumsum() - allowed[c])
allowed['a_n'] = gd.cumcount()
tg = tg.merge(allowed[['game_id', 'defense', 'a_pass_yds', 'a_rush_yds', 'a_pass_att', 'a_sacks', 'a_dropbacks', 'a_n']], left_on=['game_id', 'opp'], right_on=['game_id', 'defense'])
lg = tg.groupby('season')[['pass_yds', 'rush_yds', 'pass_att']].transform('mean')
d = tg[tg.a_n >= 3].copy()
# residual of team passing yards after the market (implied points) and pace: does the opponent's pass defense add information?
from numpy.linalg import lstsq
for y, a in (('pass_yds', 'a_pass_yds'), ('rush_yds', 'a_rush_yds')):
    opp_rate = d[a]/d.a_n
    X = np.c_[np.ones(len(d)), d.implied_pts, d.exp_margin, d.plays_pre]
    b0, *_ = lstsq(X, d[y], rcond=None); r0 = d[y] - X@b0
    X1 = np.c_[X, opp_rate]; b1, *_ = lstsq(X1, d[y], rcond=None); r1 = d[y] - X1@b1
    print(f'{y}: market-only resid SD {r0.std():.2f}; + opponent allowed/game: coef {b1[-1]:.3f}, resid SD {r1.std():.2f} ({(1-r1.var()/r0.var())*100:.2f}% variance explained)')
# weather (outdoor games): wind and temperature effects on passing yards and attempts beyond the closing total
o = d[d.roof.isin(['outdoors', 'open'])].copy()
o['wb'] = pd.cut(o.wind, [-1, 5, 10, 15, 20, 60]); o['tb'] = pd.cut(o.temp, [-30, 32, 45, 60, 75, 120])
X = np.c_[np.ones(len(d)), d.implied_pts, d.exp_margin]
b, *_ = lstsq(X, d.pass_yds, rcond=None)
o['res_py'] = o.pass_yds - np.c_[np.ones(len(o)), o.implied_pts, o.exp_margin]@b
b2, *_ = lstsq(X, d.rush_yds, rcond=None); o['res_ry'] = o.rush_yds - np.c_[np.ones(len(o)), o.implied_pts, o.exp_margin]@b2
o['res_pts'] = o.pts - o.implied_pts
print('\nby wind (mph), outdoor games: residual passing yards / rushing yards / points vs the closing lines')
print(o.groupby('wb', observed=True).agg(n=('res_py', 'size'), pass_yds=('res_py', 'mean'), rush_yds=('res_ry', 'mean'), pts=('res_pts', 'mean')).round(2).to_string())
print('by temperature (F):'); print(o.groupby('tb', observed=True).agg(n=('res_py', 'size'), pass_yds=('res_py', 'mean'), rush_yds=('res_ry', 'mean'), pts=('res_pts', 'mean')).round(2).to_string())
dome = d.roof.isin(['dome', 'closed']); d['res_py'] = d.pass_yds - np.c_[np.ones(len(d)), d.implied_pts, d.exp_margin]@b
print('dome/closed vs outdoor passing-yard residual: %.2f vs %.2f' % (d.res_py[dome].mean(), d.res_py[~dome].mean()))
# home field on team passing and rushing beyond the lines
print('home vs away residual passing yards %.2f vs %.2f; rushing %.2f vs %.2f' % (d.res_py[d.home == 1].mean(), d.res_py[d.home == 0].mean(),
      (d.rush_yds - np.c_[np.ones(len(d)), d.implied_pts, d.exp_margin]@b2)[d.home == 1].mean(), (d.rush_yds - np.c_[np.ones(len(d)), d.implied_pts, d.exp_margin]@b2)[d.home == 0].mean()))
# defense vs position: receiving yards allowed to WR / TE / RB as a share of that defense's passing yards allowed
pgx = pg[pg.position.isin(['WR', 'TE', 'RB'])]
pos_allowed = pgx.groupby(['game_id', 'opp', 'position'])['rec_yds'].sum().unstack(fill_value=0).reset_index()
pos_allowed = pos_allowed.merge(tg[['game_id', 'opp', 'season', 'week']].drop_duplicates(['game_id', 'opp']), on=['game_id', 'opp']).sort_values(['opp', 'season', 'week'])
gp = pos_allowed.groupby(['opp', 'season'])
for c in ('WR', 'TE', 'RB'):
    pos_allowed[f'pre_{c}'] = gp[c].cumsum() - pos_allowed[c]
pos_allowed['n'] = gp.cumcount()
pa = pos_allowed[pos_allowed.n >= 4].copy()
tot = pa.pre_WR + pa.pre_TE + pa.pre_RB
for c in ('WR', 'TE', 'RB'):
    sh_pre = pa[f'pre_{c}']/tot; sh_now = pa[c]/(pa.WR + pa.TE + pa.RB).replace(0, np.nan)
    lg_sh = (pa[c].sum()/(pa.WR + pa.TE + pa.RB).sum())
    ok = sh_now.notna()
    c_ = np.corrcoef(sh_pre[ok] - lg_sh, sh_now[ok] - lg_sh)[0, 1]
    print(f'defense-vs-position {c}: correlation of season-to-date share allowed with next-game share allowed = {c_:.3f}')
