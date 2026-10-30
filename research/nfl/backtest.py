"""Walk-forward NFL backtest: the current football_model (old_football_model.py, from the sports-betting-research skill) vs the new
nfl_props engine, with identical pregame-only inputs for every team-game in the test seasons.

Inputs per game: the closing spread and total; season-to-date team tendencies (pace, neutral pass rate, sack, scramble, interception,
completion and yards-per-completion rates, shrunk); the players who were active (inactives are announced 90 minutes before kickoff)
with season-to-date target and carry shares, efficiency and red-zone usage (shrunk toward last season). Scored on what happened.
Usage: python research/nfl/backtest.py [first_season] [last_season] [n_sims] [tag]
"""
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "skills", "nfl-player-props", "scripts"))
import data  # noqa: E402
import nfl_props as new  # noqa: E402
import old_football_model as old  # noqa: E402

LGPOS = dict(catch=dict(WR=0.62, TE=0.70, RB=0.77), ypt=dict(WR=8.0, TE=7.3, RB=6.0), ypc=dict(RB=4.27, WR=5.8, TE=4.0))


def ewm(vals, hl):
    v = np.asarray(vals, float); w = 0.5**(np.arange(len(v))[::-1]/hl); return float(np.sum(w*v)), float(np.sum(w))


def team_inputs(T):
    tg = T["team_games"].sort_values(["team", "season", "week"]).copy()
    pg = T["player_games"]
    cm = pg.groupby(["game_id", "team"]).agg(cmp=("rec", "sum"), tg=("targets", "sum"), rec_yds=("rec_yds", "sum")).reset_index()
    p = T["plays"]; p = p[~p.two_point_attempt & p.posteam.notna()]
    sc = p.groupby(["game_id", "posteam"]).agg(scr=("qb_scramble", "sum"), kneel=("qb_kneel", "sum")).reset_index().rename(columns={"posteam": "team"})
    qbr = pg[pg.position == "QB"].groupby(["game_id", "team"]).agg(qb_rush=("rush_att", "sum"), qb_scr=("scrambles", "sum"), qb_kn=("kneels", "sum")).reset_index()
    tg = tg.merge(cm, on=["game_id", "team"]).merge(sc, on=["game_id", "team"]).merge(qbr, on=["game_id", "team"], how="left").fillna({"qb_rush": 0, "qb_scr": 0, "qb_kn": 0})
    tg["qb_design"] = tg.qb_rush - tg.qb_scr - tg.qb_kn
    tg["design"] = tg.rush_att - tg.scr - tg.kneel
    g = tg.groupby(["team", "season"])
    for c in ("plays", "neutral_db", "neutral_play", "sacks", "dropbacks", "scr", "ints", "pass_att", "cmp", "pass_yds", "qb_design", "design",
              "pass_td", "rush_td"):
        tg[f"c_{c}"] = g[c].cumsum() - tg[c]
    tg["n_prior"] = g.cumcount()
    L = new.LG
    tg["pace"] = (tg.c_plays + 3*L["pace"])/(tg.n_prior + 3)
    tg["npr"] = (tg.c_neutral_db + new.NPR_K*L["npr"])/(tg.c_neutral_play + new.NPR_K)
    tg["sack"] = (tg.c_sacks + 489*L["sack"])/(tg.c_dropbacks + 489)
    tg["scramble"] = (tg.c_scr + 80*L["scramble"])/(tg.c_dropbacks - tg.c_sacks + 80)
    tg["int"] = (tg.c_ints + 2490*L["int"])/(tg.c_pass_att + 2490)
    tg["comp"] = (tg.c_cmp + 368*L["comp"])/(tg.c_pass_att + 368)
    tg["ypcomp"] = (tg.c_pass_yds + 150*L["ypcomp"])/(tg.c_cmp + 150)
    tg["design_qb"] = (tg.c_qb_design + 100*L["design_qb"])/(tg.c_design + 100)
    tg["pass_td_share"] = (tg.c_pass_td + 10*L["pass_td_share"])/(tg.c_pass_td + tg.c_rush_td + 10)
    o = tg[["game_id", "team", "pace"]].rename(columns={"team": "opp", "pace": "opp_pace"})
    tg = tg.merge(o, on=["game_id", "opp"], how="left")
    # league norms known before each game: last season's averages blended with this season to date (by week)
    ls = tg.groupby("season").agg(lp=("plays", "mean"), lt=("total_line", "mean"))
    tg = tg.join(ls.shift(1).rename(columns={"lp": "prev_lp", "lt": "prev_lt"}), on="season")
    wk = tg.groupby(["season", "week"]).agg(wp=("plays", "sum"), wn=("plays", "size"), wt=("total_line", "sum")).groupby(level=0).cumsum()
    wk = wk.groupby(level=0).shift(1)
    tg = tg.join(wk, on=["season", "week"])
    w = (tg.wn.fillna(0)/(tg.wn.fillna(0) + 160))
    tg["lg_pace"] = (1 - w)*tg.prev_lp.fillna(L["pace"]) + w*(tg.wp/tg.wn).fillna(L["pace"])
    tg["lg_total"] = (1 - w)*tg.prev_lt.fillna(45.0) + w*(tg.wt/tg.wn).fillna(45.0)
    tg["pace"] = (tg.c_plays + 3*tg.lg_pace)/(tg.n_prior + 3)
    tg["opp_pace"] = tg.groupby("game_id").pace.transform("sum") - tg.pace
    tg["exp_plays"] = new.expected_plays(tg.total_line, tg.exp_margin, tg.pace, tg.opp_pace, tg.lg_pace, tg.lg_total)
    tg["lg_total_now"] = tg.lg_total
    return tg.set_index(["game_id", "team"])


