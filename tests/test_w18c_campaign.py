"""The continuation budget and withheld-data gates must survive interruptions."""
import json

import pytest

from scripts import run_w18c_campaign as C


def harness(monkeypatch,tmp_path,*,gain=.01,initial_wave=1):
    points=[dict(name=f'w1_{i}',wave=1) for i in range(49)]
    results=[] if initial_wave==1 else [dict(name=p['name'],ok=True) for p in points]
    if initial_wave==2:
        points.extend(dict(name=f'w2_{i}',wave=2,predicted_objective=1-gain) for i in range(16))
    events=[]
    monkeypatch.setattr(C,'readiness',lambda:None)
    monkeypatch.setattr(C,'state',lambda out,stage,**kw:events.append(('state',stage)))
    monkeypatch.setattr(C.P,'load_plan',lambda path:({},tmp_path))
    monkeypatch.setattr(C.P,'read_design',lambda out:points)
    monkeypatch.setattr(C.P,'read_results',lambda out:results)
    monkeypatch.setattr(C,'ranking',lambda plan,out:({},1.))
    monkeypatch.setattr(C,'validate',lambda plan,out:events.append(('validate',)))
    def evaluate(plan,out):
        pending=[p for p in points if p['name'] not in {r['name'] for r in results}]
        events.append(('evaluate',len(pending)))
        results.extend(dict(name=p['name'],ok=True) for p in pending)
    def propose(plan,out,k):
        events.append(('propose',k));wave=max(p['wave'] for p in points)+1
        points.extend(dict(name=f'w{wave}_{i}',wave=wave,predicted_objective=1-gain) for i in range(k))
    monkeypatch.setattr(C,'evaluate_pending',evaluate);monkeypatch.setattr(C.P,'propose',propose)
    return events,results


def test_small_predicted_gain_does_not_spend_another_wave(monkeypatch,tmp_path):
    events,results=harness(monkeypatch,tmp_path,gain=.004)
    C.main()
    assert len(results)==49
    assert events.count(('propose',16))==1 and events.count(('validate',))==1


def test_continuation_cannot_exceed_81_evaluations(monkeypatch,tmp_path):
    events,results=harness(monkeypatch,tmp_path,gain=.02)
    C.main()
    assert len(results)==81 and events.count(('propose',16))==2
    assert events.count(('validate',))==1


def test_resume_of_unspent_proposal_checks_stopping_before_evaluation(monkeypatch,tmp_path):
    events,results=harness(monkeypatch,tmp_path,gain=.002,initial_wave=2)
    C.main()
    assert len(results)==49 and not any(e[0] in ['evaluate','propose'] for e in events)
    assert events.count(('validate',))==1


def test_closed_fine_failure_cannot_restart_search(monkeypatch,tmp_path):
    events,_=harness(monkeypatch,tmp_path)
    (tmp_path/'campaign_status.json').write_text(json.dumps(dict(stage='closed_fine_gate_failed')))
    C.main()
    assert not events


@pytest.mark.parametrize('development_passes',[False,True])
def test_sealed_data_is_never_reached_after_development_or_fine_failure(monkeypatch,tmp_path,development_passes):
    folder=tmp_path/'runs/best';folder.mkdir(parents=True)
    (folder/'candidate_params.json').write_text('{}')
    events=[]
    monkeypatch.setattr(C,'ROOT',tmp_path)
    monkeypatch.setattr(C,'PLAN',folder/'candidate_params.json')
    monkeypatch.setattr(C,'ranking',lambda plan,out:(dict(name='best'),.98))
    monkeypatch.setattr(C,'readiness',lambda:None)
    monkeypatch.setattr(C,'state',lambda out,stage,**kw:events.append(stage))
    monkeypatch.setattr(C,'benchmark',lambda *a,**kw:None)
    monkeypatch.setattr(C,'gate',lambda stage,*a,**kw:development_passes if stage=='dev6' else False)
    # No AA declaration exists in this fixture: any attempt to open it fails.
    C.validate(dict(reference='reference'),tmp_path)
    assert events[-1]==('closed_fine_gate_failed' if development_passes else 'closed_development_gate_failed')
    assert not (tmp_path/'calibration/sealed_20261126AA').exists()
