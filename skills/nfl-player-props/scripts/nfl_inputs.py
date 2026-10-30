"""nfl_inputs: builds every sim_game() input from nflverse data, the same way the walk-forward backtest built them (2023-25).

Usage (needs github.com and raw.githubusercontent.com; about 40 MB the first time, cached in ./nfl_cache):
    import nfl_props as m, nfl_inputs as d
    D = d.load(2026)                                   # this season and last: plays, player-games, snaps, games with lines
    print(d.slate(D, week=8))                          # the week's games, closing-style lines, roofs, listed QBs
    g, players, notes = d.game(D, 'GB', 'CAR', out=['Christian Watson'])   # home team first (team A); out = confirmed inactives
    S = m.sim_game(g, players)
If the download is blocked, build the inputs by hand (SKILL.md Step 3) from the skill's sources list (references/sources.md,
Appendix A in the single-file skill).
Official-stat conventions (how props settle): pass attempts exclude sacks and include spikes; passing yards are gross; rush attempts
include scrambles and kneel-downs; two-point tries never count; targets are pass attempts with a listed receiver, interceptions included.
"""
import os
import urllib.request

import numpy as np
import pandas as pd

import nfl_props as m

REL = "https://github.com/nflverse/nflverse-data/releases/download/{tag}/{file}"
GAMES = "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
TEAM_MAP = {"OAK": "LV", "SD": "LAC", "STL": "LA"}
COLS = ["game_id", "season", "week", "season_type", "posteam", "defteam", "pass_attempt", "complete_pass", "interception", "sack",
        "qb_scramble", "qb_kneel", "qb_dropback", "rush_attempt", "yards_gained", "passing_yards", "receiving_yards", "rushing_yards",
        "pass_touchdown", "rush_touchdown", "td_player_id", "two_point_attempt", "passer_player_id", "receiver_player_id",
        "rusher_player_id", "yardline_100", "down", "wp", "qtr"]
LGPOS = dict(catch=dict(WR=0.62, TE=0.70, RB=0.77, FB=0.75), ypt=dict(WR=8.0, TE=7.3, RB=6.0, FB=5.5), ypc=dict(RB=4.27, WR=5.8, TE=4.0, FB=3.5))


def _get(url, cache):
    os.makedirs(cache, exist_ok=True); path = os.path.join(cache, url.rsplit("/", 1)[1])
    if not os.path.exists(path):
        urllib.request.urlretrieve(url, path)
    return path


def _plays(season, cache):
    f = _get(REL.format(tag="pbp", file=f"play_by_play_{season}.csv.gz"), cache)
    p = pd.read_csv(f, usecols=lambda c: c in COLS, low_memory=False)
    p = p[p.season_type == "REG"].copy()
    for c in ("pass_attempt", "complete_pass", "interception", "sack", "qb_scramble", "qb_kneel", "qb_dropback", "rush_attempt",
              "pass_touchdown", "rush_touchdown"):
        p[c] = p[c].fillna(0).astype(int)
    p["two_point_attempt"] = p.two_point_attempt.fillna(0).astype(bool)
    return p[~p.two_point_attempt & p.posteam.notna()]


def _player_games(p):
    att = p[(p.pass_attempt == 1) & (p.sack == 0)]
    out = [att.groupby(["game_id", "posteam", "passer_player_id"]).agg(pass_att=("pass_attempt", "size"), pass_cmp=("complete_pass", "sum"),
                                                                     pass_yds=("passing_yards", "sum"), pass_td=("pass_touchdown", "sum"))]
    ru = p[(p.rush_attempt == 1) & p.rusher_player_id.notna()]
    ru = ru.assign(rz=(ru.yardline_100 <= 20).astype(int), scr=ru.qb_scramble, kneel=ru.qb_kneel,
                   scr_y=np.where(ru.qb_scramble == 1, ru.rushing_yards.fillna(0), 0.0),
                   des_y=np.where((ru.qb_scramble == 0) & (ru.qb_kneel == 0), ru.rushing_yards.fillna(0), 0.0))
    out.append(ru.groupby(["game_id", "posteam", "rusher_player_id"]).agg(rush_att=("rush_attempt", "size"), rush_yds=("rushing_yards", "sum"),
                                                                        rz_car=("rz", "sum"), scrambles=("scr", "sum"), kneels=("kneel", "sum"),
                                                                        scr_y=("scr_y", "sum"), des_y=("des_y", "sum")))
    tg = att[att.receiver_player_id.notna()]
    tg = tg.assign(i10=(tg.yardline_100 <= 10).astype(int), recyds=np.where(tg.complete_pass == 1, tg.receiving_yards.fillna(tg.yards_gained), 0.0))
    out.append(tg.groupby(["game_id", "posteam", "receiver_player_id"]).agg(targets=("pass_attempt", "size"), rec=("complete_pass", "sum"),
                                                                          rec_yds=("recyds", "sum"), i10_tgt=("i10", "sum")))
    out = [o.rename_axis(["game_id", "team", "player_id"]) for o in out]
    pg = pd.concat(out, axis=1).fillna(0).reset_index()
    return pg.groupby(["game_id", "team", "player_id"], as_index=False).sum()


