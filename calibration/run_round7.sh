#!/bin/sh
# Round 7: continue the v5 calibration from the current best, then re-render everything.
cd "$(dirname "$0")/.."
rm -f calibration/r7.done
python3 -m rotclimate.calibrate --out calibration/r7_retrograde --start calibration/best_params.json \
  --fix '{"retrograde":0.75}' --seed 71 --evals 480 --workers 4 --objective balanced --physics v5 \
  --seeds 1,2,3 --sigma 0.1 > calibration/r7_retrograde.log 2>&1
echo calibrated > calibration/r7.calibrated
# wait for the final-pipeline code to be marked ready (edited while calibrating)
while [ ! -f scripts/.final_ready ]; do sleep 10; done
cp calibration/r7_retrograde/best_params.json calibration/best_params.json
sh scripts/final_run.sh
echo done > calibration/r7.done
