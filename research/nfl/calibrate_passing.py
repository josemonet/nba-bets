"""Joint calibration of the passing layer (per-catch spread, depth shock, score-link scale, field constraint, target-share noise)
against within-team-season moments from real games: team passing yards, attempts, completions, yards per completion and the
completion%/depth trade-off, plus a 22-30% target-share WR's yards, targets and receptions spread and his links to the QB and the WR2."""
import itertools, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..', '..', 'skills', 'nfl-player-props', 'scripts'))
import nfl_props as m
T = json.load(open('data/cache/nfl/pass_targets.json'))
W = dict(team_pass_yds=1/69.7, att=1/7.7, cmp=1/5.5, ypc=1/2.36, cc=1/0.1, wr1_sd=1/39.3, wr1_tgt_sd=1/3.15, wr1_rec_sd=1/2.47, qb_wr1=1/0.1, wr1_wr2=1/0.1)
def moments(seed=11):
    pl = [dict(name='QB', team='A', pos='QB'), dict(name='WR1', team='A', pos='WR', tgt=0.255, catch=0.644, ypr=12.9, eff_cv=0.0, share_cv=0.0),
          dict(name='WR2', team='A', pos='WR', tgt=0.18, catch=0.64, ypr=12.0, eff_cv=0.0, share_cv=0.0)]
    S = m.sim_game(dict(exp_margin=0.0, total=45.0), pl, n=30000, seed=seed); A = S['A']; ok = A['ATT'] >= 12
    w1, w2, q = S['WR1']['RECYDS'], S['WR2']['RECYDS'], S['QB']['PYDS']
    return dict(team_pass_yds=A['PASS_YDS'].std(), att=A['ATT'].std(), cmp=A['CMP'].std(), ypc=(A['PASS_YDS'][ok]/np.maximum(A['CMP'][ok], 1)).std(),
                cc=np.corrcoef(A['CMP'][ok]/A['ATT'][ok], A['PASS_YDS'][ok]/np.maximum(A['CMP'][ok], 1))[0, 1], wr1_sd=w1.std(),
                wr1_tgt_sd=S['WR1']['TGT'].std(), wr1_rec_sd=S['WR1']['REC'].std(), qb_wr1=np.corrcoef(w1, q)[0, 1], wr1_wr2=np.corrcoef(w1, w2)[0, 1])
def loss(v): return sum(((v[k]-T[k])*W[k])**2 for k in T)
if __name__ == '__main__':
    base = dict(lc=m.SPREAD['catch'], d=m.DEPTH_SD, ls=m.LINK_SCALE, yc=m.YARD_COMP, kt=1.0)
    grid = dict(lc=(0.92, 1.0), d=(0.10, 0.14), ls=(0.75, 1.0), yc=(0.35, 0.5, 0.65), kt=(1.0, 1.5, 2.0))
    k0 = dict(m.TGT_KAPPA); res = []
    for lc, d, ls, yc, kt in itertools.product(*grid.values()):
        m.SPREAD['catch'], m.DEPTH_SD, m.LINK_SCALE, m.YARD_COMP = lc, d, ls, yc
        m.TGT_KAPPA.update({k: v*kt for k, v in k0.items()})
        v = moments(); res.append((loss(v), dict(lc=lc, d=d, ls=ls, yc=yc, kt=kt), v))
        m.TGT_KAPPA.update(k0)
    res.sort(key=lambda t: t[0])
    for L, prm, v in res[:6]:
        print(f'loss {L:.3f} {prm} | ' + ' '.join(f'{k} {v[k]:.3f}/{T[k]:.3f}' for k in T))
    json.dump(res[0][1], open('data/cache/nfl/passing_fit.json', 'w'))
