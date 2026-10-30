"""NFL data layer: play-by-play (nflverse) -> plays, player-game stats, team-game volume, games with closing lines.

Run research/nfl/fetch_data.sh first. Outputs are cached in data/cache/nfl/ (gitignored).
Official-stat conventions (they decide how props settle):
- Pass attempts exclude sacks and two-point tries and include spikes; passing yards are gross (sack yards are not taken off a QB).
- Rush attempts include QB scrambles and kneel-downs (kneels lose yards); two-point tries never count.
- Targets are pass attempts with a listed receiver, interceptions included.
"""
import os

import numpy as np
import pandas as pd

RAW = os.environ.get("NFL_RAW", "data/raw/nfl")
CACHE = os.environ.get("NFL_CACHE", "data/cache/nfl")
SEASONS = range(2016, 2027)
TEAM_MAP = {"OAK": "LV", "SD": "LAC", "STL": "LA"}   # play-by-play uses current franchise codes; snaps and schedules use historical ones

PBP_COLS = ["game_id", "season", "week", "season_type", "posteam", "defteam", "home_team", "away_team", "play_type",
            "pass_attempt", "complete_pass", "interception", "sack", "qb_scramble", "qb_kneel", "qb_spike", "rush_attempt",
            "yards_gained", "passing_yards", "receiving_yards", "rushing_yards", "air_yards", "yards_after_catch",
            "touchdown", "pass_touchdown", "rush_touchdown", "td_player_id", "two_point_attempt",
            "passer_player_id", "receiver_player_id", "rusher_player_id", "yardline_100", "down", "ydstogo",
            "score_differential", "wp", "vegas_wp", "qtr", "game_seconds_remaining", "spread_line", "total_line", "roof",
            "temp", "wind", "fumble_lost", "fumbled_1_player_id", "qb_dropback", "xpass", "epa", "drive",
            "solo_tackle_1_player_id", "solo_tackle_2_player_id", "assist_tackle_1_player_id", "assist_tackle_2_player_id",
            "assist_tackle_3_player_id", "assist_tackle_4_player_id", "tackle_with_assist_1_player_id", "tackle_with_assist_2_player_id",
            "solo_tackle_1_team", "solo_tackle_2_team", "assist_tackle_1_team", "assist_tackle_2_team", "assist_tackle_3_team",
            "assist_tackle_4_team", "tackle_with_assist_1_team", "tackle_with_assist_2_team",
            "sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id",
            "kicker_player_id", "field_goal_attempt", "field_goal_result", "kick_distance", "extra_point_result",
            "posteam_score", "defteam_score", "home_score", "away_score"]


def load_plays(seasons=SEASONS, raw=RAW):
    frames = []
    for y in seasons:
        f = f"{raw}/play_by_play_{y}.csv.gz"
        if not os.path.exists(f):
            continue
        d = pd.read_csv(f, usecols=lambda c: c in PBP_COLS, low_memory=False)
        frames.append(d[d.season_type == "REG"])
    p = pd.concat(frames, ignore_index=True)
    for c in ("pass_attempt", "complete_pass", "interception", "sack", "qb_scramble", "qb_kneel", "qb_spike", "rush_attempt",
              "touchdown", "pass_touchdown", "rush_touchdown", "two_point_attempt", "fumble_lost", "qb_dropback",
              "field_goal_attempt"):
        p[c] = p[c].fillna(0).astype(int)
    p["two_point_attempt"] = p["two_point_attempt"].astype(bool)
    return p


