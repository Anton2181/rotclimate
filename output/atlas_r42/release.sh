# r42 release into the Earth-fit atlas (reports/R42_20261101.md): adopted under policy v3
cd /home/user/rotclimate
set -e
PY=.venv/bin/python
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
echo "build stage $(date +%H:%M)"
$PY -u -I scripts/build_atlas_variant.py --params calibration/map_world_r42/params.json --name earth_fit_r42_stage \
  --title "Rotclimate Earth-Fit Atlas" --eyebrow "Climate, farming and settlement · three layouts · c.200 AD" \
  --note "Earth r42 physics on the published world's geometry. Climate averages surroundings layouts 1–3, with verified numerical checks. Farming and population use low-input c.200 AD settlement scenarios." \
  --downsample 8 --image-scale 2 --seeds 1,2,3 --workers 2 --fit-objective zonefit --require-verified \
  --checkpoint output/r42_world/candidate_001.pkl > output/atlas_r42/build.log 2>&1
echo "diagnostics $(date +%H:%M)"
$PY -I scripts/add_r40_atlas_diagnostics.py atlases/earth_fit_r42_stage --out output/atlas_r42/diagnostics --release r42 > output/atlas_r42/diagnostics.log 2>&1
echo "corrections $(date +%H:%M)"
TAG=r42 PARAMS=calibration/local_accuracy_20261023/r42_params.json OUT=output/earth_correction_r42_20261101 CAL=calibration/earth_correction_r42_20261101 \
  bash scripts/retrain_earth_corrections.sh > output/atlas_r42/corrections.log 2>&1
echo "promote $(date +%H:%M)"
mkdir -p output/atlas_r42/previous_atlases
rm -rf output/atlas_r42/previous_atlases/earth_fit_r41
mv atlases/earth_fit output/atlas_r42/previous_atlases/earth_fit_r41
mv atlases/earth_fit_r42_stage atlases/earth_fit
echo "corrected layers $(date +%H:%M)"
$PY -I scripts/add_corrected_layers.py atlases/earth_fit --checkpoint output/r42_world/candidate_001.pkl \
  --corrections calibration/earth_correction_r42_20261101 --evals output/earth_correction_r42_20261101 > output/atlas_r42/layers.log 2>&1
echo "corrected climate $(date +%H:%M)"
$PY -I scripts/add_corrected_climate.py atlases/earth_fit --checkpoint output/r42_world/candidate_001.pkl \
  --corrections calibration/earth_correction_r42_20261101 > output/atlas_r42/corrected.log 2>&1
echo "languages $(date +%H:%M)"
$PY -I scripts/add_language_layers.py atlases/earth_fit > output/atlas_r42/languages.log 2>&1
echo "pages $(date +%H:%M)"
$PY - <<'PYEOF'
import json
from pathlib import Path
p = Path("atlases/pages.json"); d = json.loads(p.read_text())
d["earth_fit"]["note"] = d["earth_fit"]["note"].replace("Earth r41 physics (adopted on the 31-region Earth test, 1 November 2026)",
    "Earth r42 physics (adopted on overall Earth accuracy over 49 development regions and an unseen sealed set, 1 November 2026)")
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
PYEOF
sed -i "s|Earth r41 physics, the best on the 31-region Earth test|Earth r42 physics, the best on the Earth test (49 development regions and an unseen sealed set)|; s|reports/R41_20261101.md\">Earth r41 calibration|reports/R42_20261101.md\">Earth r42 calibration|" scripts/build_fit_hub.py
$PY -I scripts/refresh_atlas_pages.py > output/atlas_r42/pages.log 2>&1
$PY -I scripts/build_fit_hub.py >> output/atlas_r42/pages.log 2>&1
echo "RELEASE DONE $(date +%H:%M)"
