#!/usr/bin/env bash
# Paired dev49 runs (dev31 + retired a,b,c) for REF and candidate, then the policy-v3 dev gate.
#   OUT=... CAND=... [REF_NAME=r50 REF_FIT=...] bash scripts/dev49_pair.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
REF_NAME=${REF_NAME:-r50}
REF_FIT=${REF_FIT:-calibration/local_accuracy_20261023/r50_params.json}
mkdir -p "$OUT"; cp "$CAND" "$OUT/candidate_params.json"; C="$OUT/candidate_params.json"
names() { $PY -c "import json,sys; print(' '.join(json.load(open(sys.argv[1]))))" "$1"; }
for fit in "$REF_NAME":"$REF_FIT" candidate:"$C"; do
  n=${fit%%:*}; f=${fit#*:}
  [ "$n" = "$REF_NAME" ] && [ -f "$OUT/${n}_retired_c/summary.json" ] && continue
  $PY -I scripts/benchmark_local.py --fit "$f" --regions dev31 --out "$OUT/${n}_dev31" > "$OUT/${n}_dev31.log" 2>&1
  for part in a:calibration/sealed_20261031/regions.json b:calibration/sealed_20261031b/regions.json c:calibration/sealed_20261101c/regions.json; do
    spec=${part#*:}
    $PY -I scripts/benchmark_local.py --fit "$f" --regions $(names "$spec") --region-specs "$spec" --out "$OUT/${n}_retired_${part%%:*}" > "$OUT/${n}_retired_${part%%:*}.log" 2>&1
  done
done
$PY -I scripts/gate_v3.py dev "$OUT" "$REF_NAME" || true
