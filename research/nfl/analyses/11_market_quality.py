# Does the market's view of team quality (implied points, expected margin) explain what the season-to-date team inputs miss?
# Team-level sim means (walk-forward backtest inputs) vs actual, by the team's expected margin and implied points, 2020-25.
import os, sys
sys.path.insert(0, 'research/nfl'); sys.path.insert(0, 'skills/nfl-player-props/scripts')
from multiprocessing import Pool
import numpy as np, pandas as pd
import backtest as bt, data, nfl_props as m

T = data.build(); TG = T['team_games'].set_index(['game_id', 'team']); G = T['games'].set_index('game_id')


def run(job):
    S = m.sim_game(job['g'], [{k: v for k, v in p.items() if k != 'meta'} for p in job['players']], n=3000, seed=abs(hash(job['game_id'])) % 2**31)
    gm = G.loc[job['game_id']]; out = []
    for side, team, sign in (('A', gm.home_team, 1), ('B', gm.away_team, -1)):
        x = S[side]; a = TG.loc[(job['game_id'], team)]; em = sign*job['g']['exp_margin']
        out.append(dict(season=job['season'], em=em, imp=(job['g']['total']+em)/2, plays=a.plays, s_plays=x['PLAYS'].mean(), att=a.pass_att,
                        s_att=x['ATT'].mean(), pyds=a.pass_yds, s_pyds=x['PASS_YDS'].mean(), cmp=a.pass_att and np.nan, ryds=a.rush_yds,
                        s_ryds=x['RUSH_YDS'].mean(), ptd=a.pass_td, s_ptd=x['PTD'].mean(), rtd=a.rush_td, s_rtd=x['RTD'].mean(),
                        ypa=a.pass_yds/max(a.pass_att, 1), s_ypa=x['PASS_YDS'].mean()/max(x['ATT'].mean(), 1)))
    return out


if __name__ == '__main__':
    jobs = bt.build(2020, 2025)
    with Pool(os.cpu_count()) as pool: parts = pool.map(run, jobs, chunksize=8)
    r = pd.DataFrame([x for q in parts for x in q]); r.to_pickle('data/cache/nfl/market_quality.pkl')
    r['emb'] = pd.cut(r.em, [-30, -7, -3, 3, 7, 30]); r['ib'] = pd.cut(r.imp, [0, 19, 22, 25, 50])
    for by in ('emb', 'ib'):
        t = r.groupby(by, observed=True).apply(lambda d: pd.Series({c: round(float(d[c].mean()/d['s_'+c].mean()), 3) for c in ('plays', 'att', 'pyds', 'ypa', 'ryds', 'ptd', 'rtd')} | dict(n=len(d))))
        print(f'actual / simulated by {by}:'); print(t.to_string())
    # fit log(actual/sim) on the expected margin and implied points, 2020-22; test the error reduction on 2023-25
    for c in ('att', 'ypa', 'pyds', 'ryds', 'ptd'):
        tr, te = r[r.season <= 2022], r[r.season >= 2023]
        X = lambda d: np.c_[np.ones(len(d)), d.em, d.imp-22.5]
        yv = lambda d: np.log(np.maximum(d[c], 1)/np.maximum(d['s_'+c], 1)) if c not in ('ptd',) else (d[c]-d['s_'+c])/np.maximum(d['s_'+c], 0.3)
        b = np.linalg.lstsq(X(tr), yv(tr), rcond=None)[0]
        e0 = np.mean((te[c]-te['s_'+c])**2); adj = te['s_'+c]*np.exp(X(te)@b) if c != 'ptd' else te['s_'+c]*(1+X(te)@b)
        e1 = np.mean((te[c]-adj)**2)
        print(f'{c:5s} fit 2020-22: const {b[0]:+.4f} per point of expected margin {b[1]:+.5f} per implied point {b[2]:+.5f} | 2023-25 MSE {e0:.2f} -> {e1:.2f}')