def _team_games(p):
    s = p.assign(play=((p.pass_attempt == 1) | (p.rush_attempt == 1)).astype(int), db=((p.pass_attempt == 1) | (p.qb_scramble == 1)).astype(int),
                 neutral=((p.wp.between(0.2, 0.8)) & (p.qtr <= 3) & (p.down <= 2)).astype(int))
    s = s.assign(neutral_db=s.db*s.neutral, neutral_play=s.play*s.neutral, official_att=((s.pass_attempt == 1) & (s.sack == 0)).astype(int),
                 des=((s.rush_attempt == 1) & (s.qb_scramble == 0) & (s.qb_kneel == 0)).astype(int),
                 gross=np.where(s.complete_pass == 1, s.passing_yards.fillna(0), 0.0))
    t = s.groupby(["game_id", "posteam", "season", "week"]).agg(plays=("play", "sum"), dropbacks=("db", "sum"), pass_att=("official_att", "sum"),
                                                                cmp=("complete_pass", "sum"), sacks=("sack", "sum"), scr=("qb_scramble", "sum"),
                                                                ints=("interception", "sum"), pass_yds=("gross", "sum"), des=("des", "sum"),
                                                                pass_td=("pass_touchdown", "sum"), rush_td=("rush_touchdown", "sum"),
                                                                neutral_db=("neutral_db", "sum"), neutral_play=("neutral_play", "sum"))
    return t.reset_index().rename(columns={"posteam": "team"})


def load(season, cache="nfl_cache", prev=True):
    """Downloads (once) and builds this season's and last season's tables. Returns a dict used by every function below."""
    seasons = [season-1, season] if prev else [season]
    P = pd.concat([_plays(s, cache) for s in seasons], ignore_index=True)
    for c in ("posteam", "defteam"):
        P[c] = P[c].replace(TEAM_MAP)
    pg, tg = _player_games(P), _team_games(P)
    games = pd.read_csv(_get(GAMES, cache)); games = games[(games.game_type == "REG") & games.season.isin(seasons)].copy()
    for c in ("home_team", "away_team"):
        games[c] = games[c].replace(TEAM_MAP)
    pl = pd.read_csv(_get(REL.format(tag="players", file="players.csv"), cache), usecols=["gsis_id", "display_name", "position", "pfr_id"])
    sn = []
    for s in seasons:
        x = pd.read_csv(_get(REL.format(tag="snap_counts", file=f"snap_counts_{s}.csv"), cache))
        sn.append(x[x.game_type == "REG"])
    sn = pd.concat(sn, ignore_index=True); sn["team"] = sn.team.replace(TEAM_MAP)
    sn = sn.merge(pl[["gsis_id", "pfr_id"]].dropna().drop_duplicates("pfr_id"), left_on="pfr_player_id", right_on="pfr_id", how="left")
    sn = sn[sn.gsis_id.notna() & (sn.offense_snaps > 0)][["game_id", "team", "gsis_id", "offense_snaps", "offense_pct"]].rename(columns={"gsis_id": "player_id"})
    pg = pg.merge(sn, on=["game_id", "team", "player_id"], how="outer")      # a player who played and touched nothing counts as zeros
    num = [c for c in pg.columns if c not in ("game_id", "team", "player_id")]
    pg[num] = pg[num].fillna(0)
    pg = pg.merge(pl.rename(columns={"gsis_id": "player_id", "display_name": "name"})[["player_id", "name", "position"]], on="player_id", how="left")
    wk = tg[["game_id", "team", "season", "week"]]
    pg = pg.merge(wk, on=["game_id", "team"], how="inner")
    tt = pg.assign(nq=np.where(pg.position == "QB", 0, pg.rush_att)).groupby(["game_id", "team"]).agg(
        t_tgt=("targets", "sum"), t_nq=("nq", "sum"), t_i10=("i10_tgt", "sum"), t_rzc=("rz_car", "sum")).reset_index()
    pg = pg.merge(tt, on=["game_id", "team"]).merge(tg[["game_id", "team", "des"]].rename(columns={"des": "t_des"}), on=["game_id", "team"])
    pg["nq_rush"] = np.where(pg.position == "QB", 0, pg.rush_att); pg["qdes"] = pg.rush_att-pg.scrambles-pg.kneels
    tgm = tg[["team", "season", "week", "game_id"]].sort_values(["team", "season", "week"]).copy(); tgm["k"] = tgm.groupby(["team", "season"]).cumcount()
    pg = pg.merge(tgm[["game_id", "team", "k"]], on=["game_id", "team"]).sort_values(["player_id", "season", "week"])
    return dict(season=season, plays=P, pg=pg, tg=tg, games=games, tgm=tgm)


