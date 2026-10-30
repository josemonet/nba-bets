# Who scores the team's TDs: receiving TDs vs target share, red-zone and inside-10 shares; rushing TDs vs carry and goal-line shares.
import sys; sys.path.insert(0, 'research/nfl')
import numpy as np, pandas as pd, data
T = data.build(); pg = T['player_games'].copy()
pg = pg[pg.season.notna()].sort_values(['player_id', 'season', 'week'])
tt = pg.groupby(['game_id', 'team']).agg(t_tgt=('targets', 'sum'), t_rz=('rz_tgt', 'sum'), t_i10=('i10_tgt', 'sum'), t_rectd=('rec_td', 'sum'),
                                          t_car=('rush_att', 'sum'), t_rzc=('rz_car', 'sum'), t_glc=('gl_car', 'sum'), t_rushtd=('rush_td', 'sum')).reset_index()
pg = pg.merge(tt, on=['game_id', 'team'])
g = pg.groupby(['player_id', 'season'], sort=False)
def prior_share(num, den, hl=4):
    a = g[num].transform(lambda x: x.shift().ewm(halflife=hl, ignore_na=True).mean())
    b = g[den].transform(lambda x: x.shift().ewm(halflife=hl, ignore_na=True).mean())
    return a/b.replace(0, np.nan)
pg['n_prior'] = g.cumcount()
for a, b in (('targets', 't_tgt'), ('rz_tgt', 't_rz'), ('i10_tgt', 't_i10'), ('rec_td', 't_rectd'),
             ('rush_att', 't_car'), ('rz_car', 't_rzc'), ('gl_car', 't_glc'), ('rush_td', 't_rushtd')):
    pg[f's_{a}'] = prior_share(a, b)
ev = pg[(pg.n_prior >= 4) & (pg.season >= 2017)].copy()
def ll(p, y): p = np.clip(p, 1e-4, 1-1e-4); return float(-np.mean(y*np.log(p) + (1-y)*np.log(1-p)))
# receiving: P(>=1 rec TD) given the team's actual receiving TDs and a weight w (share of each team rec TD)
r = ev[ev.position.isin(['WR', 'TE', 'RB']) & ev.s_targets.notna() & (ev.t_rectd > 0)].copy()
y = (r.rec_td > 0).astype(float).values
for lab, w in (('target share', r.s_targets), ('red-zone target share', r.s_rz_tgt.fillna(r.s_targets)), ('inside-10 share', r.s_i10_tgt.fillna(r.s_targets)),
               ('past rec-TD share', r.s_rec_td.fillna(r.s_targets))):
    w = np.clip(w.fillna(0).values, 0, 0.9); p = 1 - (1 - w)**r.t_rectd.values
    print(f'rec TD | team rec TDs, weight = {lab:22s}: log loss {ll(p, y):.4f}  pred {p.mean():.3f} act {y.mean():.3f}')
best = None
for a in (0.0, 0.25, 0.5, 0.75, 1.0):
    for b_ in (0.0, 0.15, 0.3):
        w = (1-a-b_)*r.s_targets.fillna(0) + a*r.s_rz_tgt.fillna(r.s_targets).fillna(0) + b_*r.s_i10_tgt.fillna(r.s_targets).fillna(0)
        if a + b_ > 1: continue
        p = 1 - (1 - np.clip(w.values, 0, 0.9))**r.t_rectd.values; L = ll(p, y)
        if best is None or L < best[2]: best = (a, b_, L, p.mean())
print('best receiving blend: %.2f red-zone + %.2f inside-10 + rest target share: log loss %.4f (pred %.3f)' % best)
# position effect at equal weight: TEs and big WRs score more per red-zone look?
r['w'] = (1-best[0]-best[1])*r.s_targets.fillna(0) + best[0]*r.s_rz_tgt.fillna(r.s_targets).fillna(0) + best[1]*r.s_i10_tgt.fillna(r.s_targets).fillna(0)
r['p'] = 1 - (1 - np.clip(r.w, 0, 0.9))**r.t_rectd
print('actual/predicted rec-TD rate by position:', r.groupby('position').apply(lambda d: round(float((d.rec_td > 0).mean()/d.p.mean()), 3), include_groups=False).to_dict())
# rushing: weights from carry share and goal-line share (QBs included)
q = ev[ev.s_rush_att.notna() & (ev.t_rushtd > 0) & (ev.s_rush_att > 0)].copy(); yq = (q.rush_td > 0).astype(float).values
best = None
for a in (0.0, 0.25, 0.5, 0.75, 1.0):
    for b_ in (0.0, 0.25, 0.5):
        if a + b_ > 1: continue
        w = (1-a-b_)*q.s_rush_att.fillna(0) + a*q.s_rz_car.fillna(q.s_rush_att).fillna(0) + b_*q.s_gl_car.fillna(q.s_rush_att).fillna(0)
        p = 1 - (1 - np.clip(w.values, 0, 0.95))**q.t_rushtd.values; L = ll(p, yq)
        if best is None or L < best[2]: best = (a, b_, L, p.mean(), yq.mean())
print('best rushing blend: %.2f red-zone + %.2f goal-line + rest carry share: log loss %.4f (pred %.3f act %.3f)' % best)
q['w'] = (1-best[0]-best[1])*q.s_rush_att.fillna(0) + best[0]*q.s_rz_car.fillna(q.s_rush_att).fillna(0) + best[1]*q.s_gl_car.fillna(q.s_rush_att).fillna(0)
q['p'] = 1 - (1 - np.clip(q.w, 0, 0.95))**q.t_rushtd
print('actual/predicted rush-TD rate by position:', q.groupby('position').apply(lambda d: round(float((d.rush_td > 0).mean()/d.p.mean()), 3), include_groups=False).to_dict())
