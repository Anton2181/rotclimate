#!/bin/sh
# Round 16b: run both spins on toward convergence (reversed spin was still
# improving when round 16's 320 evals ran out): 160 more evals each from each
# spin's round 16 best, same settings, smaller steps.
cd "$(dirname "$0")/.."
SET='{"downsample": 8, "steps_per_year": 25, "map_width_mi": 2286.8, "map_height_mi": 1058.2}'
for spin in retrograde prograde; do
  fix='{"retrograde":0.75}'; seed=163
  [ $spin = prograde ] && fix='{"retrograde":0.25}' && seed=164
  python3 -m rotclimate.calibrate --out calibration/r16b_$spin --start calibration/r16_$spin/best_params.json \
    --fix "$fix" --seed $seed --evals 160 --workers 4 --objective f1r --physics v8 \
    --seeds 1,2,3 --sigma 0.05 --set "$SET" > calibration/r16b_$spin.log 2>&1
done
echo done > calibration/r16b.done
