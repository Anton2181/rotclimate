#!/bin/bash
cd /home/user/rotclimate
PY=".venv/bin/python -u -I"; FIT=calibration/local_accuracy_20261023/r41_params.json; O=output/desert_heat_20261101
SA=$(.venv/bin/python -c "import json;print(' '.join(json.load(open('calibration/sealed_20261031/regions.json'))))")
SB=$(.venv/bin/python -c "import json;print(' '.join(json.load(open('calibration/sealed_20261031b/regions.json'))))")
run() { name=$1; set_json=$2
  $PY scripts/benchmark_local.py --fit $FIT --regions dev31 --set "$set_json" --out $O/${name}_dev31 > $O/${name}_dev31.log 2>&1
  $PY scripts/benchmark_local.py --fit $FIT --regions $SA --region-specs calibration/sealed_20261031/regions.json --set "$set_json" --out $O/${name}_sa > $O/${name}_sa.log 2>&1
  $PY scripts/benchmark_local.py --fit $FIT --regions $SB --region-specs calibration/sealed_20261031b/regions.json --set "$set_json" --out $O/${name}_sb > $O/${name}_sb.log 2>&1
  echo "$name done $(date +%H:%M)"; }
run b10 '{"subsidence_branch": 1.0}'
run b10s5 '{"subsidence_branch": 1.0, "subsidence": 0.5}'
run s5 '{"subsidence": 0.5}'
echo "SCREENS2 DONE"
