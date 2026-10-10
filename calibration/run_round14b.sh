#!/bin/sh
# Round 14r continued on the faster code (FFT smoothing, trend-started
# temperature passes, racing): the remaining 272 of its 320 evals, from the
# best of its first 48.
cd "$(dirname "$0")/.."
python3 -m rotclimate.calibrate --out calibration/r14b_retrograde --start calibration/r14_retrograde_first48.json \
  --fix '{"retrograde":0.75}' --seed 143 --evals 272 --workers 4 --objective f1 --physics v6 \
  --seeds 1,2,3 --sigma 0.05 --set '{"downsample": 8, "steps_per_year": 25, "map_width_mi": 2286.8, "map_height_mi": 1058.2}' \
  > calibration/r14b_retrograde.log 2>&1
echo done > calibration/r14.done
