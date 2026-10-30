#!/usr/bin/env bash
# Download the public nflverse data used to calibrate and backtest the NFL prop engine (not committed).
# Play-by-play, weekly player stats, snap counts and injury reports per season, plus schedules with closing lines.
# Source: https://github.com/nflverse/nflverse-data (releases) and https://github.com/nflverse/nfldata (games.csv).
set -euo pipefail
dest="${1:-data/raw/nfl}"; first="${2:-2016}"; last="${3:-2025}"
mkdir -p "$dest"
base="https://github.com/nflverse/nflverse-data/releases/download"
for y in $(seq "$first" "$last"); do
  for f in "pbp/play_by_play_$y.csv.gz" "player_stats/player_stats_$y.csv" "snap_counts/snap_counts_$y.csv" "injuries/injuries_$y.csv"; do
    out="$dest/$(basename "$f")"
    [ -s "$out" ] || curl -sSfL -m 900 -o "$out" "$base/$f" || echo "missing: $f"
  done
done
curl -sSfL -m 300 -o "$dest/games.csv" "https://raw.githubusercontent.com/nflverse/nfldata/master/data/games.csv"
ls -la "$dest"
