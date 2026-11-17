"""Independent single-store funding, role priority and original-tolerance stock replay."""
from dataclasses import asdict
import math
from pathlib import Path
import sys
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import harvest.food_stocks as stocks
from audit_warehouse_no_hold import sha,read,write

OUT=ROOT/'output/urban_warehouse_roles_20261117'


def main():
    assert not (OUT/'review.json').exists(),'Preserve completed shared-role review'
    r=read(OUT/'results.json');assert r['status']=='completed_seven_shared_role_scenarios_and_seven_exact_aggregate_reductions'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    cases=read(OUT/'scenarios.json');assert len(cases)==7
    max_ratio=0.;max_residual=0.;rows=[]
    with patch.object(stocks,'_year',wraps=stocks._year) as years,patch.object(stocks,'_advance',wraps=stocks._advance) as advances:
        for case in cases:
            f=case['fixture'];c=case['result'];inventory=c['inventory'];values={key:np.asarray(value) for key,value in c['food_year'].items()}
            k=len(f['store_ids']);incoming=np.zeros((12,k));requests=np.zeros_like(incoming)
            assert len(set(f['ids']))==len(f['ids'])==c['consignment_funding']['consignments']
            for index,(store,month,grain) in enumerate(zip(f['consignment_store'],f['arrival'],f['delivered'])):
                assert month==(f['departure'][index]+1)%12 and f['destination'][index]==f['store_nodes'][store]
                incoming[month,store]+=grain
            for role,store in enumerate(f['role_store']):requests[:,store]+=np.asarray(f['requests'])[:,role]
            np.testing.assert_array_equal(incoming,inventory['incoming'])
            np.testing.assert_array_equal(inventory['capacity'],f['capacity'])
            np.testing.assert_array_equal(inventory['requested'],requests)
            # One canonical ledger year from its supplied recorded initial stock; no new adapter.
            expected=stocks.food_year(incoming,requests,f['capacity'],initial_stock=values['initial_stock'],
                loss_fraction_year=f['loss'],step_days=365/12,record=True)
            for key,value in asdict(expected).items():np.testing.assert_array_equal(value,values[key],err_msg=f'{case["name"]}:{key}')
            tolerance=1e-10*np.maximum(1,np.maximum(incoming.sum(0),requests.sum(0)))
            ratio=float(np.max(expected.periodic_residual/tolerance));assert ratio<=1
            max_ratio=max(max_ratio,ratio)
            paid=np.asarray(c['paid']);unmet=np.asarray(c['unmet']);demand=np.asarray(f['requests'])
            assert np.all(paid>=0) and np.all(paid<=demand)
            np.testing.assert_array_equal(unmet,demand-paid)
            actual_by_store=np.zeros_like(incoming)
            for role,store in enumerate(f['role_store']):actual_by_store[:,store]+=paid[:,role]
            np.testing.assert_allclose(actual_by_store,inventory['departures'],rtol=0,atol=float(tolerance.max()))
            # Priority cannot pay a later role while an earlier role at the same store is unmet.
            for order,role in enumerate(f['priority']):
                for earlier in f['priority'][:order]:
                    if f['role_store'][earlier]==f['role_store'][role]:assert not ((paid[:,role]>tolerance[f['role_store'][role]])&(unmet[:,earlier]>tolerance[f['role_store'][role]])).any()
            # Separately reconstruct every monthly physical grain account with supplied stock path.
            capacity=np.asarray(f['capacity']);path=values['stock_path'];decay=-np.expm1(np.log1p(-f['loss'])/12)
            spoil=np.zeros(k);spill=np.zeros(k)
            for month in range(12):
                available=path[month]+incoming[month];take=np.minimum(available,requests[month])
                carry=available-take;overflow=np.maximum(carry-capacity,0);held=np.minimum(carry,capacity);loss=held*decay
                assert np.all(abs(actual_by_store[month]-take)<=tolerance)
                assert np.all(abs(held-loss-path[month+1])<=tolerance)
                spoil+=loss;spill+=overflow
            assert np.all(abs(spoil-values['spoiled'])<=tolerance) and np.all(abs(spill-values['overflow'])<=tolerance)
            total=lambda v:math.fsum(np.asarray(v).ravel())
            freight=math.fsum(float(sent)-float(got) for sent,got in zip(f['sent'],f['delivered']))
            residual=total(f['sent'])-math.fsum([freight,total(paid),total(spoil),total(spill),total(path[-1]-path[0])])
            assert abs(residual)<=1e-10*max(1,total(f['sent']))
            max_residual=max(max_residual,abs(residual))
            assert not c['upstream_rural_work_certified'] and not c['handling_work_certified'] and not c['rights_inferred']
            rows.append(dict(name=case['name'],stores=k,roles=len(f['role_ids']),exact_inventory_fields=15,
                paid_kcal=total(paid),paid_by_role=paid.sum(0).tolist(),physical_residual_kcal=residual,
                periodic_residual_fraction_original_tolerance=ratio))
    lookup={c['name']:c for c in cases}
    np.testing.assert_array_equal(np.array(lookup['priority_ab']['result']['paid']).sum(0),[13,2])
    np.testing.assert_array_equal(np.array(lookup['priority_ba']['result']['paid']).sum(0),[11,4])
    for key,value in lookup['priority_ab']['result']['food_year'].items():np.testing.assert_array_equal(value,lookup['priority_ba']['result']['food_year'][key])
    assert np.array(lookup['two_stores']['result']['paid'])[:,1].sum()==0
    assert np.array(lookup['zero_delivery']['result']['paid']).sum()==0
    assert np.array(lookup['zero_delivery']['result']['food_year']['initial_stock']).sum()==0
    assert np.array(lookup['zero_capacity']['result']['food_year']['stock_path']).sum()==0
    write(OUT/'review.json',dict(status='passed_independent_shared_role_grain_priority_and_canonical_inventory_checks',
        reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),scenarios=rows,
        max_fraction_original_inventory_tolerance=max_ratio,max_abs_whole_grain_residual_kcal=max_residual,
        reviewer_role_adapter_calls=0,reviewer_shared_store_adapter_calls=0,
        reviewer_canonical_year_evaluations=years.call_count,reviewer_canonical_annual_map_advances=advances.call_count,
        new_Earth_food_scenarios=0,actual_warehouse_mappings=0,new_fit=False,new_validation_claim=False,adopt=False))
    print('Independent shared-role review passed:seven cases,zero adapter calls,',years.call_count,'canonical years;',max_ratio,'original-tolerance ratio',flush=True)


if __name__=='__main__':main()
