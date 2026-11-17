"""Independent grouping,stocks and conserved per-store physical ledgers."""
import math
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import harvest.food_stocks as stocks
from audit_shared_warehouse import OUT,LEGACY,sha,read,write
from review_urban_storage_loss import zero_inventory
from review_urban_earth_monthly import inventory as five_percent_inventory


def verify(deposits,mapping,capacity,requests,values,paid,loss):
    incoming=np.zeros_like(requests)
    for origin,store in enumerate(mapping):
        if store>=0:incoming[:,store]+=deposits[:,origin]
        else:assert np.all(deposits[:,origin]==0)
    flat={'store__'+key:np.asarray(value) for key,value in values.items()}
    if loss==0:ratio=zero_inventory(flat,'store',incoming,requests,capacity)
    else:_,ratio=five_percent_inventory(flat,'store',incoming,requests,capacity)
    np.testing.assert_array_equal(paid,requests-flat['store__unmet_path'])
    # Reconstruct every physical step from supplied recorded initial stock.
    stock=flat['store__initial_stock'].copy();spoiled=np.zeros_like(stock);overflow=spoiled.copy();funded=spoiled.copy()
    fraction=-np.expm1(np.log1p(-loss)/12)
    scale=np.maximum(1,np.maximum(incoming.sum(0),requests.sum(0)));tol=1e-10*scale+100*np.finfo(float).eps*scale
    for month in range(12):
        available=stock+incoming[month];take=np.minimum(available,requests[month]);remaining=available-take
        spill=np.maximum(remaining-capacity,0);held=np.minimum(remaining,capacity);decay=held*fraction
        stock=held-decay;spoiled+=decay;overflow+=spill;funded+=take
        assert np.all(abs(stock-flat['store__stock_path'][month+1])<=tol)
        assert np.all(abs(take-paid[month])<=tol)
    for expected,key in [(spoiled,'spoiled'),(overflow,'overflow'),(funded,'consumed')]:
        assert np.all(abs(expected-flat['store__'+key])<=tol)
    residual=incoming.sum(0)-paid.sum(0)-spoiled-overflow-(stock-flat['store__initial_stock'])
    assert np.all(abs(residual)<=tol)
    total=lambda x:math.fsum(np.asarray(x).ravel())
    ledger=total(deposits)-math.fsum([total(paid),total(spoiled),total(overflow),total(stock-flat['store__initial_stock'])])
    assert abs(ledger)<=1e-10*max(1,total(deposits),total(requests))
    return ratio,ledger


def main():
    assert not (OUT/'review.json').exists(),'Preserve completed review'
    r=read(OUT/'results.json')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    maximum=0.;residuals=[];groups=0
    with patch.object(stocks,'_year',wraps=stocks._year) as years,patch.object(stocks,'_advance',wraps=stocks._advance) as advances:
        for case in read(OUT/'manufactured.json'):
            args=case['inputs'];c=case['result'];n=len(c['store_ids'])
            assert len(set(c['store_ids']))==n and c['capacity']==args['capacity']
            ratio,residual=verify(np.asarray(args['deposits']),args['origin_store'],np.asarray(args['capacity']),
                np.asarray(args['withdrawals']),c['food_year'],np.asarray(c['departures']),args['loss'])
            maximum=max(maximum,ratio);residuals.append(residual);groups+=1
            if case['name']=='shared_pulse':
                assert c['food_year']['peak_stock']==[20.]
                assert sum(row[0] for row in c['departures'])==30
                assert c['food_year']['overflow']==[90.]
            if case['name']=='zero_deposits':assert sum(c['food_year']['initial_stock'])==0
        for control in read(OUT/'controls.json'):
            assert control['fields_exact']==15 and not control['new_Earth_food_scenario']
            path=LEGACY/'cases'/f"{control['reading']}_{control['control']}"/'fields.npz'
            assert sha(path)==control['source_fields_sha256'];c=dict(np.load(path));n=len(c['reference_market'])
            assert control['source_origins']==control['physical_stores']==n
            values={key[len('export_food__'):]:value for key,value in c.items() if key.startswith('export_food__')}
            ratio,residual=verify(c['marketed'],np.arange(n),c['commercial_capacity'],c['dispatch'],values,c['departures'],control['loss'])
            maximum=max(maximum,ratio);residuals.append(residual);groups+=1
    receipt=dict(status='passed_independent_shared_store_grouping_inventory_and_physical_ledgers',reviewer_sha256=sha(Path(__file__)),
        reviewer_dependencies_sha256={name:sha(ROOT/name) for name in ['scripts/review_urban_storage_loss.py','scripts/review_urban_earth_monthly.py']},
        results_sha256=sha(OUT/'results.json'),manufactured_cases=5,legacy_reduction_controls=4,inventory_groups=groups,
        max_fraction_original_inventory_tolerance=maximum,max_abs_whole_grain_residual_kcal=max(abs(x) for x in residuals),
        independent_canonical_year_evaluations=years.call_count,independent_canonical_annual_map_advances=advances.call_count,
        reviewer_shared_adapter_calls=0,exact_inventory_fields_per_control=15,model_capacities_changed=False,
        new_Earth_food_scenarios=0,real_origin_to_port_mappings=0,actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False)
    write(OUT/'review.json',receipt);print(receipt,flush=True)


if __name__=='__main__':main()
