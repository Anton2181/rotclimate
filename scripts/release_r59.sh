#!/usr/bin/env bash
# Full atlas rebuild on r59 physics (r58 + e132b warm currents fade toward the equator). The world runs r59w = r59 + e116z
# (calibration/map_world_r58_planet/edge_forcing.md). Chain as scripts/release_r51.sh; world geometry carried from W6 (calibration/map_world_r59/selection.json).
# World: calibration/map_world_r59 (no new search). Corrections retrained for r59w.
# Report: reports/RELEASE_R59_20261128.md. Resumable: output/atlas_r59/stages_done.

set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; OUT=output/atlas_r59; STAGE=earth_fit_r59_stage; ATLAS=atlases/$STAGE
WORLD=${WORLD:-calibration/map_world_r59/params.json}
CK=output/r59_world/candidate_001.pkl; CAL=calibration/earth_correction_r59_20261128; EVALS=output/earth_correction_r59_20261128
PHYS=calibration/local_accuracy_20261023/r59w_params.json; REPORT=reports/RELEASE_R59_20261128.md
mkdir -p "$OUT"; touch "$OUT/stages_done"
run() { local name=$1; shift; if grep -qx "$name" "$OUT/stages_done"; then echo "skip $name"; return; fi
  echo "== $name $(date -u +%H:%M:%S)"; "$@" > "$OUT/$name.log" 2>&1; echo "$name" >> "$OUT/stages_done"; echo "done $name $(date -u +%H:%M:%S)"; }
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ROTCLIMATE_FOREST_TRAVEL=1
NOTE='Earth r59 physics (r51 plus maritime, sea-ice, snowpack and eddy-barrier refits and equatorial warm currents fading as on Earth; land edges take the latitude land-mean column water, e116z) on the world geometry refitted under r58 with the drawn-river width ranking, on the eroded height map v2.2 with every drawn river shown in full; rivers and deltas from Budyko–Fu runoff, grazing seasons from the GPP-tested phenology; layouts 1–3 and verified numerical checks.'
run world $PY -u -I scripts/build_atlas_variant.py --params $WORLD --name $STAGE \
  --title 'Rotclimate Earth-Fit Atlas' --eyebrow 'Climate, farming and settlement · three layouts · c.200 AD' \
  --note "$NOTE" --downsample 8 --image-scale 2 --seeds 1,2,3 --workers 1 --fit-objective zonefit_rivers --require-verified --checkpoint $CK
run diagnostics $PY -I scripts/add_r40_atlas_diagnostics.py $ATLAS --out $OUT/diagnostics --release r59
run corrected_layers $PY -I scripts/add_corrected_layers.py $ATLAS --checkpoint $CK --corrections $CAL --evals $EVALS
run corrected_climate $PY -I scripts/add_corrected_climate.py $ATLAS --checkpoint $CK --corrections $CAL --gif
run languages $PY -I scripts/add_language_layers.py $ATLAS
run release_identity $PY -I scripts/tag_atlas_physics.py $ATLAS --params $PHYS --profile r59 --report $REPORT
echo "base stages complete"
if ! grep -qx promote "$OUT/stages_done"; then
  mkdir -p "$OUT/previous_atlases"
  [ -d "$OUT/previous_atlases/earth_fit_r58" ] || mv atlases/earth_fit "$OUT/previous_atlases/earth_fit_r58"
  mv $ATLAS atlases/earth_fit
  for f in evidence.js; do [ -f "$OUT/previous_atlases/earth_fit_r58/$f" ] && cp "$OUT/previous_atlases/earth_fit_r58/$f" atlases/earth_fit/$f; done
  $PY -I - <<'PYEOF'
import json
from pathlib import Path
p = Path('atlases/pages.json'); pages = json.loads(p.read_text())
pages['earth_fit']['note'] = ('Earth r59 physics (r51 plus maritime, sea-ice, snowpack and eddy-barrier refits and equatorial warm currents fading as on Earth; land edges take the latitude land-mean column water) on the world geometry refitted under r58 with a drawn-river width target, '
    'with the eroded height map v2.2 (every drawn river a flow path through its lakes to the sea; runoff by the Earth-tested Budyko–Fu rule); arable land from slope, river irrigation and Earth-sized delta fans. '
    'Climate averages surroundings layouts 1–3 with verified numerical checks. The map opens on Earth-trained corrected climate; raw climate remains available. '
    'Food, population and foraging are c.200 AD scenarios, with the Earth-validated malaria rule.')
p.write_text(json.dumps(pages, indent=1, ensure_ascii=False) + '\n')
PYEOF
  echo promote >> "$OUT/stages_done"; echo "promoted $(date -u +%H:%M:%S)"
fi
run forest_layer $PY -I scripts/forest_map.py --publish
run herding_layer $PY -I scripts/herders_layer.py --publish
run nomads_layer $PY -I scripts/nomads_layer.py --publish
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

