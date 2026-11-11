"""Independently check shared work scenarios against unchanged atlas food ledgers."""
import gzip
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from harvest.food_stocks import periodic_food_year
from build_settlement_service_capacity import OUT,PLAN,MODELS


def main():
    result=json.loads((OUT/'results.json').read_text());fields=dict(np.load(OUT/'fields.npz'))
    assert result['plan_sha256']==sha(PLAN) and result['fields_sha256']==sha(OUT/'fields.npz')
    for path,digest in {**result['sources'],**result['producers']}.items():assert sha(ROOT/path)==digest,path
    expected_keys=set();checked=0;food_checked=0;source_controls=[]
    for climate,path in MODELS.items():
        relative=str(path.relative_to(ROOT))
        assert subprocess.check_output(['git','show','a9b3858c:'+relative],cwd=ROOT)==path.read_bytes()
        source_controls.append(relative)
        model=json.loads(gzip.decompress(path.read_bytes()));spec=model['specification'];n=len(model['sites'])
        np.testing.assert_array_equal(fields[climate+'__nodes'],[s['node'] for s in model['sites']]);expected_keys.add(climate+'__nodes')
        for case in model['cases']:
            if not case.get('food_constrained'):continue
            name=case['id'];prefix=climate+'__'+name;staff=np.array(case['institutional_people']);people=np.array(case['civilian_people'])+staff
            for suffix,values in [('people',people),('staff',staff)]:
                np.testing.assert_array_equal(fields[prefix+'__'+suffix],values);expected_keys.add(prefix+'__'+suffix)
            arrivals=np.array(case['monthly_arrivals_kcal']).T;need=np.array(case['monthly_need_kcal']).T
            np.testing.assert_allclose(need,np.broadcast_to(people*spec['ration_kcal_person_day']*spec['year_days']/12,need.shape),rtol=1e-12)
            year=periodic_food_year(arrivals,need,people*spec['ration_kcal_person_day']*spec['destination_store_demand_days'],
                loss_fraction_year=spec['annual_stored_energy_loss_fraction'],step_days=spec['year_days']/12,record=True)
            assert np.all(people<=np.array(case['food_ceiling_people'])+1e-6*np.maximum(1,people))
            assert np.all(year.unmet<=1e-6*np.maximum(1,year.needed))
            for attr,key in [('consumed','resident_consumed_kcal'),('spoiled','destination_loss_kcal'),('overflow','destination_unused_kcal')]:
                assert np.isclose(getattr(year,attr).sum(),case['ledger'][key],rtol=1e-10,atol=.01)
            food_checked+=1
            for fraction in [0.,.5,1.]:
                available=staff*600*(1-fraction);requested_hours=3*people
                factor=np.minimum(1,np.divide(available,requested_hours,out=np.ones_like(people),where=requested_hours>0))
                each=people*factor;served=np.stack([each,each]);unmet=np.stack([people-each,people-each]);used=np.stack([each,each*2])
                tag=prefix+f'__committed{int(fraction*100)}'
                direct={'served':served,'unmet':unmet,'unreachable':np.zeros((2,n)),
                    'capacity_unmet':unmet,'provider_hours':used,'unused_hours':np.maximum(0,available-used.sum(axis=0)),'available_hours':available}
                for suffix,values in direct.items():
                    expected_keys.add(tag+'__'+suffix);np.testing.assert_allclose(fields[tag+'__'+suffix],values,rtol=1e-12,atol=1e-8)
                summaries=[r for r in result['scenarios'] if r['climate']==climate and r['case']==name and r['committed_fraction']==fraction]
                assert len(summaries)==1;s=summaries[0]
                for key,value in {'residents':people.sum(),'supported_staff':staff.sum(),'gross_staff_hours':staff.sum()*600,
                    'committed_staff_hours':staff.sum()*600*fraction,'available_staff_hours':available.sum(),
                    'used_staff_hours':used.sum(),'unused_staff_hours':direct['unused_hours'].sum()}.items():assert np.isclose(s[key],value,rtol=1e-12,atol=1e-7)
                np.testing.assert_allclose(s['requested_by_channel'],[people.sum()]*2,rtol=1e-12)
                np.testing.assert_allclose(s['fulfilled_by_channel'],served.sum(axis=1),rtol=1e-12)
                np.testing.assert_allclose(s['unmet_by_channel'],unmet.sum(axis=1),rtol=1e-12)
                if people.sum()==0:assert s['fulfilled_request_fraction'] is None
                else:assert np.isclose(s['fulfilled_request_fraction'],each.sum()/people.sum(),rtol=1e-12)
                np.testing.assert_allclose(fields[tag+'__served']+fields[tag+'__unmet'],np.broadcast_to(people,(2,n)),rtol=1e-12,atol=1e-8)
                assert np.all(fields[tag+'__provider_hours'].sum(axis=0)<=available+1e-8)
                checked+=1
    assert set(fields)==expected_keys and checked==len(result['scenarios'])==60 and food_checked==len(result['food_replays'])==20
    assert not result['adopt'] and not result['earth_calibrated_service_rates'] and not result['population_food_staff_control_changed']
    write(OUT/'review.json',dict(status='passed',source_result_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),
        periodic_food_cases=food_checked,shared_hour_cases=checked,all_per_origin_requests_and_provider_hours_checked=True,
        fields_checked=len(expected_keys),unchanged_atlas_snapshots=source_controls,unchanged_baseline='a9b3858c',adopt=False))
    print('Reviewed20periodic food cases,60shared-hour scenarios;all origin/provider budgets pass;atlas snapshots unchanged.')


if __name__=='__main__':main()