def player_inputs(T, first, last):
    pg = T["player_games"].copy()
    # QB rushing split: designed-run yards vs scramble yards, and the team's designed runs (QBs' personal rushing inputs)
    r = T["plays"]; r = r[~r.two_point_attempt & r.posteam.notna() & (r.rush_attempt == 1)]
    sp = r.assign(scr_y=np.where(r.qb_scramble == 1, r.rushing_yards.fillna(0), 0.0),
                  des_y=np.where((r.qb_scramble == 0) & (r.qb_kneel == 0), r.rushing_yards.fillna(0), 0.0)).groupby(
        ["game_id", "rusher_player_id"]).agg(scr_y=("scr_y", "sum"), des_y=("des_y", "sum")).rename_axis(["game_id", "player_id"]).reset_index()
    pg = pg.merge(sp, on=["game_id", "player_id"], how="left").fillna({"scr_y": 0.0, "des_y": 0.0})
    pg = pg.merge(T["team_games"][["game_id", "team", "nonqb_rush"]].rename(columns={"nonqb_rush": "t_des"}), on=["game_id", "team"], how="left")
    pg["qdes"] = pg.rush_att - pg.scrambles - pg.kneels
    played = pg[(pg.offense_snaps > 0) | (pg.targets > 0) | (pg.rush_att > 0) | (pg.pass_att > 0)].copy()
    tt = played.assign(nq=np.where(played.position == "QB", 0, played.rush_att)).groupby(["game_id", "team"]).agg(
        t_tgt=("targets", "sum"), t_nq=("nq", "sum"), t_i10=("i10_tgt", "sum"), t_rzc=("rz_car", "sum")).reset_index()
    played = played.merge(tt, on=["game_id", "team"]).sort_values(["player_id", "season", "week"])
    tgm = played[["game_id", "team", "season", "week"]].drop_duplicates().sort_values(["team", "season", "week"])
    tgm["k"] = tgm.groupby(["team", "season"]).cumcount()
    played = played.merge(tgm[["game_id", "team", "k"]], on=["game_id", "team"]).sort_values(["player_id", "season", "week"])
    nxt = tgm.set_index(["team", "season", "k"]).game_id
    played["nq_rush"] = np.where(played.position == "QB", 0, played.rush_att)
    seas = played.groupby(["player_id", "season"]).agg(tg=("targets", "sum"), ttg=("t_tgt", "sum"), car=("nq_rush", "sum"), tnq=("t_nq", "sum"),
                                                     rec=("rec", "sum"), ry=("rec_yds", "sum"), rsy=("rush_yds", "sum"), ra=("rush_att", "sum"),
                                                     qdes=("qdes", "sum"), tdes=("t_des", "sum"), scr=("scrambles", "sum"), patt=("pass_att", "sum"),
                                                     desy=("des_y", "sum"), scry=("scr_y", "sum"))
    prev = seas.copy(); prev.index = prev.index.set_levels(prev.index.levels[1] + 1, level=1)
    played = played.join(prev.add_prefix("p_"), on=["player_id", "season"])
    rows = {}; absent = []
    for (pid, season), d in played[(played.season >= first - 1) & (played.season <= last)].groupby(["player_id", "season"], sort=False):
        d = d.reset_index(drop=True)
        # fresh absences: he played the team's last game and sits this one (what the inactives list tells you 90 minutes before kickoff)
        if season >= first and d.position.iloc[0] in ("WR", "TE", "RB", "FB"):
            ks = set(zip(d.team, d.k))
            for i in range(len(d)):
                tm_, k1 = d.team.iloc[i], d.k.iloc[i] + 1
                if (tm_, k1) in ks or (tm_, season, k1) not in nxt.index:
                    continue
                h = d.iloc[:i + 1]; r0 = d.iloc[i]
                pr_t = r0.p_tg/r0.p_ttg if (r0.p_ttg == r0.p_ttg and r0.p_ttg >= 100) else None
                pr_c = r0.p_car/r0.p_tnq if (r0.p_tnq == r0.p_tnq and r0.p_tnq >= 80) else None
                absent.append(dict(game_id=nxt.loc[(tm_, season, k1)], team=tm_, player_id=pid, pos=r0.position,
                                   tgt=new.project_share(h.targets.values, h.t_tgt.values, "tgt", pr_t),
                                   car=new.project_share(h.nq_rush.values, h.t_nq.values, "car", pr_c)))
        for i in range(len(d)):
            r = d.iloc[i]
            if r.season < first:
                continue
            h = d.iloc[:i]; pos = r.position if r.position in ("WR", "TE", "RB", "QB", "FB") else None
            if pos is None:
                continue
            has_prev = r.p_ttg == r.p_ttg and r.p_ttg >= 100
            if len(h) < 2 and not has_prev:
                continue
            pr_t = r.p_tg/r.p_ttg if has_prev else None
            pr_c = r.p_car/r.p_tnq if (r.p_tnq == r.p_tnq and r.p_tnq >= 80) else None
            tsh = new.project_share(h.targets.values, h.t_tgt.values, "tgt", pr_t) if (len(h) or pr_t is not None) else 0.0
            csh = new.project_share(h.nq_rush.values, h.t_nq.values, "car", pr_c) if (len(h) or pr_c is not None) else 0.0
            p_catch = (r.p_rec/r.p_tg) if has_prev and r.p_tg >= 20 else LGPOS["catch"].get(pos, 0.65)
            p_ypt = (r.p_ry/r.p_tg) if has_prev and r.p_tg >= 20 else LGPOS["ypt"].get(pos, 7.5)
            catch = new.project_rate(h.rec.sum(), h.targets.sum(), p_catch, "catch")
            ypt = new.project_rate(h.rec_yds.sum(), h.targets.sum(), p_ypt, "ypt")
            p_ypc = (r.p_rsy/r.p_ra) if (r.p_ra == r.p_ra and r.p_ra >= 40) else LGPOS["ypc"].get(pos, 4.27)
            ypc = new.project_rate(h.rush_yds.sum(), h.rush_att.sum(), p_ypc, "ypc")
            i10 = (h.i10_tgt.sum() + 2*tsh)/(h.t_i10.sum() + 2) if len(h) else tsh
            rz = (h.rz_car.sum() + 3*csh)/(h.t_rzc.sum() + 3) if len(h) else csh
            qbr = {}
            if pos == "QB":                                                # his own rushing profile, shrunk toward last season or the league
                L = new.LG; ok = lambda v, m: v == v and v >= m
                pr_ds = r.p_qdes/r.p_tdes if ok(r.p_tdes, 100) else L["design_qb"]
                pr_sr = r.p_scr/(r.p_patt + r.p_scr) if ok(r.p_patt, 150) else L["scramble"]
                pr_yd = r.p_desy/r.p_qdes if ok(r.p_qdes, 20) else L["ypc_qb_design"]
                pr_ys = r.p_scry/r.p_scr if ok(r.p_scr, 30) else L["ypc_qb_scramble"]
                qbr = dict(design_qb=new.project_rate(h.qdes.sum(), h.t_des.sum(), pr_ds, "design"),
                           scramble=new.project_rate(h.scrambles.sum(), (h.pass_att + h.scrambles).sum(), pr_sr, "scramble"),
                           ypc_design=new.project_rate(h.des_y.sum(), h.qdes.sum(), pr_yd, "ypc_design"),
                           ypc_scramble=new.project_rate(h.scr_y.sum(), h.scrambles.sum(), pr_ys, "ypc_scramble"))
            missed = int(r.k - (h.k.iloc[-1] if len(h) else -1) - 1) if (len(h) == 0 or h.team.iloc[-1] == r.team) else 0
            if pos != "QB":                                                # first game back: usage comes in light (return_keep)
                tsh *= new.return_keep("tgt", missed, len(h) == 0, r.k == 0); csh *= new.return_keep("car", missed, len(h) == 0, r.k == 0)
            rows[(r.game_id, pid)] = dict(game_id=r.game_id, team=r.team, player_id=pid, name=r["name"], pos=pos, n_prior=len(h), has_prev=bool(has_prev), qbr=qbr,
                                         missed=missed,
                                         tgt=tsh, car=csh if pos != "QB" else 0.0, catch=float(np.clip(catch, 0.3, 0.95)),
                                         ypr=float(np.clip(ypt/max(catch, 0.3), 4.0, 25.0)), ypc=float(np.clip(ypc, 2.0, 8.0)), i10=float(i10), rz=float(rz),
                                         pass_att=r.pass_att, y=dict(REC=r.rec, RECYDS=r.rec_yds, RYDS=r.rush_yds, RATT=r.rush_att, TDS=r.td_any, ANYTD=float(r.td_any > 0),
                                                                     PYDS=r.pass_yds, ATT=r.pass_att, CMP=r.pass_cmp, PTD=r.pass_td, INT=r.ints, TGT=r.targets,
                                                                     RRY=r.rec_yds + r.rush_yds),
                                         avg=dict(REC=h.rec.mean() if len(h) else np.nan, RECYDS=h.rec_yds.mean() if len(h) else np.nan,
                                                  RYDS=h.rush_yds.mean() if len(h) else np.nan, PYDS=h.pass_yds.mean() if len(h) else np.nan,
                                                  ATT=h.pass_att.mean() if len(h) else np.nan, RATT=h.rush_att.mean() if len(h) else np.nan,
                                                  RRY=(h.rec_yds + h.rush_yds).mean() if len(h) else np.nan),
                                         td_rate=float((h.td_any > 0).mean()) if len(h) else np.nan)
    return pd.DataFrame(rows.values()), pd.DataFrame(absent)


