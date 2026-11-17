"""Four exact quota controls, then exactly two declared fixed-reference cases."""
import argparse
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.earth_fixed_dispatch import fixed_dispatch_food
from urban_storage_loss import flatten, routes, INPUTS
from urban_earth_monthly import read, write, sha, total, SHARES, inspect, KCAL

OUT=ROOT/'output/urban_fixed_dispatch_20261117'
BASE=ROOT/'output/urban_earth_monthly_20261116'
PARENT=ROOT/'output/urban_storage_loss_20261117'
AUDIT=ROOT/'output/urban_storage_throughput_20261117'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116/wind_1981/prepared'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/fixed_dispatch_loss_control.json'


def gate():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    sources={};protected={}
    for folder in [BASE,PARENT,AUDIT]:
        q=read(folder/'qualification.json');assert q['status'].startswith('passed_')
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in q[key].items():assert sha(prefix/name)==digest,name
        sources[str((folder/'qualification.json').relative_to(ROOT))]=sha(folder/'qualification.json')
        protected.update(q['protected_sha256'])
    tests=read(OUT/'tests.json');assert tests['status']=='passed' and tests['exit_code']==0
    for name,digest in tests['sources_sha256'].items():assert sha(ROOT/name)==digest,name
    paths=[Path(__file__),PLAN,OUT/'tests.json',ROOT/'polity/earth_fixed_dispatch.py',ROOT/'polity/earth_storage_loss.py',
        ROOT/'tests/test_earth_fixed_dispatch.py',ROOT/'scripts/urban_storage_loss.py',ROOT/'scripts/urban_earth_monthly.py',
        ROOT/'harvest/food_stocks.py',ROOT/'harvest/field_support.py',ROOT/'polity/seasonal_settlement_network.py',ROOT/'polity/wide_supply.py']
    for reading in ['central','low']:
        for folder in [BASE/'cases'/reading,PARENT/'cases'/f'{reading}_loss05_days90',PARENT/'cases'/f'{reading}_loss00_days90']:
            p=folder/'fields.npz';assert sha(p)==read(folder/'results.json')['fields_sha256'];paths.append(p)
        paths.append(ANNUAL/f'low_{reading}.npz')
    sources.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
    return sources,protected


def setup(reading):
    baseline=dict(np.load(BASE/'cases'/reading/'fields.npz'))
    a=dict(np.load(ANNUAL/f'low_{reading}.npz'))
    args=[baseline[key] for key in ['produced_components','boundary','rural','request','owner','retention']]+[routes(a)]
    reference=baseline['marketed'].sum(0)
    common=dict(marketed_share=SHARES[reading],reference_market=reference,commercial_days=90)
    return baseline,args,reference,common


def controls():
    sources,protected=gate();folder=OUT/'controls';folder.mkdir(parents=True,exist_ok=True)
    for reading in ['central','low']:
        baseline,args,reference,common=setup(reading)
        for label,loss in [('loss05_days90',.05),('loss00_days90',0.)]:
            path=folder/f'{reading}_{label}.json';assert not path.exists(),'Preserve completed controls'
            original=dict(np.load(PARENT/'cases'/f'{reading}_{label}'/'fields.npz'))
            c=flatten(fixed_dispatch_food(*args,**common,loss=loss))
            for key,value in c.items():np.testing.assert_array_equal(value,original[key],err_msg=key)
            write(path,dict(status='all70_existing_own_quota_food_arrays_exact',reading=reading,control=label,arrays_exact=70,
                sources_sha256=sources,protected_sha256=protected))
            print(reading,label,'all70 EXACT',flush=True)


def main(reading):
    sources,protected=gate()
    for density in ['central','low']:
        for label in ['loss05_days90','loss00_days90']:
            path=OUT/'controls'/f'{density}_{label}.json';c=read(path);assert c['arrays_exact']==70
            assert c['sources_sha256']==sources and c['protected_sha256']==protected
    folder=OUT/'cases'/reading;folder.mkdir(parents=True,exist_ok=True)
    assert not (folder/'results.json').exists(),'Preserve completed cases'
    baseline,args,reference,common=setup(reading)
    try:
        c=fixed_dispatch_food(*args,**common,loss=0.,dispatch_reference=reference)
        old=dict(np.load(PARENT/'cases'/f'{reading}_loss00_days90'/'fields.npz'))
        flat=flatten(c)
        for key in ['harvest','marketed']+[key for key in flat if key.startswith('rural_food__')]:
            np.testing.assert_array_equal(flat[key],old[key],err_msg=key)
        values={key:baseline[key] for key in INPUTS};values.update(flat)
        values.update(reference_market=reference,commercial_capacity=reference*90/365,dispatch_reference=reference)
        np.savez_compressed(folder/'fields.npz',**values)
        audit=inspect(c,baseline['rural'],baseline['request'],SimpleNamespace(produced_total=baseline['harvest'].sum(0)))
        result=dict(status='fixed_baseline_quota_case_pending_independent_review',reading=reading,loss_fraction_year=0.,commercial_days=90,
            marketed_share=SHARES[reading],dispatch_rule='original baseline annual marketed energy /12,masked by original routes',
            sources_sha256=sources,protected_sha256=protected,fields_sha256=sha(folder/'fields.npz'),audit=audit,
            rural_inventory_and_marketed_grain_exact_to_own_quota_zero_loss_case=True,
            zero_reference_origins=int((reference==0).sum()),zero_reference_departures_kcal=total(c['departures'][:,reference==0]),
            demographic_iteration=False,actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False)
        assert result['zero_reference_departures_kcal']==0
        for name,digest in protected.items():assert sha(ROOT/name)==digest,name
        write(folder/'results.json',result);print(reading,'fixed quota meals',audit['town_meal_fraction'],flush=True)
    except BaseException as error:
        write(folder/'failure.json',dict(status='preserved_fixed_quota_failure',error=f'{type(error).__name__}: {error}',producer_sha256=sha(Path(__file__))))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['controls','central','low']);args=parser.parse_args()
    controls() if args.phase=='controls' else main(args.phase)