def player_games(p):
    """One row per player-game with official-stat counts, red-zone usage, longest plays and defensive and kicking stats."""
    s = p[~p.two_point_attempt]
    att = s[(s.pass_attempt == 1) & (s.sack == 0)]                 # official pass attempts (spikes included)
    out = []
    g = att.groupby(["game_id", "posteam", "passer_player_id"])
    out.append(g.agg(pass_att=("pass_attempt", "size"), pass_cmp=("complete_pass", "sum"), pass_yds=("passing_yards", "sum"),
                     pass_td=("pass_touchdown", "sum"), ints=("interception", "sum"),
                     pass_long=("passing_yards", "max")).rename_axis(["game_id", "team", "player_id"]))
    sk = s[s.sack == 1].groupby(["game_id", "posteam", "passer_player_id"]).agg(sacked=("sack", "size"))
    out.append(sk.rename_axis(["game_id", "team", "player_id"]))
    ru = s[(s.rush_attempt == 1) & s.rusher_player_id.notna()]
    ru = ru.assign(rz=(ru.yardline_100 <= 20).astype(int), i10=(ru.yardline_100 <= 10).astype(int), gl=(ru.yardline_100 <= 5).astype(int),
                   rtd=((ru.rush_touchdown == 1) & (ru.td_player_id == ru.rusher_player_id)).astype(int),
                   kneel=ru.qb_kneel, scr=ru.qb_scramble)
    out.append(ru.groupby(["game_id", "posteam", "rusher_player_id"]).agg(
        rush_att=("rush_attempt", "size"), rush_yds=("rushing_yards", "sum"), rush_td=("rtd", "sum"), rush_long=("rushing_yards", "max"),
        rz_car=("rz", "sum"), i10_car=("i10", "sum"), gl_car=("gl", "sum"), kneels=("kneel", "sum"), scrambles=("scr", "sum"))
        .rename_axis(["game_id", "team", "player_id"]))
    tg = att[att.receiver_player_id.notna()]
    tg = tg.assign(rz=(tg.yardline_100 <= 20).astype(int), i10=(tg.yardline_100 <= 10).astype(int),
                   rectd=((tg.pass_touchdown == 1) & (tg.td_player_id == tg.receiver_player_id)).astype(int),
                   ay=tg.air_yards.fillna(0), recyds=np.where(tg.complete_pass == 1, tg.receiving_yards.fillna(tg.yards_gained), 0.0))
    out.append(tg.groupby(["game_id", "posteam", "receiver_player_id"]).agg(
        targets=("pass_attempt", "size"), rec=("complete_pass", "sum"), rec_yds=("recyds", "sum"), rec_td=("rectd", "sum"),
        rec_long=("recyds", "max"), air_yds=("ay", "sum"), rz_tgt=("rz", "sum"), i10_tgt=("i10", "sum"))
        .rename_axis(["game_id", "team", "player_id"]))
    # defense: combined tackles (solo + with-assist + assists) and sacks (half sacks count 0.5)
    tk = []
    for c in ("solo_tackle_1", "solo_tackle_2", "tackle_with_assist_1", "tackle_with_assist_2", "assist_tackle_1", "assist_tackle_2",
              "assist_tackle_3", "assist_tackle_4"):
        x = p[p[f"{c}_player_id"].notna()][["game_id", f"{c}_team", f"{c}_player_id"]]
        x = x.rename(columns={f"{c}_player_id": "player_id", f"{c}_team": "team"}); x["tackles"] = 1; tk.append(x)   # tackler's own team
    for c, w in (("sack_player_id", 1.0), ("half_sack_1_player_id", 0.5), ("half_sack_2_player_id", 0.5)):
        x = p[p[c].notna()][["game_id", "defteam", c]].rename(columns={c: "player_id", "defteam": "team"}); x["sacks"] = w; tk.append(x)
    d = pd.concat(tk, ignore_index=True).fillna(0).groupby(["game_id", "team", "player_id"])[["tackles", "sacks"]].sum()
    out.append(d)
    k = p[p.kicker_player_id.notna() & ((p.field_goal_attempt == 1) | p.extra_point_result.notna())]
    k = k.assign(fga=k.field_goal_attempt, fgm=(k.field_goal_result == "made").astype(int), xpm=(k.extra_point_result == "good").astype(int),
                 fg_long=np.where(k.field_goal_result == "made", k.kick_distance, np.nan))
    out.append(k.groupby(["game_id", "posteam", "kicker_player_id"]).agg(fga=("fga", "sum"), fgm=("fgm", "sum"), xpm=("xpm", "sum"),
                                                                       fg_long=("fg_long", "max")).rename_axis(["game_id", "team", "player_id"]))
    pg = pd.concat(out, axis=1).fillna(0).reset_index()
    pg = pg.groupby(["game_id", "team", "player_id"], as_index=False).sum()   # one row per player-game and team
    pg["kick_pts"] = 3 * pg.fgm + pg.xpm
    pg["td_any"] = pg.rush_td + pg.rec_td
    pg["rush_rec_yds"] = pg.rush_yds + pg.rec_yds
    pg["pass_rush_yds"] = pg.pass_yds + pg.rush_yds
    return pg


def team_games(p):
    """Offensive volume per team-game: plays, dropbacks, attempts, carries, sacks, yards, TDs, neutral pass rate."""
    s = p[~p.two_point_attempt & p.posteam.notna()]
    s = s.assign(play=((s.pass_attempt == 1) | (s.rush_attempt == 1)).astype(int),
                 db=((s.pass_attempt == 1) | (s.qb_scramble == 1)).astype(int),
                 neutral=((s.wp.between(0.2, 0.8)) & (s.qtr <= 3) & (s.down <= 2)).astype(int))
    s = s.assign(neutral_db=s.db * s.neutral, neutral_play=s.play * s.neutral,
                 official_att=((s.pass_attempt == 1) & (s.sack == 0)).astype(int),
                 nonqb_rush=((s.rush_attempt == 1) & (s.qb_scramble == 0) & (s.qb_kneel == 0)).astype(int),
                 net_pass=np.where(s.pass_attempt == 1, s.yards_gained.fillna(0), 0.0),
                 rush_y=np.where(s.rush_attempt == 1, s.rushing_yards.fillna(0), 0.0),
                 gross_pass=np.where((s.complete_pass == 1), s.passing_yards.fillna(0), 0.0))
    t = s.groupby(["game_id", "posteam"]).agg(plays=("play", "sum"), dropbacks=("db", "sum"), pass_att=("official_att", "sum"),
                                              rush_att=("rush_attempt", "sum"), nonqb_rush=("nonqb_rush", "sum"), sacks=("sack", "sum"),
                                              pass_yds=("gross_pass", "sum"), net_pass=("net_pass", "sum"), rush_yds=("rush_y", "sum"),
                                              pass_td=("pass_touchdown", "sum"), rush_td=("rush_touchdown", "sum"),
                                              neutral_db=("neutral_db", "sum"), neutral_play=("neutral_play", "sum"),
                                              ints=("interception", "sum"), fum_lost=("fumble_lost", "sum"),
                                              rz_plays=("yardline_100", lambda x: int((x <= 20).sum())))
    t = t.rename_axis(["game_id", "team"]).reset_index()
    t["neutral_pr"] = t.neutral_db / t.neutral_play.replace(0, np.nan)
    return t


