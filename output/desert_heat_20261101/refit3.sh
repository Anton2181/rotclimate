#!/bin/bash
cd /home/user/rotclimate
while ! grep -q -E "validation done|no candidate beat" output/desert_heat_20261101/refit2b.log 2>/dev/null; do sleep 60; done
echo "search $(date +%H:%M)"
for k in 1 2 3; do
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .venv/bin/python -u -I scripts/gate_calibrate.py --plan calibration/desert_refit3_20261101/plan.json --out calibration/desert_refit3_20261101/search $([ $k -gt 1 ] && echo --resume) --hours 4 >> output/desert_heat_20261101/search3.log 2>&1
  n=$(wc -l < calibration/desert_refit3_20261101/search/evals.jsonl); [ "$n" -ge 80 ] && break
done
best=$(.venv/bin/python -c "import json;print(min(json.loads(l)['cost'] for l in open('calibration/desert_refit3_20261101/search/evals.jsonl')))")
echo "search done $(date +%H:%M), best cost $best"
