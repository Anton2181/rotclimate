#!/usr/bin/env bash
# The unchanged gate for the stable-land search's best candidate (calibration/stable_land_20261025/plan.json,
# "afterwards"): a fresh r37 reference over dev31 at 56 km, the gate (policy v2), city rain, the paired 28 km
# check and the sealed six once.
set -u
cd "$(dirname "$0")/.."
O=output/stable_land_20261025/gate
F=calibration/local_accuracy_20261023/r37_params.json
C=calibration/stable_land_20261025/candidate.json
SP=calibration/local_accuracy_20261023/regions_sealed6.json
mkdir -p $O
cp calibration/stable_land_20261025/search/best_params.json $C
W=${WORKERS:-4}
python3 -I scripts/benchmark_local.py --fit $F --regions dev31 --workers $W --out $O/reference > $O/reference.log 2>&1
python3 -I scripts/benchmark_local.py --fit $C --regions dev31 --workers $W --out $O/candidate > $O/candidate.log 2>&1
python3 -I scripts/gate_local.py $O/reference $O/candidate --out $O/gate_review.json > $O/gate.log 2>&1
python3 -I scripts/city_rain.py $O/reference $O/candidate --out $O/city_rain.json > $O/city_rain.log 2>&1
python3 -I scripts/benchmark_local.py --fit $F --cell-km 28 --workers $W --regions california western_europe japan new_zealand --out $O/check28_ref > $O/check28_ref.log 2>&1
python3 -I scripts/benchmark_local.py --fit $C --cell-km 28 --workers $W --regions california western_europe japan new_zealand --out $O/check28_cand > $O/check28_cand.log 2>&1
S6="norway southeast_africa caucasus yunnan northeast_us tasmania"
python3 -I scripts/benchmark_local.py --fit $F --regions $S6 --region-specs $SP --workers $W --out $O/sealed6_ref > $O/sealed6_ref.log 2>&1
python3 -I scripts/benchmark_local.py --fit $C --regions $S6 --region-specs $SP --workers $W --out $O/sealed6_cand > $O/sealed6_cand.log 2>&1
python3 -I - <<'EOF' > $O/checks.log 2>&1
import json, sys
sys.path.insert(0, 'scripts')
from gate_local import score, measures
O = 'output/stable_land_20261025/gate'
for tag, names, ref, cand, limit in (('28 km', ['california', 'western_europe', 'japan', 'new_zealand'], 'check28_ref', 'check28_cand', 1.01),
                                     ('sealed six', ['norway', 'southeast_africa', 'caucasus', 'yunnan', 'northeast_us', 'tasmania'], 'sealed6_ref', 'sealed6_cand', None)):
    r = json.load(open(f'{O}/{ref}/summary.json')); c = json.load(open(f'{O}/{cand}/summary.json'))
    mr, mc = measures(r, names), measures(c, names)
    s = score(mc, mr)
    print(tag, mr, mc, 'S', round(s, 4), '' if limit is None else ('PASS' if s <= limit else 'FAIL'))
    for n in names:
        print('  ', n, round(r['regions'][n]['temperature']['monthly_mae_C'], 3), round(c['regions'][n]['temperature']['monthly_mae_C'], 3),
              round(r['regions'][n]['rain']['loss'], 4), round(c['regions'][n]['rain']['loss'], 4))
EOF
echo "gate done"; grep -E "passes_development_gate|\"score\"|training|holdout|midlatitude|dev12|T_monthly_mae|P_loss" $O/gate.log | head -14; cat $O/checks.log
