import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
from scipy.stats import norm
g = data.load_games()
g = g.sort_values(['date','game_id'])
# one row per game from the home team's perspective
h = g[g.home==1].copy()
print('games', len(h))
# OT rate by season
print('OT rate by season\n', h.groupby('season')['ot'].apply(lambda s: (s>0).mean()).round(3).to_string())
print('overall OT', round((h.ot>0).mean(),4), 'multi-OT share of OT', round((h.ot>1).sum()/(h.ot>0).sum(),3))
# blowout share by season
h['am'] = h['margin'].abs()
print('share |margin|>=20 by season\n', h.groupby('season')['am'].apply(lambda s: (s>=20).mean()).round(3).to_string())
# leave-one-out season net rating (pts diff per 100 poss) for each team -> expected margin
g['net100'] = (g.team_pts - g.opp_pts) / g.poss * 100
g['pace'] = g.pace48
def loo(df, col):
    grp = df.groupby(['season','team_id'])[col]
    s, c = grp.transform('sum'), grp.transform('count')
    return (s - df[col]) / (c - 1)
g['net_loo'] = loo(g, 'net100'); g['pace_loo'] = loo(g, 'pace')
lg_pace = g.groupby('season')['pace'].transform('mean')
opp = g[['game_id','team_id','net_loo','pace_loo']].rename(columns={'team_id':'opp_id','net_loo':'opp_net_loo','pace_loo':'opp_pace_loo'})
gg = g.merge(opp, on=['game_id','opp_id'])
gg = gg[gg.home==1].copy()
gg['exp_pace'] = gg.pace_loo + gg.opp_pace_loo - lg_pace.loc[gg.index]
gg['exp_poss'] = gg.exp_pace
# expected margin: (net diff)/2 per 100 * poss/100 ... use simple regression
X = np.c_[np.ones(len(gg)), (gg.net_loo - gg.opp_net_loo) * gg.exp_poss / 100]
y = gg.margin.values
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
res = y - X @ beta
print('margin model: HCA %.2f, slope %.3f, resid SD %.2f' % (beta[0], beta[1], res.std()))
gg['exp_margin'] = X @ beta
# SD of margin by recent seasons
for s in sorted(gg.season.unique()):
    m = gg.season == s; print(s, 'resid SD %.2f' % res[m].std(), 'pace resid SD %.2f' % (gg.pace[m] - gg.exp_pace[m]).std())
# tails: kurtosis of margin residuals
from scipy.stats import kurtosis, skew
print('margin resid kurtosis', round(kurtosis(res),3), 'skew', round(skew(res),3))
# OT rate vs expected margin bucket
gg['em_b'] = pd.cut(gg.exp_margin.abs(), [0,2,4,6,8,10,14,30])
t = gg.groupby('em_b', observed=True).agg(n=('ot','size'), ot=('ot', lambda s: (s>0).mean()), em=('exp_margin', lambda s: s.abs().mean()))
t['model_2.1pdf'] = [float(np.clip(2.1*norm.pdf(e,0,12),0,0.09)) for e in t.em]
print(t.round(3).to_string())
# regulation tie probability check: P(|margin at end of regulation| == 0) approximated by OT share
# pace: SD of game possessions around exp
pr = gg.pace - gg.exp_pace
print('pace48 resid SD all %.2f' % pr.std(), ' recent(2019+) %.2f' % pr[gg.season>=2019].std())
# pace vs margin correlation and pace vs abs margin
print('corr(pace resid, |margin|) %.3f' % np.corrcoef(pr, gg.margin.abs())[0,1])
# share of 20+ blowouts vs normal model with SD from residuals
for s in [2021, 2022, 2023]:
    m = gg.season == s
    emp = (gg.margin[m].abs() >= 20).mean()
    mod = np.mean([norm.sf(20, e, res[m].std()) + norm.cdf(-20, e, res[m].std()) for e in gg.exp_margin[m]])
    mod12 = np.mean([norm.sf(20, e, 12) + norm.cdf(-20, e, 12) for e in gg.exp_margin[m]])
    print(s, 'blowout20 empirical %.3f model(resid SD) %.3f model(SD12) %.3f' % (emp, mod, mod12))
gg[['game_id','season','exp_margin','exp_pace','margin','pace','ot']].to_pickle('data/cache/game_expect.pkl')
