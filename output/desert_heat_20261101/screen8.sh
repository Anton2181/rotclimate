#!/bin/bash
cd /home/user/rotclimate
PY=".venv/bin/python -u -I"; FIT=calibration/local_accuracy_20261023/r41_params.json; O=output/desert_heat_20261101
reg() { .venv/bin/python -c "import json;print(' '.join(json.load(open('$1'))))"; }
run() { name=$1; set_json=$2
  $PY scripts/benchmark_local.py --fit $FIT --regions dev31 --set "$set_json" --out $O/${name}_dev31 > $O/${name}_dev31.log 2>&1
  for s in a:calibration/sealed_20261031/regions.json b:calibration/sealed_20261031b/regions.json c:calibration/sealed_20261101c/regions.json; do
    $PY scripts/benchmark_local.py --fit $FIT --regions $(reg ${s#*:}) --region-specs ${s#*:} --set "$set_json" --out $O/${name}_s${s%%:*} > $O/${name}_s${s%%:*}.log 2>&1
  done
  echo "$name done $(date +%H:%M)"; }
run d10 '{"subsidence_branch": 1.0, "subsidence_drying": 0.1}'
run d20 '{"subsidence_branch": 1.0, "subsidence_drying": 0.2}'
run d20w '{"subsidence_branch": 1.0, "subsidence_drying": 0.2, "subsidence_warming": 4.0, "subsidence_warming_taper": 10.0, "subsidence_warming_chi0": 0.7, "subsidence_warming_rain": 2.0, "subsidence_warming_top_m": 2500.0}'
echo "SCREENS8 DONE"
