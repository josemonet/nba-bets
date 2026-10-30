#!/usr/bin/env bash
# Re-run every NFL calibration analysis and the walk-forward backtest; outputs land in research/nfl/results/.
# Prerequisites: research/nfl/fetch_data.sh, then python research/nfl/data.py (builds data/cache/nfl/tables.pkl).
set -uo pipefail
cd "$(dirname "$0")/../.."
mkdir -p research/nfl/results
for f in research/nfl/analyses/*.py; do
  n=$(basename "$f" .py); echo "== $n"; python -I "$f" > "research/nfl/results/$n.txt" 2>&1 || echo "   failed (see results/$n.txt)"
done
python -I research/nfl/calibrate_passing.py > research/nfl/results/calibrate_passing.txt 2>&1 || true
python -I research/nfl/backtest.py 2023 2025 2000 _final > research/nfl/results/backtest_2023_2025.txt 2>&1
python -I research/nfl/audit.py data/cache/nfl/backtest_2023_2025_final.pkl > research/nfl/results/audit_2023_2025.txt 2>&1
