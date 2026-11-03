"""Fixed reused-region fitted-flux screen; no tuning, sealed data or adoption."""
from pathlib import Path
import argparse
import fcntl
import importlib.metadata
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,freeze,write_json
from expand_storm_exchange import prepare_model
from run_r42_conservative_replay import numerical_drift
from validate_r42_multistart import paired_score


def publication_files(folder):
    """Keep pinned source worktrees and transient state out of result commits."""
    result=[]
    for parent,dirs,files in os.walk(folder):
        dirs[:]=[d for d in dirs if d not in {'model','.git'}]
        result += [Path(parent)/n for n in files if Path(n).suffix in {'.json','.npz','.log'}
                   and n not in {'status.json','push.log'}]
    return sorted(result)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True)
    a=ap.parse_args();plan=json.loads(a.plan.read_text());out=ROOT/plan['output'];out.mkdir(parents=True,exist_ok=True)
    lock=(out/'.screen.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    marker=out/'status.json'
    if marker.exists() and json.loads(marker.read_text()).get('stage')=='finished_pushed':return
    relative=str(a.plan.resolve().relative_to(ROOT))
    if subprocess.check_output(['git','show','HEAD:'+relative],cwd=ROOT)!=a.plan.read_bytes():
        raise ValueError('Commit the prospective screen declaration first')
    freeze(out/'plan.json',plan);model=prepare_model(plan)
    def status(stage,**extra):
        from datetime import datetime,timezone
        row=dict(stage=stage,updated_utc=datetime.now(timezone.utc).isoformat(),**extra)
        write_json(marker,row);print(json.dumps(row),flush=True)
    def check():
        if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!=plan['branch']:
            raise ValueError('Publication branch changed')
        if subprocess.check_output(['git','rev-parse','HEAD'],cwd=model,text=True).strip()!=plan['model_commit']:
            raise ValueError('Pinned model changed')
        for root,items in [(ROOT,plan['sources']),(model,plan['model_sources'])]:
            for n,h in items.items():
                if file_hash(root/n)!=h:raise ValueError('Frozen input changed: '+n)
        if any(importlib.metadata.version(n)!=v for n,v in plan['libraries'].items()):
            raise ValueError('Scientific libraries changed')
    def bench(label,params):
        check();status('running',profile=label)
        folder=out/label
        with (out/(label+'.log')).open('a') as stream:
            process=subprocess.run([str(ROOT/'.venv/bin/python'),'-u','-I','scripts/benchmark_local.py',
                '--fit',str(ROOT/params),'--regions',*plan['regions'],'--region-specs',str(ROOT/plan['region_specs']),
                '--workers','1','--cell-km','56','--out',str(folder)],cwd=model,
                env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),stdout=stream,stderr=subprocess.STDOUT)
        check();summary=json.loads((folder/'summary.json').read_text())
        if set(summary['regions'])!=set(plan['regions']):raise ValueError('Missing declared case')
        if process.returncode not in (0,1):raise RuntimeError('Unexpected benchmark failure')
        for n,row in summary['regions'].items():
            if row['status']=='passed' and file_hash(folder/'cells'/(n+'.npz'))!=row['cells_sha256']:
                raise ValueError('Raw packet changed')
        return summary
    try:
        status('waiting_for_atlas_publication');deadline=time.monotonic()+43200
        while True:
            path=ROOT/plan['after_status'];current=json.loads(path.read_text()) if path.exists() else {}
            if current.get('stage')=='finished_pushed':break
            if current.get('stage')=='failed' or time.monotonic()>deadline:
                raise RuntimeError('Atlas publication failed or timed out; screen has not integrated')
            time.sleep(15)
        control=bench('reference',plan['reference'])
        if not control.get('complete'):raise ValueError('Incomplete default-arithmetic control')
        drift=numerical_drift({n:dict(reference=plan['raw_reference']) for n in plan['regions']},control,
            out/'reference',dict(max_T_c=.01,max_P_mm_month=.05))
        write_json(out/'default_control.json',drift)
        result=dict(adoption=False,sealed_run=False,profiles={})
        if not drift['passes']:result['outcome']='stopped_at_default_control'
        else:
            packets={}
            for name,params in plan['profiles'].items():
                candidate=bench(name,params)
                if candidate.get('complete'):packets[name]=candidate['regions']
                score=paired_score(control['regions'],candidate['regions'],plan['regions']) if candidate.get('complete') else None
                result['profiles'][name]=dict(status='complete' if score else 'failed',score=score)
            if {'upwind_flux','fitted_flux'}<=set(packets):
                result['fitted_vs_upwind']=paired_score(packets['upwind_flux'],packets['fitted_flux'],plan['regions'])
            result['outcome']='screen_complete'
        result['scope']='Eight reused development regions; unchanged physical diffusivity and closures between the two flux operators. No global accuracy, sealed evaluation or adoption.'
        write_json(out/'result.json',result)
        check();names=[str(p.relative_to(ROOT)) for p in publication_files(out)]
        subprocess.run(['git','add','-f','--',*names],cwd=ROOT,check=True,capture_output=True)
        if subprocess.run(['git','diff','--cached','--quiet','--',*names],cwd=ROOT).returncode:
            subprocess.run(['git','commit','--only','-m','Record complete fitted versus upwind conservative vapor screen','--',*names],cwd=ROOT,check=True,capture_output=True)
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        with (out/'push.log').open('a') as stream:
            subprocess.run(['git','push','--atomic',plan['remote'],*[commit+':'+r for r in plan['push_refs']]],
                cwd=ROOT,check=True,stdout=stream,stderr=subprocess.STDOUT)
        status('finished_pushed',commit=commit,result=result)
    except Exception as error:
        status('failed',error=repr(error));raise


if __name__=='__main__':main()
