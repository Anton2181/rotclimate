#!/bin/bash
cd /home/user/rotclimate
PY=".venv/bin/python -u -I"; FIT=calibration/local_accuracy_20261023/r41_params.json; O=output/desert_heat_20261101
SB=$(.venv/bin/python -c "import json;print(' '.join(json.load(open('calibration/sealed_20261031b/regions.json'))))")
for spec in 'cm0:{"continental_mean": 0.0}' 'lo0:{"land_offset": 0.0}' 'ct0:{"continentality": 0.0}' 'wc0:{"wet_cooling": 0.0}'; do
  name=${spec%%:*}; js=${spec#*:}
  $PY scripts/benchmark_local.py --fit $FIT --regions $SB --region-specs calibration/sealed_20261031b/regions.json --set "$js" --out $O/p_${name}_sb > $O/p_${name}_sb.log 2>&1
  $PY scripts/benchmark_local.py --fit $FIT --regions north_india iran_plateau --set "$js" --out $O/p_${name}_ni > $O/p_${name}_ni.log 2>&1
  echo "$name done"
done
echo PROBES DONE
