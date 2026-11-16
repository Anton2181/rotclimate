#!/usr/bin/env bash
# Release 4: control v2 / v2.1 on the release-4 supply-fed staffing (placements installed from output/settlement_release4_20261116/release3)
set -euo pipefail
cd "$(dirname "$0")/.."
export ROTCLIMATE_RELEASE3_DIR=output/settlement_release4_20261116/release3
[ "${1:-}" = request ] || .venv/bin/python -I scripts/run_on_release3.py scripts/build_control_v2.py "output/settlement_fertility_20261106=>output/settlement_release4_20261116/reach/settlement_supplyfed" "control_v2_20261107=>control_v2_release4_20261116"
[ "${1:-}" = request ] || .venv/bin/python -I scripts/run_on_release3.py scripts/build_control_v21.py "output/settlement_fertility_20261106=>output/settlement_release4_20261116/reach/settlement_supplyfed" "control_v21_20261107=>control_v21_release4_20261116" "control_v2_20261107=>control_v2_release4_20261116"
[ "${1:-}" = request ] || echo CHAIN-DONE
# the "earlier 7.5% request" option set: the same builders on the fertility packet (no supply-fed staffing)
if [ "${1:-}" = request ]; then
.venv/bin/python -I scripts/run_on_release3.py scripts/build_control_v2.py "output/settlement_fertility_20261106=>output/settlement_release4_20261116/fertility" "control_v2_20261107=>control_v2_release4req_20261116"
.venv/bin/python -I scripts/run_on_release3.py scripts/build_control_v21.py "output/settlement_fertility_20261106=>output/settlement_release4_20261116/fertility" "control_v21_20261107=>control_v21_release4req_20261116" "control_v2_20261107=>control_v2_release4req_20261116"
echo REQUEST-DONE
fi
