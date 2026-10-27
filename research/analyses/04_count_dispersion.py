import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
df = data.player_games()
p = df[(df.played==1)].copy()
p['fg2a'] = p.fga - p.fg3a; p['fg2m'] = p.fgm - p.fg3m
tp = p.groupby(['team_id','season'])['pace48'].transform('mean')
p['pf_'] = p.pace48 / tp          # pace factor vs team season average
grp = p.groupby(['player_id','season','team_id'])
p['n_g'] = grp['min'].transform('size'); p['M'] = grp['min'].transform('sum')
p = p[(p.n_g >= 40) & (p.M/p.n_g >= 15) & (p['min'] >= 6)]
stats = ['fga','fg3a','fg2a','fta','reb','oreb','dreb','ast','stl','blk','tov','pf','pts']
R = {}
exp_mu = {}
for s in stats:
    S = p.groupby(['player_id','season','team_id'])[s].transform('sum')
    # leave-one-out rate per minute, scaled by this game's minutes and pace
    rate = (S - p[s]) / (p.M - p['min'])
    mu = rate * p['min'] * p.pf_
    exp_mu[s] = mu
    r = p[s] - mu
    R[s] = r
    b = pd.qcut(mu, 10, duplicates='drop')
    t = pd.DataFrame({'mu':mu,'r2':r**2,'y':p[s]}).groupby(b, observed=True).agg(mu=('mu','mean'), var=('r2','mean'), n=('mu','size'))
    t['D'] = t['var']/t['mu']
    # fit var = a*mu + b*mu^2 (weighted LS over bins)
    A = np.c_[t.mu, t.mu**2]; coef, *_ = np.linalg.lstsq(A, t['var'], rcond=None)
    print(f"{s:5s} D by mu-decile: " + ' '.join(f"{m:.1f}:{d:.2f}" for m, d in zip(t.mu, t.D)) + f"  | fit a={coef[0]:.3f} b={coef[1]:.4f} (cv_game={np.sqrt(max(coef[1],0)):.3f})")
# residual correlation matrix (standardized by sqrt(mu))
Z = pd.DataFrame({s: R[s]/np.sqrt(np.maximum(exp_mu[s], 0.3)) for s in ['fga','fta','fg3a','reb','ast','stl','blk','tov','pf','pts']})
print(Z.corr().round(3).to_string())
p[['player_id','season','team_id','game_id','min','pf_']].assign(**{f'r_{s}': R[s] for s in stats}, **{f'mu_{s}': exp_mu[s] for s in stats}).to_pickle('data/cache/disp.pkl')
