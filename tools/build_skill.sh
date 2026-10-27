#!/usr/bin/env bash
# Package the skill for upload to Claude: dist/nba-player-props.zip with the skill folder at the zip root.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -f dist/nba-player-props.zip
mkdir -p dist
(cd skills && zip -qr ../dist/nba-player-props.zip nba-player-props -x '*/__pycache__/*' '*.pyc')
unzip -l dist/nba-player-props.zip
