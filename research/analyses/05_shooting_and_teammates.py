import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, data
df = data.player_games()
p = df[(df.played==1)].copy()
p['fg2a'] = p.fga - p.fg3a; p['fg2m'] = p.fgm - p.fg3m
key = ['player_id','season','team_id']
grp = p.groupby(key)
p['n_g'] = grp['min'].transform('size'); p['M'] = grp['min'].transform('sum')
p = p[(p.n_g >= 40) & (p.M/p.n_g >= 15)]
def bb_rho(made, att, key_df):
    S_m = key_df.groupby(key)[made].transform('sum'); S_a = key_df.groupby(key)[att].transform('sum')
    n = key_df[att].values.astype(float); m = key_df[made].values.astype(float)
    pr = ((S_m - key_df[made]) / (S_a - key_df[att]).replace(0, np.nan)).values
    ok = (n > 0) & np.isfinite(pr) & (pr > 0) & (pr < 1)
    n, m, pr = n[ok], m[ok], pr[ok]
    num = ((m - n*pr)**2).sum() - (n*pr*(1-pr)).sum()
    den = (n*(n-1)*pr*(1-pr)).sum()
    rho = num/den; return rho, (1/rho - 1) if rho > 0 else np.inf
for made, att in (('fg2m','fg2a'), ('fg3m','fg3a'), ('ftm','fta'), ('fg3a','fga')):
    rho, kap = bb_rho(made, att, p)
    print(f'{made}/{att}: rho={rho:.4f} kappa={kap:.0f}')
# by era (3pt revolution)
for lo, hi in ((2010, 2015), (2016, 2019), (2020, 2023)):
    q = p[(p.season>=lo)&(p.season<=hi)]
    out = []
    for made, att in (('fg2m','fg2a'), ('fg3m','fg3a'), ('ftm','fta'), ('fg3a','fga')):
        rho, kap = bb_rho(made, att, q); out.append(f'{made}/{att} kappa={kap:.0f}')
    print(lo, hi, ' | '.join(out))
# ---- team-level correlations among teammates (residuals standardized)
d = pd.read_pickle('data/cache/disp.pkl')
d = d.merge(p[['player_id','game_id','fgm','fga','fg3m','fg3a','fg2m','fg2a','ast','reb','dreb','oreb']], on=['player_id','game_id'])
# pairwise teammate correlation of standardized residuals
def pair_corr(col_a, col_b, mu_a, mu_b, sample=400000):
    z = d[['game_id','team_id','player_id']].copy()
    z['a'] = d[col_a]/np.sqrt(np.maximum(d[mu_a], 0.3)); z['b'] = d[col_b]/np.sqrt(np.maximum(d[mu_b], 0.3))
    m = z.merge(z, on=['game_id','team_id'])
    m = m[m.player_id_x != m.player_id_y]
    if len(m) > sample: m = m.sample(sample, random_state=1)
    return np.corrcoef(m.a_x, m.b_y)[0,1], len(m)
for a, b in (('r_fga','r_fga'), ('r_pts','r_pts'), ('r_reb','r_reb'), ('r_ast','r_ast'), ('r_ast','r_pts'), ('r_fta','r_fta'), ('r_fg3a','r_fg3a')):
    c, n = pair_corr(a, b, 'mu_'+a[2:], 'mu_'+b[2:])
    print(f'teammates corr {a} vs {b}: {c:+.3f} (pairs {n})')
# team shooting: does a team's hot/cold night show up? corr between teammates' FG% residual
p2 = p.copy()
S_m = p2.groupby(key)['fgm'].transform('sum'); S_a = p2.groupby(key)['fga'].transform('sum')
p2['fg_loo'] = (S_m - p2.fgm)/(S_a - p2.fga)
p2['fg_res'] = (p2.fgm - p2.fga*p2.fg_loo)/np.sqrt(np.maximum(p2.fga*p2.fg_loo*(1-p2.fg_loo), 0.25))
z = p2[['game_id','team_id','player_id','fg_res']]
m = z.merge(z, on=['game_id','team_id']); m = m[m.player_id_x != m.player_id_y].sample(400000, random_state=2)
print('teammates corr FG made residual:', round(np.corrcoef(m.fg_res_x, m.fg_res_y)[0,1], 4))
