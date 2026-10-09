#!/bin/sh
# Round 12: F1 objective (each zone's rule must cover its painted area AND stay
# out of areas painted as other zones), at the published 14 km, from round 11.
cd "$(dirname "$0")/.."
python3 -m rotclimate.calibrate --out calibration/r12_retrograde --start calibration/r11_retrograde/best_params.json \
  --fix '{"retrograde":0.75}' --seed 121 --evals 208 --workers 4 --objective f1 --physics v6 \
  --seeds 1,2,3 --sigma 0.09 --set '{"downsample": 8, "steps_per_year": 25}' > calibration/r12_retrograde.log 2>&1
echo done > calibration/r12.done