def league(D, week=None):
    """This season's league norms known before `week`, blended with last season by weeks played (as the backtest did)."""
    tg, s = D["tg"], D["season"]; cur = tg[(tg.season == s) & ((tg.week < week) if week else True)]; prv = tg[tg.season == s-1]
    g = D["games"]; gc = g[(g.season == s) & ((g.week < week) if week else g.result.notna())]; gp = g[g.season == s-1]
    w = len(cur)/(len(cur)+160.0)
    pace = (1-w)*(prv.plays.mean() if len(prv) else m.LG["pace"])+w*(cur.plays.mean() if len(cur) else m.LG["pace"])
    tot = (1-w)*(gp.total_line.mean() if len(gp) else 45.0)+w*(gc.total_line.mean() if len(gc) else 45.0)
    npr = (cur.neutral_db.sum()+prv.neutral_db.sum()*0.5)/max(cur.neutral_play.sum()+prv.neutral_play.sum()*0.5, 1)
    return dict(pace=round(float(pace), 2), total=round(float(tot), 2), npr=round(float(npr), 4))


def slate(D, week):
    """The week's games from nflverse's schedule: lines (spread_line > 0 means the home team is favored), roof, listed QBs, rest."""
    g = D["games"]; g = g[(g.season == D["season"]) & (g.week == week)]
    return g[["game_id", "gameday", "gametime", "away_team", "home_team", "spread_line", "total_line", "away_moneyline", "home_moneyline",
              "roof", "temp", "wind", "away_qb_name", "home_qb_name", "away_rest", "home_rest"]].reset_index(drop=True)


def _hist(D, team, week):
    tg = D["tg"]; s = D["season"]
    return tg[(tg.team == team) & (tg.season == s) & ((tg.week < week) if week else True)]


def team_profile(D, team, week=None, lg=None):
    """Season-to-date team tendencies, shrunk by the fitted weights (pace 3 games, neutral pass rate 150 plays, sacks 489 dropbacks...)."""
    h = _hist(D, team, week); L = m.LG; lg = lg or league(D, week); n = len(h)
    c = lambda col: float(h[col].sum())
    return dict(games=n, pace=(c("plays")+3*lg["pace"])/(n+3), npr=(c("neutral_db")+m.NPR_K*lg["npr"])/(c("neutral_play")+m.NPR_K),
                sack=(c("sacks")+489*L["sack"])/(c("dropbacks")+489), int=(c("ints")+2490*L["int"])/(c("pass_att")+2490),
                comp=(c("cmp")+368*L["comp"])/(c("pass_att")+368), ypcomp=(c("pass_yds")+150*L["ypcomp"])/(c("cmp")+150),
                pass_td_share=(c("pass_td")+10*L["pass_td_share"])/(c("pass_td")+c("rush_td")+10))


