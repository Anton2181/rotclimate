#!/bin/sh
# Round 13: F1 objective with the waterlogged-swamp rule (hot, wet AND flat
# ground; the swamp wins where its rule is met), hex scale, 14 km, from round 12.
cd "$(dirname "$0")/.."
python3 -m rotclimate.calibrate --out calibration/r13_retrograde --start calibration/r12_retrograde/best_params.json \
  --fix '{"retrograde":0.75}' --seed 131 --evals 208 --workers 4 --objective f1 --physics v6 \
  --seeds 1,2,3 --sigma 0.07 --set '{"downsample": 8, "steps_per_year": 25}' > calibration/r13_retrograde.log 2>&1
echo done > calibration/r13.done
