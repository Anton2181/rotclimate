#!/usr/bin/env bash
# Stage 2 of the D1 + D2 release (arable share from slope, irrigation by height above the river; reports/ARABLE_SLOPE_20261108.md): promote the staged Earth-fit atlas
# (live copy backed up) and rebuild the add-on layers on it in dependency order. Resumable (output/atlas_d1/addons_done).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=output/atlas_d1
grep -qx languages_fw "$OUT/stages_done" || { echo "base stages not complete"; exit 1; }
touch "$OUT/addons_done"
run() { local name=$1; shift; if grep -qx "$name" "$OUT/addons_done"; then echo "skip $name"; return; fi
  echo "== $name $(date -u +%H:%M:%S)"; "$@" > "$OUT/addon_$name.log" 2>&1; echo "$name" >> "$OUT/addons_done"; echo "done $name $(date -u +%H:%M:%S)"; }
if ! grep -qx promote "$OUT/addons_done"; then
  mkdir -p "$OUT/previous_atlases"
  [ -d "$OUT/previous_atlases/earth_fit_rivers" ] || mv atlases/earth_fit "$OUT/previous_atlases/earth_fit_rivers"
  mv atlases/earth_fit_d1_stage atlases/earth_fit
  # carry the add-on scripts' viewer files the base build does not copy
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
  echo promote >> "$OUT/addons_done"; echo "promoted $(date -u +%H:%M:%S)"
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
echo "add-ons complete"
