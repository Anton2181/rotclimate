#!/bin/bash
# P3: after the search, the frozen validation (only if a candidate beats r41's cost of 1).
cd /home/user/rotclimate
while ! grep -q "P3 search done" output/atlas_r41/after_w2.log; do sleep 60; done
best=$(.venv/bin/python -c "import json;print(min(json.loads(l)['cost'] for l in open('calibration/maritime_refit_20261101/search/evals.jsonl')))")
echo "best search cost $best"
if .venv/bin/python -c "import sys;sys.exit(0 if $best < 1.0 else 1)"; then
  echo "validation $(date +%H:%M)"
  OUT=output/maritime_refit_20261101/refit REF_NAME=r41 REF_FIT=calibration/local_accuracy_20261023/r41_params.json \
    BEST=calibration/maritime_refit_20261101/search/best_params.json SEALED_SPEC=calibration/sealed_20261101c/regions.json \
    bash scripts/validate_monsoon_refit.sh > output/maritime_refit_20261101/validation.log 2>&1
  echo "validation done $(date +%H:%M)"
else
  echo "no candidate beat r41; validation not run"
fi
