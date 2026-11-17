"""Eight declared manufactured cases and exactly two original arrival reductions."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from polity.no_hold import NoHoldLedger

OUT=ROOT/'output/urban_warehouse_no_hold_20261117'
PARENT=ROOT/'output/urban_warehouse_routes_20261117'
MONTHLY=ROOT/'output/urban_earth_monthly_20261116'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116/wind_1981'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/warehouse_no_hold_contract.json'
CONTROLS=PLAN.with_name('warehouse_no_hold_controls.json')


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text())
def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def serial(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,dict):return {k:serial(v) for k,v in value.items()}
    if isinstance(value,(tuple,list)):return [serial(v) for v in value]
    return value


def gate():
    for path in [PLAN,CONTROLS]:
        assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()
    sources={};protected={}
    for folder in [PARENT,MONTHLY]:
        q=read(folder/'qualification.json');assert q['status'].startswith('passed_')
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in q[key].items():assert sha(prefix/name)==digest,name
        sources[str((folder/'qualification.json').relative_to(ROOT))]=sha(folder/'qualification.json');protected.update(q['protected_sha256'])
    tests=read(OUT/'tests.json');assert tests['status']=='passed' and '34 passed' in tests['stdout']
    for name,digest in tests['sources_sha256'].items():assert sha(ROOT/name)==digest,name
    paths=[Path(__file__),PLAN,CONTROLS,OUT/'tests.json',ROOT/'polity/no_hold.py',ROOT/'tests/test_no_hold.py']
    for reading in ['central','low']:
        paths.extend([MONTHLY/'cases'/reading/'fields.npz',ANNUAL/'prepared'/f'low_{reading}.npz'])
    return {**sources,**{str(p.relative_to(ROOT)):sha(p) for p in paths}},protected


def allocation(sent,delivered):
    charge=sent-delivered;part=charge*.25
    return np.stack([part,part,charge-(part+part)])


def main():
    sources,protected=gate();assert not (OUT/'results.json').exists() and not (OUT/'failure.json').exists(),'Preserve completed/failed no-hold controls'
    manufactured=[]
    for fixture in read(CONTROLS)['manufactured']:
        ledger=NoHoldLedger()
        b=ledger.record([fixture['name']],[10],[20],[fixture['sent']],[fixture['delivered']],
            [fixture['departure']],[fixture['arrival']],event_labels=('event-a','event-b','terminal-charge'),
            charge_allocation=np.array(fixture['charges'])[:,None])
        manufactured.append(dict(name=fixture['name'],batch=serial(asdict(b)),ledger=ledger.summary()))
    assert len(manufactured)==8
    write(OUT/'manufactured.json',manufactured)
    controls=[]
    for reading in ['central','low']:
        with np.load(MONTHLY/'cases'/reading/'fields.npz') as z:
            c={key:z[key] for key in ['source_indices','owner','retention','departures','shipments','direct','inter_received','inter_exported','arrivals','request']}
        with np.load(ANNUAL/'prepared'/f'low_{reading}.npz') as z:nodes=z['nodes']
        ledger=NoHoldLedger();towns=len(nodes);direct=np.zeros((12,towns));received=np.zeros_like(direct);exported=np.zeros_like(direct)
        max_ratio=0.;source_count=0;source_wrap=0
        for month in range(12):
            q=month//3;valid=(c['owner'][q]>=0)&(c['retention'][q]>0)
            rows=np.flatnonzero(valid);sent=c['departures'][month,valid];delivered=sent*c['retention'][q,valid]
            b=ledger.record([f'{reading}:source:{month}:{int(i)}' for i in c['source_indices'][valid]],
                c['source_indices'][valid],nodes[c['owner'][q,valid]],sent,delivered,
                np.full(len(rows),month),np.full(len(rows),(month+1)%12),
                event_labels=('annotation-a','annotation-b','terminal-charge'),charge_allocation=allocation(sent,delivered))
            np.testing.assert_array_equal(b.delivered,delivered)
            direct[(month+1)%12]+=np.bincount(c['owner'][q,valid],weights=b.delivered,minlength=towns)
            max_ratio=max(max_ratio,float(np.max(abs(b.residual)/(1e-10*np.maximum(1,b.sent)),initial=0)))
            source_count+=len(rows);source_wrap+=int(month==11)*int(np.count_nonzero(sent))
        # Preserve shipment row order. This is accounting only, never ship()/a stock solve.
        shipments=c['shipments'];n=len(shipments);month=shipments[:,0].astype(int);sender=shipments[:,1].astype(int);receiver=shipments[:,2].astype(int)
        b=ledger.record([f'{reading}:intertown:{i}' for i in range(n)],nodes[sender],nodes[receiver],shipments[:,3],shipments[:,4],
            month,(month+1)%12,event_labels=('annotation-a','annotation-b','terminal-charge'),charge_allocation=allocation(shipments[:,3],shipments[:,4]))
        for i in range(n):
            received[b.arrival_bin[i],receiver[i]]+=b.delivered[i]
            exported[b.departure_bin[i],sender[i]]+=b.sent[i]
        max_ratio=max(max_ratio,float(np.max(abs(b.residual)/(1e-10*np.maximum(1,b.sent)),initial=0)))
        arrivals=direct+received
        for key,value in [('direct',direct),('inter_received',received),('inter_exported',exported),('arrivals',arrivals)]:
            np.testing.assert_array_equal(value,c[key],err_msg=f'{reading}:{key}')
        fields=OUT/f'{reading}_arrivals.npz';np.savez_compressed(fields,direct=direct,inter_received=received,inter_exported=exported,arrivals=arrivals)
        controls.append(dict(status='four_original_arrival_export_arrays_exact',reading=reading,source_rows=source_count,
            intertown_rows=n,source_wrap_positive_rows=source_wrap,intertown_wrap_rows=int((month==11).sum()),
            ledger=ledger.summary(),max_charge_residual_fraction_of_original_grain_tolerance=max_ratio,
            fields_sha256=sha(fields),new_Earth_food_scenario=False,food_kernel_calls=0,stock_solves=0))
        print(reading,'four arrival/export arrays EXACT;',ledger.summary()['consignments'],'consignments',flush=True)
    write(OUT/'controls.json',controls)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    r=dict(status='completed_eight_manufactured_no_hold_cases_and_two_exact_arrival_reductions',sources_sha256=sources,
        protected_sha256=protected,files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},tests=34,
        manufactured_cases=8,legacy_reductions=2,exact_arrays_per_reading=4,
        manufactured_ledger_calls=8,legacy_ledger_calls=sum(c['ledger']['record_calls'] for c in controls),
        legacy_consignment_rows=sum(c['ledger']['consignments'] for c in controls),
        food_kernel_calls=0,stock_solves=0,dijkstra_calls=0,graph_rebuilds=0,new_Earth_food_scenarios=0,
        actual_warehouse_mappings=0,physical_duration_inferred=False,actual_population_changed=False,new_fit=False,new_validation_claim=False,
        adopt=False,main_atlas_changed=False)
    write(OUT/'results.json',r)


if __name__=='__main__':
    try:main()
    except BaseException as error:
        OUT.mkdir(exist_ok=True)
        if not (OUT/'failure.json').exists():write(OUT/'failure.json',dict(status='preserved_no_hold_control_failure',
            error=f'{type(error).__name__}: {error}',producer_sha256=sha(Path(__file__)),adopt=False))
        raise
