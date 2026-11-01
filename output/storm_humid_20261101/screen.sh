#!/bin/bash
# e68h screens on dev31 against r41 (reference: output/spring_refit_20261101/refit41/candidate_dev31)
cd /home/user/rotclimate
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
for n in k1_h45 k1_h60; do
  .venv/bin/python -I scripts/benchmark_local.py --fit output/storm_humid_20261101/${n}_params.json --regions dev31 --workers 4 --out output/storm_humid_20261101/$n > output/storm_humid_20261101/$n.log 2>&1
  .venv/bin/python -I scripts/gate_local.py output/spring_refit_20261101/refit41/candidate_dev31 output/storm_humid_20261101/$n --out output/storm_humid_20261101/${n}_gate.json > output/storm_humid_20261101/${n}_gate.log 2>&1
  echo "$n done $(date +%H:%M)"
done
