"""Fixed development-only probes beyond the former calibration search bounds."""
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
from screen_fitted_flux import publication_files
from validate_r42_multistart import paired_score


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True)
    a=ap.parse_args();plan=json.loads(a.plan.read_text());out=ROOT/plan['output'];out.mkdir(parents=True,exist_ok=True)
    lock=(out/'.study.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    marker=out/'status.json'
    if marker.exists() and json.loads(marker.read_text()).get('stage')=='finished_pushed':return
    if subprocess.check_output(['git','show','HEAD:'+str(a.plan.resolve().relative_to(ROOT))],cwd=ROOT)!=a.plan.read_bytes():
        raise ValueError('Commit the prospective declaration first')
    freeze(out/'plan.json',plan);model=ROOT/plan['model_root']
    def status(stage,**extra):
        from datetime import datetime,timezone
        row=dict(stage=stage,updated_utc=datetime.now(timezone.utc).isoformat(),**extra)
        write_json(marker,row);print(json.dumps(row),flush=True)
    def check():
        if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!=plan['branch']:
            raise ValueError('Publication branch changed')
        if subprocess.check_output(['git','rev-parse','HEAD'],cwd=model,text=True).strip()!=plan['model_commit']:
            raise ValueError('Pinned model changed')
        for n,h in plan['sources'].items():
            if file_hash(ROOT/n)!=h:raise ValueError('Declared screen input changed: '+n)
        if any(importlib.metadata.version(n)!=v for n,v in plan['libraries'].items()):
            raise ValueError('Scientific libraries changed')
    try:
        status('waiting_for_fitted_screen');deadline=time.monotonic()+43200
        while True:
            path=ROOT/plan['after_status'];current=json.loads(path.read_text()) if path.exists() else {}
            if current.get('stage')=='finished_pushed':break
            if current.get('stage')=='failed' or time.monotonic()>deadline:raise RuntimeError('Dependency failed or timed out')
            time.sleep(15)
        check();reference=ROOT/plan['reference']
        if (json.loads((reference.parent/'result.json').read_text())['outcome']!='screen_complete'
                or not json.loads((reference.parent/'default_control.json').read_text())['passes']):
            raise ValueError('The source-pinned fresh r43 control did not qualify')
        ref=json.loads((reference/'summary.json').read_text());protocol=json.loads((reference/'protocol.json').read_text())
        if not ref.get('complete') or set(ref['regions'])!=set(plan['regions']):raise ValueError('Incomplete control')
        if protocol['params']!=json.loads((ROOT/plan['reference_params']).read_text()):raise ValueError('Different reference params')
        if protocol['cell_km']!=56. or set(protocol['regions'])!=set(plan['regions']):raise ValueError('Different reference footprint')
        for n,h in protocol['sources'].items():
            if file_hash(model/n)!=h:raise ValueError('Reference source changed: '+n)
        for n,row in ref['regions'].items():
            if file_hash(reference/'cells'/(n+'.npz'))!=row['cells_sha256']:raise ValueError('Reference packet changed')
        freeze(out/'reference_receipt.json',dict(protocol_sha256=file_hash(reference/'protocol.json'),
            summary_sha256=file_hash(reference/'summary.json'),source=plan['reference'],sources=protocol['sources']))
        scores={}
        for name,params in plan['profiles'].items():
            check();status('running',profile=name);folder=out/name
            with (out/(name+'.log')).open('a') as stream:
                process=subprocess.run([str(ROOT/'.venv/bin/python'),'-u','-I','scripts/benchmark_local.py',
                    '--fit',str(ROOT/params),'--regions',*plan['regions'],'--region-specs',str(ROOT/plan['region_specs']),
                    '--workers','1','--cell-km','56','--out',str(folder)],cwd=model,
                    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'),stdout=stream,stderr=subprocess.STDOUT)
            check();own=json.loads((folder/'protocol.json').read_text());summary=json.loads((folder/'summary.json').read_text())
            for n,h in protocol['sources'].items():
                if file_hash(model/n)!=h:raise ValueError('Pinned source changed during integration: '+n)
            if own['sources']!=protocol['sources'] or own['region_specs']!=protocol['region_specs']:
                raise ValueError('Profile changed sources/footprint')
            if set(summary['regions'])!=set(plan['regions']):raise ValueError('Missing case')
            if process.returncode not in (0,1):raise RuntimeError('Unexpected benchmark failure')
            for n,row in summary['regions'].items():
                if row['status']=='passed' and file_hash(folder/'cells'/(n+'.npz'))!=row['cells_sha256']:
                    raise ValueError('Changed profile packet')
            score=paired_score(ref['regions'],summary['regions'],plan['regions']) if summary.get('complete') else None
            scores[name]=dict(status='complete' if score else 'failed',score=score)
        write_json(out/'result.json',dict(adoption=False,sealed_run=False,selected=None,
            profiles=scores,scope=plan['policy']))
        names=[str(p.relative_to(ROOT)) for p in publication_files(out)]
        subprocess.run(['git','add','-f','--',*names],cwd=ROOT,check=True,capture_output=True)
        if subprocess.run(['git','diff','--cached','--quiet','--',*names],cwd=ROOT).returncode:
            subprocess.run(['git','commit','--only','-m','Record all fixed calibration-bound probes on reused development regions','--',*names],cwd=ROOT,check=True,capture_output=True)
        commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
        with (out/'push.log').open('a') as stream:
            subprocess.run(['git','push','--atomic',plan['remote'],*[commit+':'+r for r in plan['push_refs']]],
                cwd=ROOT,check=True,stdout=stream,stderr=subprocess.STDOUT)
        status('finished_pushed',commit=commit,scores=scores)
    except Exception as error:
        status('failed',error=repr(error));raise


if __name__=='__main__':main()
