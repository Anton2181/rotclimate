#!/bin/sh
# Round 6: physics v5 (asymmetric storm track), retrograde then prograde check.
cd "$(dirname "$0")/.."
python3 -m rotclimate.calibrate --out calibration/r6_retrograde --start calibration/r5_retrograde/best_params.json \
  --fix '{"retrograde":0.75}' --seed 61 --evals 400 --workers 4 --objective balanced --physics v5 \
  --seeds 1,2,3 --sigma 0.1 --set '{"storm_asym":0.6,"storm_reach":5.0}' > calibration/r6_retrograde.log 2>&1
python3 -m rotclimate.calibrate --out calibration/r6_prograde --start calibration/r5_prograde/best_params.json \
  --fix '{"retrograde":0.25}' --seed 62 --evals 300 --workers 4 --objective balanced --physics v5 \
  --seeds 1,2 --sigma 0.15 --set '{"storm_asym":0.6,"storm_reach":5.0}' > calibration/r6_prograde.log 2>&1
echo done > calibration/r6.done
