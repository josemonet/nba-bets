"""Walk-forward backtest: the v1 engine (research/old_engine.py) vs the v2 engine (scripts/nba_props.py).

Three variants: v1 = the original skill's recipe and engine, v1e = new inputs with the original engine (engine-only effect),
v2 = new recipe and engine. The v1e and v2 variants get identical pregame-only inputs for every player-game in the test seasons: minutes from his earlier games,
per-36 rates shrunk toward last season, shooting %, opponent factors, expected pace and margin from team ratings to date.
Scored on what happened: randomized PIT (is every quantile honest?), central-interval coverage, CRPS, and log loss / Brier
at a book-style proxy line (his season average to date, rounded to a half point).

Usage: python research/backtest.py [first_season] [n_sims] [max_rows|all] [last_season] [tag]
"""
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "skills", "nba-player-props", "scripts"))
import data  # noqa: E402
import nba_props as new  # noqa: E402
import old_engine as old  # noqa: E402

STATS = {"PTS": "pts", "REB": "reb", "AST": "ast", "FG3M": "fg3m", "PRA": "pra", "MIN": "min"}
R36 = ["fga", "fta", "reb", "ast", "stl", "blk", "tov"]
V1_STAB = dict(fga=300, fta=300, reb=250, ast=250, stl=800, blk=500, tov=500)   # the original skill's STAB (pts36 used for shots)
V1_CLOSE = dict(star=1.5, starter=0.8, rotation=-0.5, bench=-1.0)


def v1_inputs(r, h, change, has_prev, lg36, pct_prior, prior_s3):
    """The original skill's recipe: close-game minutes (calibrate_min), season rates shrunk by the old STAB, no recency, drift or home."""
    mins, marg = np.asarray(h[0], float)[-10:], np.asarray(h[1], float)[-10:]
    close = mins[np.abs(marg) < 10]
    avg = float(close.mean()) if len(close) >= 3 else float(mins.mean())
    if change == "promoted":
        avg += float(np.interp(avg, *new.PROMOTED[:2]))
    elif change == "demoted":
        avg += float(np.interp(avg, *new.DEMOTED[:2]))
    role = new.role_for(avg)
    r36 = {}
    for s in R36:
        obs = 36 * getattr(r, f"cum_{s}") / r.cum_min
        prior = 36 * getattr(r, f"prev_{s}") / r.prev_min if has_prev else lg36.loc[r.season, s]
        r36[s] = float(old.shrink(obs, r.cum_min, prior, V1_STAB[s]))
    pr2, pr3, prf = pct_prior
    pct = dict(p2=(r.cum_fg2m + 350 * pr2) / (r.cum_fg2a + 350), p3=(r.cum_fg3m + 750 * pr3) / (r.cum_fg3a + 750),
               ft=(r.cum_ftm + 200 * prf) / (r.cum_fta + 200))
    adj = {s: old.matchup_adj(getattr(r, f"of_{s}"), 1.0, r.opp_n) if r.opp_n >= 3 and np.isfinite(getattr(r, f"of_{s}")) else 1.0 for s in R36}
    return dict(role=role, min=avg - 0.5 * V1_CLOSE[role], r36=r36, s3=float((r.cum_fg3a + 100 * prior_s3) / (r.cum_fga + 100)), pct=pct, adj=adj)


def team_context(df):
    """Pregame team ratings: season-to-date pace and net rating per 100, shrunk early in the season."""
    g = df.drop_duplicates(["game_id", "team_id"])[["game_id", "team_id", "opp_id", "season", "date", "home", "pace48",
                                                     "team_pts", "opp_pts", "poss"]].sort_values("date")
    gb = g.groupby(["team_id", "season"])
    g["n_prior"] = gb.cumcount()
    for c in ("pace48", "team_pts", "opp_pts", "poss"):
        g[f"cum_{c}"] = gb[c].cumsum() - g[c]
    lg_pace = g.groupby("season")["pace48"].transform("mean")
    k = 8.0
    g["pace_pre"] = (g.cum_pace48 + k * lg_pace) / (g.n_prior + k)
    g["net_pre"] = 100 * (g.cum_team_pts - g.cum_opp_pts) / (g.cum_poss + k * 99.0)
    o = g[["game_id", "team_id", "pace_pre", "net_pre"]].rename(columns={"team_id": "opp_id", "pace_pre": "opp_pace_pre",
                                                                         "net_pre": "opp_net_pre"})
    g = g.merge(o, on=["game_id", "opp_id"])
    g["exp_poss"] = (g.pace_pre + g.opp_pace_pre) / 2
    g["exp_margin"] = 0.89 * (g.net_pre - g.opp_net_pre) * g.exp_poss / 100 + np.where(g.home == 1, 2.5, -2.5)
    return g[["game_id", "team_id", "pace_pre", "exp_poss", "exp_margin"]]


