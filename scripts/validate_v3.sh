#!/usr/bin/env bash
# Validate a candidate under policy v3 (calibration/local_accuracy_20261023/policy_v3.json):
# fresh paired runs on the 49 development regions, the paired 28 km check, then the
# unseen sealed set once, only for a candidate that passes both.
#   OUT=... CAND=... [REF_NAME=r41 REF_FIT=... SEALED_SPEC=...] bash scripts/validate_v3.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
REF_NAME=${REF_NAME:-r41}
REF_FIT=${REF_FIT:-calibration/local_accuracy_20261023/r41_params.json}
SEALED_SPEC=${SEALED_SPEC:-calibration/sealed_20261101d/regions.json}
mkdir -p "$OUT"; cp "$CAND" "$OUT/candidate_params.json"; C="$OUT/candidate_params.json"
names() { $PY -c "import json,sys; print(' '.join(json.load(open(sys.argv[1]))))" "$1"; }
for fit in "$REF_NAME":"$REF_FIT" candidate:"$C"; do
  n=${fit%%:*}; f=${fit#*:}
  $PY -I scripts/benchmark_local.py --fit "$f" --regions dev31 --out "$OUT/${n}_dev31" > "$OUT/${n}_dev31.log" 2>&1
  for part in a:calibration/sealed_20261031/regions.json b:calibration/sealed_20261031b/regions.json c:calibration/sealed_20261101c/regions.json; do
    spec=${part#*:}
    $PY -I scripts/benchmark_local.py --fit "$f" --regions $(names "$spec") --region-specs "$spec" --out "$OUT/${n}_retired_${part%%:*}" > "$OUT/${n}_retired_${part%%:*}.log" 2>&1
  done
  $PY -I scripts/benchmark_local.py --fit "$f" --regions california western_europe japan new_zealand --cell-km 28 --out "$OUT/${n}_fine28" > "$OUT/${n}_fine28.log" 2>&1
done
dev=0; fine=0
$PY -I scripts/gate_v3.py dev "$OUT" "$REF_NAME" > "$OUT/v3_dev.log" 2>&1 || dev=1
$PY -I scripts/gate_v3.py fine "$OUT" "$REF_NAME" > "$OUT/v3_fine.log" 2>&1 || fine=1
echo "dev pass=$((1-dev)) fine pass=$((1-fine))"
if [ $dev -eq 0 ] && [ $fine -eq 0 ]; then
  for fit in "$REF_NAME":"$REF_FIT" candidate:"$C"; do
    n=${fit%%:*}; f=${fit#*:}
    $PY -I scripts/benchmark_local.py --fit "$f" --regions $(names "$SEALED_SPEC") --region-specs "$SEALED_SPEC" --out "$OUT/${n}_sealed_d" > "$OUT/${n}_sealed_d.log" 2>&1
  done
  $PY -I scripts/gate_v3.py sealed "$OUT" "$REF_NAME" > "$OUT/v3_sealed.log" 2>&1 && echo "sealed pass=1" || echo "sealed pass=0"
fi
