#!/bin/sh
# Round 11: refine round 10 at the published resolution (14 km cells). The
# converged-temperature physics makes 25 steps a year match the 73-step maps,
# so only the grid differs from earlier rounds.
cd "$(dirname "$0")/.."
python3 -m rotclimate.calibrate --out calibration/r11_retrograde --start calibration/r10_retrograde/best_params.json \
  --fix '{"retrograde":0.75}' --seed 111 --evals 192 --workers 4 --objective balanced --physics v6 \
  --seeds 1,2,3 --sigma 0.07 --set '{"downsample": 8, "steps_per_year": 25}' > calibration/r11_retrograde.log 2>&1
echo done > calibration/r11.done