def build(first, last):
    T = data.build()
    ti = team_inputs(T)
    pi, ab = player_inputs(T, first, last)
    ab = ab[(ab.tgt >= 0.15) | (ab.car >= 0.30)]
    ab = {k: v.to_dict("records") for k, v in ab.groupby(["game_id", "team"])}
    p = T["plays"]; p = p[~p.two_point_attempt & p.posteam.notna() & ((p.qb_dropback == 1) | (p.pass_attempt == 1) | (p.qb_scramble == 1))]
    st = p.assign(qb=p.passer_player_id.fillna(p.rusher_player_id)).groupby(["game_id", "posteam"]).qb.first().to_dict()
    allg = T["games"]; allg = allg[allg.result.notna() & allg.total_line.notna()].sort_values(["season", "week", "game_id"]).copy()
    allg["res"] = (allg.home_score + allg.away_score - allg.total_line)/2                  # per team: points beyond the closing total
    allg["drift"] = allg.res.shift(1).rolling(256, min_periods=100).mean()               # the last ~season of games before this one
    drift = allg.set_index("game_id").drift.fillna(0.0).to_dict()
    games = T["games"]; games = games[(games.season >= first) & (games.season <= last) & games.result.notna() & games.spread_line.notna()]
    jobs = []
    for gm in games.itertuples():
        A, B = gm.home_team, gm.away_team
        if (gm.game_id, A) not in ti.index or (gm.game_id, B) not in ti.index:
            continue
        ta, tb = ti.loc[(gm.game_id, A)], ti.loc[(gm.game_id, B)]
        if ta.n_prior < 2 or tb.n_prior < 2:
            continue
        dk = float(os.environ.get("DRIFT_K", "0"))                                        # experiment: carry part of the recent over/under drift
        g = dict(exp_margin=float(gm.spread_line), total=float(gm.total_line) + 2*dk*drift.get(gm.game_id, 0.0), wind=float(gm.wind) if gm.wind == gm.wind else 0.0,
                 temp=float(gm.temp) if gm.temp == gm.temp else 60.0, roof=gm.roof)
        tm = {}
        for side, t in (("A", ta), ("B", tb)):
            tm[side] = dict(pace=float(t.exp_plays), npr=float(t.npr), sack=float(t.sack), scramble=float(t.scramble), int=float(t.int), comp=float(t.comp),
                            ypcomp=float(t.ypcomp), design_qb=float(t.design_qb), pass_td_share=float(t.pass_td_share))
        g.update(tm); g["lg_total"] = float(ta.lg_total)
        pl = pi[pi.game_id == gm.game_id]
        players = []
        for side, team in (("A", A), ("B", B)):
            d = pl[pl.team == team]
            starter = st.get((gm.game_id, team))
            for r in d.itertuples():
                if r.pos == "QB":
                    if r.player_id == starter:
                        players.append(dict(name=r.player_id, team=side, pos="QB", meta=r._asdict()))
                        g[side].update(r.qbr)                              # the starter's own scramble rate, run share and yards per run
                    continue
                players.append(dict(name=r.player_id, team=side, pos=r.pos, tgt=float(r.tgt) if r.tgt >= 0.02 else 0.0,
                                    car=float(r.car) if r.car >= 0.03 else 0.0, catch=r.catch, ypr=r.ypr, ypc=r.ypc, i10=r.i10, rz=r.rz,
                                    share_cv=0.30 if r.missed > 0 else 0.20 if r.n_prior < 3 else 0.10 if (r.has_prev and r.n_prior >= 6) else 0.14,
                                    meta=r._asdict()))
            # a regular who played last week is inactive: his teammates' shares shift (usage_shift_nfl, as the skill does live)
            for o in ab.get((gm.game_id, team), []):
                mates = {p["name"]: p for p in players if p["team"] == side and p["pos"] not in ("QB",)}
                for nm, q in new.usage_shift_nfl(dict(pos=o["pos"], tgt=o["tgt"], car=o["car"]), mates).items():
                    mates[nm].update(tgt=q.get("tgt", 0.0), car=q.get("car", 0.0), shifted=True)
            # the team's listed shares as a whole regress (share_budget, fitted on 2020-22 backtests)
            if os.environ.get("NO_BUDGET") != "1":
                mine = [p for p in players if p["team"] == side and p["pos"] != "QB"]; rest = [p for p in players if not (p["team"] == side and p["pos"] != "QB")]
                players = rest + new.share_budget(new.share_budget(mine, "tgt"), "car")
            players = [p for p in players if p["pos"] == "QB" or p.get("tgt", 0) >= 0.05 or p.get("car", 0) >= 0.08]
        jobs.append(dict(game_id=gm.game_id, season=gm.season, week=gm.week, g=g, players=players))
    return jobs


