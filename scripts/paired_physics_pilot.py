"""Shared actual-model recorder for frozen small Earth physics comparisons."""
from pathlib import Path
from functools import lru_cache
from dataclasses import asdict
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from benchmark_local import DEV12_SPECS,temperature_metrics
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash,file_hash,write_json
from rainfall_metrics import local_metrics
from rotclimate import earth,joint
from rotclimate.koppen import monthly_stats,monthly_weights
from rotclimate.model import ClimateModel
from rotclimate.numerics import matrix_product


@lru_cache(maxsize=1)
def circulation_fields(plan_path):
    from circulation_reference import acquire
    return acquire(ROOT,json.loads((ROOT/plan_path).read_text()))[0]


def extra_circulation_diagnostics(case,params,model,result,plan,*,reference=False):
    """Audit new native vectors separately from historical climate NPZ fields."""
    from circulation_reference import diagnose_model
    report,native=diagnose_model(case,params,model,result,
        circulation_fields(plan['extra_circulation_reference_plan']))
    if reference:
        archive=ROOT/plan['extra_circulation_reference_archive']
        old_record=json.loads(archive.with_suffix('.json').read_text())
        if (old_record.get('status')!='passed'
                or old_record.get('numerics',{}).get('all_checks_passed') is not True
                or file_hash(archive)!=old_record.get('arrays_sha256')):
            raise ValueError('Invalid extra native circulation archive')
        with np.load(archive) as old:
            if not np.array_equal(native['circulation_model'],old['circulation_model']):
                raise ValueError('Exact extra native circulation control changed')
        report['legacy_exact']=True
    return report,native