def qb_profile(D, qb, week=None):
    """The starter's own rushing: share of team designed runs, scramble rate, yards per designed run and per scramble (shrunk to last season
    or the league). qb: name or gsis id."""
    pg, s, L = D["pg"], D["season"], m.LG
    x = pg[(pg.player_id == qb) | (pg.name == qb)]
    cur = x[(x.season == s) & ((x.week < week) if week else True)]; prv = x[x.season == s-1]
    ok = lambda v, k: v >= k
    pr_ds = prv.qdes.sum()/prv.t_des.sum() if ok(prv.t_des.sum(), 100) else L["design_qb"]
    pr_sr = prv.scrambles.sum()/(prv.pass_att.sum()+prv.scrambles.sum()) if ok(prv.pass_att.sum(), 150) else L["scramble"]
    pr_yd = prv.des_y.sum()/prv.qdes.sum() if ok(prv.qdes.sum(), 20) else L["ypc_qb_design"]
    pr_ys = prv.scr_y.sum()/prv.scrambles.sum() if ok(prv.scrambles.sum(), 30) else L["ypc_qb_scramble"]
    return dict(design_qb=m.project_rate(cur.qdes.sum(), cur.t_des.sum(), pr_ds, "design"),
                scramble=m.project_rate(cur.scrambles.sum(), (cur.pass_att+cur.scrambles).sum(), pr_sr, "scramble"),
                ypc_design=m.project_rate(cur.des_y.sum(), cur.qdes.sum(), pr_yd, "ypc_design"),
                ypc_scramble=m.project_rate(cur.scr_y.sum(), cur.scrambles.sum(), pr_ys, "ypc_scramble"),
                games=int(len(cur)), name=str(x.name.iloc[0]) if len(x) else qb)


def starter(D, team, week=None):
    """The QB who took the team's first dropback in its latest game: a default only. Confirm the starter from news (Step 3e)."""
    h = _hist(D, team, week)
    if not len(h): return None
    gid = h.sort_values("week").game_id.iloc[-1]; p = D["plays"]
    d = p[(p.game_id == gid) & (p.posteam == team) & ((p.qb_dropback == 1) | (p.pass_attempt == 1) | (p.qb_scramble == 1))]
    q = d.passer_player_id.fillna(d.rusher_player_id).dropna()
    return q.iloc[0] if len(q) else None


