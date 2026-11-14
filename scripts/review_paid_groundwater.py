"""Independent replay of every saved finite-groundwater history and demo."""
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from groundwater_scalar import scalar_groundwater,STOCKS,FIELD_FLUXES,RIVER

OUT=ROOT/'output/paid_groundwater_20261114'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs(z,prefix):
    return {name[len(prefix+'__input_'):]:value for name,value in z.items() if name.startswith(prefix+'__input_')}


def main():
    r=json.loads((OUT/'results.json').read_text())
    for name,digest in {**r['producers'],**r['unchanged_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert r['controls_sha256']==sha(OUT/'controls.json')
    controls=json.loads((OUT/'controls.json').read_text());assert '223 passed' in controls['stdout']
    assert controls['producer_sha256']==sha(ROOT/'scripts/paid_groundwater_benchmarks.py')
    with np.load(OUT/'synthetic.npz') as archive:z={name:archive[name] for name in archive.files}
    cells=0;steps=0;maxerror=0.;maxfield=0.;maxjoint=0.
    for case in range(100):
        prefix=f'{case:03}';a=inputs(z,prefix)
        ref,final,mass,joint=scalar_groundwater(a)
        maxfield=max(maxfield,mass);maxjoint=max(maxjoint,joint)
        for name,value in ref.items():
            actual=z[prefix+'__actual_'+name];maxerror=max(maxerror,float(np.max(np.abs(actual-value))));cells+=value.size
            np.testing.assert_allclose(actual,value,atol=2e-10,rtol=2e-11,err_msg=prefix+' '+name)
        steps+=len(a['dt'])*len(a['area_m2'])
        for t,days in enumerate(a['dt']):
            charge=z[prefix+'__actual_aquifer_recharge_mm'][t]
            assert np.all(charge+z[prefix+'__actual_infiltration_mm'][t]<=a['infiltration_rate']*days+1e-9)
            assert np.all(z[prefix+'__actual_aquifer_mm'][t]<=a['aquifer_capacity_mm']+1e-9)
        if case%10==0:
            assert not a['aquifer_capacity_mm'].any()
            assert not z[prefix+'__actual_aquifer_mm'].any() and not z[prefix+'__actual_capillary_rise_mm'].any()
    assert steps==4680==r['synthetic_field_steps'] and r['exact_zero_groundwater_cases']==10
    spec=json.loads((ROOT/'calibration/paid_groundwater_20261114/demo_spec.json').read_text())
    assert spec['profile']==dict(theta_fc=.25,theta_wp=.1,root_depth_m=1,evaporation_depth_m=.1,rew_mm=9)
    assert spec['crop_kcb']==.75 and spec['efficiency']==1 and spec['bare_background']==.15
    demo_refs={}
    for case in spec['cases']:
        prefix=case['id'];a=inputs(z,prefix);flood=spec['flood_steps'];nt=flood+spec['crop_steps']
        assert np.all(a['initial_5stocks']==0) and np.all(a['dt']==spec['step_days'])
        assert a['area_m2'][0]==spec['area_m2'] and len(a['area_m2'])==1
        np.testing.assert_array_equal(a['pond_mask'][:,0],np.arange(nt)<flood)
        np.testing.assert_array_equal(a['crop_mask'],~a['pond_mask'])
        np.testing.assert_array_equal(a['capture_mask'],a['pond_mask'])
        np.testing.assert_array_equal(a['recharge_mask'],a['pond_mask'])
        assert np.all(a['permission'][:flood]==0) and np.all(a['permission'][flood:]==case['crop_permission_mm_day'])
        assert np.all(a['aquifer_capacity_mm']==case['aquifer_capacity_mm']) and np.all(a['recharge_rate']==case['recharge_mm_day'])
        assert np.all(a['source_m3'][:flood]==spec['source_flood_m3_per_step']) and np.all(a['source_m3'][flood:]==spec['source_crop_m3_per_step'])
        assert np.all(a['rain_mm']==spec['rain_mm_per_step']) and np.all(a['eto_mm_day']==spec['eto_mm_day'])
        assert np.all(a['pond_capacity_mm']==spec['pond_capacity_mm']) and np.all(a['infiltration_rate']==spec['infiltration_mm_day'])
        ref,final,mass,joint=scalar_groundwater(a);demo_refs[prefix]=ref
        for name,value in ref.items():np.testing.assert_allclose(z[prefix+'__'+name],value,atol=2e-10,rtol=2e-11)
        row=next(v for v in r['demonstrations'] if v['case']==prefix)
        for key,flux in [('recharge_mm','aquifer_recharge_mm'),('capillary_mm','capillary_rise_mm'),('root_uptake_mm','root_uptake_mm'),('root_potential_mm','root_potential_mm'),('river_delivered_m3','river_delivered_m3'),('aquifer_loss_mm','aquifer_loss_mm')]:
            assert abs(row[key]-float(ref[flux].sum()))<1e-9
        assert abs(row['final_aquifer_mm']-final[4,0])<1e-9
        initial=np.zeros((5,1))
        for year in range(1,51):
            periodic,next_state,_,_=scalar_groundwater(a,initial=initial)
            residual=float(np.max(np.abs(next_state-initial)))
            if residual<=1e-6:break
            initial=next_state
        assert year==row['periodic_cycles'] and residual<=1e-6
        for name,value in periodic.items():np.testing.assert_allclose(z[prefix+'__periodic_'+name],value,atol=2e-10,rtol=2e-11)
        np.testing.assert_allclose(z[prefix+'__periodic_initial'],initial,atol=2e-10,rtol=2e-11)
    csv_rows=0
    with (OUT/'demonstrations.csv').open() as file:
        for row in csv.DictReader(file):
            case=row['case'];t=int(row['step']);ref=demo_refs[case]
            assert abs(float(row['day_end'])-(t+1)*spec['step_days'])<1e-12
            for name in STOCKS+FIELD_FLUXES+RIVER:assert abs(float(row[name])-ref[name][t,0])<2e-10
            csv_rows+=1
    assert csv_rows==180
    finite=demo_refs['finite_groundwater'];stored=demo_refs['stored_no_permission']
    assert finite['aquifer_mm'].max()>0 and finite['aquifer_mm'][-1,0]==0
    assert not stored['capillary_rise_mm'].any() and stored['aquifer_mm'][-1,0]>0
    fresh={}
    for name in ['results.json','synthetic.npz','demonstrations.csv']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name;fresh[name]=sha(OUT/name)
    assert not r['earth_fields_scored'] and not r['adopt']
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),scalar_sha256=sha(ROOT/'scripts/groundwater_scalar.py'),results_sha256=sha(OUT/'results.json'),method='Independent scalar soil/pond/forest and groundwater phases; new component and producer not imported; every saved history, shared infiltration/capacity bound, demo input/output, periodic state and CSV cell checked',synthetic_forests=100,synthetic_field_steps=steps,synthetic_history_cells=cells,max_history_numeric_error=maxerror,max_scalar_field_mass_residual_mm=maxfield,max_scalar_joint_mass_residual_m3=maxjoint,demonstrations=3,demo_csv_rows=csv_rows,fresh_byte_exact=fresh,protected_files=len(r['unchanged_sha256']),earth_fields_scored=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Reviewed100forests;',cells,'history cells;three demos and their five-stock periodic cycles;three fresh files byte-exact')


if __name__=='__main__':main()
