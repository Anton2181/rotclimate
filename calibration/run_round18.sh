#!/bin/sh
# Round 18: polish both spins' round 17 bests with the same batch pattern
# search (scripts/polish.py), 330 evals each, offsets still within +-2 C. The
# ten genes that sensitivity screening found inert for both spins are frozen.
# Then the 60-world rematch.
cd "$(dirname "$0")/.."
FREEZE=itcz_mean,itcz_shift,trade_speed,storm_reach,subsidence_summer,subsidence_asym,tier3_add,tier4_add,orographic,terrain_drag
BOUNDS='{"sst_offset": [-2, 2], "land_offset": [-2, 2]}'
for spin in retrograde earthlike; do
  python3 scripts/polish.py calibration/round17_$spin.json --out calibration/r18_$spin --physics v8 \
    --objective f1r --seeds 1,2,3 --freeze $FREEZE --bounds "$BOUNDS" --evals 330 > calibration/r18_$spin.log 2>&1
done
python3 scripts/spin_rematch.py calibration/r18_retrograde calibration/r18_earthlike \
  --k 3 --worlds 60 --objective f1r --out calibration/r18_rematch.json > calibration/r18_rematch.log 2>&1
echo done > calibration/r18.done
