#!/usr/bin/env bash
# Full atlas rebuild on r49 physics (owner override 20 Nov 2026: "Use the latest model in full, even if the zone agreement
# falls. Earth calibration is the most important"). World: W3 refit selection (calibration/map_world_r49_planet) on the
# height map v2.2. Corrections retrained for r49. Harvest carries the malaria rule. Report: reports/RELEASE_R49_20261121.md.
# Resumable: output/atlas_r49/stages_done.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=output/atlas_r49; STAGE=earth_fit_r49_stage; ATLAS=atlases/$STAGE
WORLD=${WORLD:-calibration/map_world_r49/params.json}
CK=output/r49_world/candidate_001.pkl; CAL=calibration/earth_correction_r49_20261121; EVALS=output/earth_correction_r49_20261121
PHYS=calibration/local_accuracy_20261023/r49_params.json; REPORT=reports/RELEASE_R49_20261121.md
mkdir -p "$OUT"; touch "$OUT/stages_done"
run() { local name=$1; shift; if grep -qx "$name" "$OUT/stages_done"; then echo "skip $name"; return; fi
  echo "== $name $(date -u +%H:%M:%S)"; "$@" > "$OUT/$name.log" 2>&1; echo "$name" >> "$OUT/stages_done"; echo "done $name $(date -u +%H:%M:%S)"; }
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROTCLIMATE_FOREST_TRAVEL=1
NOTE='Earth r49 physics (plateau-anchored rain belt, monsoon onset, 1,750 m plateau anchor) on the world geometry refitted under r49, with the eroded height map v2.2; layouts 1–3 and verified numerical checks.'
run world $PY -u -I scripts/build_atlas_variant.py --params $WORLD --name $STAGE \
  --title 'Rotclimate Earth-Fit Atlas' --eyebrow 'Climate, farming and settlement · three layouts · c.200 AD' \
  --note "$NOTE" --downsample 8 --image-scale 2 --seeds 1,2,3 --workers 1 --fit-objective zonefit --require-verified --checkpoint $CK
run diagnostics $PY -I scripts/add_r40_atlas_diagnostics.py $ATLAS --out $OUT/diagnostics --release r49
run corrected_layers $PY -I scripts/add_corrected_layers.py $ATLAS --checkpoint $CK --corrections $CAL --evals $EVALS
run corrected_climate $PY -I scripts/add_corrected_climate.py $ATLAS --checkpoint $CK --corrections $CAL --gif
run languages $PY -I scripts/add_language_layers.py $ATLAS
run release_identity $PY -I scripts/tag_atlas_physics.py $ATLAS --params $PHYS --profile r49 --report $REPORT
echo "base stages complete"
if ! grep -qx promote "$OUT/stages_done"; then
  mkdir -p "$OUT/previous_atlases"
  [ -d "$OUT/previous_atlases/earth_fit_r44" ] || mv atlases/earth_fit "$OUT/previous_atlases/earth_fit_r44"
  mv $ATLAS atlases/earth_fit
  for f in evidence.js; do [ -f "$OUT/previous_atlases/earth_fit_r44/$f" ] && cp "$OUT/previous_atlases/earth_fit_r44/$f" atlases/earth_fit/$f; done
  $PY -I - <<'PYEOF'
import json
from pathlib import Path
p = Path('atlases/pages.json'); pages = json.loads(p.read_text())
pages['earth_fit']['note'] = ('Earth r49 physics (rain belt anchored by large plateaus, monsoon onset, 1,750 m plateau anchor) on the world geometry refitted under r49, '
    'with the eroded height map v2.2 (every drawn river a flow path through its lakes to the sea); arable land from slope, river irrigation and Earth-sized delta fans. '
    'Climate averages surroundings layouts 1–3 with verified numerical checks. The map opens on Earth-trained corrected climate; raw climate remains available. '
    'Food, population and foraging are c.200 AD scenarios, with the Earth-validated malaria rule.')
p.write_text(json.dumps(pages, indent=1, ensure_ascii=False) + '\n')
PYEOF
  echo promote >> "$OUT/stages_done"; echo "promoted $(date -u +%H:%M:%S)"
fi
run forest_layer $PY -I scripts/forest_map.py --publish
run herding_layer $PY -I scripts/herders_layer.py --publish
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
echo "core add-ons complete (next: settlement chain release 4, provisional r5, pages, accuracy, hub)"