def player_profiles(D, team, week=None):
    """Every player who played for the team this season: target share and non-QB carry share (recency-weighted, shrunk toward last
    season), catch rate, yards per catch, yards per carry, inside-10 and red-zone shares, games, games just missed, share_cv."""
    pg, s = D["pg"], D["season"]; tk = D["tgm"]; tk = tk[(tk.team == team) & (tk.season == s) & ((tk.week < week) if week else True)]
    k_now = len(tk)                                                     # the upcoming game's index in the team's season
    cur = pg[(pg.team == team) & (pg.season == s) & ((pg.week < week) if week else True)]
    prv = pg[pg.season == s-1].groupby("player_id").agg(tg=("targets", "sum"), ttg=("t_tgt", "sum"), car=("nq_rush", "sum"), tnq=("t_nq", "sum"),
                                                        rec=("rec", "sum"), ry=("rec_yds", "sum"), rsy=("rush_yds", "sum"), ra=("rush_att", "sum"))
    rows = []
    for pid, h in cur.sort_values("week").groupby("player_id"):
        pos = h.position.iloc[0]
        if pos not in ("WR", "TE", "RB", "FB"): continue
        pv = prv.loc[pid] if pid in prv.index else None
        has_prev = pv is not None and pv.ttg >= 100
        pr_t = pv.tg/pv.ttg if has_prev else None
        pr_c = pv.car/pv.tnq if (pv is not None and pv.tnq >= 80) else None
        tsh = m.project_share(h.targets.values, h.t_tgt.values, "tgt", pr_t); csh = m.project_share(h.nq_rush.values, h.t_nq.values, "car", pr_c)
        p_catch = pv.rec/pv.tg if (has_prev and pv.tg >= 20) else LGPOS["catch"].get(pos, 0.65)
        p_ypt = pv.ry/pv.tg if (has_prev and pv.tg >= 20) else LGPOS["ypt"].get(pos, 7.5)
        p_ypc = pv.rsy/pv.ra if (pv is not None and pv.ra >= 40) else LGPOS["ypc"].get(pos, 4.27)
        catch = m.project_rate(h.rec.sum(), h.targets.sum(), p_catch, "catch"); ypt = m.project_rate(h.rec_yds.sum(), h.targets.sum(), p_ypt, "ypt")
        ypc = m.project_rate(h.rush_yds.sum(), h.rush_att.sum(), p_ypc, "ypc")
        missed = int(k_now-h.k.iloc[-1]-1)
        rows.append(dict(name=h.name.iloc[0], player_id=pid, pos=pos, games=len(h), missed=missed, has_prev=bool(has_prev),
                         tgt=tsh, car=csh, catch=float(np.clip(catch, 0.3, 0.95)), ypr=float(np.clip(ypt/max(catch, 0.3), 4.0, 25.0)),
                         ypc=float(np.clip(ypc, 2.0, 8.0)), i10=float((h.i10_tgt.sum()+2*tsh)/(h.t_i10.sum()+2)),
                         rz=float((h.rz_car.sum()+3*csh)/(h.t_rzc.sum()+3)),
                         share_cv=0.20 if (missed > 0 or len(h) < 3) else 0.10 if (has_prev and len(h) >= 6) else 0.14,
                         last3_tgt=round(float(h.targets.tail(3).sum()/max(h.t_tgt.tail(3).sum(), 1)), 3),
                         last3_car=round(float(h.nq_rush.tail(3).sum()/max(h.t_nq.tail(3).sum(), 1)), 3),
                         snap_pct=round(float(h.offense_pct.tail(3).mean()), 2)))
    return pd.DataFrame(rows).sort_values("tgt", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()


def split_shares(D, team, with_=(), without=(), week=None):
    """Lineup split: target and non-QB carry shares over this season's games where every `with_` player played and no `without` player did.
    Use it when the lineup changed (a starter back from injury, a trade): the season-long numbers mix two different offenses."""
    pg, s = D["pg"], D["season"]; x = pg[(pg.team == team) & (pg.season == s) & ((pg.week < week) if week else True)]
    on = x.groupby("game_id").name.apply(set); keep = [gid for gid, st in on.items() if set(with_) <= st and not (set(without) & st)]
    y = x[x.game_id.isin(keep)]
    if not len(y): return pd.DataFrame()
    t = y.groupby("game_id").agg(tt=("targets", "sum"), tc=("nq_rush", "sum")).sum()
    r = y.groupby(["name", "position"]).agg(games=("game_id", "nunique"), tgt=("targets", "sum"), car=("nq_rush", "sum")).reset_index()
    r["tgt"] = (r.tgt/max(t.tt, 1)).round(3); r["car"] = (r.car/max(t.tc, 1)).round(3)
    return r[(r.tgt >= 0.02) | (r.car >= 0.03)].sort_values("tgt", ascending=False).reset_index(drop=True).assign(team_games=len(keep))


def game(D, home, away, spread_home=None, total=None, week=None, wind=None, temp=None, roof=None, out=(), back=(), qbs=None, extra=(),
         shares=None):
    """Team A = home. Lines default to nflverse's schedule (spread_line > 0: home favored); pass the live spread and total when you have
    them. The default active list is everyone who played the team's last game (what the backtest knew); then:
      out: confirmed inactives (names). A regular who played last week gets usage_shift_nfl() applied to his teammates.
      back: players returning from a missed game or more (confirmed active): they get return_keep() and share_cv 0.30.
      extra: player dicts (team 'A' or 'B') for anyone with no game this season (an IR return: last season's share x return_keep(..., True)).
      shares: {name: dict(tgt=..., car=...)} to override a projection (a lineup split from split_shares(), news of a role change).
      qbs: {team: starter name}; default the schedule's listed QB, else the QB who took the first snap of the team's last game.
    Each team's list then gets share_budget(). Returns (g, players, notes) for m.sim_game(g, players); read every note."""
    s = D["season"]; gm = D["games"]; row = gm[(gm.season == s) & (gm.home_team == home) & (gm.away_team == away)]
    row = row[row.result.isna()] if week is None and row.result.isna().any() else row
    if week is None and len(row): week = int(row.week.iloc[-1])
    r = row[row.week == week].iloc[0] if len(row) else None
    spread_home = float(r.spread_line) if spread_home is None and r is not None else spread_home     # home expected margin
    total = float(r.total_line) if total is None and r is not None else total
    roof = roof or (r.roof if r is not None and isinstance(r.roof, str) else "outdoors")
    lg = league(D, week); m.LG_SEASON.update(lg)
    g = dict(exp_margin=float(spread_home), total=float(total), wind=float(wind or 0.0), temp=60.0 if temp is None else float(temp), roof=roof)
    notes = [f"week {week}, league norms {lg}; lines: home expected margin {spread_home:+.1f}, total {total}"]; players = []
    tp = {t: team_profile(D, t, week, lg) for t in (home, away)}
    for side, team, opp in (("A", home, away), ("B", away, home)):
        sign = 1 if side == "A" else -1
        g[side] = {k: v for k, v in tp[team].items() if k != "games"}
        g[side]["pace"] = m.expected_plays(total, sign*spread_home, tp[team]["pace"], tp[opp]["pace"], lg["pace"], lg["total"])
        listed = (r.home_qb_name if team == home else r.away_qb_name) if r is not None else None
        listed = listed if isinstance(listed, str) and (D["pg"].name == listed).any() else None
        q = (qbs or {}).get(team) or listed or starter(D, team, week)
        if q is not None:
            qp = qb_profile(D, q, week); g[side].update({k: qp[k] for k in ("design_qb", "scramble", "ypc_design", "ypc_scramble")})
            players.append(dict(name=qp["name"], team=side, pos="QB")); notes.append(f"{team} QB {qp['name']} ({qp['games']} games this season)")
        pp = player_profiles(D, team, week)
        if not len(pp): continue
        recent = pp[pp.missed == 0]; idle = pp[(pp.missed > 0) & ~pp.name.isin(back) & ((pp.tgt >= 0.05) | (pp.car >= 0.08))]
        if len(idle):
            notes.append(f"{team}: not in the last game (left out; add to back= if active): " +
                         ", ".join(f"{a.name} (tgt {a.tgt:.2f}, car {a.car:.2f}, missed {a.missed})" for a in idle.itertuples()))
        act = pd.concat([recent[~recent.name.isin(out)], pp[pp.name.isin(back)]], ignore_index=True)
        for c in ("tgt", "car"):
            act[c] = [v*m.return_keep(c, int(ms), False, False) if ms > 0 else v for v, ms in zip(act[c], act.missed)]
        act.loc[act.missed > 0, "share_cv"] = 0.30
        mates = {rr["name"]: dict(rr) for rr in act.to_dict("records")}
        for nm, ov in (shares or {}).items():
            if nm in mates: mates[nm].update(ov); notes.append(f"{team}: {nm} shares set by hand {ov}")
        for o in recent[recent.name.isin(out)].to_dict("records"):
            if o["tgt"] >= 0.15 or o["car"] >= 0.30:
                mates = m.usage_shift_nfl(dict(pos=o["pos"], tgt=o["tgt"], car=o["car"]), mates)
                notes.append(f"{team}: {o['name']} out (tgt {o['tgt']:.2f}, car {o['car']:.2f}): teammates' usage shifted")
        lst = [dict(v, team=side) for v in mates.values()] + [dict(e, missed=e.get("missed", 0)) for e in extra if e.get("team") == side]
        for v in lst:
            v["tgt"] = v["tgt"] if v.get("tgt", 0) >= 0.02 else 0.0; v["car"] = v["car"] if v.get("car", 0) >= 0.03 else 0.0
            if v.get("missed", 0) > 0: notes.append(f"{team}: {v['name']} back after {v['missed']} missed game(s): usage x return_keep, share_cv 0.30")
        lst = m.share_budget(m.share_budget(lst, "tgt"), "car")
        players += [v for v in lst if v["tgt"] >= 0.05 or v["car"] >= 0.08]
    return g, players, notes
