# Game level against the closing line: margin and total spread, team points around the implied team total, key numbers,
# overtime, and how team points split into TDs and field goals.
import sys; sys.path.insert(0, 'research/nfl')
import numpy as np, pandas as pd, data
from scipy.stats import norm
T = data.build(); tg = T['team_games']; g = T['games']
g = g[g.result.notna() & g.spread_line.notna()].copy()
g['res_margin'] = g.result - g.spread_line          # home margin minus the closing home spread (positive = home beat the line)
g['res_total'] = g.total - g.total_line
print('games', len(g), '| margin resid SD %.2f | total resid SD %.2f | corr %.3f' % (g.res_margin.std(), g.res_total.std(), np.corrcoef(g.res_margin, g.res_total)[0, 1]))
for lo, hi in ((0, 3), (3, 7), (7, 10.5), (10.5, 30)):
    m = g.spread_line.abs().between(lo, hi, inclusive='left'); print(f'  |spread| {lo}-{hi}: n {m.sum()} margin resid SD {g.res_margin[m].std():.2f}')
for lo, hi in ((30, 41), (41, 45), (45, 49), (49, 70)):
    m = g.total_line.between(lo, hi, inclusive='left'); print(f'  total {lo}-{hi}: n {m.sum()} total resid SD {g.res_total[m].std():.2f} mean resid {g.res_total[m].mean():+.2f}')
print('by season margin SD / total SD:', {int(s): (round(d.res_margin.std(), 1), round(d.res_total.std(), 1)) for s, d in g.groupby('season')})
# key numbers: frequency of final margins
am = g.result.abs(); vc = am.value_counts(normalize=True).sort_index()
print('final |margin| frequencies (%):', {int(k): round(v*100, 1) for k, v in vc.items() if k <= 24})
print('OT share %.3f; ties %.4f' % (g.overtime.mean(), (g.result == 0).mean()))
# team points around implied
tv = tg[tg.pts.notna() & tg.implied_pts.notna()].copy(); tv['res'] = tv.pts - tv.implied_pts
tv['ib'] = pd.cut(tv.implied_pts, [0, 17, 20, 23, 26, 29, 50])
print(tv.groupby('ib', observed=True)['res'].agg(['mean', 'std', 'size']).round(2).to_string())
pr = tv.merge(tv[['game_id', 'team', 'res']].rename(columns={'team': 'opp', 'res': 'opp_res'}), on=['game_id', 'opp'])
print('corr of the two teams\' points residuals %.3f' % np.corrcoef(pr.res, pr.opp_res)[0, 1])
# points -> TDs and FGs
tv['td'] = tv.pass_td + tv.rush_td
fg = T['player_games'].groupby(['game_id', 'team'])[['fgm', 'fga', 'xpm']].sum().reset_index()
tv = tv.merge(fg, on=['game_id', 'team'], how='left')
print('team TDs per point %.4f; mean TDs %.2f sd %.2f; FGM %.2f; pass-TD share %.3f' % ((tv.td/tv.pts.replace(0, np.nan)).mean(), tv.td.mean(), tv.td.std(), tv.fgm.mean(), tv.pass_td.sum()/tv.td.sum()))
tv['pb'] = pd.cut(tv.implied_pts, [0, 17, 20, 23, 26, 29, 50])
print(tv.groupby('pb', observed=True)[['td', 'fgm', 'pass_td', 'rush_td']].mean().round(2).to_string())
# pass-TD share vs realized margin
tv['mb'] = pd.cut(tv.margin, [-60, -14, -7, 0, 7, 14, 60])
print('pass-TD share by realized margin:', tv.groupby('mb', observed=True).apply(lambda d: round(d.pass_td.sum()/max(d.td.sum(), 1), 3), include_groups=False).to_dict())
tv.to_pickle('data/cache/nfl/team_view.pkl')
