"""Fit the in-season drift multipliers (DRIFT in nba_props.py): next-game rate / the projected rate, with drift switched off."""
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "skills", "nba-player-props", "scripts"))
import backtest as bt  # noqa: E402
import data  # noqa: E402
import nba_props as new  # noqa: E402


def main(first=2014, last=2023):
    new.DRIFT = {k: 1.0 for k in new.DRIFT}
    df = data.player_games()
    rows = bt.build_inputs(df, first, last)
    act = df[df.played == 1].set_index(["player_id", "game_id"])
    A = act.loc[[r["key"] for r in rows], ["min", "fga", "fta", "fg3a", "fgm", "fg3m", "ftm", "reb", "ast", "stl", "blk", "tov"]].reset_index(drop=True)
    P = pd.DataFrame([{**r["player"]["r36"], "s3": r["player"]["s3"], **{f"pct_{k}": v for k, v in r["player"]["pct"].items()},
                       "pf": r["game"]["poss"] / r["player"]["team_poss"], "season": r["season"],
                       **{f"adj_{k}": v for k, v in r["player"]["adj"].items()}} for r in rows])
    out = {}
    for s in ("fga", "fta", "reb", "ast", "stl", "blk", "tov"):
        out[s] = A[s].sum() / (P[s] * P[f"adj_{s}"] * A["min"] / 36 * P["pf"]).sum()
    out["s3"] = A.fg3a.sum() / (P.s3 * A.fga).sum()
    out["p2"] = (A.fgm - A.fg3m).sum() / (P.pct_p2 * (A.fga - A.fg3a)).sum()
    out["p3"] = A.fg3m.sum() / (P.pct_p3 * A.fg3a).sum()
    out["ft"] = A.ftm.sum() / (P.pct_ft * A.fta).sum()
    print(f"rows {len(rows)} seasons {first}-{last}")
    print("DRIFT =", {k: round(float(v), 3) for k, v in out.items()})
    by = {}
    for season, idx in P.groupby("season").groups.items():
        a, p = A.loc[idx], P.loc[idx]
        by[season] = (round(float(a.fg3a.sum() / (p.s3 * a.fga).sum()), 3), round(float(a.ast.sum() / (p.ast * p.adj_ast * a["min"] / 36 * p.pf).sum()), 3))
    print("by season (3PA share, assists):", by)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if a else 2014, int(a[1]) if len(a) > 1 else 2023)
