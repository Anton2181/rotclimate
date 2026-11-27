#!/usr/bin/env bash
# r59 adopted 28 Nov 2026: corrections for r59w, then the full release (world geometry carried from W6).
set -euo pipefail
cd "$(dirname "$0")/.."
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
TAG=r59 PARAMS=calibration/local_accuracy_20261023/r59w_params.json OUT=output/earth_correction_r59_20261128 \
  CAL=calibration/earth_correction_r59_20261128 bash scripts/retrain_earth_corrections.sh
mkdir -p output/r59_world
bash scripts/release_r59.sh
