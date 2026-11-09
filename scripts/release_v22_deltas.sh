#!/usr/bin/env bash
# Earth-fit release: height map v2.2 (rivers flow through open lakes; plan_R1 amendment 5) and Earth-median delta fans
# at every drawn-river mouth (calibration/delta_fans_20261108). Report: reports/LAKES_DELTAS_20261108.md.
# Base build from the verified v2.2 checkpoint (output/r44_lakes_world/candidate_001.pkl), promotion, add-ons once.
# Earth fit only (free and Whittaker retired). Resumable: output/atlas_v22/stages_done.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=${ROTCLIMATE_V22_OUT:-output/atlas_v22}; STAGE=earth_fit_v22_stage; ATLAS=atlases/$STAGE
CK=output/r44_lakes_world/candidate_001.pkl; CAL=calibration/earth_correction_r44_20261107; EVALS=output/earth_correction_r44_20261107
REPORT=reports/LAKES_DELTAS_20261108.md
$PY -I scripts/check_v22_release_inputs.py --out "$OUT" --record
mkdir -p "$OUT"; touch "$OUT/stages_done"
run() { local name=$1; shift; if grep -qx "$name" "$OUT/stages_done"; then echo "skip $name"; return; fi
  echo "== $name $(date -u +%H:%M:%S)"; "$@" > "$OUT/$name.log" 2>&1; echo "$name" >> "$OUT/stages_done"; echo "done $name $(date -u +%H:%M:%S)"; }
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
run world $PY -u -I scripts/build_atlas_variant.py --params calibration/map_world_r44_terrain22/params.json --name $STAGE \
  --title 'Rotclimate Earth-Fit Atlas' --eyebrow 'Climate, farming and settlement · three layouts · c.200 AD' \
  --note 'Earth r44 physics on the published world geometry with the eroded height map v2.2 (every drawn river a flow path, through its lakes to the sea); layouts 1–3 and verified numerical checks.' \
  --downsample 8 --image-scale 2 --seeds 1,2,3 --workers 1 --fit-objective zonefit --require-verified --checkpoint $CK
run diagnostics $PY -I scripts/add_r40_atlas_diagnostics.py $ATLAS --out $OUT/diagnostics --release r44
run corrected_layers $PY -I scripts/add_corrected_layers.py $ATLAS --checkpoint $CK --corrections $CAL --evals $EVALS
run corrected_climate $PY -I scripts/add_corrected_climate.py $ATLAS --checkpoint $CK --corrections $CAL --gif
run languages $PY -I scripts/add_language_layers.py $ATLAS
run release_identity $PY -I scripts/tag_atlas_physics.py $ATLAS --params calibration/local_accuracy_20261023/r44_params.json --profile r44 --report $REPORT
if ! grep -qx promote "$OUT/stages_done"; then
  mkdir -p "$OUT/previous_atlases"
  [ -d "$OUT/previous_atlases/earth_fit_d1" ] || mv atlases/earth_fit "$OUT/previous_atlases/earth_fit_d1"
  mv $ATLAS atlases/earth_fit
  for f in evidence.js; do [ -f "$OUT/previous_atlases/earth_fit_d1/$f" ] && cp "$OUT/previous_atlases/earth_fit_d1/$f" atlases/earth_fit/$f; done
  $PY -I - <<'PYEOF'
import json
from pathlib import Path
p = Path('atlases/pages.json'); pages = json.loads(p.read_text())
pages['earth_fit']['note'] = ('Earth r44 physics on the published world geometry with the eroded height map v2.2 (Earth-tested erosion, every drawn river a flow path in an Earth-fitted valley '
    'and on through its lakes to the sea, unmarked lowland hills); arable land from slope, river irrigation by height above the river and Earth-sized delta fans at the river mouths. '
    'Climate averages surroundings layouts 1–3 with verified numerical checks. The map opens on Earth-trained corrected climate; raw climate remains available. Food, population and foraging are c.200 AD scenarios.')
p.write_text(json.dumps(pages, indent=1, ensure_ascii=False) + '\n')
PYEOF
  echo promote >> "$OUT/stages_done"; echo "promoted $(date -u +%H:%M:%S)"
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
run accuracy $PY -I scripts/publish_current_earth.py
run hub $PY -I scripts/build_fit_hub.py
echo "v2.2 + deltas release complete"