def _old_inputs(job):
    g = job["g"]; L = new.LG
    og = dict(sport="nfl", exp_margin=g["exp_margin"], total=g["total"])
    for side in ("A", "B"):
        t = g[side]
        og[side] = dict(pass_rate=float(np.clip(0.185 + 0.78*t["npr"], 0.4, 0.75)), comp=t["comp"], ypcomp=t["ypcomp"], ypc=4.3, sack=t["sack"],
                        int_rate=t["int"], pass_td=t["pass_td_share"], qb_rush=0.14)
    pl = []
    for p in job["players"]:
        if p["pos"] == "QB":
            pl.append(dict(name=p["name"], team=p["team"], pos="QB")); continue
        pl.append(dict(name=p["name"], team=p["team"], pos=p["pos"], tgt=p.get("tgt", 0)*L["tgt_per_att"], catch=p["catch"], ypr=p["ypr"],
                       car=p.get("car", 0), ypc=p["ypc"], rz_rec=p.get("tgt", 0), rz_rush=p.get("car", 0)*0.86, cv=p.get("share_cv", 0.15)))
    return og, pl


STATS = dict(REC="REC", RECYDS="RECYDS", RYDS="RYDS", RATT="RATT", ANYTD="ANYTD", PYDS="PYDS", ATT="ATT", CMP="CMP", PTD="PTD", RRY="RRY")


