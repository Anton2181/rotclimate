"""Capture e91 land exchange directly; preserve the failed original diagnostics."""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
os.environ.setdefault('OPENBLAS_NUM_THREADS','1')
import csv
import inspect
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate import earth,moisture
from rotclimate.model import ClimateModel
from rotclimate.koppen import monthly_stats,monthly_weights
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
from somalia_transport_trace import COMPONENTS

ORIGINAL=ROOT/'output/somalia_transport_trace_20261126'
PARENT=ROOT/'output/somalia_mechanism_20261126'
OUT=ROOT/'output/somalia_marine_exchange_trace_20261126'
PLAN=ROOT/'calibration/somalia_transport_trace_20261126/marine_exchange_followup.json'


def marine_exchange(rate,target,water):
    """Signed humidity relaxation in mm/day; includes import AND removal."""
    return np.asarray(rate)*(np.asarray(target)-np.asarray(water))*86400.


def main():
    assert not (OUT/'results.json').exists(),'Preserve completed correction'
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    before=json.loads((ORIGINAL/'results.json').read_text())
    for n,h in before['sources_sha256'].items():assert file_hash(ROOT/n)==h,n
    for n,h in before['files_sha256'].items():assert file_hash(ORIGINAL/n)==h,n
    sources={**before['sources_sha256'],str(PLAN.relative_to(ROOT)):file_hash(PLAN),
             str(Path(__file__).relative_to(ROOT)):file_hash(Path(__file__)),
             str((ORIGINAL/'results.json').relative_to(ROOT)):file_hash(ORIGINAL/'results.json')}
    specs={}
    for n in ['calibration/sealed_20261123S18/regions.json','calibration/sealed_20261124U18/regions.json']:
        specs.update(json.loads((ROOT/n).read_text()))
    earth.REGIONS.update({r['region']:specs[r['region']] for r in before['rows']})
    base=load_params(ROOT/'calibration/local_accuracy_20261023/r58_params.json')
    assert base.ocean_sink==1.,'Exact capture assumes the frozen r58 ocean_sink=1'
    OUT.mkdir(parents=True,exist_ok=True);freeze(OUT/'preparation.json',dict(sources_sha256=sources,additional_replays=3))
    rows=[];table=[];files={};signature=inspect.signature(moisture.solve_moisture)
    for old in before['rows']:
        region,variant=old['region'],old['variant'];folder=OUT/region/variant;folder.mkdir(parents=True,exist_ok=True)
        receipt=folder/'result.json';packet=folder/'capture.npz'
        if receipt.exists():
            row=json.loads(receipt.read_text());assert row['capture_sha256']==file_hash(packet)
        else:
            case=earth.region_case(region,56.,1100.);assert case_hash(case)==old['case_identity']
            with np.load(ORIGINAL/region/variant/'trace.npz') as z:previous=dict(z)
            ii,jj=previous['rows'],previous['cols'];assert case.grid.land[ii,jj].all()
            p=earth.earth_params(base.replace(**old['overrides']),case);model=ClimateModel(p,grid=case.grid)
            model.trace_cells=(ii,jj);captured=[];original=moisture.solve_moisture
            def capture(*args,**kwargs):
                call=signature.bind(*args,**kwargs);call.apply_defaults();a=call.arguments
                assert a['p'].ocean_sink==1.
                solution=original(*args,**kwargs);W=solution.water
                marine=marine_exchange(a['lamE'],a['ocean_water'],W)
                net=marine+np.broadcast_to(a['land_source'],W.shape)*86400.
                if a['sink'] is not None:net=net-a['sink']*W*86400.
                if a['gain'] is not None:net=net+a['gain']*W*86400.
                captured.append(dict(marine=marine[ii,jj].copy(),net_source=net[ii,jj].copy(),
                                     rain=solution.rain[ii,jj].copy(),global_scaled_residual=solution.scaled_residual))
                return solution
            moisture.solve_moisture=capture
            try:result=model.run(diagnose_moisture=True)
            finally:moisture.solve_moisture=original
            assert result.numerics['all_checks_passed']
            args=dict(year_days=p.year_days,summer_solstice=p.winter_solstice_day+p.year_days/2)
            st=monthly_stats(result.T,result.P,result.days,**args);full=dict(T=st['Tm'],P=np.maximum(st['Pm'],0))
            for k in ['E','W','u','v']:
                st=monthly_stats(getattr(result,k),getattr(result,k),result.days,**args);full[k]=st['Pm' if k=='E' else 'Tm']
            with np.load(PARENT/region/variant/'fields.npz') as baseline:
                for k,v in full.items():np.testing.assert_array_equal(v,baseline[k])
                crop_mask=baseline['mask'][case.grid.map_slice()]
            for k,v in result.moisture_budget.items():np.testing.assert_array_equal(v[:,crop_mask],previous['budget__'+k])
            order=np.argsort([r['day'] for r in model.trace]);records=captured[-len(model.trace):]
            days=np.array([model.trace[i]['day'] for i in order]);np.testing.assert_array_equal(days,previous['days'])
            c={k:np.stack([records[i][k] for i in order]) for k in ['marine','net_source','rain','global_scaled_residual']}
            for k in ['P','E','W','u','v']:
                raw=np.stack([model.trace[i][k] for i in order]);np.testing.assert_array_equal(raw,previous['trace__'+k])
            np.testing.assert_array_equal(c['rain'].astype(np.float32),previous['rain_mm_day'])
            corrected=sum(previous['budget__'+k].astype(float) for k in COMPONENTS)+c['marine']-c['rain']
            total_scale=np.maximum(c['rain']+np.abs(c['net_source']),.1)
            rounding=4*np.finfo(np.float32).eps*sum(np.abs(previous['budget__'+k].astype(float)) for k in COMPONENTS)+1e-8
            np.testing.assert_array_less(np.abs(corrected-(previous['budget__residual']+c['marine'])),rounding+1e-7)
            scaled=np.abs(corrected)/total_scale
            assert np.all(scaled<=c['global_scaled_residual'][:,None]+rounding/total_scale+1e-8)
            assert np.all(scaled<=p.moisture_residual_tol+rounding/total_scale+1e-8)
            c.update(days=days,corrected_residual=corrected,corrected_scaled_residual=scaled,
                     original_residual=previous['budget__residual'],production_scale=total_scale)
            np.savez_compressed(packet,**c)
            weights=monthly_weights(days,p.year_days);months=[]
            for m in range(12):
                mean=lambda a:float((weights[m]@a.astype(float)).mean())
                months.append(dict(month=m+1,marine_exchange_mm=mean(c['marine'])*p.year_days/12,
                    original_residual_mm=mean(previous['budget__residual'])*p.year_days/12,
                    original_absolute_residual_mm=mean(np.abs(previous['budget__residual']))*p.year_days/12,
                    corrected_residual_mm=mean(corrected)*p.year_days/12,
                    corrected_absolute_residual_mm=mean(np.abs(corrected))*p.year_days/12))
            row=dict(region=region,variant=variant,capture_sha256=file_hash(packet),months=months,
                full_physical_arrays_exact=True,original_trace_and_budget_exact=True,numeric_certificate=result.numerics,
                marine_exchange_annual_mm=sum(r['marine_exchange_mm'] for r in months),
                corrected_absolute_residual_annual_mm=sum(r['corrected_absolute_residual_mm'] for r in months),
                max_corrected_scaled_residual=float(scaled.max()),existing_equation_tolerance=p.moisture_residual_tol,
                max_global_solver_certificate=float(c['global_scaled_residual'].max()),
                closure_corroborated=True,global_conservation_claim=False)
            write_json(receipt,row)
        rows.append(row);table.extend(dict(region=region,variant=variant,**m) for m in row['months'])
        for path in [receipt,packet]:files[str(path.relative_to(OUT))]=file_hash(path)
        print(region,variant,'marine annual',row['marine_exchange_annual_mm'],'max residual',row['max_corrected_scaled_residual'],flush=True)
    with (OUT/'months.csv').open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(table[0]));w.writeheader();w.writerows(table)
    files['months.csv']=file_hash(OUT/'months.csv')
    for n,h in sources.items():assert file_hash(ROOT/n)==h,n
    write_json(OUT/'results.json',dict(status='captured_omitted_marine_exchange_local_equations_close',
        sources_sha256=sources,files_sha256=files,rows=rows,additional_integrations=3,total_instrumented_replays=6,
        exact_physical_replays=3,climate_adopted=False,original_failed_checks_preserved=True,
        core_diagnostic_patch_deferred_until_W18c_closed=True,global_conservative_budget=False))


if __name__=='__main__':main()