def opponent_factors(df):
    """Season-to-date per-possession stats allowed by each defense, relative to league, with games played."""
    pl = df[df.played == 1]
    tg = pl.groupby(["game_id", "team_id", "opp_id", "season", "date"])[R36].sum().reset_index()
    tg = tg.merge(df.drop_duplicates(["game_id", "team_id"])[["game_id", "team_id", "poss"]], on=["game_id", "team_id"])
    tg = tg.sort_values("date")
    d = tg.groupby(["opp_id", "season"])
    out = tg[["game_id", "team_id"]].copy()
    out["opp_n"] = d.cumcount()
    cum_poss = d["poss"].cumsum() - tg["poss"]
    lg = tg.groupby("season").apply(lambda x: x[R36].sum() / x["poss"].sum(), include_groups=False)
    for s in R36:
        allowed = (d[s].cumsum() - tg[s]) / cum_poss
        out[f"of_{s}"] = (allowed / lg.loc[tg.season, s].values).values
    return out


def build_inputs(df, first_season, last_season=9999, min_prior=10, min_proj=20.0):
    p = df[df.played == 1].copy().sort_values(["player_id", "date", "game_id"])
    p["pra"] = p.pts + p.reb + p.ast
    p["fg2a"] = p.fga - p.fg3a
    p["fg2m"] = p.fgm - p.fg3m
    cols = ["min", "fga", "fta", "reb", "ast", "stl", "blk", "tov", "pf", "fg3a", "fg2a", "fg2m", "fg3m", "ftm", "pts", "pra"]
    ps = p.groupby(["player_id", "season"])[cols].sum()
    prev = ps.copy()
    prev.index = prev.index.set_levels(prev.index.levels[1] + 1, level=1)
    p = p.join(prev.rename(columns=lambda c: "prev_" + c), on=["player_id", "season"])
    g = p.groupby(["player_id", "season"], sort=False)
    p["n_prior"] = g.cumcount()
    for c in cols:
        p[f"cum_{c}"] = g[c].cumsum() - p[c]
        p[f"l10_{c}"] = g[c].transform(lambda x: x.shift().rolling(10, min_periods=1).sum())
    p["st_prev5"] = g["starter"].transform(lambda x: x.shift().rolling(5, min_periods=1).mean())
    lg36 = p.groupby("season").apply(lambda d: d[cols].sum() / d["min"].sum() * 36, include_groups=False)
    p = p.merge(team_context(df), on=["game_id", "team_id"]).merge(opponent_factors(df), on=["game_id", "team_id"])
    p = p.sort_values(["player_id", "date", "game_id"])
    ev = p[(p.season >= first_season) & (p.season <= last_season) & (p.n_prior >= min_prior)].copy()
    # recent minutes, margins and overtime periods (last 15 games, oldest first)
    hist = {}
    for (pid, season), grp in p[(p.season >= first_season) & (p.season <= last_season)].groupby(["player_id", "season"], sort=False):
        mins, marg, ots = grp["min"].values, grp["margin"].values, grp["ot"].values
        for i, idx in enumerate(grp.index):
            hist[idx] = (mins[:i], marg[:i], ots[:i])   # his whole season log so far (project_minutes weights recent games)
    rows = []
    for r in ev.itertuples():
        h = hist.get(r.Index)
        if h is None or len(h[0]) < min_prior:
            continue
        change = "promoted" if (r.starter == 1 and r.st_prev5 <= 0.2) else "demoted" if (r.starter == 0 and r.st_prev5 >= 0.8) else None
        pm = new.project_minutes(h[0], h[1], h[2], role_change=change)
        if pm["min"] < min_proj:
            continue
        has_prev = r.prev_min >= 300 if r.prev_min == r.prev_min else False
        r36 = {}
        for s in R36:
            r36[s] = new.project_rate(s if s in new.STAB else "pts", getattr(r, f"cum_{s}"), r.cum_min,
                                      getattr(r, f"prev_{s}") if has_prev else None, r.prev_min if has_prev else None,
                                      getattr(r, f"l10_{s}"), r.l10_min, league36=lg36.loc[r.season, s])
        prior_s3 = (r.prev_fg3a / max(r.prev_fga, 1)) if has_prev and r.prev_fga >= 100 else lg36.loc[r.season, "fg3a"] / lg36.loc[r.season, "fga"]
        s3 = new.project_share(r.cum_fg3a, r.cum_fga, prior_s3)
        lg_p2 = lg36.loc[r.season, "fg2m"] / lg36.loc[r.season, "fg2a"]
        lg_p3 = lg36.loc[r.season, "fg3m"] / lg36.loc[r.season, "fg3a"]
        lg_ft = lg36.loc[r.season, "ftm"] / lg36.loc[r.season, "fta"]
        pr2 = (r.prev_fg2m / r.prev_fg2a) if has_prev and r.prev_fg2a >= 100 else lg_p2
        pr3 = (r.prev_fg3m / r.prev_fg3a) if has_prev and r.prev_fg3a >= 50 else lg_p3
        prf = (r.prev_ftm / r.prev_fta) if has_prev and r.prev_fta >= 50 else lg_ft
        pct = dict(p2=new.project_pct(r.cum_fg2m, r.cum_fg2a, pr2, "p2"), p3=new.project_pct(r.cum_fg3m, r.cum_fg3a, pr3, "p3"),
                   ft=new.project_pct(r.cum_ftm, r.cum_fta, prf, "ft"))
        p1 = v1_inputs(r, h, change, has_prev, lg36, (pr2, pr3, prf), prior_s3)
        adj = {s: new.matchup_adj(getattr(r, f"of_{s}"), 1.0, r.opp_n, stat=s) if r.opp_n >= 3 and np.isfinite(getattr(r, f"of_{s}")) else 1.0
               for s in R36}
        pf36 = (r.cum_pf + 300 * 3.0 / 36) / (r.cum_min + 300) * 36
        rate_cv = 0.05 if (has_prev and r.n_prior >= 20) else 0.09 if (has_prev or r.n_prior >= 20) else 0.13
        player = dict(min=pm["min"], min_sd_extra=pm["min_sd_extra"], r36=r36, s3=float(s3), pct=pct, adj=adj, pf36=float(pf36),
                      home=bool(r.home), team_poss=float(r.pace_pre), rate_cv=rate_cv, starter=bool(r.starter))
        player_v1 = dict(p1, pf36=float(pf36), team_poss=float(r.pace_pre), rate_cv=rate_cv)
        game = dict(exp_margin=float(r.exp_margin), poss=float(r.exp_poss), team_poss=float(r.pace_pre))
        line = {k: np.floor(getattr(r, f"cum_{v}") / r.n_prior) + 0.5 for k, v in STATS.items()}
        y = {k: getattr(r, v) for k, v in STATS.items()}
        rows.append(dict(key=(r.player_id, r.game_id), season=r.season, role=pm["role"], n_prior=int(r.n_prior), has_prev=bool(has_prev),
                         change=change or "same", player=player, player_v1=player_v1, game=game, line=line, y=y))
    return rows


