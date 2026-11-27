"""Exactly two native source checks for the unfitted southern-belt correction."""
from dataclasses import asdict
import argparse
import fcntl
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT)]
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
PLAN=ROOT/'calibration/southern_zonal_belts_fix_20261127/plan.json'
OUT=ROOT/'output/southern_zonal_belts_fix_20261127'
MODEL=OUT/'model'


def check(plan):
    for section in ['model_sources_sha256','execution_sources_sha256','inputs_sha256']:
        for name,digest in plan[section].items():
            assert file_hash(ROOT/name)==digest,name
    for name,digest in plan['private_files_sha256'].items():
        f=MODEL/name
        assert not f.is_symlink() and f.stat().st_nlink==1 and file_hash(f)==digest,name
    for name,version in plan['libraries'].items():
        assert importlib.metadata.version(name)==version
    for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
        assert os.environ.get(name)=='1'
    assert os.getpriority(os.PRIO_PROCESS,0)>=10


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run',action='store_true')
    args=ap.parse_args()
    plan=json.loads(PLAN.read_text())
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert len(plan['cases'])==plan['maximum_integrations']==2
    lock=(OUT/'.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    assert not (OUT/'failure.json').exists(),'Preserve failure; no automatic retry'
    if not args.run:
        assert not (OUT/'preparation.json').exists()
        for name,digest in plan['private_files_sha256'].items():
            origin=ROOT if name in plan['model_sources_sha256'] or name in plan['helper_sources_sha256'] else ROOT/plan['cache_origin']
            assert file_hash(origin/name)==digest,name
            target=MODEL/name
            assert not target.exists()
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(origin/name,target)
        (OUT/'.gitignore').write_text('model/\n.lock\nstatus.json\nrun.log\n')
    else:
        assert not (OUT/'results.json').exists()
    check(plan)
    assert not any(n=='rotclimate' or n.startswith('rotclimate.') for n in sys.modules)
    sys.path[:0]=[str(MODEL/'scripts'),str(MODEL)]
    import benchmark_local as benchmark
    from rotclimate import earth,model as physical
    from rotclimate.config import Params
    from rotclimate.koppen import monthly_stats
    assert Path(physical.__file__).resolve().is_relative_to(MODEL.resolve())
    assert Path(benchmark.__file__).resolve().is_relative_to(MODEL.resolve())
    assert earth.CACHE.resolve().is_relative_to(MODEL.resolve())
    specs=json.loads((ROOT/plan['region_specs']).read_text())
    earth.REGIONS.update(specs)
    params=Params.from_json(ROOT/plan['params'])
    assert params.wind_source==params.sst_source=='model'
    assert params.t_require_convergence and params.moisture_require_convergence and params.solver_require_convergence
    assert params.moisture_residual_tol==.01
    if not args.run:
        actual={}
        for s in plan['cases']:
            actual[s['name']]=case_hash(earth.region_case(s['region'],56.,s['pad_km']))
            assert actual[s['name']]==s['case_identity']
            assert json.loads((ROOT/s['control_protocol']).read_text())['params']==json.loads(json.dumps(asdict(params)))
        freeze(OUT/'preparation.json',dict(plan_sha256=file_hash(PLAN),actual_case_identities=actual,integrations=0))
        print('Prepared two actual input identities; zero integrations',flush=True)
        return
    assert json.loads((OUT/'preparation.json').read_text())['plan_sha256']==file_hash(PLAN)
    freeze(OUT/'protocol.json',dict(plan_sha256=file_hash(PLAN),preparation_sha256=file_hash(OUT/'preparation.json'),
        execution_sources_sha256=plan['execution_sources_sha256']))
    rows=[]
    for s in plan['cases']:
        check(plan)
        name=s['region']
        folder=OUT/s['name']
        for sub in ['cells','cases','attempts']:
            (folder/sub).mkdir(parents=True,exist_ok=True)
        identity=freeze(folder/'protocol.json',dict(params=asdict(params),regions=[name],region_specs={name:specs[name]},
            cell_km=56.,pad_km=s['pad_km'],sources=plan['benchmark_protocol_sources_sha256'],
            note='Unfitted source correction: southern extra-tropical background belts; ordinary-domain arrays must be exact, wider-domain changed fields reported.'))
        record=folder/'cases'/(name+'.json')
        capture=folder/'cells'/(name+'_winds.npz')
        attempt=folder/'attempts'/(name+'.json')
        if record.exists():
            row=json.loads(record.read_text())
            assert row['status']=='passed' and row['numerics']['all_checks_passed']
            assert row['identity']==identity and row['case_identity']==s['case_identity']
            assert file_hash(folder/'cells'/(name+'.npz'))==row['cells_sha256']
            assert file_hash(capture)==row['wind_capture_sha256']
            rows.append(dict(name=s['name'],**row))
            continue
        assert not attempt.exists(),'Preserve interrupted integration; record recovery separately'
        freeze(attempt,dict(spec=s,protocol_sha256=file_hash(folder/'protocol.json'),campaign_protocol_sha256=file_hash(OUT/'protocol.json')))
        write_json(OUT/'status.json',dict(stage='integrating',completed=len(rows),total=2,name=s['name']))
        case=earth.region_case(name,56.,s['pad_km'])
        assert case_hash(case)==s['case_identity']
        with np.load(ROOT/s['control_cells']) as z:
            ii,jj=z['i'].copy(),z['j'].copy()
        original_run=physical.ClimateModel.run
        def recorded_run(self,*a,**kw):
            result=original_run(self,*a,**kw)
            if result.numerics['all_checks_passed']:
                active=[]
                for d in result.days:
                    season=self.season_index(float(d),self.p.circulation_lag_days)
                    edge=-(self.p.hadley_edge-self.p.hadley_shift*season)*self.hadley_scale
                    active.append(int((self.lat<min(edge,0.)).sum()))
                fields=dict(days=result.days,full_lat=self.lat.copy(),full_lon=case.lon.copy(),
                    raw_u=result.u,raw_v=result.v,active_cells_per_step=np.asarray(active),i=ii,j=jj,
                    lat=self.lat[ii,jj],lon=case.lon[ii,jj])
                for k in ['u','v']:
                    fields[k]=monthly_stats(getattr(result,k),getattr(result,k),result.days,result.params.year_days)['Tm'][:,ii,jj]
                np.savez_compressed(capture,**fields)
            return result
        physical.ClimateModel.run=recorded_run
        try:
            row=benchmark.one((name,asdict(params),56.,str(folder),specs,identity,s['pad_km']))
        except BaseException as error:
            write_json(OUT/'failure.json',dict(name=s['name'],exception=repr(error),automatic_retry=False))
            raise
        finally:
            physical.ClimateModel.run=original_run
        if row['status']!='passed' or row['numerics']['all_checks_passed'] is not True:
            write_json(OUT/'failure.json',dict(name=s['name'],record=row,automatic_retry=False))
            raise RuntimeError('Original numerical criteria failed; stop')
        assert row['case_identity']==s['case_identity']
        row['wind_capture_sha256']=file_hash(capture)
        write_json(record,row)
        if s['must_be_exact']:
            with np.load(folder/'cells'/(name+'.npz')) as new,np.load(ROOT/s['control_cells']) as old:
                assert set(new)==set(old)
                for k in old:
                    assert new[k].shape==old[k].shape and new[k].dtype==old[k].dtype and new[k].tobytes()==old[k].tobytes(),k
        write_json(folder/'summary.json',dict(complete=True,identity=identity,regions={name:row},
            cell_km=56.,pad_km=s['pad_km'],all=benchmark.group_means({name:row},[name])))
        rows.append(dict(name=s['name'],**row))
        print('Southern-belt source check:',s['name'],'passed original numerics',flush=True)
    check(plan)
    write_json(OUT/'results.json',dict(status='completed_two_fixed_southern_belt_source_checks',rows=rows,integrations=2,
        protocol_sha256=file_hash(OUT/'protocol.json'),atlas_changed=False))
    subprocess.run([str(ROOT/'.venv/bin/python'),'-I',str(ROOT/'scripts/review_southern_belts_source_checks.py')],cwd=ROOT,check=True)
    write_json(OUT/'status.json',dict(stage='ready_for_agent_review',completed=2))


if __name__=='__main__':
    main()
