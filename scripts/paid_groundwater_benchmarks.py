"""Seeded forest histories and fixed synthetic finite-groundwater columns."""
import argparse
import csv
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.groundwater_fields import GroundwaterFieldState,groundwater_field_year,periodic_groundwater_fields
from harvest.river_fields import FieldState,field_year
from harvest.soil_drying import SoilState,soil_profile
from groundwater_scalar import scalar_groundwater,STOCKS,FIELD_FLUXES,RIVER
from settlement_locations_earth import sha,write

OUT=ROOT/'output/paid_groundwater_20261114'
PLAN=ROOT/'calibration/paid_groundwater_20261114/plan.json'
SPEC=PLAN.parent/'demo_spec.json'


def arguments(a):
    initial=a['initial_5stocks']
    clock=SimpleNamespace(step_days=a['dt'],river_order=a['order'],river_receiver=a['receiver'])
    return dict(profile=soil_profile(.25,.1,1.,.1,9.),area_m2=a['area_m2'],field_nodes=a['field_nodes'],source_m3=a['source_m3'],clock=clock,rain_mm=a['rain_mm'],eto_mm_day=a['eto_mm_day'],crop_mask=a['crop_mask'],capture_mask=a['capture_mask'],pond_mask=a['pond_mask'],crop_kcb=.75,pond_capacity_mm=a['pond_capacity_mm'],infiltration_mm_day=a['infiltration_rate'],efficiency=float(a['efficiency']),bare_background=float(a['background']),aquifer_capacity_mm=a['aquifer_capacity_mm'],capillary_permission_mm_day=a['permission'],recharge_mm_day=a['recharge_rate'],recharge_mask=a['recharge_mask'],aquifer_loss_mm_day=a['loss_rate'],initial=GroundwaterFieldState(SoilState(initial[0],initial[1],initial[2]),initial[3],initial[4]))


def demo_inputs(spec,case):
    flood=spec['flood_steps'];nt=flood+spec['crop_steps'];pond=np.arange(nt)[:,None]<flood
    return dict(dt=np.full(nt,spec['step_days']),order=np.array([0]),receiver=np.array([-1]),area_m2=np.array([spec['area_m2']],float),field_nodes=np.array([0]),source_m3=np.where(pond,spec['source_flood_m3_per_step'],spec['source_crop_m3_per_step']).astype(float),rain_mm=np.full((nt,1),spec['rain_mm_per_step'],float),eto_mm_day=np.full((nt,1),spec['eto_mm_day'],float),crop_mask=~pond,pond_mask=pond,capture_mask=pond,recharge_mask=pond,pond_capacity_mm=np.array([spec['pond_capacity_mm']],float),infiltration_rate=np.array([spec['infiltration_mm_day']],float),efficiency=np.array(spec['efficiency'],float),background=np.array(spec['bare_background'],float),aquifer_capacity_mm=np.array([case['aquifer_capacity_mm']],float),permission=np.where(pond,0.,case['crop_permission_mm_day']),recharge_rate=np.full((nt,1),case['recharge_mm_day'],float),loss_rate=np.full((nt,1),spec['aquifer_loss_mm_day'],float),initial_5stocks=np.zeros((5,1)))


