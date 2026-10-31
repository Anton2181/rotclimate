cd /home/user/rotclimate
set -e
for a in free_fit earth_fit whittaker_fit; do cp atlases/$a/data/atlas.json output/corrected_climate/$a.atlas.json.before_drytowns; done
.venv/bin/python -I scripts/export_reach.py atlases/free_fit atlases/earth_fit atlases/whittaker_fit > output/corrected_climate/reach.log 2>&1
echo REACH DONE
cp atlases/earth_fit/data/atlas.json output/corrected_climate/atlas.json.before
.venv/bin/python -I scripts/add_corrected_climate.py atlases/earth_fit --checkpoint output/r40_world/candidate_001.pkl --corrections calibration/earth_correction_r40_20261031 > output/corrected_climate/run.log 2>&1
echo CORRECTED DONE
