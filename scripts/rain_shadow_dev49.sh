#!/usr/bin/env bash
# Rain-shadow amendment 1 (calibration/rain_shadow_20261115/amendment_1.json), stage 1: r44 once, then each candidate, on the 49 development
# regions and the 28 km check; gate_v3 dev + fine per candidate (reference results linked into each candidate folder).
# Resumable: finished runs are skipped. No sealed set is run here.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
OUT=output/rain_shadow_20261115/gate; PLAN=calibration/rain_shadow_20261115
mkdir -p "$OUT"
names() { $PY -c "import json,sys; print(' '.join(json.load(open(sys.argv[1]))))" "$1"; }
bench() {  # name params outdir
  local n=$1 f=$2 o=$3; mkdir -p "$o"
  [ -f "$o/${n}_dev31/summary.json" ] || $PY -I scripts/benchmark_local.py --fit "$f" --regions dev31 --workers 4 --out "$o/${n}_dev31" > "$o/${n}_dev31.log" 2>&1
  for part in a:calibration/sealed_20261031/regions.json b:calibration/sealed_20261031b/regions.json c:calibration/sealed_20261101c/regions.json; do
    spec=${part#*:}; d="$o/${n}_retired_${part%%:*}"
    [ -f "$d/summary.json" ] || $PY -I scripts/benchmark_local.py --fit "$f" --regions $(names "$spec") --region-specs "$spec" --workers 4 --out "$d" > "$d.log" 2>&1
  done
  [ -f "$o/${n}_fine28/summary.json" ] || $PY -I scripts/benchmark_local.py --fit "$f" --regions california western_europe japan new_zealand --cell-km 28 --workers 4 --out "$o/${n}_fine28" > "$o/${n}_fine28.log" 2>&1
}
echo "== r44 $(date -u +%H:%M)"; bench r44 calibration/local_accuracy_20261023/r44_params.json "$OUT/ref"
for c in E1 E2 E3; do
  o="$OUT/$c"; mkdir -p "$o"; cp "$PLAN/${c}_params.json" "$o/candidate_params.json"
  echo "== $c $(date -u +%H:%M)"; bench candidate "$o/candidate_params.json" "$o"
  for part in dev31 retired_a retired_b retired_c fine28; do ln -sfn "../ref/r44_$part" "$o/r44_$part"; done
  $PY -I scripts/gate_v3.py dev "$o" r44 > "$o/v3_dev.log" 2>&1 && dv=1 || dv=0
  $PY -I scripts/gate_v3.py fine "$o" r44 > "$o/v3_fine.log" 2>&1 && fn=1 || fn=0
  echo "$c dev_pass=$dv fine_pass=$fn"; tail -2 "$o/v3_dev.log"
done
echo "stage 1 complete $(date -u +%H:%M)"
