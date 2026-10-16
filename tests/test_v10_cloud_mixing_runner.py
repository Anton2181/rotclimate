"""Staged expansion, source guards, time limits and same-command resume."""
import json
from pathlib import Path
import numpy as np
import pytest
from scripts import check_v10_cloud_mixing as r
from rotclimate_v10.earth import atomic_json,sha256


def test_fixed_plan_controls_screen_repeat_numerics_and_prerequisites():
    jobs=r.make_jobs({'california':None,'iberia':None})
    assert len(jobs)==52 and len({j['key'] for j in jobs})==52
    assert [sum(j['phase']==phase for j in jobs) for phase in ('control','screen','repeat','numerics')]==[4,4,32,12]
    assert all(j['phase']=='control' for j in jobs[:4]) and all(j['phase']=='screen' for j in jobs[4:8])
    assert {j['seed'] for j in jobs if j['phase']=='repeat'}=={67,103,149,211}
    assert all(j['time_factor']==.5 for j in jobs if j['phase']=='numerics')
    assert {j['mode'] for j in jobs if j['phase']=='numerics'}=={'bulk','parcel_lower','parcel_all'}


def fake_row(folder,gain=10.,settled=True,thermal=True):
    folder.mkdir(parents=True,exist_ok=True);atomic_json(folder/'config.json',{'toy':True})
    (folder/'year1.npz').write_bytes(b'toy-evidence')
    row={'settling':{'passed':settled},'guards':{'lower_temperature':thermal,'upper_temperature':thermal},
        'coastal_winter_gain_mm':gain,'monthly_mae_change_mm':-1.,'response':{'coast_winter_mm':30.},
        'uppermost_subgrid_rain_fraction':0.,'case_config_sha256':sha256(folder/'config.json'),
        'evidence_sha256':{'year1.npz':sha256(folder/'year1.npz')}}
    atomic_json(folder/'summary.json',row);return row


def fixture(tmp_path,monkeypatch):
    jobs=r.make_jobs({'california':None,'iberia':None})[:8]
    jobs.append({'key':'repeat_one','phase':'repeat'})
    protocol={'code_sha256':r.source_id(),'jobs':jobs,'screen_gate':{'minimum_coastal_winter_gain_mm_each_strong_lift_region':5.}}
    monkeypatch.setattr(r,'prepare',lambda:(protocol,{},None,{},{}))
    prepared=tmp_path/'prepared';atomic_json(prepared/'manifest.json',{'protocol':protocol});monkeypatch.setattr(r,'PREFLIGHT',prepared)
    return protocol


def test_smoke_then_overnight_resumes_without_repeating(tmp_path,monkeypatch):
    fixture(tmp_path,monkeypatch);calls=[]
    def case(folder,job,*args):calls.append(job['key']);return fake_row(folder)
    out=tmp_path/'result';state=r.batch(out,stage='smoke',case_runner=case)
    assert state['status']=='smoke_complete' and len(calls)==8 and state['screen_gate']['passed']
    state=r.batch(out,stage='overnight',case_runner=case)
    assert state['status']=='complete' and len(calls)==9 and len(state['invocations'])==2
    (out/'cases'/calls[0]/'year1.npz').write_bytes(b'changed')
    assert r.batch(out,case_runner=case)['status']=='needs_diagnosis'


@pytest.mark.parametrize('gain,settled,thermal',[(4.,True,True),(10.,False,True),(10.,True,False)])
def test_failed_screen_prevents_expansion(gain,settled,thermal,tmp_path,monkeypatch):
    fixture(tmp_path,monkeypatch);calls=[]
    def case(folder,job,*args):calls.append(job['key']);return fake_row(folder,gain,settled,thermal)
    state=r.batch(tmp_path/'result',case_runner=case)
    assert state['status']=='screen_complete_no_expansion' and not state['screen_gate']['passed']
    assert len(calls)==8


