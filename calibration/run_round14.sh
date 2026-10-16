#!/bin/sh
# Round 14: (p) fairness re-check of Earth-like spin under the current physics,
# F1 objective, swamp rule and hex scale; then (r) a longer retrograde refinement.
cd "$(dirname "$0")/.."
SET=$(python3 -c "import json;p=json.load(open('calibration/r8_prograde/best_params.json'));print(json.dumps({'beyond_southeast_land':p['beyond_south_land'],'beyond_northeast_land':p['beyond_north_land'],'instability':0.3,'downsample':8,'steps_per_year':25,'t_iters':12,'soil_memory_days':50.8,'map_width_mi':2293.7,'map_height_mi':1062.0}))")
python3 -m rotclimate.calibrate --out calibration/r14_prograde --start calibration/r8_prograde/best_params.json \
  --fix '{"retrograde":0.25}' --seed 141 --evals 320 --workers 4 --objective f1 --physics v6 \
  --seeds 1,2,3 --sigma 0.15 --set "$SET" > calibration/r14_prograde.log 2>&1
echo done > calibration/r14p.done
python3 -m rotclimate.calibrate --out calibration/r14_retrograde --start calibration/r13_retrograde/best_params.json \
  --fix '{"retrograde":0.75}' --seed 142 --evals 320 --workers 4 --objective f1 --physics v6 \
  --seeds 1,2,3 --sigma 0.05 --set '{"downsample": 8, "steps_per_year": 25}' > calibration/r14_retrograde.log 2>&1
echo done > calibration/r14.done
