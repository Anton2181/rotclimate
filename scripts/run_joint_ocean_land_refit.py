"""Run equal-budget ocean/land starts in resumable, interleaved stages."""
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from local_benchmark_protocol import file_hash,freeze,write_json


def records(folder):
    path=folder/'evals.jsonl'
    return [json.loads(s) for s in path.read_text().splitlines()] if path.exists() else []


def main():
    campaign_path=ROOT/'calibration/joint_ocean_land_20261110/campaign.json'
    campaign=json.loads(campaign_path.read_text());out=ROOT/'output/joint_ocean_land_20261110'
    for name,digest in {**campaign['reference_sha256'],**campaign['source_knobs_sha256']}.items():
        if file_hash(ROOT/name)!=digest:raise ValueError('Changed campaign input: '+name)
    inputs=[campaign_path,Path(__file__),*[ROOT/p for p in campaign['starts'].values()]]
    identity=freeze(out/'driver_identity.json',dict(inputs_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in inputs}))
    env=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')
    for limit in campaign['budget']['phases']:
        for name,plan in campaign['starts'].items():
            folder=out/name;folder.mkdir(exist_ok=True)
            while len(records(folder))<limit:
                before=len(records(folder))
                write_json(out/'status.json',dict(status='running',identity=identity,phase=limit,start=name,
                    completed_evaluations={n:len(records(out/n)) for n in campaign['starts']}))
                command=[sys.executable,'-u','-I',str(ROOT/'scripts/gate_calibrate.py'),'--plan',str(ROOT/plan),
                    '--out',str(folder),'--workers','3','--through-eval',str(limit),'--hours','1.9']
                if (folder/'state.pkl').exists():command.append('--resume')
                print('==',name,'through',limit,flush=True)
                with (out/(name+'.log')).open('a') as log:
                    process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
                    for line in process.stdout:
                        log.write(line);log.flush();print(name,line.rstrip(),flush=True)
                    code=process.wait()
                if code or len(records(folder))<=before:
                    write_json(out/'status.json',dict(status='blocked',identity=identity,phase=limit,start=name,exit_code=code))
                    raise RuntimeError('Search did not advance: '+name)
    result={name:dict(evaluations=len(records(out/name)),best=min(records(out/name),key=lambda r:r['cost'])) for name in campaign['starts']}
    assert all(r['evaluations']==campaign['budget']['per_start'] for r in result.values())
    write_json(out/'summary.json',dict(status='completed_development_search',identity=identity,starts=result,
        adopted='r44',fresh_independent_validation=False))
    write_json(out/'status.json',dict(status='completed',identity=identity,
        completed_evaluations={n:r['evaluations'] for n,r in result.items()}))


if __name__=='__main__':main()
