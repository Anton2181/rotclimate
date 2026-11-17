"""Seven declared shared-role scenarios and seven exact aggregate reductions."""
from dataclasses import asdict
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import harvest.food_stocks as stocks
from polity.no_hold import NoHoldLedger
from polity.warehouse_roles import shared_role_year
from polity.shared_warehouse import shared_warehouse_year
from audit_warehouse_no_hold import sha,read,write,serial

OUT=ROOT/'output/urban_warehouse_roles_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/warehouse_shared_roles_controls.json'


def fixtures():
    base=dict(ids=['leg-a','leg-b'],origin=[10,11],destination=[20,20],sent=[60,60],delivered=[60,60],departure=[11,11],arrival=[0,0],
        consignment_store=[0,0],store_ids=['manufactured-store-a'],store_nodes=[20],capacity=[20.],role_ids=['commercial','town'],
        role_store=[0,0],requests=np.tile([8.,2.],(12,1)).tolist(),priority=[0,1],consignment_pool=['net cereal','net cereal'],
        store_pool=['net cereal'],pooling_authorized=[True],loss=0.)
    return [('shared_pulse',base),('priority_ab',{**base,'capacity':[5.]}),
        ('priority_ba',{**base,'capacity':[5.],'priority':[1,0]}),
        ('calendar_wrap',{**base,'delivered':[50.,50.],'departure':[10,11],'arrival':[11,0],'capacity':[30.],
            'requests':np.tile([5.,3.],(12,1)).tolist(),'loss':.05}),
        ('two_stores',{**base,'store_ids':['manufactured-store-a','manufactured-store-b'],'store_nodes':[20,30],
            'capacity':[20.,20.],'role_store':[0,1],'requests':np.full((12,2),10.).tolist(),
            'store_pool':['net cereal','net cereal'],'pooling_authorized':[True,False]}),
        ('zero_capacity',{**base,'capacity':[0.]}),
        ('zero_delivery',{**base,'delivered':[0.,0.]})]


def make_args(f):
    ledger=NoHoldLedger();b=ledger.record(f['ids'],f['origin'],f['destination'],f['sent'],f['delivered'],f['departure'],f['arrival'])
    a={k:f[k] for k in ['consignment_store','store_ids','store_nodes','capacity','role_ids','role_store','requests','priority',
        'consignment_pool','store_pool','pooling_authorized','loss']}
    a['batches']=[b]
    return a


