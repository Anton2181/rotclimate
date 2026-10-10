#!/bin/sh
# After round 16: each spin's top 3 finalists on 60 fresh worlds (seeds 101-160)
cd "$(dirname "$0")/.."
until [ -f calibration/r16.done ]; do sleep 30; done
python3 scripts/spin_rematch.py calibration/r16_retrograde calibration/r16_prograde \
  --k 3 --worlds 60 --out calibration/r16_rematch.json > calibration/r16_rematch.log 2>&1
echo done > calibration/r16_rematch.done
