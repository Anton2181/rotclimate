"""Resume the declared W18c budget; select on development only, then gate once."""
import json
import os
from pathlib import Path
import subprocess
import sys

# Keep the small cloud computer's BLAS jobs from oversubscribing its region workers.
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
import ppe as P
from local_benchmark_protocol import file_hash, write_json

PLAN=ROOT/'calibration/ppe_20261123/plan_W18c.json'
AMENDMENT=ROOT/'calibration/ppe_20261123/W18c_runtime_amendment.json'
QUALIFICATION=ROOT/'output/climate_runtime_20261126/qualification.json'


def readiness():
    q=json.loads(QUALIFICATION.read_text())
    assert q['status']=='passed_fresh_paired_r58_reference_historical_replay_not_exact'
    for section in ['sources_sha256','reference_protocols_sha256','shared_inputs_sha256']:
        for n,h in q[section].items():
            path=ROOT/n
            if section=='reference_protocols_sha256':path=path/'protocol.json'
            assert file_hash(path)==h,n
    for path in [PLAN,AMENDMENT]:
        assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()


def state(out,stage,**more):
    write_json(out/'campaign_status.json',dict(stage=stage,plan_sha256=file_hash(PLAN),
        runtime_amendment_sha256=file_hash(AMENDMENT),runtime_qualification_sha256=file_hash(QUALIFICATION),
        supervisor_sha256=file_hash(Path(__file__)),**more))
    print(stage,more,flush=True)


def ranking(plan,out):
    results,names,_,Y,ref=P.training(plan,out)
    values=P.objective(plan,*P.gate_terms(Y,ref,names,P.t_names_of(plan)))
    i=int(np.argmin(values))
    return results[i],float(values[i])


def evaluate_pending(plan,out):
    done={r['name'] for r in P.read_results(out)};base=P.base_params(plan)
    for point in P.read_design(out):
        if point['name'] in done:continue
        readiness();params={**base,**point['x']};name=point['name']
        state(out,'evaluating_development',candidate=name,wave=point['wave'],completed=len(done))
        try:
            P.R.evaluate(name,params)
            row=dict(name=name,wave=point['wave'],x=point['x'],regions=P.region_values(name),ok=True)
        except Exception as error:
            row=dict(name=name,wave=point['wave'],x=point['x'],ok=False,error=repr(error)[:1000])
        with (out/'results.jsonl').open('a') as stream:stream.write(json.dumps(row)+'\n')
        done.add(name)
        if not row['ok'] and name=='w1_base':
            state(out,'base_failed_investigate_before_remaining_budget',error=row['error'])
            raise RuntimeError('Base failed; inspect regional summaries before proceeding')


def benchmark(params,destination,regions,cell=56.,spec=None):
    command=[sys.executable,'-I',str(ROOT/'scripts/benchmark_local.py'),'--fit',str(params),
             '--workers','3','--cell-km',str(cell),'--out',str(destination),'--regions',*regions]
    if spec:command+=['--region-specs',str(ROOT/spec)]
    subprocess.run(command,cwd=ROOT,check=True)


def gate(stage,folder,extra=()):
    command=[sys.executable,'-I',str(ROOT/'scripts/gate_v3.py'),stage,str(folder),'r58',*extra]
    result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
    (folder/f'gate_{stage}.log').write_text(result.stdout+result.stderr)
    assert result.returncode in [0,1],result.stderr
    record=json.loads((folder/f'v3_{stage}.json').read_text())
    assert record['passes']==(result.returncode==0)
    print('gate',stage,record['passes'],flush=True)
    return record['passes']


