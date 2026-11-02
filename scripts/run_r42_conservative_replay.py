"""Queue a conservative-transport replay after the r42 atlas is verified/pushed.

Uses existing production opt-in mechanisms, with new prospective parameters;
never adopts physics or changes an atlas. Every failed case is retained.
"""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import json
import os
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,freeze,write_json

PREFIX='output/r42_conservative_replay_20261102/'


def publish_results(root, files):
    names=[str(p.resolve().relative_to(root.resolve())) for p in files]
    if not names or any(not n.startswith(PREFIX) for n in names):
        raise ValueError('Refusing unrelated experiment artifacts')
    subprocess.run(['git','add','-f','--',*names],cwd=root,check=True,capture_output=True)
    subprocess.run(['git','commit','--only','-m','Record conservative r42 replay controls and all completed outcomes','--',*names],cwd=root,check=True,capture_output=True)
    return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()


def numerical_drift(reference, candidate, out, limits):
    import numpy as np
    rows={}
    for name, r in reference.items():
        folder=r['reference']
        expected=json.loads((ROOT/folder/'summary.json').read_text())['regions'][name]
        if candidate['regions'][name]['case_identity']!=expected['case_identity']:
            raise ValueError('Numerical control forcing identity differs: '+name)
        with np.load(ROOT/folder/'cells'/f'{name}.npz') as a, np.load(out/'cells'/f'{name}.npz') as b:
            for key in ('i','j','To','Po','lat','lon','elev','elev_max','coast_km'):
                if not np.array_equal(a[key],b[key]):raise ValueError('Numerical control inputs differ: '+name)
            rows[name]=dict(max_T_c=float(np.max(np.abs(a['Ts']-b['Ts']))),
                            max_P_mm_month=float(np.max(np.abs(a['Ps']-b['Ps']))))
    return dict(regions=rows,passes=all(r['max_T_c']<=limits['max_T_c'] and r['max_P_mm_month']<=limits['max_P_mm_month'] for r in rows.values()))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--workers',type=int,default=1);a=ap.parse_args()
    if a.workers<1:ap.error('workers must be positive')
    plan=json.loads(a.plan.read_text());a.out.mkdir(parents=True,exist_ok=True)
    if subprocess.check_output(['git','show','HEAD:'+str(a.plan.resolve().relative_to(ROOT))],cwd=ROOT)!=a.plan.read_bytes():raise ValueError('Commit the prospective declaration first')
    freeze(a.out/'protocol.json',plan)
    def status(stage,**fields):
        row=dict(stage=stage,updated_utc=datetime.now(timezone.utc).isoformat(),**fields);write_json(a.out/'status.json',row);print(json.dumps(row),flush=True)
    prior=a.out/'status.json'
    if prior.exists() and json.loads(prior.read_text()).get('stage')=='finished_pushed':return
    try:
        status('waiting_for_r42_atlas_publication');deadline=time.monotonic()+plan['timeout_s']
        while True:
            marker=ROOT/plan['after_status']
            if marker.exists():
                current=json.loads(marker.read_text())
                if current.get('stage')=='finished_pushed':break
                if current.get('stage')=='failed':raise RuntimeError('Atlas publication failed; physics queue remains unstarted')
            if time.monotonic()>deadline:raise RuntimeError('Timed out waiting for atlas publication')
            time.sleep(15)
        for name,digest in plan['sources'].items():
            if file_hash(ROOT/name)!=digest:raise ValueError('Frozen replay input changed: '+name)
        if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!=plan['branch']:raise ValueError('Replay branch changed')
        from dataclasses import asdict
        from earth_benchmark import load_params
        base=load_params(ROOT/plan['params']);completed={};numeric=None
        for profile,overrides in plan['profiles'].items():
            for name,digest in plan['sources'].items():
                if file_hash(ROOT/name)!=digest:raise ValueError('Frozen replay input changed: '+name)
            folder=a.out/profile;folder.mkdir(exist_ok=True);params=folder/'params.json'
            content=json.dumps(asdict(base.replace(**overrides)),indent=2)+'\n'
            if params.exists() and params.read_text()!=content:raise ValueError('Retain changed profile inputs in another output')
            params.write_text(content);status('running_profile',profile=profile)
            command=[sys.executable,'-u','-I','scripts/benchmark_local.py','--fit',str(params),'--regions',*plan['regions'],
                     '--region-specs',plan['region_specs'],'--workers',str(a.workers),'--out',str(folder)]
            with (a.out/(profile+'.log')).open('a') as log:
                result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,
                                      env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1'))
            if not (folder/'summary.json').exists():raise RuntimeError('Infrastructure interruption before profile summary: '+profile)
            summary=json.loads((folder/'summary.json').read_text())
            for name,digest in plan['sources'].items():
                if file_hash(ROOT/name)!=digest:raise ValueError('Replay source changed during integration: '+name)
            if set(summary['regions'])!=set(plan['regions']):raise ValueError('Missing declared cases')
            for name,spec in plan['regions'].items():
                expected=json.loads((ROOT/spec['reference']/'summary.json').read_text())['regions'][name]
                if summary['regions'][name]['case_identity']!=expected['case_identity']:
                    raise ValueError('Profile forcing identity differs: '+name)
            if result.returncode and summary.get('complete'):raise RuntimeError('Unexpected profile process failure')
            completed[profile]=summary
            if profile=='reference_damped':
                if not summary['complete']:
                    numeric=dict(passes=False,reason='Numerical control failed strict checks')
                else:numeric=numerical_drift(plan['regions'],summary,folder,plan['control_drift'])
                write_json(a.out/'numerical_control.json',numeric)
                if not numeric['passes']:break
        def means(summary):
            if not summary.get('complete'):return None
            rows=list(summary['regions'].values())
            return [sum(r['temperature']['monthly_mae_C'] for r in rows)/len(rows),sum(r['rain']['loss'] for r in rows)/len(rows)]
        ref=means(completed['reference_damped']);ratios={}
        for name,summary in completed.items():
            value=means(summary)
            ratios[name]=None if not ref or not value else dict(T=value[0]/ref[0],P=value[1]/ref[1],S=.5*(value[0]/ref[0]+value[1]/ref[1]))
        result=dict(stage='screen_complete' if numeric['passes'] else 'stopped_at_numerical_control',
                    adoption=False,numerical_control=numeric,profiles=completed,ratios_vs_damped=ratios,
                    planned_new_regional_integrations=40,completed_profiles=len(completed),
                    note='Eight reused development regions; no full49/fine/sealed qualification or wind/SST validation. No partial-case aggregate scores. Existing r42 remains adopted.')
        write_json(a.out/'results.json',result);status('committing_results',result=result['stage'])
        files=[p for p in a.out.rglob('*') if p.is_file() and p.suffix in {'.json','.npz','.log'} and p.name not in ('status.json','push.log')]
        commit=publish_results(ROOT,files);status('committed_pushing',commit=commit)
        with (a.out/'push.log').open('w') as log:subprocess.run(['git','push',plan['remote'],commit+':'+plan['push_ref']],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        status('finished_pushed',commit=commit,result=result['stage'])
    except Exception as error:
        status('failed',error=repr(error));raise


if __name__=='__main__':main()
