#!/usr/bin/env bash
# Download the public 2010-11 to 2023-24 regular-season box scores used for calibration.
# Source: https://github.com/NocturneBear/NBA-Data-2010-2024 (CSV, about 75 MB). Not committed to this repo.
set -euo pipefail
dest="${1:-data/raw}"
mkdir -p "$dest"
base="https://raw.githubusercontent.com/NocturneBear/NBA-Data-2010-2024/main"
for f in regular_season_totals_2010_2024.csv \
         regular_season_box_scores_2010_2024_part_1.csv \
         regular_season_box_scores_2010_2024_part_2.csv \
         regular_season_box_scores_2010_2024_part_3.csv; do
  [ -s "$dest/$f" ] || curl -sSfL -m 600 -o "$dest/$f" "$base/$f"
  echo "$f $(wc -c < "$dest/$f") bytes"
done
