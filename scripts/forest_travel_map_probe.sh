#!/usr/bin/env bash
# C2 map probe: control v2 / v2.1 on the release-4 supply-fed staffing with ROTCLIMATE_FOREST_TRAVEL=1 (towns, supply and staffing
# fixed at release 4; only the control step's walking cost changes). Outputs: output/control_v2{,1}_forest_probe_20261116.
set -euo pipefail
cd "$(dirname "$0")/.."
export ROTCLIMATE_RELEASE3_DIR=output/settlement_release4_20261116/release3 ROTCLIMATE_FOREST_TRAVEL=1
.venv/bin/python -I scripts/run_on_release3.py scripts/build_control_v2.py "output/settlement_fertility_20261106=>output/settlement_release4_20261116/reach/settlement_supplyfed" "control_v2_20261107=>control_v2_forest_probe_20261116"
.venv/bin/python -I scripts/run_on_release3.py scripts/build_control_v21.py "output/settlement_fertility_20261106=>output/settlement_release4_20261116/reach/settlement_supplyfed" "control_v21_20261107=>control_v21_forest_probe_20261116" "control_v2_20261107=>control_v2_forest_probe_20261116"
echo PROBE-DONE
