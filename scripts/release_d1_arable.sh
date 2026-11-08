#!/usr/bin/env bash
# D1 + D2 release (calibration/geography_control_20261107/plan_D1.json; reports/ARABLE_SLOPE_20261108.md): the arable share
# from slope, irrigation gated by height above the river, and FALLOW 0.600. Earth-fit: staged base build from the height map v2.1 checkpoint (the climate is
# unchanged). Free and Whittaker: farming, population, foraging, reach and language layers refreshed in place, after a
# local backup. Resumable: finished stages are recorded in output/atlas_d1/stages_done.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=output/atlas_d1; STAGE=earth_fit_d1_stage; ATLAS=atlases/$STAGE
CK=output/r44_rivers_world/candidate_001.pkl; CAL=calibration/earth_correction_r44_20261107; EVALS=output/earth_correction_r44_20261107
mkdir -p "$OUT"; touch "$OUT/stages_done"
run() { local name=$1; shift; if grep -qx "$name" "$OUT/stages_done"; then echo "skip $name"; return; fi
  echo "== $name $(date -u +%H:%M:%S)"; "$@" > "$OUT/$name.log" 2>&1; echo "$name" >> "$OUT/stages_done"; echo "done $name $(date -u +%H:%M:%S)"; }
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
run world $PY -u -I scripts/build_atlas_variant.py --params calibration/map_world_r44_terrain21/params.json --name $STAGE \
  --title 'Rotclimate Earth-Fit Atlas' --eyebrow 'Climate, farming and settlement · three layouts · c.200 AD' \
  --note 'Earth r44 physics on the published world geometry with the eroded height map v2.1 (every drawn river a flow path); layouts 1–3 and verified numerical checks.' \
  --downsample 8 --image-scale 2 --seeds 1,2,3 --workers 1 --fit-objective zonefit --require-verified --checkpoint $CK
run diagnostics $PY -I scripts/add_r40_atlas_diagnostics.py $ATLAS --out $OUT/diagnostics --release r44
run corrected_layers $PY -I scripts/add_corrected_layers.py $ATLAS --checkpoint $CK --corrections $CAL --evals $EVALS
run corrected_climate $PY -I scripts/add_corrected_climate.py $ATLAS --checkpoint $CK --corrections $CAL --gif
run languages $PY -I scripts/add_language_layers.py $ATLAS
run release_identity $PY -I scripts/tag_atlas_physics.py $ATLAS --params calibration/local_accuracy_20261023/r44_params.json --profile r44 --report reports/ARABLE_SLOPE_20261108.md
if ! grep -qx backup_fw "$OUT/stages_done"; then
  mkdir -p "$OUT/previous_atlases"
  for a in free_fit whittaker_fit; do [ -d "$OUT/previous_atlases/$a" ] || cp -a atlases/$a "$OUT/previous_atlases/$a"; done
  echo backup_fw >> "$OUT/stages_done"
fi
run food_fw $PY -I scripts/add_harvest_to_atlas.py atlases/free_fit atlases/whittaker_fit
run foraging_fw $PY -I scripts/add_foraging_to_atlas.py atlases/free_fit atlases/whittaker_fit
run reach_fw $PY -I scripts/export_reach.py atlases/free_fit atlases/whittaker_fit
run languages_fw $PY -I scripts/add_language_layers.py atlases/free_fit atlases/whittaker_fit
echo "base stages complete"
