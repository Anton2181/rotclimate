#!/usr/bin/env bash
# Owner choice 27 Nov 2026 "Atlas rebuild on r58": world search -> selection -> corrections for r58w -> release.
set -euo pipefail
cd "$(dirname "$0")/.."
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while pgrep -f "world_campaign_r58.py search" > /dev/null; do sleep 60; done
[ -f calibration/map_world_r58_planet/best_result.json ] || { echo "world search did not finish"; exit 1; }
[ -f calibration/map_world_r58/selection.json ] || .venv/bin/python -u -I scripts/select_world_r58.py
TAG=r58 PARAMS=calibration/local_accuracy_20261023/r58w_params.json OUT=output/earth_correction_r58_20261127 \
  CAL=calibration/earth_correction_r58_20261127 bash scripts/retrain_earth_corrections.sh
bash scripts/release_r58.sh
