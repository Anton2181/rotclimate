#!/bin/sh
# Round 17, Earth-like half and the rematch (the first launch was stopped by a
# job time limit after the retrograde half finished).
cd "$(dirname "$0")/.."
SET='{"downsample": 8, "steps_per_year": 25, "map_width_mi": 2286.8, "map_height_mi": 1058.2}'
BOUNDS='{"sst_offset": [-2, 2], "land_offset": [-2, 2]}'
python3 -m rotclimate.calibrate --out calibration/r17_prograde --start calibration/r16b_prograde/best_params.json \
  --fix '{"retrograde":0.25}' --seed 172 --evals 200 --workers 4 --objective f1r --physics v8 \
  --seeds 1,2,3 --sigma 0.06 --set "$SET" --bounds "$BOUNDS" > calibration/r17_prograde.log 2>&1
python3 scripts/spin_rematch.py calibration/r17_retrograde calibration/r17_prograde \
  --k 3 --worlds 60 --objective f1r --out calibration/r17_rematch.json > calibration/r17_rematch.log 2>&1
echo done > calibration/r17.done
