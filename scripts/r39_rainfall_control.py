"""Reproduce qualified r39, retaining raw fields for Gregorian footprint scoring."""
from pathlib import Path
import argparse,json,subprocess,sys,traceback
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import case_hash,file_hash,write_json
from rotclimate import earth
from rotclimate.config import Params
from rotclimate.koppen import monthly_stats


def run(path,out,preflight=False):
    plan=json.loads(path.read_text())
    for n,h in plan['sources'].items():assert file_hash(ROOT/n)==h,n
    p=Params.from_json(ROOT/plan['physics']);region=plan['region'];earth.REGIONS[region]=plan['region_spec'];case=earth.region_case(region,plan['cell_km']);identity=case_hash(case,observed_sea=p.sst_source=='observed')
    if not (p.t_require_convergence and p.moisture_require_convergence and p.solver_require_convergence and p.moisture_residual_tol>0):raise ValueError('Need the strict qualified r39 numerical settings')
    prior=json.loads((ROOT/plan['archived_case']).read_text());assert identity==prior['case_identity'],'Changed archived r39 case inputs'
    with np.load(ROOT/plan['archived_cells']) as f:archive={k:f[k] for k in f.files}
    assert file_hash(ROOT/plan['archived_cells'])==prior['cells_sha256']
    np.testing.assert_array_equal(case.grid.lat[archive['i'],archive['j']],archive['lat']);np.testing.assert_array_equal(case.lon[archive['i'],archive['j']],archive['lon'])
    if preflight:
        print(json.dumps(dict(status='r39_input_identity_verified_no_integration',region=region,actual_legacy_integrations_started=0,shape=list(case.grid.land.shape),archived_case_identity=identity,literal_plan_sha256=file_hash(path)),indent=2));return
    if subprocess.check_output(['git','show','HEAD:'+str(path.resolve().relative_to(ROOT))],cwd=ROOT)!=path.read_bytes():raise ValueError('Commit literal r39 control before integrating')
    if out.exists() and any(out.iterdir()):raise ValueError('Retain previous r39 controls')
    out.mkdir(parents=True,exist_ok=True);write_json(out/'frozen_plan.json',plan);write_json(out/'progress.json',dict(actual_legacy_integrations_started=1,region=region));res=None
    row=dict(region=region,actual_legacy_integrations_started=1,new_prototype_integrations=0,legacy_benchmark_attempts_added=1,legacy_strict_passes_added=0,climate_run_completed=False,qualified_r39_reproduced=False)
    try:
        res=earth.run_case(p,case,steps=p.steps_per_year);finite=bool(np.isfinite(res.T).all() and np.isfinite(res.P).all() and np.min(res.P)>=0);numerical=res.numerics.get('all_checks_passed') is True
        pr=res.params;st=monthly_stats(res.T,res.P,res.days,pr.year_days,summer_solstice=pr.winter_solstice_day+pr.year_days/2);i,j=archive['i'],archive['j']
        exact=dict(temperature=st['Tm'][:,i,j].astype(np.float32).tobytes()==archive['Ts'].tobytes(),rain=np.maximum(st['Pm'][:,i,j],0).astype(np.float32).tobytes()==archive['Ps'].tobytes())
        fields=out/'raw.npz';np.savez_compressed(fields,temperature=res.T,rain_rate=res.P,days=res.days,observed_rain=case.obs_P,observed_temperature=case.obs_T,latitude=case.grid.lat,longitude=case.lon,land=case.grid.land,inmap=case.grid.inmap,elevation=case.grid.elev,coast_km=case.coast_km)
        row.update(climate_run_completed=finite,qualified_r39_reproduced=bool(finite and numerical and all(exact.values())),archived_float32_monthly_exact=exact,numerics=res.numerics,fields_sha256=file_hash(fields),actual_planet=dict(tilt_deg=pr.tilt,retrograde=pr.retrograde,year_days=pr.year_days,winter_solstice_day=pr.winter_solstice_day,planet_radius_earth=pr.planet_radius),raw_units=dict(temperature='degC',rain_rate='mm/day'))
        row['legacy_strict_passes_added']=int(row['qualified_r39_reproduced'])
    except Exception as error:row.update(error=repr(error),traceback=traceback.format_exc(),numerics=getattr(res,'numerics',None))
    row.update(status='passed' if row['qualified_r39_reproduced'] else 'failed',literal_plan_sha256=file_hash(path),case_identity=identity,physics_adoption=False,recalibration=False,scope='One new legacy Earth benchmark attempt; zero prototype integrations. Exact archived monthly reproduction required before quoting as qualified r39. Raw climate retained for separate Gregorian calendar/common-footprint rainfall evaluation; no observations nudge winds or humidity.')
    write_json(out/'verification.json',row);print(json.dumps({k:v for k,v in row.items() if k not in ['numerics','traceback']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--preflight',action='store_true');a=p.parse_args();run(a.plan,a.out,a.preflight)
