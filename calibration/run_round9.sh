#!/bin/sh
# Round 9: physics v6 (instability, split north/south edges), from the round-7 best.
cd "$(dirname "$0")/.."
SET=$(python3 -c "import json;p=json.load(open('calibration/best_params.json'));print(json.dumps({'beyond_southeast_land':p['beyond_south_land'],'beyond_northeast_land':p['beyond_north_land'],'instability':0.3}))")
python3 -m rotclimate.calibrate --out calibration/r9_retrograde --start calibration/best_params.json \
  --fix '{"retrograde":0.75}' --seed 91 --evals 400 --workers 4 --objective balanced --physics v6 \
  --seeds 1,2,3 --sigma 0.12 --set "$SET" > calibration/r9_retrograde.log 2>&1
echo done > calibration/r9.done
