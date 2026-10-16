#!/bin/sh
# Regenerate every map, GIF, chart and the atlas data from one parameter file.
#   scripts/make_all.sh [calibration/best_params.json]
set -e
cd "$(dirname "$0")/.."
P=${1:-calibration/best_params.json}
echo "== full-resolution render ($P)"
python3 -m rotclimate render --params "$P" --out output
echo "== experiments"
python3 -m rotclimate.experiments spin --params "$P" --out output/spin_flip.gif
python3 -m rotclimate.experiments tilt --params "$P" --out output/tilt_sweep.gif
python3 -m rotclimate.experiments surroundings --params "$P" --out output/surroundings.gif
python3 -m rotclimate.experiments lat --params "$P" --out output/latitude_sweep.gif
python3 -m rotclimate.experiments history --out output/improvement.gif
python3 -m rotclimate.experiments robust --params "$P" --out output/robustness.json
echo "== atlas"
python3 -m rotclimate.atlas --params "$P"
echo "done"
