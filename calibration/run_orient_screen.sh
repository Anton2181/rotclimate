#!/bin/sh
# Orientation screen: true north at every 30 deg from the top of the map, both
# spins. Each case gets a short calibration (80 evals, one surrounding world,
# broad steps) from that spin's round 18 best, so latitude, tilt and the rest
# can adapt to the new orientation. Results: calibration/orient/<bearing>_<spin>.
cd "$(dirname "$0")/.."
mkdir -p calibration/orient
for b in 0 30 60 90 120 150 180 210 240 270 300 330; do
  for spin in earthlike retrograde; do
    fix='{"retrograde":0.25}'; [ $spin = retrograde ] && fix='{"retrograde":0.75}'
    out=calibration/orient/${b}_$spin
    [ -f $out/best_params.json ] && [ -f $out.done ] && continue
    python3 -m rotclimate.calibrate --out $out --start calibration/round18_$spin.json \
      --fix "$fix" --seed $((1000 + b)) --evals 80 --workers 4 --objective f1r --physics v8 \
      --seeds 1 --sigma 0.15 --race 0 \
      --set "{\"downsample\": 8, \"steps_per_year\": 25, \"north_bearing\": $b}" > $out.log 2>&1
    echo done > $out.done
  done
done
echo done > calibration/orient/screen.done
