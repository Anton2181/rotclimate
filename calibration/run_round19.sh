#!/bin/sh
# Round 19, after the orientation screen: both spins on the Koppen-consistent
# zone rules with the map's orientation free (physics v9). Each spin starts
# from its best screened orientation, gets 320 CMA-ES evals on worlds 1-3, the
# same pattern-search polish as round 18, then the 60-world rematch.
set -eu
cd "$(dirname "$0")/.."
# The downloaded handoff omits the orientation-screen outputs. Use the
# retained round-18 fits when no completed screen is available.
SET='{"downsample": 8, "steps_per_year": 25}'
BOUNDS='{"sst_offset": [-2, 2], "land_offset": [-2, 2]}'
FREEZE=itcz_mean,itcz_shift,trade_speed,storm_reach,subsidence_summer,subsidence_asym,tier3_add,tier4_add,orographic,terrain_drag
for spin in earthlike retrograde; do
  fix='{"retrograde":0.25}'; [ $spin = retrograde ] && fix='{"retrograde":0.75}'
  start=$(python3 - "$spin" <<'PY'
import glob, json, sys
from pathlib import Path
best = None
for d in glob.glob(f"calibration/orient/*_{sys.argv[1]}"):
    if not Path(f"{d}.done").exists() or not Path(f"{d}/best_params.json").exists():
        continue
    rows = [json.loads(l) for l in open(f"{d}/evals.jsonl")]
    rows = [r for r in rows if not r.get("error") and not r.get("raced")]
    if not rows:
        continue
    s = max(r["score"] for r in rows)
    if best is None or s > best[0]:
        best = (s, d)
print(f"{best[1]}/best_params.json" if best else f"calibration/round18_{sys.argv[1]}.json")
PY
)
  echo "$spin starts from $start" >> calibration/r19.log
  python3 -m rotclimate.calibrate --out calibration/r19_$spin --start $start --fix "$fix" --seed 19$((${#spin})) \
    --evals 321 --workers 4 --objective f1r --physics v9 --seeds 1,2,3 --sigma 0.06 --race 0 \
    --set "$SET" --bounds "$BOUNDS" > calibration/r19_$spin.log 2>&1
  python3 scripts/polish.py calibration/r19_$spin/best_params.json --out calibration/r19p_$spin --physics v9 \
    --objective f1r --seeds 1,2,3 --freeze $FREEZE --bounds "$BOUNDS" --evals 330 > calibration/r19p_$spin.log 2>&1
done
python3 scripts/spin_rematch.py calibration/r19p_retrograde calibration/r19p_earthlike \
  --k 3 --worlds 60 --objective f1r --out calibration/r19_rematch.json > calibration/r19_rematch.log 2>&1
echo done > calibration/r19.done
