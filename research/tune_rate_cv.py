"""Tune the rate-uncertainty multipliers (RATE_CV) on training seasons so predictive intervals hold their nominal coverage."""
import os
import pickle
import sys
from multiprocessing import Pool

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "skills", "nba-player-props", "scripts"))
import nba_props as new  # noqa: E402

STATS = ("PTS", "REB", "AST", "FG3M", "PRA")


def _run(args):
    rows, mult = args
    new.RATE_RHO = mult.pop("rho", new.RATE_RHO)
    new.RATE_CV.update(mult)
    out = {k: [] for k in STATS}
    for row in rows:
        S = new.sim_player(row["player"], row["game"], n=1500, seed=hash(row["key"]) % (2**31))
        rng = np.random.default_rng((hash(row["key"]) + 7) % (2**32))
        for k in STATS:
            x = np.sort(S[k].astype(float)); y = row["y"][k]
            lo = np.searchsorted(x, y - 0.5, side="right") / len(x); hi = np.searchsorted(x, y + 0.5, side="right") / len(x)
            out[k].append(lo + rng.random() * (hi - lo))
    return out


def coverage(pits):
    p = np.asarray(pits)
    return tuple(round(float(np.mean((p >= (1 - c) / 2) & (p <= 1 - (1 - c) / 2))), 3) for c in (0.5, 0.8, 0.9))


if __name__ == "__main__":
    rows = pickle.load(open("data/cache/rows_2014_2020.pkl", "rb"))
    rng = np.random.default_rng(3)
    rows = [rows[i] for i in rng.choice(len(rows), 8000, replace=False)]
    grids = [dict(vol=v, three=t, reb=r, ast=a) for v, t, r, a in ((2.8, 2.0, 0.9, 1.4), (2.8, 2.0, 1.2, 1.6))]
    with Pool(os.cpu_count()) as pool:
        for mult in grids + [dict(g, rho=0.8) for g in grids[:1]]:
            parts = pool.map(_run, [(rows[i::os.cpu_count()], mult) for i in range(os.cpu_count())])
            res = {k: sum((p[k] for p in parts), []) for k in STATS}
            print(mult, 'rho', new.RATE_RHO, ' '.join(f"{k} {coverage(res[k])}" for k in STATS), flush=True)
