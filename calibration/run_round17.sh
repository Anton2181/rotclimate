#!/bin/sh
# Round 17: is the spin verdict an artefact of the free temperature offsets?
# Both spins, from their round 16b bests, with the sea and land offsets (the
# stand-ins for cloud, greenhouse and ocean heat transport the energy balance
# misses) limited to +-2 C instead of +-4 / +-5 C. Then the 60-world rematch.
cd "$(dirname "$0")/.."
SET='{"downsample": 8, "steps_per_year": 25, "map_width_mi": 2286.8, "map_height_mi": 1058.2}'
BOUNDS='{"sst_offset": [-2, 2], "land_offset": [-2, 2]}'
for spin in retrograde prograde; do
  fix='{"retrograde":0.75}'; seed=171
  [ $spin = prograde ] && fix='{"retrograde":0.25}' && seed=172
  python3 -m rotclimate.calibrate --out calibration/r17_$spin --start calibration/r16b_$spin/best_params.json \
    --fix "$fix" --seed $seed --evals 200 --workers 4 --objective f1r --physics v8 \
    --seeds 1,2,3 --sigma 0.06 --set "$SET" --bounds "$BOUNDS" > calibration/r17_$spin.log 2>&1
done
python3 scripts/spin_rematch.py calibration/r17_retrograde calibration/r17_prograde \
  --k 3 --worlds 60 --objective f1r --out calibration/r17_rematch.json > calibration/r17_rematch.log 2>&1
echo done > calibration/r17.done
