import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
df = data.player_games()
p = df[df.played==1].copy()
gm = df.drop_duplicates(['game_id','team_id'])[['game_id','team_id','opp_id','season','pace48']]
def loo(d, by, col):
    gb = d.groupby(by)[col]; return (gb.transform('sum') - d[col])/(gb.transform('count') - 1)
gm['tpace'] = loo(gm, ['team_id','season'], 'pace48')
opp = gm[['game_id','team_id','tpace']].rename(columns={'team_id':'opp_id','tpace':'opace'})
gm = gm.merge(opp, on=['game_id','opp_id'])
lgp = gm.groupby('season')['pace48'].transform('mean')
gm['exp_pace'] = gm.tpace + gm.opace - lgp
gm['xf'] = gm.exp_pace/gm.tpace
p = p.merge(gm[['game_id','team_id','xf','tpace']], on=['game_id','team_id'])
key = ['player_id','season','team_id']
for s in ('pts','reb','ast','fg3m','fga','fta','stl','blk','tov'):
    S = p.groupby(key)[s].transform('sum'); M = p.groupby(key)['min'].transform('sum')
    base = (S - p[s])/(M - p['min'])*p['min']
    ok = (base > 0.5) & (p.groupby(key)['min'].transform('size') >= 30)
    X = np.log(p.xf[ok]); Y = np.log((p[s][ok]+0.5)/(base[ok]+0.5))
    b = np.polyfit(X, Y, 1)[0]
    # ratio method by bins of expected pace factor
    bins = pd.cut(p.xf[ok], [0.9, 0.96, 0.98, 1.0, 1.02, 1.04, 1.1])
    r = (p[s][ok].groupby(bins, observed=True).sum()/base[ok].groupby(bins, observed=True).sum())
    print(f'{s:5s} elasticity to expected pace {b:.2f} | ratio by exp-pace bin: ' + ' '.join(f'{i.mid:.2f}:{v:.3f}' for i, v in r.items()))
