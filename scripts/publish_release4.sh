#!/usr/bin/env bash
# Release 4 (WP3 river confluences) publication: the published publishers, unchanged, run on output/settlement_release4_20261116
# (staged by scripts/settlement_chain.py calibration/settlement_chain/release4_confluence.json build, then copied).
# Each step mirrors the release-3/hierarchy publication's commands (same substitutions).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python; R=output/settlement_release4_20261116
step=${1:-all}
if [ "$step" = all ] || [ "$step" = settlements ]; then
  $PY -I scripts/exec_with.py scripts/publish_settlement_release3.py "output/settlement_release3_20261113=>$R/release3" \
    ", DATA / 'settlement_release2.json')}=>)}"  # r49: release-2 manifest retired (superseded)
fi
if [ "$step" = all ] || [ "$step" = note ]; then
  $PY - <<'P'
import json
p='atlases/earth_fit/data/settlement_release3.json'; d=json.load(open(p,encoding='utf-8'))
add='Release 4: proposed towns also favour river confluences (blind-tested on European cities of 1300; reports/WP3_CONFLUENCE_20261116.md). '
n=0
for m,pk in d['packets'].items():
    for o in pk['options']['reach_towns']:
        if o['value'] in ('release3_central','release3_low') and not o.get('note','').startswith('Release 4'):
            o['note']=add+o.get('note',''); n+=1
open(p,'w').write(json.dumps(d,indent=2,allow_nan=False)+'\n'); print('notes updated',n)   # the publishers' own format (settlement_locations_earth.write)
P
fi

if [ "$step" = all ] || [ "$step" = supply ]; then
  $PY -I scripts/exec_with.py scripts/publish_wide_supply_release3.py "output/settlement_wide_supply_20261113=>$R/supply" "output/settlement_release3_20261113=>$R/release3" \
    "('central_x39', '39% of surplus grain marketed (Earth-calibrated)')=>('central_x34', '34% of surplus grain marketed (Earth-calibrated, Egypt included)')" \
    "key.endswith('39')=>key.endswith('34')" "key = f'{density}_x39'=>key = {'central': 'central_x34', 'low': 'low_x14'}[density]" \
    "(39% of surplus marketed, the share that feeds Roman cities; see the grain supply map)=>({100 * s['extraction']:.0f}% of surplus marketed, the share that feeds 95% of Roman city residents at this density reading, Egypt included; see the grain supply map)" \
    "wide supply, 39% marketed=>wide supply, 34% marketed at the sliding reading, 14% at the flat reading" \
    "the marketed share and haul limit are checked against the Roman Empire without Egypt.=>the marketed share and haul limit are calibrated on the whole Roman Empire, Egypt included (floodplain rule, Greek wall circuits at their inhabited share; development, not blind)."
fi
if [ "$step" = all ] || [ "$step" = ensemble ]; then
  $PY -I scripts/exec_with.py scripts/publish_settlement_ensemble.py "output/settlement_ensemble_20261115=>$R/ensemble" "output/settlement_hierarchy_map_20261115=>$R"
fi
if [ "$step" = all ] || [ "$step" = reach ]; then
  # after scripts/release4_reach_chain.sh and moving its images to data/release3/reach_fed (originals restored from git)
  # both option sets: supply-fed (control_*_release4_20261116) and the earlier 7.5% request (control_*_release4req_20261116)
  $PY -I scripts/exec_with.py scripts/publish_supply_reach_release3.py "supplyfed_release3_20261113=>release4_20261116" "release3_20261113=>release4req_20261116" \
    "output/settlement_downstream_20261113=>$R/downstream" \
    "(39% of surplus marketed, the Earth-calibrated share)=>(34% of surplus marketed, the Earth-calibrated share with Egypt included)"
fi
if [ "$step" = all ] || [ "$step" = layers ]; then
  # reach and trade layers from the staged atlases (scripts/stage_atlas.py + export_reach_release3.py on the release-4 towns);
  # controls: unmodified exporter on fresh staged copies (atlas_*_control), which reproduced the published layers
  # r49 (21 Nov 2026): staging release4_r49; the controls are the release build's own unmodified exports of the live atlas
  S=output/chain_staging/release4_r49
  $PY -I scripts/exec_with.py scripts/publish_downstream_release3.py "output/settlement_downstream_20261113=>$R/downstream" -- \
    $S/atlas_raw $S/atlas_corrected output/polity_map/earth_fit_r49_stage.npz output/polity_map/earth_fit_r49_stage_corrected.npz
fi