def _score(args):
    job, n = args
    out = []
    seed = abs(hash(job["game_id"])) % (2**31)
    new.LG_SEASON["total"] = job["g"].get("lg_total", new.LG_SEASON["total"])     # the league's average total known before the game
    S2 = new.sim_game(job["g"], [{k: v for k, v in p.items() if k != "meta"} for p in job["players"]], n=n, seed=seed)
    og, opl = _old_inputs(job)
    S1 = old.sim_football(og, opl, n=n, seed=seed)
    rng = np.random.default_rng(seed + 1)
    for p in job["players"]:
        meta = p["meta"]; y = meta["y"]; avg = meta["avg"]
        stats = ("PYDS", "ATT", "CMP", "PTD", "RYDS") if p["pos"] == "QB" else ("REC", "RECYDS", "RYDS", "RATT", "ANYTD", "RRY")
        for st in stats:
            if p["pos"] != "QB" and st in ("RYDS", "RATT") and p.get("car", 0) < 0.08:
                continue
            if p["pos"] != "QB" and st in ("REC", "RECYDS") and p.get("tgt", 0) < 0.05:
                continue
            row = dict(game_id=job["game_id"], season=job["season"], week=job["week"], player=p["name"], pos=p["pos"], stat=st, y=float(y[st]),
                       n_prior=meta["n_prior"], has_prev=meta["has_prev"], tgt=p.get("tgt", 0), car=p.get("car", 0), spread=abs(job["g"]["exp_margin"]),
                       share_cv=p.get("share_cv", 0), shifted=p.get("shifted", False), missed=meta.get("missed", 0))
            for tag, S in (("v1", S1), ("v2", S2)):
                key = st if not (tag == "v1" and st == "ANYTD") else "ANYTD"
                x = np.asarray(S[p["name"]][key], float)
                if st != "ANYTD":
                    x = np.round(x); xs = np.sort(x)
                    lo = np.searchsorted(xs, y[st] - 0.5, side="right")/len(xs); hi = np.searchsorted(xs, y[st] + 0.5, side="right")/len(xs)
                    row[f"{tag}_pit"] = lo + rng.random()*(hi - lo)
                    h = len(x)//2; row[f"{tag}_crps"] = float(np.mean(np.abs(x - y[st])) - np.mean(np.abs(x[:h] - x[h:2*h]))/2)
                    line = avg.get(st, np.nan)
                    if line == line:
                        line = np.floor(line) + 0.5; row["line"] = line
                        row[f"{tag}_pover"] = float(np.clip((x > line).mean(), 1e-3, 1 - 1e-3))
                    row[f"{tag}_mean"] = float(x.mean()); row[f"{tag}_med"] = float(np.median(x))
                else:
                    row[f"{tag}_p"] = float(np.clip(x.mean(), 1e-3, 1 - 1e-3))
            if st == "ANYTD":
                row["base_p"] = float(np.clip(meta["td_rate"] if meta["td_rate"] == meta["td_rate"] else 0.25, 0.02, 0.9))
            out.append(row)
    return out