def load_games(raw=RAW):
    g = pd.read_csv(f"{raw}/games.csv")
    g = g[(g.game_type == "REG") & (g.season >= min(SEASONS))].copy()
    for c in ("home_team", "away_team"):
        g[c] = g[c].replace(TEAM_MAP)
    return g


def team_view(games):
    """Two rows per game (one per team) with the closing line from that team's side: exp_margin = its expected margin."""
    rows = []
    for side, opp in (("home", "away"), ("away", "home")):
        d = games[["game_id", "season", "week", "gameday", f"{side}_team", f"{opp}_team", f"{side}_score", f"{opp}_score",
                   "spread_line", "total_line", "overtime", "roof", "surface", "temp", "wind", "div_game", f"{side}_rest",
                   f"{opp}_rest", f"{side}_moneyline", "location"]].copy()
        d.columns = ["game_id", "season", "week", "gameday", "team", "opp", "pts", "opp_pts", "spread_line", "total_line", "overtime",
                     "roof", "surface", "temp", "wind", "div_game", "rest", "opp_rest", "moneyline", "location"]
        d["home"] = int(side == "home")
        sign = 1 if side == "home" else -1
        d["exp_margin"] = sign * d.spread_line          # nflverse spread_line: positive = home team favored
        d["implied_pts"] = (d.total_line + d.exp_margin) / 2
        d["margin"] = d.pts - d.opp_pts
        rows.append(d)
    return pd.concat(rows, ignore_index=True)


def load_snaps(seasons=SEASONS, raw=RAW):
    """Snap counts (Pro Football Reference via nflverse), mapped to gsis ids so every player who took a snap is in the table."""
    fr = [pd.read_csv(f"{raw}/snap_counts_{y}.csv") for y in seasons if os.path.exists(f"{raw}/snap_counts_{y}.csv")]
    s = pd.concat(fr, ignore_index=True)
    s = s[s.game_type == "REG"].copy()
    s["team"] = s.team.replace(TEAM_MAP)
    pl = pd.read_csv(f"{raw}/players.csv", usecols=["gsis_id", "pfr_id"]).dropna().drop_duplicates("pfr_id")
    s = s.merge(pl, left_on="pfr_player_id", right_on="pfr_id", how="left").rename(columns={"gsis_id": "player_id"})
    return s[["game_id", "team", "player_id", "player", "position", "offense_snaps", "offense_pct", "defense_snaps", "defense_pct",
              "st_snaps"]].rename(columns={"position": "snap_pos", "player": "snap_name"})


def build(refresh=False):
    os.makedirs(CACHE, exist_ok=True)
    path = f"{CACHE}/tables.pkl"
    if not refresh and os.path.exists(path):
        return pd.read_pickle(path)
    p = load_plays()
    pg, tg = player_games(p), team_games(p)
    games = load_games()
    tv = team_view(games)
    tg = tg.merge(tv, on=["game_id", "team"], how="left")
    pl = pd.read_csv(f"{RAW}/players.csv", usecols=["gsis_id", "display_name", "position", "position_group", "pfr_id"])
    sn = load_snaps()
    sn = sn[sn.player_id.notna() & ((sn.offense_snaps > 0) | (sn.defense_snaps > 0))]
    pg = pg.merge(sn, on=["game_id", "team", "player_id"], how="outer")       # players who played with no stat get zeros
    stat_cols = [c for c in pg.columns if c not in ("game_id", "team", "player_id", "snap_name", "snap_pos")]
    pg[stat_cols] = pg[stat_cols].fillna(0)
    pg = pg.merge(pl.rename(columns={"gsis_id": "player_id", "display_name": "name"}), on="player_id", how="left")
    pg["position"] = pg.position.fillna(pg.snap_pos)
    pg = pg.merge(tv[["game_id", "team", "season", "week", "gameday", "opp", "home", "exp_margin", "implied_pts", "total_line", "spread_line",
                      "margin", "pts", "roof", "temp", "wind", "overtime"]], on=["game_id", "team"], how="left")
    out = dict(plays=p, player_games=pg, team_games=tg, games=games)
    pd.to_pickle(out, path)
    return out


if __name__ == "__main__":
    T = build(refresh=True)
    pg, tg = T["player_games"], T["team_games"]
    print("plays", len(T["plays"]), "player-games", len(pg), "team-games", len(tg), "seasons", sorted(pg.season.dropna().unique()))
    print(tg[["plays", "pass_att", "rush_att", "sacks", "pass_yds", "rush_yds", "pts", "neutral_pr"]].describe().round(2).to_string())
