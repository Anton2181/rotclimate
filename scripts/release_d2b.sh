#!/usr/bin/env bash
# D2b refresh (calibration/geography_control_20261107/plan_D1.json "D2b"; reports/ARABLE_SLOPE_20261108.md): the irrigation
# height gate 10 -> 5 m. Only the Earth-fit atlas has an eroded terrain file, so only it changes: farming (raw and on the
# corrected climate), foraging, reach and languages refreshed in place after a backup, then the add-on layers in dependency
# order. The climate and the free / Whittaker atlases are unchanged. Resumable (output/atlas_d2b/stages_done).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=output/atlas_d2b; ATLAS=atlases/earth_fit
CK=output/r44_rivers_world/candidate_001.pkl; CAL=calibration/earth_correction_r44_20261107
grep -q '^IRRIGATION_HAND_H0 = 5.0' harvest/export.py || { echo "harvest/export.py does not carry the D2b gate"; exit 1; }
mkdir -p "$OUT"; touch "$OUT/stages_done"
run() { local name=$1; shift; if grep -qx "$name" "$OUT/stages_done"; then echo "skip $name"; return; fi
  echo "== $name $(date -u +%H:%M:%S)"; "$@" > "$OUT/$name.log" 2>&1; echo "$name" >> "$OUT/stages_done"; echo "done $name $(date -u +%H:%M:%S)"; }
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
if ! grep -qx backup "$OUT/stages_done"; then
  mkdir -p "$OUT/previous_atlases"; [ -d "$OUT/previous_atlases/earth_fit_d1" ] || cp -a $ATLAS "$OUT/previous_atlases/earth_fit_d1"
  echo backup >> "$OUT/stages_done"
fi
run food $PY -I scripts/add_harvest_to_atlas.py $ATLAS
run corrected_climate $PY -I scripts/add_corrected_climate.py $ATLAS --checkpoint $CK --corrections $CAL --gif
run foraging $PY -I scripts/add_foraging_to_atlas.py $ATLAS
run reach $PY -I scripts/export_reach.py $ATLAS
run languages $PY -I scripts/add_language_layers.py $ATLAS
run release_identity $PY -I scripts/tag_atlas_physics.py $ATLAS --params calibration/local_accuracy_20261023/r44_params.json --profile r44 --report reports/ARABLE_SLOPE_20261108.md
run admin_inventory $PY -I scripts/audit_administrative_inventory.py
run coverage_review $PY -I scripts/review_world_coverage.py
run coverage $PY -I scripts/publish_world_coverage.py
run pasture $PY -I scripts/build_pasture_maps.py
run farm_work $PY -I scripts/build_cereal_work_maps.py
run presence $PY -I scripts/build_presence_mobility.py
run imperial_review $PY -I scripts/review_imperial_access.py
run imperial_access $PY -I scripts/publish_imperial_access.py
run hierarchy_review $PY -I scripts/review_administrative_hierarchy.py
run hierarchy $PY -I scripts/publish_administrative_hierarchy.py
run fertility_maps $PY -I scripts/fertility_integration.py maps
run settlement_review $PY -I scripts/review_settlement_integration.py
run settlement_labour $PY -I scripts/extend_settlement_labour.py
run settlement_fertility $PY -I scripts/extend_settlement_fertility.py
run control_v2 $PY -I scripts/build_control_v2.py
run control_v21 $PY -I scripts/build_control_v21.py
run settlement_publish $PY -I scripts/publish_settlement_integration.py --origin output/settlement_fertility_20261106
run pages python3 -I scripts/refresh_atlas_pages.py
echo "D2b refresh complete"