def summarize(res):
    def cov(p): return tuple(round(float(np.mean((p >= (1 - c)/2) & (p <= 1 - (1 - c)/2))), 3) for c in (0.5, 0.8, 0.9))
    def ll(p, y): p = np.clip(p, 1e-3, 1 - 1e-3); return float(-np.mean(y*np.log(p) + (1 - y)*np.log(1 - p)))
    lines = []
    for st, d in res.groupby("stat"):
        if st == "ANYTD":
            y = d.y.values > 0
            lines.append(f"ANYTD n={len(d)}: log loss v1 {ll(d.v1_p.values, y):.4f} v2 {ll(d.v2_p.values, y):.4f} base(season TD rate) {ll(d.base_p.values, y):.4f} | "
                         f"mean p v1 {d.v1_p.mean():.3f} v2 {d.v2_p.mean():.3f} actual {y.mean():.3f}")
            continue
        s = f"{st:6s} n={len(d)}: coverage 50/80/90 v1 {cov(d.v1_pit.values)} v2 {cov(d.v2_pit.values)} | CRPS v1 {d.v1_crps.mean():.3f} v2 {d.v2_crps.mean():.3f}"
        dd = d[d.line.notna()] if "line" in d else d.iloc[0:0]
        if len(dd):
            yo = (dd.y > dd.line).astype(float).values
            s += f" | logloss@line v1 {ll(dd.v1_pover.values, yo):.4f} v2 {ll(dd.v2_pover.values, yo):.4f} | bias v1 {(dd.v1_mean - dd.y).mean():+.2f} v2 {(dd.v2_mean - dd.y).mean():+.2f}"
        lines.append(s)
    return lines


def main(first=2023, last=2025, n=2000, tag=""):
    t0 = time.time(); jobs = build(first, last)
    print(f"{len(jobs)} games, {sum(len(j['players']) for j in jobs)} player slots; inputs built in {time.time() - t0:.0f}s", flush=True)
    with Pool(os.cpu_count()) as pool:
        parts = pool.map(_score, [(j, n) for j in jobs], chunksize=8)
    res = pd.DataFrame([r for p in parts for r in p])
    os.makedirs(data.CACHE, exist_ok=True); res.to_pickle(f"{data.CACHE}/backtest_{first}_{last}{tag}.pkl")
    print(f"scored in {time.time() - t0:.0f}s")
    for line in summarize(res):
        print(line)
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    main(int(a[0]) if a else 2023, int(a[1]) if len(a) > 1 else 2025, int(a[2]) if len(a) > 2 else 2000, a[3] if len(a) > 3 else "")
