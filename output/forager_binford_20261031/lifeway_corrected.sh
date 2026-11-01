#!/bin/bash
# The corrected climate's foraging layers with lifeways: re-run the corrected export on the Earth-fit atlas, then pages and smoke.
cd /home/user/rotclimate
while ! grep -q "SCREENS10 DONE" output/desert_heat_20261101/screen10.log 2>/dev/null; do sleep 60; done
echo "corrected $(date +%H:%M)"
.venv/bin/python -I scripts/add_corrected_climate.py atlases/earth_fit --checkpoint output/r41_world/candidate_001.pkl \
  --corrections calibration/earth_correction_r41_20261101 > output/forager_binford_20261031/lifeway_corrected.log 2>&1
.venv/bin/python -I scripts/refresh_atlas_pages.py > /dev/null 2>&1; .venv/bin/python -I scripts/build_fit_hub.py > /dev/null 2>&1
echo "corrected done $(date +%H:%M)"
