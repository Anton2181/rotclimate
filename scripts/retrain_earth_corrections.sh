#!/usr/bin/env bash
# Retrain and evaluate both Earth correction stages (temperature, rain pattern)
# for an adopted physics profile, as reports/EARTH_CORRECTION_20261030.md did
# for r39: dev31 with whole clusters held out, the 28 and 14 km pairs, and the
# two correction-sealed regions.
#   TAG=r40 PARAMS=calibration/local_accuracy_20261023/r40_params.json \
#   OUT=output/earth_correction_r40_20261031 CAL=calibration/earth_correction_r40_20261031 \
#   bash scripts/retrain_earth_corrections.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PY:-.venv/bin/python}
export OPENBLAS_NUM_THREADS=1
: "${TAG:?}" "${PARAMS:?}" "${OUT:?}" "${CAL:?}"
SEALED=calibration/climate_physics_20261023/rainfall_validation_regions.json
PAIR="california western_europe japan new_zealand"
mkdir -p "$OUT"

run() {  # name, extra benchmark arguments
  local name=$1; shift
  $PY -I scripts/benchmark_local.py --fit "$PARAMS" "$@" --out "$OUT/${TAG}_$name" > "$OUT/${TAG}_$name.log" 2>&1
}
run dev31 --regions dev31
run fine28 --regions $PAIR --cell-km 28
run fine14 --regions $PAIR --cell-km 14
run sealed --regions norway southeast_africa --region-specs "$SEALED"

$PY -I scripts/train_earth_correction.py --run "$OUT/${TAG}_dev31" --params "$PARAMS" --out "$CAL/temperature" > "$OUT/train_temperature.log" 2>&1
for name in dev31 fine28 fine14 sealed; do
  extra=(); holdout=(--holdout)
  [ "$name" = sealed ] && extra=(--region-specs "$SEALED") && holdout=()
  $PY -I scripts/evaluate_earth_correction.py --run "$OUT/${TAG}_$name" --correction "$CAL/temperature" "${holdout[@]}" "${extra[@]}" \
      --out "$OUT/eval_$name.json" > "$OUT/eval_$name.log" 2>&1
  $PY -I scripts/collect_earth_fields.py --run "$OUT/${TAG}_$name" --params "$PARAMS" "${extra[@]}" --out "$OUT/fields_$name" > "$OUT/fields_$name.log" 2>&1
done
$PY -I scripts/train_rain_pattern.py --run "$OUT/${TAG}_dev31" --fields "$OUT/fields_dev31" --params "$PARAMS" --out "$CAL/rain_pattern" > "$OUT/train_rain.log" 2>&1
for name in dev31 fine28 fine14 sealed; do
  extra=(); holdout=(--holdout)
  [ "$name" = sealed ] && extra=(--region-specs "$SEALED") && holdout=()
  $PY -I scripts/evaluate_rain_pattern.py --run "$OUT/${TAG}_$name" --fields "$OUT/fields_$name" --rain "$CAL/rain_pattern" \
      --temperature "$CAL/temperature" "${holdout[@]}" "${extra[@]}" --out "$OUT/eval_rain_$name.json" > "$OUT/eval_rain_$name.log" 2>&1
done
echo done
