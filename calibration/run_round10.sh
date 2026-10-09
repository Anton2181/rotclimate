#!/bin/sh
# Round 10: physics v6 with converged temperature each step (t_iters) and soil
# memory in days, so the 25-step calibration matches the 73-step maps.
cd "$(dirname "$0")/.."
python3 -m rotclimate.calibrate --out calibration/r10_retrograde --start calibration/best_params.json \
  --fix '{"retrograde":0.75}' --seed 101 --evals 480 --workers 4 --objective balanced --physics v6 \
  --seeds 1,2,3 --sigma 0.12 --set '{"t_iters": 12, "soil_memory_days": 50.8}' > calibration/r10_retrograde.log 2>&1
echo done > calibration/r10.done
