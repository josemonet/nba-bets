# Engine self-checks against the data: variance/mean of every stat at fixed minutes and pace, and same-game correlations.
# Needs 04_count_dispersion.py first (for the data side of the correlation check).
import sys; sys.path.insert(0, 'research'); sys.path.insert(0, 'skills/nba-player-props/scripts')
import numpy as np, pandas as pd, nba_props as m
d = pd.read_pickle('data/cache/disp.pkl')
z = d[['game_id','team_id','player_id','r_ast','mu_ast','r_pts','mu_pts','r_fga','mu_fga']]
a = z[z.mu_ast >= 5][['game_id','team_id','player_id','r_ast']]; b = z[z.mu_pts >= 12][['game_id','team_id','player_id','r_pts']]
mm = a.merge(b, on=['game_id','team_id']); mm = mm[mm.player_id_x != mm.player_id_y]
print('data: corr(AST of a 5+ assist player, PTS of a 12+ point teammate) %.3f' % np.corrcoef(mm.r_ast, mm.r_pts)[0,1])
c = z[z.mu_fga >= 10][['game_id','team_id','player_id','r_fga']]; cc = c.merge(c, on=['game_id','team_id']); cc = cc[cc.player_id_x < cc.player_id_y]
print('data: corr(FGA, FGA) among 10+ FGA teammates %.3f' % np.corrcoef(cc.r_fga_x, cc.r_fga_y)[0,1])
# freeze minutes, pace and rate uncertainty to compare the engine's game-to-game noise with the data
for r in m.ROLE.values(): r['dm'] = (0,)*12; r['sd'] = 0.0; r['tail_p'] = 0.0
m.OT_PEAK = 0.0; m.POSS_SD = 0.0
g = dict(exp_margin=0.0, total=226.0, team_poss=98.0, poss=98.0)
players = dict(star=dict(min=35, r36=dict(fga=20.0, fta=7.5, reb=5.5, ast=7.0, stl=1.3, blk=0.4, tov=3.2), s3=0.40, pct=dict(p2=0.53, p3=0.36, ft=0.86)),
               wing=dict(min=30, r36=dict(fga=13.0, fta=3.0, reb=5.0, ast=2.5, stl=1.0, blk=0.5, tov=1.5), s3=0.55, pct=dict(p2=0.52, p3=0.37, ft=0.80)),
               big=dict(min=30, r36=dict(fga=12.0, fta=5.0, reb=12.5, ast=3.0, stl=0.8, blk=1.8, tov=2.0), s3=0.05, pct=dict(p2=0.62, p3=0.30, ft=0.70)))
for nm, p in players.items():
    S = m.sim_player({**p, 'rate_cv': 0.0, 'team_poss': 98.0}, g, n=200000)
    print(nm, 'var/mean', {k: round(float(S[k].var()/max(S[k].mean(), 1e-9)), 2) for k in ('FGA','FG3A','FG3M','FTA','PTS','REB','AST','PRA','PR','PA','RA')})
print('data targets: FGA 0.82-0.91, FTA 2.05, PTS 2.06-2.26, REB 1.08, AST 1.10, FG3M ~1.06, PRA 1.72-1.92, PR/PA 1.83-2.02, RA ~1.13')
pg = dict(min=34, rate_cv=0, r36=dict(fga=17.0, fta=5.0, reb=4.5, ast=8.5, stl=1.2, blk=0.3, tov=3.0), s3=0.40, pct=dict(p2=0.52, p3=0.36, ft=0.85))
sc = dict(min=34, rate_cv=0, r36=dict(fga=19.0, fta=6.0, reb=6.0, ast=4.0, stl=1.0, blk=0.6, tov=2.5), s3=0.35, pct=dict(p2=0.54, p3=0.37, ft=0.85))
S = m.sim_game_players([pg, sc], g, n=200000)
print('engine: corr(AST pg, PTS scorer) %.3f  corr(FGA, FGA) %.3f  AST var/mean %.2f' % (np.corrcoef(S[0]['AST'], S[1]['PTS'])[0,1], np.corrcoef(S[0]['FGA'], S[1]['FGA'])[0,1], S[0]['AST'].var()/S[0]['AST'].mean()))
