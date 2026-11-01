# r41 release into the Earth-fit atlas (reports/R41_20261101.md)
cd /home/user/rotclimate
set -e
PY=.venv/bin/python
echo "build stage $(date +%H:%M)"
$PY -u -I scripts/build_atlas_variant.py --params calibration/map_world_r41/params.json --name earth_fit_r41_stage \
  --title "Rotclimate Earth-Fit Atlas" --eyebrow "Climate, farming and settlement · three layouts · c.200 AD" \
  --note "Earth r41 physics on the published world's geometry. Climate averages surroundings layouts 1–3, with verified numerical checks. Farming and population use low-input c.200 AD settlement scenarios." \
  --downsample 8 --image-scale 2 --seeds 1,2,3 --workers 2 --fit-objective zonefit --require-verified \
  --checkpoint output/r41_world/candidate_001.pkl > output/atlas_r41/build.log 2>&1
echo "diagnostics $(date +%H:%M)"
$PY -I scripts/add_r40_atlas_diagnostics.py atlases/earth_fit_r41_stage --out output/atlas_r41/diagnostics --release r41 > output/atlas_r41/diagnostics.log 2>&1
echo "corrections $(date +%H:%M)"
TAG=r41 PARAMS=calibration/local_accuracy_20261023/r41_params.json OUT=output/earth_correction_r41_20261101 CAL=calibration/earth_correction_r41_20261101 \
  bash scripts/retrain_earth_corrections.sh > output/atlas_r41/corrections.log 2>&1
echo "promote $(date +%H:%M)"
mkdir -p output/atlas_r41/previous_atlases
rm -rf output/atlas_r41/previous_atlases/earth_fit_r40
mv atlases/earth_fit output/atlas_r41/previous_atlases/earth_fit_r40
mv atlases/earth_fit_r41_stage atlases/earth_fit
# (missing from the first run, done afterwards by hand: the correction-change maps and held-out scores)
$PY -I scripts/add_corrected_layers.py atlases/earth_fit --checkpoint output/r41_world/candidate_001.pkl \
  --corrections calibration/earth_correction_r41_20261101 --evals output/earth_correction_r41_20261101 > output/atlas_r41/layers.log 2>&1
echo "corrected climate $(date +%H:%M)"
$PY -I scripts/add_corrected_climate.py atlases/earth_fit --checkpoint output/r41_world/candidate_001.pkl \
  --corrections calibration/earth_correction_r41_20261101 > output/atlas_r41/corrected.log 2>&1
# update the Earth-fit page note in atlases/pages.json to the new release before refreshing (it was left at r40 in this release)
echo "pages $(date +%H:%M)"
$PY -I scripts/refresh_atlas_pages.py > output/atlas_r41/pages.log 2>&1
$PY -I scripts/build_fit_hub.py >> output/atlas_r41/pages.log 2>&1
echo "RELEASE DONE $(date +%H:%M)"
