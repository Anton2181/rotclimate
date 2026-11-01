#!/bin/bash
# After the r41 release: apply the W2 guard form, run the W2 search, then the P3 prerequisites and search.
cd /home/user/rotclimate
while kill -0 8137 2>/dev/null; do sleep 30; done
grep -q "RELEASE DONE" output/atlas_r41/release.log || { echo "release did not finish; stopping" ; exit 1; }
git apply /tmp/claude-0/-home-user-rotclimate/2f91ef95-572a-5f1d-9d76-83d645245d5d/scratchpad/w2_guard.patch || exit 1
echo "W2 search $(date +%H:%M)"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u -I scripts/world_campaign_r41.py search > output/r41_world_planet_search.log 2>&1
echo "W2 search done $(date +%H:%M)"
mkdir -p output/maritime_refit_20261101
echo "P3 sealed-a reference $(date +%H:%M)"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u -I scripts/benchmark_local.py --fit calibration/local_accuracy_20261023/r41_params.json --regions $(.venv/bin/python -c "import json;print(' '.join(json.load(open('calibration/sealed_20261031/regions.json'))))") --region-specs calibration/sealed_20261031/regions.json --out output/maritime_refit_20261101/r41_sealed_a > output/maritime_refit_20261101/r41_sealed_a.log 2>&1
echo "P3 search $(date +%H:%M)"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u -I scripts/gate_calibrate.py --plan calibration/maritime_refit_20261101/plan.json --out calibration/maritime_refit_20261101/search > output/maritime_refit_20261101/search.log 2>&1
echo "P3 search done $(date +%H:%M)"
