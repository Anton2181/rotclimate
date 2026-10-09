#!/bin/sh
# Round 2: one CMA-ES calibration per discrete world scenario
# (spin direction x what lies west x what lies east of the map).
cd "$(dirname "$0")/.."
EVALS=${EVALS:-320}
for spin in pro retro; do
  if [ $spin = pro ]; then r=0.25; start=calibration/r1_prograde/best_params.json;
  else r=0.75; start=calibration/r1_retrograde/best_params.json; fi
  for west in ocean land; do
    if [ $west = ocean ]; then w=0.17; else w=0.5; fi
    for east in ocean land; do
      if [ $east = ocean ]; then e=0.17; else e=0.5; fi
      out=calibration/r2_${spin}_W${west}_E${east}
      python3 -m rotclimate.calibrate --out $out --evals $EVALS --workers 4 --sigma 0.2 \
        --start $start --fix "{\"retrograde\":$r,\"beyond_west\":$w,\"beyond_east\":$e}" \
        --seed 21 > $out.log 2>&1
      echo "$out $(tail -n 1 $out.log)"
    done
  done
done
