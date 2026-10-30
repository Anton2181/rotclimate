#!/usr/bin/env bash
# Validate the monsoon refit winner as calibration/monsoon_refit_20261030/plan.json declares:
# fresh paired dev31 runs and the frozen gate, then the paired 28 km check, then the sealed six
# once (only for a candidate that passed both).
#   bash scripts/validate_monsoon_refit.sh
# OUT, BEST and the reference (REF_NAME, REF_FIT; default r39) come from the environment.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
export OPENBLAS_NUM_THREADS=1
OUT=${OUT:-output/physics_gaps_20261030/refit}
BEST=${BEST:-calibration/monsoon_refit_20261030/search/best_params.json}
REF_NAME=${REF_NAME:-r39}
REF_FIT=${REF_FIT:-calibration/local_accuracy_20261023/r39_params.json}
mkdir -p "$OUT"
cp "$BEST" "$OUT/candidate_params.json"
CAND="$OUT/candidate_params.json"

# 1. development gate: both runs with the same sources
$PY -I scripts/benchmark_local.py --fit "$REF_FIT" --regions dev31 --out "$OUT/${REF_NAME}_dev31" > "$OUT/${REF_NAME}_dev31.log" 2>&1
$PY -I scripts/benchmark_local.py --fit "$CAND" --regions dev31 --out "$OUT/candidate_dev31" > "$OUT/candidate_dev31.log" 2>&1
$PY -I scripts/gate_local.py "$OUT/${REF_NAME}_dev31" "$OUT/candidate_dev31" --out "$OUT/gate_review.json" > "$OUT/gate_review.log" 2>&1 || true

# 2. paired 28 km check (S not worse by more than 1 %)
for fit in "$REF_NAME":"$REF_FIT" candidate:"$CAND"; do
  $PY -I scripts/benchmark_local.py --fit "${fit#*:}" --regions california western_europe japan new_zealand --cell-km 28 \
      --out "$OUT/${fit%%:*}_fine28" > "$OUT/${fit%%:*}_fine28.log" 2>&1
done

if $PY -I scripts/summarize_refit.py "$OUT" checks "$REF_NAME"; then
  # 3. sealed six, once, only for a candidate that passed both checks
  for fit in "$REF_NAME":"$REF_FIT" candidate:"$CAND"; do
    $PY -I scripts/benchmark_local.py --fit "${fit#*:}" --regions norway southeast_africa caucasus yunnan northeast_us tasmania \
        --region-specs calibration/local_accuracy_20261023/regions_sealed6.json --out "$OUT/${fit%%:*}_sealed6" > "$OUT/${fit%%:*}_sealed6.log" 2>&1
  done
  $PY -I scripts/summarize_refit.py "$OUT" sealed "$REF_NAME"
fi
