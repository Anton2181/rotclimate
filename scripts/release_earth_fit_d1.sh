#!/usr/bin/env bash
# Earth-fit-only completion of the D1 + D2 (+ D2b) release (reports/ARABLE_SLOPE_20261108.md). Owner, 8 Nov 2026: the free
# and Whittaker fits are retired (scripts/atlas_set.py), so their refresh stages of release_d1_arable.sh are skipped.
# Requires the Earth-fit base stages of release_d1_arable.sh (world .. release_identity) on atlases/earth_fit_d1_stage.
# With the D2b gate (harvest/export.py IRRIGATION_HAND_H0 = 5.0) the staged atlas's farming chain is re-exported first
# (raw and corrected climate, foraging, reach, languages); then promote and the add-on layers, once.
# Resumable (output/atlas_d1/earth_done).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=output/atlas_d1; STAGE=atlases/earth_fit_d1_stage
CK=output/r44_rivers_world/candidate_001.pkl; CAL=calibration/earth_correction_r44_20261107
grep -qx release_identity "$OUT/stages_done" || { echo "Earth-fit base stages not complete"; exit 1; }
touch "$OUT/earth_done"
run() { local name=$1; shift; if grep -qx "$name" "$OUT/earth_done"; then echo "skip $name"; return; fi
  echo "== $name $(date -u +%H:%M:%S)"; "$@" > "$OUT/earth_$name.log" 2>&1; echo "$name" >> "$OUT/earth_done"; echo "done $name $(date -u +%H:%M:%S)"; }
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
if grep -q '^IRRIGATION_HAND_H0 = 5.0' harvest/export.py && ! grep -qx promote "$OUT/earth_done"; then
  run d2b_food $PY -I scripts/add_harvest_to_atlas.py $STAGE
  run d2b_corrected_climate $PY -I scripts/add_corrected_climate.py $STAGE --checkpoint $CK --corrections $CAL --gif
  run d2b_foraging $PY -I scripts/add_foraging_to_atlas.py $STAGE
  run d2b_reach $PY -I scripts/export_reach.py $STAGE
  run d2b_languages $PY -I scripts/add_language_layers.py $STAGE
  run d2b_release_identity $PY -I scripts/tag_atlas_physics.py $STAGE --params calibration/local_accuracy_20261023/r44_params.json --profile r44 --report reports/ARABLE_SLOPE_20261108.md
fi
if ! grep -qx promote "$OUT/earth_done"; then
  mkdir -p "$OUT/previous_atlases"
  [ -d "$OUT/previous_atlases/earth_fit_rivers" ] || mv atlases/earth_fit "$OUT/previous_atlases/earth_fit_rivers"
  mv $STAGE atlases/earth_fit
  for f in evidence.js; do [ -f "$OUT/previous_atlases/earth_fit_rivers/$f" ] && cp "$OUT/previous_atlases/earth_fit_rivers/$f" atlases/earth_fit/$f; done
  $PY -I - <<'PYEOF'
import json
from pathlib import Path
p = Path('atlases/pages.json'); pages = json.loads(p.read_text())
pages['earth_fit']['note'] = ('Earth r44 physics on the published world geometry with the eroded height map v2.1 (Earth-tested erosion, every drawn river a flow path in an Earth-fitted valley, '
    'unmarked lowland hills); arable land from slope and river irrigation by height above the river (both Earth-tested). Climate averages surroundings layouts 1–3 with verified numerical '
    'checks. The map opens on Earth-trained corrected climate; raw climate remains available. Food, population and foraging are c.200 AD scenarios.')
p.write_text(json.dumps(pages, indent=1, ensure_ascii=False) + '\n')
PYEOF
  echo promote >> "$OUT/earth_done"; echo "promoted $(date -u +%H:%M:%S)"
fi
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
echo "Earth-fit release complete"
