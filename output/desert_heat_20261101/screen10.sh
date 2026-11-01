#!/bin/bash
cd /home/user/rotclimate
while ! grep -q "export done" output/forager_binford_20261031/lifeway_export_chain.log 2>/dev/null; do sleep 60; done
PY=".venv/bin/python -u -I"; FIT=calibration/local_accuracy_20261023/r41_params.json; O=output/desert_heat_20261101
reg() { .venv/bin/python -c "import json;print(' '.join(json.load(open('$1'))))"; }
run() { name=$1; set_json=$2
  $PY scripts/benchmark_local.py --fit $FIT --regions dev31 --set "$set_json" --out $O/${name}_dev31 > $O/${name}_dev31.log 2>&1
  for s in a:calibration/sealed_20261031/regions.json b:calibration/sealed_20261031b/regions.json c:calibration/sealed_20261101c/regions.json; do
    $PY scripts/benchmark_local.py --fit $FIT --regions $(reg ${s#*:}) --region-specs ${s#*:} --set "$set_json" --out $O/${name}_s${s%%:*} > $O/${name}_s${s%%:*}.log 2>&1
  done
  echo "$name done $(date +%H:%M)"; }
run bdr1 '{"subsidence_branch_drying": 0.2, "subsidence_branch_dry_rain": 1.0}'
run bdr1w '{"subsidence_branch_drying": 0.2, "subsidence_branch_dry_rain": 1.0, "subsidence_warming": 4.0, "subsidence_warming_taper": 10.0, "subsidence_warming_chi0": 0.7, "subsidence_warming_rain": 2.0, "subsidence_warming_top_m": 2500.0}'
echo "SCREENS10 DONE"
