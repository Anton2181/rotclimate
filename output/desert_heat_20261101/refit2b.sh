#!/bin/bash
# Finish desert refit #2 to its frozen 80 candidates (it stopped at 63 on the 1.9 h time limit), then validate if a candidate beats r41.
cd /home/user/rotclimate
while ! grep -q "SCREENS10 DONE" output/desert_heat_20261101/screen10.log 2>/dev/null; do sleep 60; done
echo "resume $(date +%H:%M)"
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u -I scripts/gate_calibrate.py --plan calibration/desert_refit2_20261101/plan.json --out calibration/desert_refit2_20261101/search --resume --hours 3 >> output/desert_heat_20261101/search2.log 2>&1
best=$(.venv/bin/python -c "import json;print(min(json.loads(l)['cost'] for l in open('calibration/desert_refit2_20261101/search/evals.jsonl')))")
echo "search done $(date +%H:%M), best cost $best"
if .venv/bin/python -c "import sys;sys.exit(0 if $best < 1.0 else 1)"; then
  OUT=output/desert_refit2_20261101/refit REF_NAME=r41 REF_FIT=calibration/local_accuracy_20261023/r41_params.json \
    BEST=calibration/desert_refit2_20261101/search/best_params.json SEALED_SPEC=calibration/sealed_20261101d/regions.json \
    bash scripts/validate_monsoon_refit.sh > output/desert_heat_20261101/validation2.log 2>&1
  echo "validation done $(date +%H:%M)"
else
  echo "no candidate beat r41"
fi