def validate(plan,out):
    best,objective=ranking(plan,out);folder=out/'runs'/best['name']
    params=folder/'candidate_params.json';frozen=out/'finalist.json'
    candidate=dict(name=best['name'],dev_objective=objective,params_sha256=file_hash(params),
                   selection='lowest_development_objective_only',plan_sha256=file_hash(PLAN))
    if frozen.exists():assert json.loads(frozen.read_text())==candidate
    else:write_json(frozen,candidate)
    state(out,'finalist_frozen',**candidate)
    if not gate('dev6',folder):
        state(out,'closed_development_gate_failed',candidate=best['name'],atlas_changed=False);return
    readiness()
    ref=ROOT/plan['reference'];r58=ROOT/'calibration/local_accuracy_20261023/r58_params.json'
    fine=['california','western_europe','japan','new_zealand']
    state(out,'fine_resolution_gate',candidate=best['name'])
    benchmark(r58,ref/'r58_fine28',fine,cell=28.)
    link=folder/'r58_fine28'
    if not link.exists():link.symlink_to((ref/'r58_fine28').resolve())
    benchmark(params,folder/'candidate_fine28',fine,cell=28.)
    if not gate('fine',folder):
        state(out,'closed_fine_gate_failed',candidate=best['name'],sealed_AA_opened=False,atlas_changed=False);return
    declaration=ROOT/'calibration/sealed_20261126AA/declaration.json'
    declared=json.loads(declaration.read_text());label='W18c/'+best['name']
    if declared['outcome']=='UNOPENED':
        assert not declared['seen_by']
        declared['seen_by']=[label];declared['outcome']='IN_PROGRESS'
        declared['reference']='fresh paired r58; W18c_runtime_amendment.json'
        write_json(declaration,declared)
    else:assert declared['seen_by']==[label], 'AA was opened for another candidate'
    spec='calibration/sealed_20261126AA/regions.json';regions=list(json.loads((ROOT/spec).read_text()))
    state(out,'single_sealed_AA_pair',candidate=best['name'])
    benchmark(r58,ref/'r58_sealed_AA',regions,spec=spec)
    link=folder/'r58_sealed_AA'
    if not link.exists():link.symlink_to((ref/'r58_sealed_AA').resolve())
    benchmark(params,folder/'candidate_sealed_AA',regions,spec=spec)
    passed=gate('sealed5',folder,['sealed_AA'])
    declared['outcome']='SPENT; '+('PASS' if passed else 'FAIL')
    write_json(declaration,declared)
    state(out,'all_gates_passed_ready_for_review' if passed else 'closed_sealed_gate_failed',
          candidate=best['name'],adopted=False,atlas_changed=False)


def main():
    readiness();plan,out=P.load_plan(PLAN)
    status=out/'campaign_status.json'
    if status.exists():
        previous=json.loads(status.read_text())
        if previous['stage']=='base_failed_investigate_before_remaining_budget':
            raise RuntimeError('Investigate the failed base before resuming the remaining budget')
        if previous['stage'].startswith('closed_') or previous['stage']=='all_gates_passed_ready_for_review':
            print('Completed campaign preserved:',previous['stage']);return
    if not P.read_design(out):P.design(plan,out)
    while True:
        points=P.read_design(out);done={r['name'] for r in P.read_results(out)}
        wave=max(p['wave'] for p in points);pending=[p for p in points if p['name'] not in done]
        # A published proposal contains its prediction; recovery never needs a second batch.
        if wave>1 and pending and not any(p['name'] in done for p in points if p['wave']==wave):
            _,observed=ranking(plan,out);predicted=min(p['predicted_objective'] for p in pending)
            gain=observed-predicted
            decision=dict(after_wave=wave-1,observed_best=observed,predicted_best=predicted,
                          predicted_gain=gain,continue_search=bool(gain>=.005))
            write_json(out/f'wave_{wave-1}_decision.json',decision)
            if gain<.005:
                state(out,'search_closed_predicted_gain_below_0.005',**decision);break
        evaluate_pending(plan,out)
        if wave==3:
            state(out,'search_closed_at_three_waves');break
        state(out,'fitting_emulators_and_publishing_one_proposal',after_wave=wave)
        P.propose(plan,out,16)
    validate(plan,out)


if __name__=='__main__':main()
