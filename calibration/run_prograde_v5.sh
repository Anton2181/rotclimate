#!/bin/sh
# Fairness check: the same v5 physics and budget as round 7, but Earth-like spin.
cd "$(dirname "$0")/.."
python3 -m rotclimate.calibrate --out calibration/r8_prograde --start calibration/best_params.json \
  --fix '{"retrograde":0.25}' --seed 81 --evals 400 --workers 3 --objective balanced --physics v5 \
  --seeds 1,2,3 --sigma 0.2 > calibration/r8_prograde.log 2>&1
echo done > calibration/r8.done
