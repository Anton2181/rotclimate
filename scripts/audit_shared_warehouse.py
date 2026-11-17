"""Five manufactured pooling controls and four exact legacy inventory reductions."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import harvest.food_stocks as stocks
from polity.shared_warehouse import shared_warehouse_year

OUT=ROOT/'output/urban_shared_warehouse_20261117'
PARENT=ROOT/'output/urban_ostia_storage_20261117'
LEGACY=ROOT/'output/urban_storage_loss_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/shared_warehouse_primitive.json'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


def serial(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {key:serial(item) for key,item in value.items()}
    if isinstance(value,(tuple,list)):return [serial(item) for item in value]
    if isinstance(value,stocks.FoodYear):return serial(asdict(value))
    return value


def fixtures():
    deposit=np.zeros((12,2));deposit[0]=[60.,60.]
    base=dict(deposits=deposit,origin_store=np.array([0,0]),store_ids=['manufactured store'],capacity=np.array([20.]),
        withdrawals=np.full((12,1),10.),origin_pool=['net cereal','net cereal'],store_pool=['net cereal'],
        pooling_authorized=np.array([True]),loss=0.)
    two=np.zeros((12,2));two[0]=[40.,10.];two[6]=[10.,40.]
    return [('shared_pulse',base),('two_pulses_loss05',{**base,'deposits':two,'withdrawals':np.full((12,1),8.),'loss':.05}),
        ('zero_deposits',{**base,'deposits':np.zeros((12,2)),'loss':.05}),
        ('zero_capacity',{**base,'capacity':np.zeros(1)}),
        ('zero_withdrawals',{**base,'withdrawals':np.zeros((12,1)),'loss':.05})]


def gate():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    sources={};protected={}
    for folder in [PARENT,LEGACY]:
        q=read(folder/'qualification.json');assert q['status'].startswith('passed_')
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT),('local_source_sha256',folder)]:
            for name,digest in q.get(key,{}).items():assert sha(prefix/name)==digest,name
        sources[str((folder/'qualification.json').relative_to(ROOT))]=sha(folder/'qualification.json');protected.update(q['protected_sha256'])
    tests=read(OUT/'tests.json');assert tests['status']=='passed' and '19 passed' in tests['stdout']
    for name,digest in tests['sources_sha256'].items():assert sha(ROOT/name)==digest,name
    paths=[Path(__file__),PLAN,ROOT/'polity/shared_warehouse.py',ROOT/'tests/test_shared_warehouse.py',
        ROOT/'polity/earth_storage_loss.py',ROOT/'polity/seasonal_settlement_network.py',ROOT/'harvest/food_stocks.py',OUT/'tests.json']
    for reading in ['central','low']:
        for label in ['loss05_days90','loss00_days90']:
            folder=LEGACY/'cases'/f'{reading}_{label}';assert sha(folder/'fields.npz')==read(folder/'results.json')['fields_sha256']
            paths.extend([folder/'fields.npz',folder/'results.json'])
    sources.update({str(path.relative_to(ROOT)):sha(path) for path in paths})
    return sources,protected


def main():
    sources,protected=gate();assert not (OUT/'results.json').exists(),'Preserve completed shared-store controls'
    manufactured=[];controls=[]
    for name,args in fixtures():
        with patch.object(stocks,'_year',wraps=stocks._year) as years,patch.object(stocks,'_advance',wraps=stocks._advance) as advances:
            result=shared_warehouse_year(**args)
        manufactured.append(dict(name=name,kind='manufactured_pooling_scenario',inputs=serial(args),result=serial(result),
            adapter_calls=1,canonical_year_evaluations=years.call_count,canonical_annual_map_advances=advances.call_count))
    write(OUT/'manufactured.json',manufactured)
    for reading in ['central','low']:
        for label,loss in [('loss05_days90',.05),('loss00_days90',0.)]:
            folder=LEGACY/'cases'/f'{reading}_{label}';c=dict(np.load(folder/'fields.npz'));n=len(c['reference_market'])
            args=dict(deposits=c['marketed'],origin_store=np.arange(n),store_ids=[f'legacy-origin:{int(i)}' for i in c['source_indices']],
                capacity=c['commercial_capacity'],withdrawals=c['dispatch'],origin_pool=np.full(n,'net edible cereal'),
                store_pool=np.full(n,'net edible cereal'),pooling_authorized=np.zeros(n,bool),loss=loss)
            with patch.object(stocks,'_year',wraps=stocks._year) as years,patch.object(stocks,'_advance',wraps=stocks._advance) as advances:
                result=shared_warehouse_year(**args)
            np.testing.assert_array_equal(result['incoming'],c['marketed'])
            np.testing.assert_array_equal(result['capacity'],c['commercial_capacity'])
            np.testing.assert_array_equal(result['departures'],c['departures'])
            fields=asdict(result['food_year']);assert len(fields)==15
            for key,value in fields.items():np.testing.assert_array_equal(value,c['export_food__'+key],err_msg=key)
            receipt=dict(status='all15_legacy_export_inventory_fields_and_departures_exact',reading=reading,control=label,
                source_fields_sha256=sha(folder/'fields.npz'),source_origins=n,physical_stores=n,
                scenario_grouping='identity reduction only;no real warehouse assignment',fields_exact=15,
                loss=loss,ledger=result['ledger'],adapter_calls=1,canonical_year_evaluations=years.call_count,
                canonical_annual_map_advances=advances.call_count,new_Earth_food_scenario=False)
            controls.append(receipt);print(reading,label,'all15 and departures EXACT',flush=True)
    write(OUT/'controls.json',controls)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    r=dict(status='completed_shared_store_manufactured_controls_and_four_exact_reductions',sources_sha256=sources,protected_sha256=protected,
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},tests=19,manufactured_cases=5,legacy_reduction_controls=4,
        exact_inventory_fields_per_control=15,physical_origin_control_rows=sum(c['source_origins'] for c in controls),
        manufactured_adapter_calls=sum(c['adapter_calls'] for c in manufactured),legacy_adapter_calls=4,
        manufactured_canonical_year_evaluations=sum(c['canonical_year_evaluations'] for c in manufactured),
        legacy_canonical_year_evaluations=sum(c['canonical_year_evaluations'] for c in controls),
        producer_canonical_annual_map_advances=sum(c['canonical_annual_map_advances'] for c in manufactured+controls),
        counter_scope='Producer only;pytest and independent reviewer kernel evaluations are separate. _year counts complete canonical ledger years;_advance counts canonical annual-map evaluations.',
        new_Earth_food_scenarios=0,real_origin_to_port_mappings=0,ownership_inferred=False,actual_population_changed=False,
        new_fit=False,new_validation_claim=False,adopt=False)
    write(OUT/'results.json',r);print({key:value for key,value in r.items() if 'evaluations' in key or 'advances' in key},flush=True)


if __name__=='__main__':main()
