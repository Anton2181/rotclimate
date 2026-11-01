#!/bin/bash
# W2 search -> W2 review (native + audit) -> P3 prerequisites and search.
cd /home/user/rotclimate
while kill -0 15720 2>/dev/null; do sleep 30; done
[ -f calibration/map_world_r41_planet/best_result.json ] || { echo "W2 search did not finish"; exit 1; }
echo "W2 search done $(date +%H:%M)"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u -I scripts/world_campaign_r41.py review > output/r41_world_planet_review.log 2>&1
echo "W2 review done $(date +%H:%M)"
mkdir -p output/maritime_refit_20261101
echo "P3 sealed-a reference $(date +%H:%M)"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u -I scripts/benchmark_local.py --fit calibration/local_accuracy_20261023/r41_params.json --regions $(.venv/bin/python -c "import json;print(' '.join(json.load(open('calibration/sealed_20261031/regions.json'))))") --region-specs calibration/sealed_20261031/regions.json --out output/maritime_refit_20261101/r41_sealed_a > output/maritime_refit_20261101/r41_sealed_a.log 2>&1
echo "P3 search $(date +%H:%M)"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u -I scripts/gate_calibrate.py --plan calibration/maritime_refit_20261101/plan.json --out calibration/maritime_refit_20261101/search > output/maritime_refit_20261101/search.log 2>&1
echo "P3 search done $(date +%H:%M)"
