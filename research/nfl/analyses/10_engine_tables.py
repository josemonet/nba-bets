# Tables the engine samples from: drives per team-game, TD/FG drive rates vs the implied total, target/attempt ratio,
# per-catch yard shapes by position (normalized by the player's average), per-carry yards by position, QB scramble yards.
import sys, json; sys.path.insert(0, 'research/nfl')
import numpy as np, pandas as pd, data
T = data.build(); p = T['plays']; pg = T['player_games']; tv = pd.read_pickle('data/cache/nfl/team_view2.pkl')
dr = p[p.posteam.notna() & p.drive.notna()].groupby(['game_id', 'posteam'])['drive'].nunique().rename('drives').reset_index().rename(columns={'posteam': 'team'})
tv = tv.merge(dr, on=['game_id', 'team'])
fg = pg.groupby(['game_id', 'team'])[['fgm', 'fga', 'xpm']].sum().reset_index(); tv = tv.drop(columns=[c for c in ('fgm', 'fga', 'xpm') if c in tv]).merge(fg, on=['game_id', 'team'])
tv['td'] = tv.pass_td + tv.rush_td
print('drives per team-game: mean %.2f sd %.2f; corr with opponent drives %.3f' % (tv.drives.mean(), tv.drives.std(),
      tv.merge(tv[['game_id', 'team', 'drives']].rename(columns={'team': 'opp', 'drives': 'od'}), on=['game_id', 'opp'])[['drives', 'od']].corr().iloc[0, 1]))
tv['ib'] = pd.cut(tv.implied_pts, [0, 17, 20, 23, 26, 29, 50])
t = tv.groupby('ib', observed=True).apply(lambda d: pd.Series({'implied': d.implied_pts.mean(), 'drives': d.drives.mean(), 'td_rate': d.td.sum()/d.drives.sum(),
     'fg_rate': d.fgm.sum()/d.drives.sum(), 'fga_rate': d.fga.sum()/d.drives.sum(), 'pts': d.pts.mean(), 'pts_sd': d.pts.std()}), include_groups=False)
print(t.round(3).to_string())
b = np.polyfit(tv.implied_pts, tv.td/tv.drives, 1); print('TD rate per drive = %.4f + %.5f x implied' % (b[1], b[0]))
bf = np.polyfit(tv.implied_pts, tv.fga/tv.drives, 1); print('FGA rate per drive = %.4f + %.5f x implied' % (bf[1], bf[0]))
print('FG make rate %.3f; XP per TD %.3f; 2-pt try share %.3f' % (tv.fgm.sum()/tv.fga.sum(), tv.xpm.sum()/tv.td.sum(), 0.0))
tt = pg.groupby(['game_id', 'team'])['targets'].sum().rename('tg').reset_index(); tv = tv.merge(tt, on=['game_id', 'team'])
print('team targets per official pass attempt %.4f' % (tv.tg.sum()/tv.pass_att.sum()))
# shapes
pos = pg.drop_duplicates('player_id').set_index('player_id').position
s = p[~p.two_point_attempt]
c = s[(s.complete_pass == 1) & s.receiver_player_id.notna() & (s.sack == 0)].copy()
c['ry'] = c.receiving_yards.fillna(c.yards_gained); c['pos'] = c.receiver_player_id.map(pos)
c['m'] = c.groupby(['receiver_player_id', 'season'])['ry'].transform('mean'); c['n'] = c.groupby(['receiver_player_id', 'season'])['ry'].transform('size')
qs = np.round(np.linspace(0, 1, 201), 3)
out = {}
for ps_ in ('WR', 'TE', 'RB'):
    z = (c[(c.pos == ps_) & (c.n >= 20)].ry/c[(c.pos == ps_) & (c.n >= 20)].m).values
    out[f'catch_{ps_}'] = np.quantile(z, qs).round(3).tolist()
    print(ps_, 'normalized catch yards: mean %.3f, median %.3f, P(>=2x) %.3f, P(>=3x) %.3f, n %d' % (z.mean(), np.median(z), (z >= 2).mean(), (z >= 3).mean(), len(z)))
ru = s[(s.rush_attempt == 1) & s.rusher_player_id.notna() & (s.qb_kneel == 0)].copy(); ru['pos'] = ru.rusher_player_id.map(pos)
ru['y'] = ru.rushing_yards.fillna(ru.yards_gained)
for ps_, filt in (('RB', (ru.pos == 'RB')), ('QB_design', (ru.pos == 'QB') & (ru.qb_scramble == 0)), ('QB_scramble', (ru.pos == 'QB') & (ru.qb_scramble == 1)), ('WR', ru.pos == 'WR')):
    y = ru[filt].y.values; out[f'carry_{ps_}'] = np.quantile(y, qs).round(2).tolist()
    print(ps_, 'carry yards: mean %.2f median %.1f sd %.2f n %d' % (y.mean(), np.median(y), y.std(), len(y)))
json.dump(out, open('data/cache/nfl/shapes.json', 'w'))
