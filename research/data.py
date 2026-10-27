"""Load the 2010-11 to 2023-24 regular-season box scores into one player-game table with game context.

Run research/fetch_data.sh first. The cleaned table is cached in data/cache/ (gitignored).
"""
import os
import numpy as np
import pandas as pd

RAW = os.environ.get("NBA_RAW", "data/raw")
CACHE = os.environ.get("NBA_CACHE", "data/cache")

BOX_COLS = {
    "season_year": "season_str", "game_date": "date", "gameId": "game_id", "teamId": "team_id", "teamTricode": "team",
    "personId": "player_id", "personName": "player", "position": "position", "comment": "comment", "minutes": "min_str",
    "fieldGoalsMade": "fgm", "fieldGoalsAttempted": "fga", "threePointersMade": "fg3m", "threePointersAttempted": "fg3a",
    "freeThrowsMade": "ftm", "freeThrowsAttempted": "fta", "reboundsOffensive": "oreb", "reboundsDefensive": "dreb",
    "reboundsTotal": "reb", "assists": "ast", "steals": "stl", "blocks": "blk", "turnovers": "tov",
    "foulsPersonal": "pf", "points": "pts", "plusMinusPoints": "pm",
}
STATS = ["fgm", "fga", "fg3m", "fg3a", "ftm", "fta", "oreb", "dreb", "reb", "ast", "stl", "blk", "tov", "pf", "pts"]


def _minutes(s):
    s = s.astype("string")
    mm = s.str.extract(r"^(\d+):(\d+)$")
    out = pd.to_numeric(mm[0], errors="coerce") + pd.to_numeric(mm[1], errors="coerce") / 60
    plain = pd.to_numeric(s, errors="coerce")
    return out.fillna(plain).fillna(0.0).astype(float)


def load_games(raw=RAW):
    """One row per team-game: possessions, margin, overtime periods, home flag, opponent."""
    t = pd.read_csv(f"{raw}/regular_season_totals_2010_2024.csv")
    t = t.rename(columns={"GAME_ID": "game_id", "TEAM_ID": "team_id", "TEAM_ABBREVIATION": "team", "GAME_DATE": "date",
                          "MATCHUP": "matchup", "MIN": "gmin", "PTS": "team_pts", "PLUS_MINUS": "margin"})
    t["date"] = pd.to_datetime(t["date"]).dt.normalize()
    t["season"] = t["SEASON_YEAR"].str[:4].astype(int)
    t["home"] = t["matchup"].str.contains("vs.").astype(int)
    t["ot"] = np.clip(np.round((t["gmin"] - 48) / 5), 0, None).astype(int)
    t["team_poss"] = t["FGA"] - t["OREB"] + t["TOV"] + 0.44 * t["FTA"]
    t["team_fga"], t["team_fgm"], t["team_fg3a"], t["team_fta"] = t["FGA"], t["FGM"], t["FG3A"], t["FTA"]
    t["team_reb"], t["team_oreb"], t["team_dreb"], t["team_ast"] = t["REB"], t["OREB"], t["DREB"], t["AST"]
    t["team_tov"], t["team_stl"], t["team_blk"], t["team_pf"] = t["TOV"], t["STL"], t["BLK"], t["PF"]
    keep = ["game_id", "team_id", "team", "date", "season", "home", "ot", "gmin", "team_pts", "margin", "team_poss",
            "team_fga", "team_fgm", "team_fg3a", "team_fta", "team_reb", "team_oreb", "team_dreb", "team_ast", "team_tov",
            "team_stl", "team_blk", "team_pf"]
    t = t[keep].drop_duplicates(["game_id", "team_id"])
    o = t[["game_id", "team_id", "team", "team_pts", "team_poss", "team_fga", "team_fgm", "team_fg3a", "team_fta",
           "team_reb", "team_oreb", "team_dreb", "team_tov"]].rename(
        columns=lambda c: c.replace("team", "opp") if c != "game_id" else c)
    g = t.merge(o, on="game_id")
    g = g[g["team_id"] != g["opp_id"]].copy()
    # game pace per 48 minutes (both teams' possession estimates averaged)
    g["poss"] = (g["team_poss"] + g["opp_poss"]) / 2
    g["pace48"] = g["poss"] * 48 / g["gmin"]
    g["total"] = g["team_pts"] + g["opp_pts"]
    return g.reset_index(drop=True)


def load_box(raw=RAW):
    parts = [pd.read_csv(f"{raw}/regular_season_box_scores_2010_2024_part_{i}.csv", low_memory=False) for i in (1, 2, 3)]
    b = pd.concat(parts, ignore_index=True)[list(BOX_COLS)].rename(columns=BOX_COLS)
    b["min"] = _minutes(b["min_str"])
    b["date"] = pd.to_datetime(b["date"]).dt.normalize()
    b["season"] = b["season_str"].str[:4].astype(int)
    b["starter"] = b["position"].notna().astype(int)
    b["played"] = (b["min"] > 0).astype(int)
    for c in STATS:
        b[c] = b[c].astype(float)
    return b.drop(columns=["min_str", "season_str"])


def player_games(raw=RAW, cache=CACHE, refresh=False):
    """Player-game rows (DNPs included, played=0) joined to game context, sorted by player and date."""
    path = f"{cache}/player_games.pkl"
    if not refresh and os.path.exists(path):
        return pd.read_pickle(path)
    os.makedirs(cache, exist_ok=True)
    b, g = load_box(raw), load_games(raw)
    df = b.merge(g.drop(columns=["team", "date", "season"]), on=["game_id", "team_id"], how="inner")
    df = df.sort_values(["player_id", "date", "game_id"]).reset_index(drop=True)
    # rest: days since the team's previous game (back-to-back = 1)
    tg = g[["team_id", "season", "date", "game_id"]].sort_values(["team_id", "date"])
    tg["rest"] = tg.groupby(["team_id", "season"])["date"].diff().dt.days
    df = df.merge(tg[["game_id", "team_id", "rest"]], on=["game_id", "team_id"], how="left")
    df = df.sort_values(["player_id", "date", "game_id"]).reset_index(drop=True)
    df.to_pickle(path)
    return df


if __name__ == "__main__":
    df = player_games(refresh=True)
    print(df.shape, df["season"].min(), df["season"].max())
    print(df[df.played == 1][["min", "pts", "reb", "ast", "fg3m"]].describe().round(2).to_string())