def run_one(job):
    name,region,updates,plan,identity,out=job
    out=Path(out);folder=out/name;folder.mkdir(exist_ok=True)
    path,arrays=folder/f'{region}.json',folder/f'{region}.npz'
    extra_arrays=folder/f'{region}_extra.npz'
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    case=earth.region_case(region,float(plan['cell_km']))
    derived=case_hash(case,observed_sea=True)
    numerical_updates=plan.get('profile_numerics',{}).get(name,{})
    if path.exists():
        row=json.loads(path.read_text())
        if (row['identity']!=identity or row['case_identity']!=derived or row['status']!='passed'
                or row['name']!=name or row['region']!=region or row['updates']!=updates
                or row.get('numerical_updates',{})!=numerical_updates
                or row.get('numerics',{}).get('all_checks_passed') is not True
                or file_hash(arrays)!=row['arrays_sha256']):
            raise ValueError('Changed inputs or preserved failed pilot run: '+str(path))
        if region in plan.get('extra_circulation_regions',[]):
            if (not row.get('extra_circulation') or not extra_arrays.exists()
                    or file_hash(extra_arrays)!=row.get('extra_circulation_arrays_sha256')):
                raise ValueError('Changed or missing extra native circulation arrays: '+str(path))
        return row
    row=dict(name=name,region=region,updates=updates,numerical_updates=numerical_updates,identity=identity,case_identity=derived)
    started=time.monotonic()
    model=None
    try:
        theta=joint.update_block(load_params(ROOT/plan['physics']),'physics',updates)
        theta=joint.update_block(theta,'numerics',numerical_updates)
        p=earth.earth_params(joint.earth_profile(theta),case)
        row['params']=asdict(p)
        g=case.grid
        land=g.inmap & g.land & np.isfinite(case.obs_T).all(0) & np.isfinite(case.obs_P).all(0)
        domain=np.ones_like(g.land);domain[[0,-1],:]=False;domain[:,[0,-1]]=False
        sea=domain & ~g.land & np.isfinite(g.obs_sst).all(0) & (g.obs_sst.min(0)>-1)
        model=ClimateModel(p,grid=g);model.trace_cells=np.nonzero(domain)
        result=model.run(diagnose_moisture=True)
        row['numerics']=result.numerics
        if result.numerics.get('all_checks_passed') is not True:
            raise ValueError('Per-step solver or transport ledger failed')
        st=monthly_stats(result.T,result.P,result.days,p.year_days,
                         summer_solstice=p.winter_solstice_day+p.year_days/2)
        if name=='reference':
            if updates or numerical_updates:
                raise ValueError('Reference overrides are forbidden')
            archive=ROOT/plan['archive'];prior=json.loads((archive/'cases'/f'{region}.json').read_text())
            old_cells=archive/'cells'/f'{region}.npz'
            if case_hash(case)!=prior['case_identity'] or file_hash(old_cells)!=prior['cells_sha256']:
                raise ValueError('Archived control inputs changed')
            with np.load(old_cells) as old:
                for key,value in [('Ts',st['Tm'][:,land]),('Ps',st['Pm'][:,land]),
                                  ('To',case.obs_T[:,land]),('Po',case.obs_P[:,land])]:
                    if not np.array_equal(value.astype(np.float32),old[key]):
                        raise ValueError('Exact archived control changed: '+key)
        weights=monthly_weights(result.days,p.year_days)
        speed=np.stack([np.hypot(t['moisture_u'],t['moisture_v']) for t in model.trace])
        sst=matrix_product(weights,np.stack([t['SST'] for t in model.trace]))
        row['column_speed']=dict(maximum_ms=float(speed.max()),p95_ms=float(np.percentile(speed,95)))
        row['sst']=None
        if sea.any():
            error=sst[:,sea[domain]]-g.obs_sst[:,sea]
            row['sst']=dict(cells=int(sea.sum()),monthly_mae_C=float(np.abs(error).mean()))
        sl=g.map_slice()
        fields=dict(valid=land[sl],elev=g.elev[sl],observed=case.obs_P[(slice(None),)+sl],
                    simulated=st['Pm'][(slice(None),)+sl])
        if result.layer_water is not None:
            fields['layer_water']=matrix_product(weights,result.layer_water.reshape(len(result.days),-1)).reshape((12,)+result.layer_water.shape[1:])
            fields['column_water']=matrix_product(weights,result.W.reshape(len(result.days),-1)).reshape((12,)+result.W.shape[1:])
        for key,value in result.moisture_budget.items():
            fields[key]=matrix_product(weights,value.reshape(len(result.days),-1)).reshape((12,)+value.shape[1:])*p.year_days/12
        row['rain']=local_metrics(st['Pm'],np.nan_to_num(case.obs_P),land)
        if region in plan.get('circulation_regions',[]):
            from circulation_reference import diagnose_model
            row['circulation'],wind_fields=diagnose_model(case,p,model,result,
                circulation_fields(plan['circulation_reference_plan']))
            fields.update(wind_fields)
            if name=='reference':
                with np.load(ROOT/'output/circulation_audit_20261026'/f'{region}.npz') as old:
                    # Source changes may not alter the external audit control.
                    if not np.array_equal(wind_fields['circulation_model'],old['model_moisture']):
                        raise ValueError('Exact native circulation control changed')
                row['circulation']['legacy_exact']=True
        if region in plan.get('extra_circulation_regions',[]):
            row['extra_circulation'],extra_fields=extra_circulation_diagnostics(case,p,model,result,plan,
                reference=name=='reference')
            with extra_arrays.with_suffix('.tmp').open('wb') as stream:
                np.savez_compressed(stream,**extra_fields)
            extra_arrays.with_suffix('.tmp').replace(extra_arrays)
            row['extra_circulation_arrays_sha256']=file_hash(extra_arrays)
        row['temperature']=temperature_metrics(st['Tm'][:,land],case.obs_T[:,land])
        row['monthly_rain']=dict(simulated=st['Pm'][:,land].mean(1).tolist(),observed=case.obs_P[:,land].mean(1).tolist())
        control_archive=plan.get('profile_control_archives',{}).get(name)
        if control_archive:
            old_path=ROOT/control_archive/f'{region}.npz'
            old_record=json.loads(old_path.with_suffix('.json').read_text())
            if (old_record['status']!='passed' or not old_record['numerics']['all_checks_passed']
                    or file_hash(old_path)!=old_record['arrays_sha256']):
                raise ValueError('Invalid declared historical physical control')
            with np.load(old_path) as old:
                if set(old.files)!=set(fields):raise ValueError('Historical control field set changed')
                for key in old.files:
                    if not np.array_equal(fields[key],old[key],equal_nan=True):
                        raise ValueError('Historical physical control changed: '+key)
            row['physical_control_exact']=True
        with arrays.with_suffix('.tmp').open('wb') as stream:np.savez_compressed(stream,**fields)
        arrays.with_suffix('.tmp').replace(arrays)
        row.update(status='passed',params=asdict(p),numerics=result.numerics,legacy_exact=name=='reference',
                   arrays_sha256=file_hash(arrays))
    except Exception as error:
        row.update(status='failed',error=repr(error))
        if model is not None:
            residuals=getattr(model,'moisture_scaled_residual',[])
            row['partial_solver_diagnostics']=dict(
                heat_linear_unconverged=sum(not x for x in model.solver.converged),
                moisture_linear_unconverged=sum(not x for x in model.moisture_solver.converged),
                completed_moisture_steps=len(getattr(model,'moisture_converged',[])),
                last_scaled_moisture_residual=float(residuals[-1]) if residuals and residuals[-1] is not None else None)
    row['seconds']=time.monotonic()-started
    write_json(path,row)
    print(name+'/'+region+': '+row['status'],flush=True)
    return row