def test_budget_stop_resume_and_stale_preflight(tmp_path,monkeypatch):
    protocol=fixture(tmp_path,monkeypatch);calls=[]
    def case(folder,job,*args):
        calls.append(job['key'])
        if len(calls)==3:raise r.model.base.BudgetStop()
        return fake_row(folder)
    out=tmp_path/'result'
    assert r.batch(out,case_runner=case)['status']=='budget_reached'
    state=r.batch(out,case_runner=case)
    assert state['status']=='complete' and len(calls)==10
    protocol['changed']=True
    with pytest.raises(ValueError,match='stale'):r.batch(tmp_path/'other')


def test_deadline_prevents_integration(tmp_path,monkeypatch):
    fixture(tmp_path,monkeypatch);ticks=[0.]
    def clock():result=ticks[0];ticks[0]=40000.;return result
    state=r.batch(tmp_path/'result',case_runner=lambda *a:pytest.fail('No time'),clock=clock)
    assert state['status']=='budget_reached' and not state['cases']


@pytest.mark.parametrize('hours',[0.,-1.,10.1,np.inf,np.nan])
def test_invalid_budget_rejected_before_prepare(hours,tmp_path,monkeypatch):
    monkeypatch.setattr(r,'prepare',lambda:pytest.fail('Bad budget'))
    with pytest.raises(ValueError,match='budget'):r.batch(tmp_path,hours)


def test_default_is_read_only(tmp_path,monkeypatch):
    monkeypatch.setattr(r,'prepare',lambda:pytest.fail('Unexpected preparation'))
    monkeypatch.setattr(r,'batch',lambda *a:pytest.fail('Unexpected annual job'))
    assert r.main(['--out',str(tmp_path/'absent')])==0
    assert not (tmp_path/'absent').exists()


def test_manufactured_control_uses_real_case_summary_and_reuses_saved_year(tmp_path,monkeypatch):
    from dataclasses import replace
    from tests.test_v10_split_column import five_fixture
    case,p,s,g,air,c=five_fixture(False)
    case=replace(case,coast_distance_km=np.broadcast_to(np.array([50.,100.,200.,400.,500.]),case.domain.land.shape).copy())
    edges=np.arange(13,dtype=float)*12*3600.
    builder=r.model.parent.build_calendar
    monkeypatch.setattr(r.model.parent,'build_calendar',lambda *a,**kw:builder(*a,**kw,edges=edges))
    table,_=r.model.parent.prepare_calendar(case,p,s,g,air,c)
    monkeypatch.setattr(r.model,'EDGES',edges);monkeypatch.setattr(r.model.parent,'EDGES',edges)
    initial=r.model.core.initial_state(case.domain,p,s,g,air)
    driver=r.previous.weather.Driver(table,case,p,s,g,air,c,1.,'steady',41)
    record=r.model.parent.year(case.domain,p,s,initial,air,case.score_mask,g,driver)
    baseline=r.run.parent.night.summarize(record,case,{'passed':True},4)
    baseline['response']=r.run.parent.review.run.review.run.rain_vector(case,record[1])
    job={'key':'toy_control','phase':'control','seed':41,'region':'california','amplitude':1.,'timing':'steady','mode':'bulk','time_factor':1.,'anchor':'toy'}
    anchors={'toy':{'initial':initial,'record':record,'row':baseline}}
    args=({'california':(case,p,g,air,c)},s,anchors,{(41,'california'):table},lambda:False,lambda *a:None,lambda *a:None,r.source_id())
    folder=tmp_path/'control';row=r.case_run(folder,job,*args)
    assert row['physical_control_exact'] and row['coastal_winter_gain_mm']==0.
    r.previous.verify_completed(folder,row)
    candidate=dict(job,key='toy_candidate',phase='screen',mode='parcel_lower')
    result=r.case_run(tmp_path/'candidate',candidate,*args)
    assert 3<=result['years']<=6 and not result['physical_control_exact']
    r.previous.verify_completed(tmp_path/'candidate',result)
    monkeypatch.setattr(r.model,'year',lambda *a,**kw:pytest.fail('Completed control should be reused'))
    again=r.case_run(folder,job,*args)
    assert again==row