def _old_player(pl, role=None):
    q = dict(pl)
    q["role"] = role or new.role_for(pl["min"])
    q["s3"] = float(np.clip(pl["s3"], 0.001, 0.999))   # v1 crashes on a 0 share (non-shooting bigs) or a 100% FT mark
    q["pct"] = {k: float(np.clip(v, 0.001, 0.999)) for k, v in pl["pct"].items()}
    q.pop("home", None)
    q.pop("starter", None)
    q.pop("min_sd_extra", None)
    return q


def _score_one(args):
    row, n_sims = args
    out = dict(key=row["key"], season=row["season"], role=row["role"], n_prior=row["n_prior"], has_prev=row["has_prev"], change=row["change"])
    variants = (("v1", old, _old_player(row["player_v1"], row["player_v1"]["role"])),   # original recipe + original engine
                ("v1e", old, _old_player(row["player"])),                              # new inputs + original engine
                ("v2", new, row["player"]))                                             # new recipe + new engine
    for tag, eng, pl in variants:
        S = eng.sim_player(pl, row["game"], n=n_sims, seed=hash(row["key"]) % (2**31))
        rng = np.random.default_rng((hash(row["key"]) + 7) % (2**32))   # PIT tie-breaks must differ by row (same for both engines)
        for k in STATS:
            raw = S[k].astype(float)
            x = np.sort(raw)
            y = row["y"][k]
            F_lo = np.searchsorted(x, y - 0.5, side="right") / len(x)    # P(X <= y-1)
            F_hi = np.searchsorted(x, y + 0.5, side="right") / len(x)    # P(X <= y)
            out[f"{tag}_{k}_pit"] = F_lo + rng.random() * (F_hi - F_lo)
            h = len(raw) // 2                                               # independent draws pair up for E|X - X'|
            out[f"{tag}_{k}_crps"] = float(np.mean(np.abs(raw - y)) - np.mean(np.abs(raw[:h] - raw[h:2 * h])) / 2)
            out[f"{tag}_{k}_pover"] = float(np.clip((x > row["line"][k]).mean(), 1e-3, 1 - 1e-3))
            out[f"{tag}_{k}_mean"] = float(x.mean())
    for k in STATS:
        out[f"y_{k}"] = row["y"][k]
        out[f"line_{k}"] = row["line"][k]
    return out