def independent_aggregate(f):
    # Assemble directly from declared fixture values, never from the new adapter output.
    pairs=sorted(set(zip(f['origin'],f['consignment_store'])));deposits=np.zeros((12,len(pairs)))
    for origin,store,arrival,grain in zip(f['origin'],f['consignment_store'],f['arrival'],f['delivered']):
        deposits[arrival,pairs.index((origin,store))]+=grain
    requests=np.zeros((12,len(f['store_ids'])))
    for role,store in enumerate(f['role_store']):requests[:,store]+=np.array(f['requests'])[:,role]
    stores=np.array([p[1] for p in pairs],int)
    return dict(deposits=deposits,origin_store=stores,store_ids=f['store_ids'],capacity=np.array(f['capacity']),withdrawals=requests,
        origin_pool=np.array(f['store_pool'])[stores],store_pool=f['store_pool'],pooling_authorized=np.array(f['pooling_authorized']),loss=f['loss'])


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert not (OUT/'results.json').exists() and not (OUT/'failure.json').exists(),'Preserve shared-role controls'
    sources={};protected={}
    for folder in [ROOT/'output/urban_warehouse_no_hold_20261117',ROOT/'output/urban_shared_warehouse_20261117']:
        q=read(folder/'qualification.json');assert q['status'].startswith('passed_')
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in q[key].items():assert sha(prefix/name)==digest,name
        sources[str((folder/'qualification.json').relative_to(ROOT))]=sha(folder/'qualification.json');protected.update(q['protected_sha256'])
    tests=read(OUT/'tests.json');assert tests['status']=='passed' and '21 passed' in tests['stdout']
    for name,digest in tests['sources_sha256'].items():assert sha(ROOT/name)==digest,name
    paths=[Path(__file__),PLAN,OUT/'tests.json',ROOT/'polity/warehouse_roles.py',ROOT/'tests/test_warehouse_roles.py',
        ROOT/'polity/no_hold.py',ROOT/'polity/shared_warehouse.py',ROOT/'polity/earth_storage_loss.py',ROOT/'harvest/food_stocks.py']
    sources.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
    scenarios=[]
    for name,f in fixtures():
        with patch.object(stocks,'_year',wraps=stocks._year) as y,patch.object(stocks,'_advance',wraps=stocks._advance) as advances:
            result=shared_role_year(**make_args(f))
        adapter_counts=dict(canonical_year_evaluations=y.call_count,canonical_annual_map_advances=advances.call_count)
        with patch.object(stocks,'_year',wraps=stocks._year) as y,patch.object(stocks,'_advance',wraps=stocks._advance) as advances:
            expected=shared_warehouse_year(**independent_aggregate(f))
        reference_counts=dict(canonical_year_evaluations=y.call_count,canonical_annual_map_advances=advances.call_count)
        for key,value in asdict(expected['food_year']).items():np.testing.assert_array_equal(asdict(result['inventory']['food_year'])[key],value,err_msg=f'{name}:{key}')
        for key in ['incoming','capacity','requested','departures']:np.testing.assert_array_equal(result['inventory'][key],expected[key])
        assert np.all(result['paid']>=0) and np.all(result['paid']<=result['requested'])
        scenarios.append(dict(name=name,fixture=f,result={**serial({k:v for k,v in result.items() if k!='inventory'}),
            'inventory':serial({k:v for k,v in result['inventory'].items() if k!='food_year'}),
            'food_year':serial(asdict(result['inventory']['food_year']))},exact_inventory_fields=15,
            adapter_calls=1,aggregate_reference_calls=1,adapter_counters=adapter_counts,reference_counters=reference_counts))
        print(name,'ALL15 aggregate inventory fields EXACT; paid',result['paid'].sum(),flush=True)
    assert len(scenarios)==7
    for key,value in scenarios[1]['result']['food_year'].items():np.testing.assert_array_equal(value,scenarios[2]['result']['food_year'][key])
    write(OUT/'scenarios.json',scenarios)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',dict(status='completed_seven_shared_role_scenarios_and_seven_exact_aggregate_reductions',
        sources_sha256=sources,protected_sha256=protected,files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},
        tests=21,manufactured_scenarios=7,aggregate_reductions=7,exact_fields_per_case=15,
        adapter_calls=7,aggregate_reference_calls=7,
        adapter_canonical_year_evaluations=sum(s['adapter_counters']['canonical_year_evaluations'] for s in scenarios),
        adapter_canonical_annual_map_advances=sum(s['adapter_counters']['canonical_annual_map_advances'] for s in scenarios),
        reference_canonical_year_evaluations=sum(s['reference_counters']['canonical_year_evaluations'] for s in scenarios),
        reference_canonical_annual_map_advances=sum(s['reference_counters']['canonical_annual_map_advances'] for s in scenarios),
        graph_rebuilds=0,dijkstra_calls=0,new_Earth_food_scenarios=0,actual_warehouse_mappings=0,
        upstream_rural_work_certified=False,handling_work_certified=False,actual_population_changed=False,
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False))


if __name__=='__main__':
    try:main()
    except BaseException as error:
        OUT.mkdir(exist_ok=True)
        if not (OUT/'failure.json').exists():write(OUT/'failure.json',dict(status='preserved_shared_role_control_failure',error=f'{type(error).__name__}: {error}',producer_sha256=sha(Path(__file__)),adopt=False))
        raise
