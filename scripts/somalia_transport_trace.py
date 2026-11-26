"""Replay three completed cases with existing trace and local-equation hooks."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate import earth
from rotclimate.model import ClimateModel
from rotclimate.koppen import monthly_stats,monthly_weights
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json

PLAN=ROOT/'calibration/somalia_transport_trace_20261126/plan.json'
OUT=ROOT/'output/somalia_transport_trace_20261126'
PARENT=ROOT/'output/somalia_mechanism_20261126'
COMPONENTS=['advection','diffusion','storm_exchange','evaporation','column_drying','convergence_import']


def main():
    assert not (OUT/'results.json').exists(),'Keep completed trace'
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    plan=json.loads(PLAN.read_text());assert len(plan['runs'])==3
    parent=json.loads((PARENT/'qualification.json').read_text())
    for n,h in parent['sources_sha256'].items():assert file_hash(ROOT/n)==h,n
    for n,h in parent['files_sha256'].items():assert file_hash(PARENT/n)==h,n
    specs={};paths=[PLAN,Path(__file__),PARENT/'qualification.json',ROOT/'scripts/local_benchmark_protocol.py',ROOT/'scripts/earth_benchmark.py']
    for n in ['calibration/sealed_20261123S18/regions.json','calibration/sealed_20261124U18/regions.json']:
        p=ROOT/n;paths.append(p);specs.update(json.loads(p.read_text()))
    earth.REGIONS.update({n:specs[n] for n in {r['region'] for r in plan['runs']}})
    params=ROOT/'calibration/local_accuracy_20261023/r58_params.json';paths.append(params)
    paths.extend(sorted((ROOT/'rotclimate').glob('*.py')))
    runtime=json.loads((ROOT/'output/climate_runtime_20261126/qualification.json').read_text())
    paths.extend(ROOT/n for n in runtime['shared_inputs_sha256'])
    for run in plan['runs']:
        paths.extend([PARENT/run['region']/run['variant']/name for name in ['fields.npz','result.json']])
    sources={str(p.relative_to(ROOT)):file_hash(p) for p in paths}
    OUT.mkdir(parents=True,exist_ok=True)
    freeze(OUT/'preparation.json',dict(plan=plan,sources_sha256=sources))
    base=load_params(params);rows=[];monthly_rows=[];files={}
    for run in plan['runs']:
        region,variant=run['region'],run['variant'];folder=OUT/region/variant;folder.mkdir(parents=True,exist_ok=True)
        receipt=folder/'result.json';packet=folder/'trace.npz'
        if receipt.exists():
            row=json.loads(receipt.read_text());assert row['trace_sha256']==file_hash(packet)
        else:
            case=earth.region_case(region,56.,1100.);identity=case_hash(case)
            previous=json.loads((PARENT/region/variant/'result.json').read_text())
            assert identity==previous['case_identity'] and run['overrides']==previous['overrides']
            p=earth.earth_params(base.replace(**run['overrides']),case)
            mask=case.grid.inmap&case.grid.land&np.isfinite(case.obs_T).all(0)&np.isfinite(case.obs_P).all(0)
            ii,jj=np.nonzero(mask);model=ClimateModel(p,grid=case.grid);model.trace_cells=(ii,jj)
            result=model.run(diagnose_moisture=True)
            assert result.numerics['all_checks_passed']
            args=dict(year_days=p.year_days,summer_solstice=p.winter_solstice_day+p.year_days/2)
            stats=monthly_stats(result.T,result.P,result.days,**args)
            full=dict(T=stats['Tm'],P=np.maximum(stats['Pm'],0))
            for key in ['E','W','u','v']:
                st=monthly_stats(getattr(result,key),getattr(result,key),result.days,**args)
                full[key]=st['Pm' if key=='E' else 'Tm']
            with np.load(PARENT/region/variant/'fields.npz') as old:
                for key in full:np.testing.assert_array_equal(full[key],old[key])
                np.testing.assert_array_equal(mask,old['mask'])
            trace=sorted(model.trace,key=lambda r:r['day'])
            days=np.array([r['day'] for r in trace]);np.testing.assert_array_equal(days,result.days)
            assert len(days)==25 and len(np.unique(days))==25
            arrays={'days':days,'rows':ii,'cols':jj}
            for key in trace[0]:
                if key!='day':arrays['trace__'+key]=np.stack([r[key] for r in trace])
            for key in ['P','E','W','u','v']:
                np.testing.assert_array_equal(arrays['trace__'+key].astype(np.float32),getattr(result,key)[:,ii,jj])
            crop_mask=mask[case.grid.map_slice()]
            for key,field in result.moisture_budget.items():arrays['budget__'+key]=field[:,crop_mask]
            arrays['rain_mm_day']=result.P[:,ii,jj]
            reconstructed=sum(arrays['budget__'+k].astype(float) for k in COMPONENTS)-arrays['rain_mm_day']
            stored=arrays['budget__residual'].astype(float)
            export_error=float(np.max(np.abs(reconstructed-stored)))
            # Eight float32 exports can accumulate rounding near cancellation.
            rounding=np.finfo(np.float32).eps*sum(np.abs(arrays['budget__'+k].astype(float)) for k in COMPONENTS)
            rounding+=np.finfo(np.float32).eps*(np.abs(arrays['rain_mm_day'])+np.abs(stored))
            assert np.all(np.abs(reconstructed-stored)<=4*rounding+1e-8)
            np.savez_compressed(packet,**arrays)
            weights=monthly_weights(result.days,p.year_days);months=[]
            for m in range(12):
                values={key:float((weights[m]@value.astype(float)).mean()) for key,value in arrays.items()
                        if key.startswith(('trace__','budget__'))}
                for k in list(values):
                    if k.startswith('budget__') or k in ['trace__P','trace__E']:values[k]*=p.year_days/12
                values['rain_mm']=float((weights[m]@arrays['rain_mm_day'].astype(float)).mean()*p.year_days/12)
                months.append(dict(month=m+1,**values))
            annual={k:sum(x['budget__'+k] for x in months) for k in COMPONENTS+['residual','absolute_residual','monsoon_drying']}
            rain=sum(x['rain_mm'] for x in months)
            scaled=arrays['budget__absolute_residual']/np.maximum(arrays['rain_mm_day']+np.abs(arrays['budget__evaporation']),.1)
            row=dict(region=region,variant=variant,case_identity=identity,overrides=run['overrides'],
                numeric_certificate=result.numerics,physical_monthly_arrays_exact=True,days_joined_exactly=True,
                traced_steps=25,traced_scored_cells=len(ii),trace_sha256=file_hash(packet),months=months,
                annual_local_equation_mm=annual,annual_rain_mm=rain,
                annual_absolute_residual_over_rain=float(annual['absolute_residual']/rain),
                max_step_scaled_residual=float(scaled.max()),existing_equation_tolerance=p.moisture_residual_tol,
                closure_corroborated=bool(scaled.max()<=p.moisture_residual_tol),
                float32_component_reconstruction_max_error_mm_day=export_error,
                conservative_boundary_flux_claim=False)
            write_json(receipt,row)
        rows.append(row);monthly_rows.extend(dict(region=region,variant=variant,**r) for r in row['months'])
        for path in [receipt,packet]:files[str(path.relative_to(OUT))]=file_hash(path)
        print(region,variant,'annual local equation',row['annual_local_equation_mm'],flush=True)
    with (OUT/'months.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(monthly_rows[0]));writer.writeheader();writer.writerows(monthly_rows)
    files['months.csv']=file_hash(OUT/'months.csv')
    for n,h in sources.items():assert file_hash(ROOT/n)==h,n
    write_json(OUT/'results.json',dict(status='completed_three_instrumented_moisture_replays',
        sources_sha256=sources,files_sha256=files,rows=rows,integrations=3,new_parameter_settings=0,
        exact_physical_replays=3,all_local_equation_checks=all(r['closure_corroborated'] for r in rows),
        global_conservative_budget=False,climate_adopted=False,sealed_AA_opened_by_this_diagnostic=False))


if __name__=='__main__':main()
