#!/usr/bin/env bash
# r44 + height map v2.1 (drawn rivers as flow paths) release of the Earth-fit atlas (reports/RIVERS_TERRAIN_20261108.md): staged base build.
# Resumable: each finished stage is recorded in output/atlas_r44r/stages_done. Live atlases are not touched.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=output/atlas_r44r; STAGE=earth_fit_r44r_stage; ATLAS=atlases/$STAGE
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
run release_identity $PY -I scripts/tag_atlas_physics.py $ATLAS --params calibration/local_accuracy_20261023/r44_params.json --profile r44 --report reports/RIVERS_TERRAIN_20261108.md
echo "base stages complete"