def summarize(res):
    lines = []
    for k in STATS:
        r = {}
        for tag in ("v1", "v1e", "v2"):
            pit = res[f"{tag}_{k}_pit"].values
            yo = (res[f"y_{k}"] > res[f"line_{k}"]).astype(float).values
            po = res[f"{tag}_{k}_pover"].values
            cov = {c: float(np.mean((pit >= (1 - c) / 2) & (pit <= 1 - (1 - c) / 2))) for c in (0.5, 0.8, 0.9)}
            hist = np.histogram(pit, bins=10, range=(0, 1))[0] / len(pit)
            ll = -np.mean(yo * np.log(po) + (1 - yo) * np.log(1 - po))
            r[tag] = dict(cov50=cov[0.5], cov80=cov[0.8], cov90=cov[0.9], tails=float(hist[0] + hist[-1]), pit_dev=float(np.abs(hist - 0.1).sum()),
                          crps=float(res[f"{tag}_{k}_crps"].mean()), logloss=float(ll), brier=float(np.mean((po - yo) ** 2)),
                          bias=float((res[f"{tag}_{k}_mean"] - res[f"y_{k}"]).mean()))
        lines.append((k, r))
    return lines


def calib_table(res, k, tag, edges=(0, 0.3, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7, 1.0)):
    po = res[f"{tag}_{k}_pover"].values
    yo = (res[f"y_{k}"] > res[f"line_{k}"]).astype(float).values
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (po >= lo) & (po < hi)
        if m.sum() >= 50:
            rows.append((f"{lo:.2f}-{hi:.2f}", int(m.sum()), round(float(po[m].mean()), 3), round(float(yo[m].mean()), 3)))
    return rows


def main(first_season=2021, n_sims=2000, max_rows=None, last_season=9999, tag=""):
    t0 = time.time()
    df = data.player_games()
    rows = build_inputs(df, first_season, last_season)
    if max_rows:
        rng = np.random.default_rng(0)
        rows = [rows[i] for i in sorted(rng.choice(len(rows), size=min(max_rows, len(rows)), replace=False))]
    print(f"{len(rows)} player-games from {first_season}; inputs built in {time.time() - t0:.0f}s", flush=True)
    with Pool(os.cpu_count()) as pool:
        out = pool.map(_score_one, [(r, n_sims) for r in rows], chunksize=200)
    res = pd.DataFrame(out)
    os.makedirs(data.CACHE, exist_ok=True)
    res.to_pickle(f"{data.CACHE}/backtest_{first_season}_{last_season}{tag}.pkl")
    print(f"scored in {time.time() - t0:.0f}s")
    for k, r in summarize(res):
        for tag in ("v1", "v1e", "v2"):
            x = r[tag]
            print(f"{k:5s} {tag}: 50%/80%/90% coverage {x['cov50']:.3f}/{x['cov80']:.3f}/{x['cov90']:.3f}  PIT tails {x['tails']:.3f} (0.200 ideal)"
                  f"  PIT dev {x['pit_dev']:.3f}  CRPS {x['crps']:.3f}  logloss {x['logloss']:.4f}  brier {x['brier']:.4f}  bias {x['bias']:+.2f}")
    for k in STATS:
        for tag in ("v1", "v2"):
            print(k, tag, "P(over proxy line) calibration [band, n, predicted, actual]:", calib_table(res, k, tag))
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if a else 2021, int(a[1]) if len(a) > 1 else 2000, int(a[2]) if len(a) > 2 and a[2] != "all" else None,
         int(a[3]) if len(a) > 3 else 9999, a[4] if len(a) > 4 else "")
