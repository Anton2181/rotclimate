#!/bin/sh
# Round 16: both spins on equal terms after the literature review
# (reports/Climate simulator improvement literature.md):
# * the swamp rule needs a hot year (mean annual >= ~21 C)
# * physics v7: summer-strengthened subtropical highs; one physically set
#   search box for both spins
# * physics v8: wet ground evaporates away part of the summer warmth, and the
#   objective (f1r) penalises humid summers hotter than Earth's
# 320 evals each from each spin's current best, same worlds 1-3, both
# starting from the same wet-cooling guess (0.4).
cd "$(dirname "$0")/.."
SET='{"downsample": 8, "steps_per_year": 25, "map_width_mi": 2286.8, "map_height_mi": 1058.2, "wet_cooling": 0.4}'
python3 -m rotclimate.calibrate --out calibration/r16_retrograde --start calibration/best_params.json \
  --fix '{"retrograde":0.75}' --seed 161 --evals 320 --workers 4 --objective f1r --physics v8 \
  --seeds 1,2,3 --sigma 0.07 --set "$SET" > calibration/r16_retrograde.log 2>&1
python3 -m rotclimate.calibrate --out calibration/r16_prograde --start calibration/r15_prograde/best_params.json \
  --fix '{"retrograde":0.25}' --seed 162 --evals 320 --workers 4 --objective f1r --physics v8 \
  --seeds 1,2,3 --sigma 0.07 --set "$SET" > calibration/r16_prograde.log 2>&1
echo done > calibration/r16.done
