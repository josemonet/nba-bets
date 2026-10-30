# When a key pass-catcher, the lead back or the starting QB misses a game: how volume and efficiency move (split-sample baselines).
import sys; sys.path.insert(0, 'research/nfl')
import numpy as np, pandas as pd, data
T = data.build(); pg = T['player_games'].copy(); tg = T['team_games']
pg = pg[pg.season.notna()]
played = pg[(pg.offense_snaps > 0) | (pg.targets > 0) | (pg.rush_att > 0) | (pg.pass_att > 0)]
tt = played.assign(nq=lambda d: np.where(d.position == 'QB', 0, d.rush_att)).groupby(['game_id', 'team']).agg(t_tgt=('targets', 'sum'), t_nq=('nq', 'sum')).reset_index()
played = played.merge(tt, on=['game_id', 'team'])
tgames = tg[['game_id', 'team', 'season', 'week', 'pass_att', 'rush_att', 'pass_yds', 'pts', 'implied_pts', 'plays']]
# key players by role (season level, 6+ games): pass-catcher with 18%+ target share; lead back with 45%+ of non-QB carries
ps = played.groupby(['player_id', 'team', 'season']).agg(g=('game_id', 'size'), tgt=('targets', 'sum'), ttgt=('t_tgt', 'sum'), car=('rush_att', 'sum'),
                                                       tnq=('t_nq', 'sum'), pos=('position', 'first'), w0=('week', 'min'), w1=('week', 'max'),
                                                       att=('pass_att', 'sum')).reset_index()
ps['tsh'] = ps.tgt/ps.ttgt; ps['csh'] = ps.car/ps.tnq
def absence_effect(keys, label, stat_y, stat_n, mates_pos):
    rows = []
    for r in keys.itertuples():
        tm = tgames[(tgames.team == r.team) & (tgames.season == r.season) & tgames.week.between(r.w0, r.w1)]
        pl = played[(played.team == r.team) & (played.season == r.season) & played.game_id.isin(tm.game_id)]
        inn = set(pl[pl.player_id == r.player_id].game_id); out = set(tm.game_id) - inn
        if len(out) < 1 or len(inn) < 5: continue
        mates = pl[(pl.player_id != r.player_id) & pl.position.isin(mates_pos)]
        for pid, d in mates.groupby('player_id'):
            di, do = d[d.game_id.isin(inn)].sort_values('week'), d[d.game_id.isin(out)]
            if len(do) < 1 or len(di) < 4: continue
            a, b = di.iloc[0::2], di.iloc[1::2]          # A classifies the teammate's role, B is the baseline
            rows.append(dict(x=r.player_id, x_pos=r.pos, x_sh=r.tsh if stat_y == 'targets' else r.csh, mate=pid, pos=d.position.iloc[0],
                             sh_a=a[stat_y].sum()/max(a[stat_n].sum(), 1), sh_b=b[stat_y].sum()/max(b[stat_n].sum(), 1),
                             sh_out=do[stat_y].sum()/max(do[stat_n].sum(), 1), n_out=do[stat_n].sum(), g_out=len(do)))
    e = pd.DataFrame(rows)
    e['d'] = e.sh_out - e.sh_b
    e['rank_a'] = e.groupby('x')['sh_a'].rank(ascending=False)
    print(f'\n{label}: {e.x.nunique()} absences, {len(e)} teammate pairs')
    print(e.groupby('rank_a').apply(lambda d: pd.Series({'n': len(d), 'share_in': np.average(d.sh_b, weights=d.n_out), 'share_out': np.average(d.sh_out, weights=d.n_out),
          'gain': np.average(d.d, weights=d.n_out)}), include_groups=False).head(5).round(3).to_string())
    if stat_y == 'targets':
        print(' gain by teammate position vs missing player position:')
        print(e.groupby(['x_pos', 'pos']).apply(lambda d: round(float(np.average(d.d, weights=d.n_out)), 3), include_groups=False).unstack().round(3).to_string())
        e['rel'] = e.d/e.x_sh
        print(' total share regained by listed teammates (sum of gains / missing share): %.2f' % (e.groupby('x').apply(lambda d: d.d.sum()/d.x_sh.iloc[0], include_groups=False).median()))
    return e
key_rec = ps[(ps.g >= 6) & (ps.tsh >= 0.18) & ps.pos.isin(['WR', 'TE', 'RB'])]
e1 = absence_effect(key_rec, 'Top pass-catcher (18%+ target share) out', 'targets', 't_tgt', ['WR', 'TE', 'RB'])
key_rb = ps[(ps.g >= 6) & (ps.csh >= 0.45) & (ps.pos == 'RB')]
e2 = absence_effect(key_rb, 'Lead back (45%+ of carries) out', 'rush_att', 't_nq', ['RB', 'WR'])
# team-level: does the offense change when the top pass-catcher sits? (attempts, passing yards vs implied)
# starting QB out: team passing vs the closing line (which already prices the backup) and vs season norms
qb = ps[(ps.pos == 'QB') & (ps.g >= 6) & (ps.att >= 150)]
rows = []
for r in qb.itertuples():
    tm = tgames[(tgames.team == r.team) & (tgames.season == r.season) & tgames.week.between(r.w0, r.w1)]
    inn = set(played[(played.player_id == r.player_id) & (played.pass_att >= 10)].game_id)
    for x in tm.itertuples(): rows.append(dict(qb_in=x.game_id in inn, pass_att=x.pass_att, pass_yds=x.pass_yds, pts=x.pts, implied=x.implied_pts))
q = pd.DataFrame(rows)
print('\nStarting QB in vs out (team per game):'); print(q.groupby('qb_in')[['pass_att', 'pass_yds', 'pts', 'implied']].mean().round(1).to_string())
print('points vs implied when the starter is out: %.2f (in: %.2f) -> the closing line prices the backup' % ((q[~q.qb_in].pts - q[~q.qb_in].implied).mean(), (q[q.qb_in].pts - q[q.qb_in].implied).mean()))
pd.to_pickle(dict(rec=e1, rb=e2), 'data/cache/nfl/absences.pkl')
