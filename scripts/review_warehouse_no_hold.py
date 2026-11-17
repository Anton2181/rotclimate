"""Independent grain/clock checks and scalar archived-arrival reductions; no ledger calls."""
import ast
from fractions import Fraction
import math
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_warehouse_no_hold import OUT,MONTHLY,ANNUAL,CONTROLS,sha,read,write


def main():
    assert not (OUT/'review.json').exists(),'Preserve completed independent no-hold review'
    r=read(OUT/'results.json');assert r['status']=='completed_eight_manufactured_no_hold_cases_and_two_exact_arrival_reductions'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    fixtures=read(CONTROLS)['manufactured'];manufactured=read(OUT/'manufactured.json');assert len(manufactured)==len(fixtures)==8
    for fixture,result in zip(fixtures,manufactured):
        assert fixture['name']==result['name'];b=result['batch']
        assert b['sent']==[fixture['sent']] and b['delivered']==[fixture['delivered']]
        assert b['departure_bin']==[fixture['departure']] and b['arrival_bin']==[(fixture['departure']+1)%12]==[fixture['arrival']]
        charges=[row[0] for row in b['charges']];assert charges==fixture['charges']
        remaining=Fraction(fixture['sent'])
        for index,charge in enumerate(charges):
            remaining-=Fraction(charge);assert remaining>=0 and b['remaining_after_charge'][index]==[float(remaining)]
        assert remaining==fixture['delivered'] and sum(map(Fraction,charges))==fixture['sent']-fixture['delivered']
        assert result['ledger']['event_funding_kcal']==result['ledger']['residual_kcal']==0
    assert Fraction(100)*(1-Fraction(25,100))*(1-Fraction(20,100))-55==5
    controls=read(OUT/'controls.json');assert len(controls)==2
    cases=[]
    for control in controls:
        reading=control['reading']
        with np.load(MONTHLY/'cases'/reading/'fields.npz') as archive:
            old={k:archive[k] for k in ['source_indices','owner','retention','departures','shipments','direct','inter_received','inter_exported','arrivals']}
        with np.load(OUT/f'{reading}_arrivals.npz') as archive:actual=dict(archive)
        n=old['direct'].shape[1];direct=np.zeros((12,n));received=direct.copy();exported=direct.copy()
        sent_parts=[];delivered_parts=[];charge_parts=[];count=0
        # Scalar accumulation in original physical-source order, independently of bincount/new ledger.
        for month in range(12):
            q=month//3;valid=(old['owner'][q]>=0)&(old['retention'][q]>0)
            send=old['departures'][month,valid];receive=send*old['retention'][q,valid]
            owners=old['owner'][q,valid]
            for target,sent,retention in zip(owners,send,old['retention'][q,valid]):
                direct[(month+1)%12,target]+=float(sent)*float(retention)
            count+=len(send);sent_parts.append(math.fsum(send));delivered_parts.append(math.fsum(receive));charge_parts.append(math.fsum(send-receive))
        shipments=old['shipments']
        for month,i,j,sent,delivered in shipments:
            month,i,j=int(month),int(i),int(j)
            assert 0<=delivered<=sent
            exported[month,i]+=float(sent);received[(month+1)%12,j]+=float(delivered)
        count+=len(shipments);sent_parts.append(math.fsum(shipments[:,3]));delivered_parts.append(math.fsum(shipments[:,4]));charge_parts.append(math.fsum(shipments[:,3]-shipments[:,4]))
        arrays=dict(direct=direct,inter_received=received,inter_exported=exported,arrivals=direct+received)
        for key,value in arrays.items():
            np.testing.assert_array_equal(value,old[key],err_msg=f'archived:{reading}:{key}')
            np.testing.assert_array_equal(value,actual[key],err_msg=f'new:{reading}:{key}')
        ledger=control['ledger'];assert count==ledger['consignments'] and ledger['record_calls']==13
        totals=[math.fsum(parts) for parts in [sent_parts,delivered_parts,charge_parts]]
        for key,value in zip(['sent_kcal','delivered_kcal','whole_leg_charge_kcal'],totals):assert ledger[key]==value,key
        residual=totals[0]-math.fsum(totals[1:]);assert abs(residual)<=1e-10*max(1,totals[0])
        assert control['max_charge_residual_fraction_of_original_grain_tolerance']<=1
        cases.append(dict(reading=reading,exact_arrays=4,consignments=count,scalar_source_reduction=True,
            whole_grain_residual_kcal=residual,arrival_clock_unchanged=True))
    # The accounting primitive imports no routing, weather, food or inventory code.
    tree=ast.parse((ROOT/'polity/no_hold.py').read_text())
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):assert all(a.name in {'math','numpy'} for a in node.names)
        if isinstance(node,ast.ImportFrom):assert node.module=='dataclasses'
    assert r['legacy_reductions']==2 and r['manufactured_cases']==8
    for key in ['food_kernel_calls','stock_solves','dijkstra_calls','graph_rebuilds','new_Earth_food_scenarios','actual_warehouse_mappings']:assert r[key]==0
    write(OUT/'review.json',dict(status='passed_independent_no_hold_grain_clock_and_two_scalar_arrival_reductions',
        reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),manufactured_fraction_checks=8,
        split_counterexample_exact_extra_grain=5,legacy_reductions=cases,exact_arrays=8,new_ledger_calls=0,
        food_kernel_calls=0,stock_solves=0,dijkstra_calls=0,graph_rebuilds=0,new_Earth_food_scenarios=0,
        actual_warehouse_mappings=0,new_fit=False,new_validation_claim=False,adopt=False))
    print('Independent no-hold review passed:8 manufactured cases,8 exact archived arrays,zero new ledger/food calls',flush=True)


if __name__=='__main__':main()
