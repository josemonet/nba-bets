"""Subgroup calibration audit of a backtest result (python research/nfl/audit.py data/cache/nfl/backtest_2023_2025_final.pkl).
For every stat: 50/80/90% coverage of the randomized PIT and the relative bias, overall and by position, uncertainty tier (share_cv),
games into the season, spread size, first game back, absence shift and season. The NBA lesson: check every tier separately."""
import sys

import numpy as np
import pandas as pd


def cov(p): return tuple(round(float(np.mean((p >= (1 - c)/2) & (p <= 1 - (1 - c)/2))), 3) for c in (0.5, 0.8, 0.9))


def main(path):
    r = pd.read_pickle(path)
    x = r[r.stat != "ANYTD"].copy()
    x["games_in"] = pd.cut(x.n_prior, [-1, 2, 5, 9, 20], labels=["0-2", "3-5", "6-9", "10+"])
    x["spread_abs"] = pd.cut(x.spread, [-1, 3, 7, 10, 30], labels=["<=3", "3-7", "7-10", "10+"])
    x["back"] = np.where(x.get("missed", 0) > 0, "first game back", "regular")
    print(f"{len(r)} rows from {r.game_id.nunique()} games, seasons {sorted(r.season.unique())}")
    for by in (None, "pos", "share_cv", "games_in", "spread_abs", "back", "shifted", "season"):
        print(f"\n== by {by or 'stat'}")
        keys = ["stat"] + ([by] if by else [])
        for k, d in x.groupby(keys, observed=True):
            if len(d) < 100: continue
            k = k if isinstance(k, tuple) else (k,)
            print(f"{' '.join(str(v) for v in k):28s} n={len(d):5d} coverage 50/80/90 {cov(d.v2_pit.values)} rel bias {(d.v2_mean - d.y).mean()/max(d.y.mean(), 1e-9):+.3f}")
    d = r[r.stat == "ANYTD"].copy(); d["yb"] = (d.y > 0).astype(float)
    d["band"] = pd.cut(d.v2_p, [0, 0.1, 0.2, 0.3, 0.4, 0.5, 1.0])
    print("\n== anytime TD: stated vs actual by band and position")
    print(d.groupby("band", observed=True).agg(n=("yb", "size"), stated=("v2_p", "mean"), actual=("yb", "mean")).round(3).to_string())
    print(d.groupby("pos").agg(n=("yb", "size"), stated=("v2_p", "mean"), actual=("yb", "mean")).round(3).to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "data/cache/nfl/backtest_2023_2025_final.pkl")