def main(out):
    for path in [PLAN,SPEC]:assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()
    tests=['groundwater_fields','capillary_hydraulics','reference_forcing','reference_eto','crop_stage','rain_timing','river_fields','field_clock','soil_drying','flood_storage','flood_water','flood_timing','flood_gauge_quality']
    control=subprocess.run([sys.executable,'-m','pytest','-q',*[f'tests/test_{name}.py' for name in tests]],cwd=ROOT,capture_output=True,text=True,check=True)
    if out.resolve()==OUT.resolve():
        out.mkdir(parents=True,exist_ok=True);write(OUT/'controls.json',dict(status='passed_before_synthetic_outputs',producer_sha256=sha(Path(__file__)),stdout=control.stdout))
    assert (OUT/'controls.json').exists(),'Canonical controls required before fresh export'
    rng=np.random.default_rng(1411202603);arrays={};steps=0;maxerror=0.;maxfield=0.;maxjoint=0.;exact=0
    for case in range(100):
        nt=int(rng.integers(3,19));nf=int(rng.integers(1,9));nn=int(rng.integers(1,7))
        receiver=np.array([-1 if i==0 or rng.random()<.3 else int(rng.integers(0,i)) for i in range(nn)])
        pond=rng.random((nt,nf))<.5;capacity=rng.uniform(0,80,nf)
        if case%10==0:capacity[:]=0
        pondcap=rng.uniform(0,30,nf);initial=np.vstack([rng.random(nf)*15,rng.random(nf)*135,rng.random(nf)*5,rng.random(nf)*pondcap,rng.random(nf)*capacity])
        if case%2:initial[:]=0
        a=dict(dt=rng.uniform(.1,1,nt),order=np.arange(nn),receiver=receiver,area_m2=rng.uniform(100,5000,nf),field_nodes=rng.integers(0,nn,nf),source_m3=rng.uniform(0,25,(nt,nn)),rain_mm=rng.uniform(0,8,(nt,nf)),eto_mm_day=rng.uniform(0,7,(nt,nf)),crop_mask=(rng.random((nt,nf))<.5)&~pond,capture_mask=rng.random((nt,nf))<.7,pond_mask=pond,recharge_mask=rng.random((nt,nf))<.7,pond_capacity_mm=pondcap,infiltration_rate=rng.uniform(2,20,nf),efficiency=np.array(rng.uniform(.5,1)),background=np.array(rng.uniform(0,.3)),aquifer_capacity_mm=capacity,permission=rng.uniform(0,6,(nt,nf)),recharge_rate=rng.uniform(0,12,(nt,nf)),loss_rate=rng.uniform(0,1,(nt,nf)),initial_5stocks=initial)
        actual=groundwater_field_year(**arguments(a));reference,final,fieldmass,joint=scalar_groundwater(a)
        maxfield=max(maxfield,fieldmass);maxjoint=max(maxjoint,joint)
        for name,value in reference.items():
            error=float(np.max(np.abs(actual[name]-value)));maxerror=max(maxerror,error)
            np.testing.assert_allclose(actual[name],value,atol=2e-10,rtol=2e-11,err_msg=f'{case} {name}')
            arrays[f'{case:03}__actual_'+name]=actual[name]
        for name,value in a.items():arrays[f'{case:03}__input_'+name]=value
        if case%10==0:
            old_args=arguments(a)
            for key in ['aquifer_capacity_mm','capillary_permission_mm_day','recharge_mm_day','recharge_mask','aquifer_loss_mm_day']:old_args.pop(key)
            old_args['initial']=FieldState(old_args['initial'].soil,old_args['initial'].pond_mm)
            old=field_year(**old_args)
            for name,value in old.items():
                if name not in ['initial','final']:np.testing.assert_array_equal(actual[name],value,err_msg='Exact zero-groundwater '+name)
            exact+=1
        steps+=nt*nf
    spec=json.loads(SPEC.read_text());demo_rows=[];summary=[]
    for case in spec['cases']:
        a=demo_inputs(spec,case);kwargs=arguments(a);actual=groundwater_field_year(**kwargs);ref,final,fieldmass,joint=scalar_groundwater(a)
        for name,value in ref.items():np.testing.assert_allclose(actual[name],value,atol=2e-10,rtol=2e-11)
        for name,value in a.items():arrays[case['id']+'__input_'+name]=value
        for name in STOCKS+FIELD_FLUXES+RIVER:arrays[case['id']+'__'+name]=actual[name]
        for t in range(len(a['dt'])):demo_rows.append(dict(case=case['id'],step=t,day_end=float(a['dt'][:t+1].sum()),**{name:float(actual[name][t,0]) for name in STOCKS+FIELD_FLUXES+RIVER}))
        kwargs.pop('initial');periodic=periodic_groundwater_fields(**kwargs)
        assert periodic['periodic'],'Synthetic demo did not converge'
        summary.append(dict(case=case['id'],recharge_mm=float(actual['aquifer_recharge_mm'].sum()),capillary_mm=float(actual['capillary_rise_mm'].sum()),final_aquifer_mm=float(actual['aquifer_mm'][-1,0]),root_uptake_mm=float(actual['root_uptake_mm'].sum()),root_potential_mm=float(actual['root_potential_mm'].sum()),river_delivered_m3=float(actual['river_delivered_m3'].sum()),aquifer_loss_mm=float(actual['aquifer_loss_mm'].sum()),periodic_cycles=periodic['years'],periodic_residual_mm=periodic['periodic_residual_mm']))
        for name in STOCKS+FIELD_FLUXES+RIVER:arrays[case['id']+'__periodic_'+name]=periodic[name]
        arrays[case['id']+'__periodic_initial']=np.array([periodic['initial'][name] for name in STOCKS])
    base=ROOT/'output/capillary_hydraulics_20261114';prior=json.loads((base/'reference.json').read_text());protected=dict(prior['unchanged_sha256'])
    review=json.loads((base/'review.json').read_text())
    for name,digest in review['fresh_byte_exact'].items():protected[str((base/name).relative_to(ROOT))]=digest
    for name in ['review.json','controls.json']:protected[str((base/name).relative_to(ROOT))]=sha(base/name)
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'synthetic.npz',**arrays)
    with (out/'demonstrations.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(demo_rows[0]));writer.writeheader();writer.writerows(demo_rows)
    paths=[Path(__file__),ROOT/'harvest/groundwater_fields.py',ROOT/'tests/test_groundwater_fields.py',ROOT/'scripts/groundwater_scalar.py',ROOT/'scripts/audit_river_fields.py',ROOT/'harvest/river_fields.py',ROOT/'harvest/soil_drying.py',ROOT/'harvest/flood_water.py',PLAN,SPEC]
    write(out/'results.json',dict(status='synthetic_finite_groundwater_budget_only',controls_sha256=sha(OUT/'controls.json'),synthetic_forests=100,synthetic_field_steps=steps,exact_zero_groundwater_cases=exact,max_history_numeric_error=maxerror,max_scalar_field_mass_residual_mm=maxfield,max_scalar_joint_mass_residual_m3=maxjoint,demonstrations=summary,producers={str(p.relative_to(ROOT)):sha(p) for p in paths},files_sha256={name:sha(out/name) for name in ['synthetic.npz','demonstrations.csv']},unchanged_sha256=protected,earth_fields_scored=False,adopt=False))
    print(control.stdout.strip());print('Passed100synthetic forests;',steps,'fieldsteps;10exact legacy cases;max history error',maxerror)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,default=OUT)
    main(parser.parse_args().out)