# ---- settlement release 4 on this climate (reports/RELEASE_R50_20261121.md section 5) ----
SPEC=calibration/settlement_chain/release4_r59.json; S=output/chain_staging/$(basename $SPEC .json); R=output/settlement_release4_20261116
D=atlases/earth_fit/data; BK=$OUT/inplace_backup
export ROTCLIMATE_CONFLUENCE_K=1.0 RELEASE_TAG=r59
stage_links() {   # province seats (lore inventory; identical in every climate) where the chain's first stage reads them
  mkdir -p $D/release3/hierarchy/corrected; cp $D/hierarchy_links.csv $D/release3/hierarchy/; cp $D/corrected/hierarchy_links.csv $D/release3/hierarchy/corrected/; }
chain_first() { rm -rf "${S:?}"; $PY -I scripts/settlement_chain.py $SPEC build --stage sizes review_placement review_sizes supply review_supply; }
staged_reach() {
  rm -rf output/trade_checkpoints/atlas_raw output/trade_checkpoints/atlas_corrected
  $PY -I scripts/stage_atlas.py $S/atlas_raw raw; $PY -I scripts/stage_atlas.py $S/atlas_corrected corrected
  ROTCLIMATE_RELEASE3_DIR=$S/release3 $PY -I scripts/export_reach_release3.py $S/atlas_raw > $OUT/reach_raw.log 2>&1 & local a=$!
  ROTCLIMATE_RELEASE3_DIR=$S/release3 $PY -I scripts/export_reach_release3.py $S/atlas_corrected > $OUT/reach_corrected.log 2>&1 & local b=$!
  wait $a && wait $b
  $PY -I scripts/install_corrected_reach.py $S/atlas_raw $S/atlas_corrected; }
chain_second() { $PY -I scripts/settlement_chain.py $SPEC build --stage integration labour fertility staffing ensemble_check; }
install_release() {
  for d in earth_results.json ensemble fertility integration labour reach release3 results.json supply; do rm -rf "${R:?}"/"${d:?}"; cp -r "$S/$d" "$R/$d"; done
  rm -rf "${R:?}"/browser "${R:?}"/downstream "${R:?}"/windows_checkout.json; }
backup_inplace() { rm -rf "${BK:?}"; mkdir -p $BK/corrected; for g in "$@"; do cp $D/$g $BK/ 2>/dev/null || true; cp $D/corrected/$g $BK/corrected/ 2>/dev/null || true; done; }
restore_inplace() { cp -r $BK/. $D/; }
reach_variants() {   # supply-fed -> release3/reach_fed, the 7.5 % request -> release3/reach; the in-place images restored after each
  local F="settled_control_v21_joint365.webp settled_control_v2_joint365.webp"
  backup_inplace $F
  for v in fed request; do
    if [ $v = fed ]; then bash scripts/release4_reach_chain.sh; dst=reach_fed; else bash scripts/release4_reach_chain.sh request; dst=reach; fi
    mkdir -p $D/release3/$dst/corrected
    for f in $F; do mv $D/$f $D/release3/$dst/$f; mv $D/corrected/$f $D/release3/$dst/corrected/$f; done
    restore_inplace
  done; }
release3_admin() {   # administration and hierarchy rebuilt on the release-4 towns, moved under release3/, in-place files restored
  backup_inplace 'administration*' 'hierarchy_*' administrative_access.json administrative_hierarchy.json
  export ROTCLIMATE_RELEASE3_DIR=$R/release3
  $PY -I scripts/run_on_release3.py scripts/review_imperial_access.py "'output/imperial_access_20261104'=>'output/imperial_access_release3_20261113'"
  $PY -I scripts/run_on_release3.py scripts/publish_imperial_access.py "ROOT/'output/imperial_access_20261104'=>ROOT/'output/imperial_access_release3_20261113'"
  $PY -I scripts/run_on_release3.py scripts/review_administrative_hierarchy.py "'output/administrative_hierarchy_20261104'=>'output/administrative_hierarchy_release3_20261113'"
  $PY -I scripts/run_on_release3.py scripts/publish_administrative_hierarchy.py "ROOT/'output/administrative_hierarchy_20261104'=>ROOT/'output/administrative_hierarchy_release3_20261113'"
  $PY -I scripts/move_release3_admin.py
  restore_inplace; }
run feedback_raw $PY -I scripts/prepare_settlement_feedback.py --mode raw
run feedback_corrected $PY -I scripts/prepare_settlement_feedback.py --mode corrected
run chain_links stage_links
run chain_first chain_first
run staged_reach staged_reach
run chain_second chain_second
run release4_install install_release
run reach_variants reach_variants
run publish_settlements bash scripts/publish_release4.sh settlements
run publish_note bash scripts/publish_release4.sh note
run publish_supply bash scripts/publish_release4.sh supply
run publish_ensemble bash scripts/publish_release4.sh ensemble
run publish_layers bash scripts/publish_release4.sh layers
run publish_reach bash scripts/publish_release4.sh reach
run release3_admin release3_admin
run pages python3 -I scripts/refresh_atlas_pages.py
run release3_page $PY -I scripts/enable_release3_page.py
run accuracy $PY -I scripts/publish_current_earth_r59.py
run hub $PY -I scripts/build_fit_hub.py
echo "r59 release complete (next: browser checks, scripts/package_atlas_artifact.py, Claude copy)"
