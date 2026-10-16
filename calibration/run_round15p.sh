#!/bin/sh
# Round 15p: Earth-like spin continued with the same 320-eval budget the
# retrograde refinement (round 14) got, on the same code, layers and scale.
cd "$(dirname "$0")/.."
until [ -f output/final.done ]; do sleep 30; done
python3 -m rotclimate.calibrate --out calibration/r15_prograde --start calibration/r14_prograde/best_params.json \
  --fix '{"retrograde":0.25}' --seed 151 --evals 320 --workers 4 --objective f1 --physics v6 \
  --seeds 1,2,3 --sigma 0.08 --set '{"downsample": 8, "steps_per_year": 25, "map_width_mi": 2286.8, "map_height_mi": 1058.2}' \
  > calibration/r15_prograde.log 2>&1
echo done > calibration/r15p.done
