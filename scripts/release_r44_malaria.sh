#!/usr/bin/env bash
# Full rebuild of the harvest-bound add-ons after the malaria rule (harvest/malaria_v2.py) was switched on, 20 Nov 2026,
# on the unchanged r44 climate (reports/MALARIA_GENETICS_20261120.md; HANDOFF "FULL REBUILD"). Mirrors the add-on block of
# scripts/release_v22_deltas.sh, in place on atlases/earth_fit (git-tracked; revert = git checkout atlases/).
# Resumable: output/rebuild_r49_20261120/stages_done.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=output/rebuild_r49_20261120
mkdir -p "$OUT/logs"; touch "$OUT/stages_done"
run() { local name=$1; shift; if grep -qx "$name" "$OUT/stages_done"; then echo "skip $name"; return; fi
  echo "== $name $(date -u +%H:%M:%S)"; "$@" > "$OUT/logs/$name.log" 2>&1; echo "$name" >> "$OUT/stages_done"; echo "done $name $(date -u +%H:%M:%S)"; }
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
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
echo "core add-ons complete"
