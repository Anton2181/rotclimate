"""Manufactured years/restarts and fake batch orchestration; no Earth year."""
import json
from dataclasses import replace
from pathlib import Path
import numpy as np
import pytest
from experiments import v10_regional_transport as model
from scripts import check_v10_regional_transport as run,check_v10_split_column as checkpoints,replay_v10_delivery as replay
from tests.test_v10_event_forcing import calendar_fixture,ToyDriver
from tests.test_v10_split_column import five_fixture
from rotclimate_v10.earth import atomic_json,sha256


@pytest.mark.parametrize('scheme',['upwind','coupled_fct'])
@pytest.mark.parametrize('mode',['bulk','parcel_lower'])
@pytest.mark.parametrize('factor',[1.,.5])
def test_manufactured_year_restart_and_independent_ledgers(scheme,mode,factor,tmp_path,monkeypatch):
    d,p,s,g,air,flows,a,_=calendar_fixture()
    monkeypatch.setattr(model,'EDGES',a['edges']);monkeypatch.setattr(model.original,'EDGES',a['edges'])
    state=model.core.initial_state(d,p,s,g,air)
    def driver():return ToyDriver(d,flows,a)
    full=model.year(d,p,s,state,air,d.land,g,driver(),condensation_mode=mode,time_factor=factor,transport_scheme=scheme)
    assert abs(full[-1]['budget']['annual_water_error_mm'])<1e-6
    assert abs(full[-1]['budget']['annual_energy_error_j_m2'])<1.
    if scheme=='upwind':
        old=model.original.year(d,p,s,state,air,d.land,g,driver(),condensation_mode=mode,time_factor=factor)
        replay.verify_physical(full,old)
    stopped=[False]
    def save(*record):
        checkpoints.write_checkpoint(tmp_path,1,record)
        if record[-1]['month']==2:stopped[0]=True
    with pytest.raises(model.base.BudgetStop):
        model.year(d,p,s,state,air,d.land,g,driver(),condensation_mode=mode,time_factor=factor,transport_scheme=scheme,
            save_month=save,should_stop=lambda:stopped[0])
    partial=checkpoints.read_checkpoint(tmp_path,1,d.land.shape)
    resumed=model.year(d,p,s,state,air,d.land,g,driver(),condensation_mode=mode,time_factor=factor,transport_scheme=scheme,checkpoint=partial)
    replay.verify_physical(resumed,full)
    run.source.run.run.validate_control_record(resumed,a['monthly_import_target_mm'])


def test_fixed_eight_case_plan_pairs_every_forcing_and_cloud_rule():
    jobs=run.make_jobs(('california','iberia'))
    assert len(jobs)==8 and len({j['key'] for j in jobs})==8
    assert all(j['phase']=='control' for j in jobs[:4])
    for region in ('california','iberia'):
        for mode in ('bulk','parcel_lower'):
            pair=[j for j in jobs if j['region']==region and j['mode']==mode]
            assert {j['scheme'] for j in pair}=={'upwind','coupled_fct'}
            assert len({j['source_case'] for j in pair})==1


def test_case_runner_real_summary_and_reused_saved_toy_year(tmp_path,monkeypatch):
    case,p,s,g,air,c=five_fixture(False)
    case=replace(case,coast_distance_km=np.broadcast_to(np.array([50.,100.,200.,400.,500.]),case.domain.land.shape).copy())
    edges=np.arange(13,dtype=float)*12*3600.
    builder=model.original.parent.build_calendar
    monkeypatch.setattr(model.original.parent,'build_calendar',lambda *a,**kw:builder(*a,**kw,edges=edges))
    table,_=model.original.parent.prepare_calendar(case,p,s,g,air,c)
    monkeypatch.setattr(model,'EDGES',edges);monkeypatch.setattr(model.original,'EDGES',edges)
    def make_driver(*args):return run.source.run.previous.weather.Driver(table,case,p,s,g,air,c,1.,'steady',41)
    monkeypatch.setattr(run,'driver_for',make_driver)
    initial=model.core.initial_state(case.domain,p,s,g,air)
    record=model.original.year(case.domain,p,s,initial,air,case.score_mask,g,make_driver(),condensation_mode='bulk')
    response=run.review.rain_vector(case,record[1])
    anchors={'saved':{'initial':initial,'record':record,'row':{'response':response}}}
    job={'key':'toy_control','region':'toy','mode':'bulk','phase':'control','scheme':'upwind','source_case':'saved'}
    args=({'toy':(case,p,g,air,c)},s,anchors,{}, {},lambda:False,lambda *a:None,lambda *a:None,run.source_id())
    folder=tmp_path/'control';row=run.case_run(folder,job,*args)
    assert row['physical_control_exact'] and row['coastal_winter_gain_mm']==0.
    run.verify_completed(folder,row)
    candidate=dict(job,key='toy_candidate',phase='candidate',scheme='coupled_fct')
    result=run.case_run(tmp_path/'candidate',candidate,*args)
    assert 3<=result['years']<=6 and not result['physical_control_exact']
    assert 'reference_arid' in result['seasonal_errors'] or 'reference_mediterranean' in result['seasonal_errors'] or 'other_reference_land' in result['seasonal_errors']
    run.verify_completed(tmp_path/'candidate',result)
    monkeypatch.setattr(model,'year',lambda *a,**kw:pytest.fail('Completed toy year reran'))
    assert run.case_run(folder,job,*args)==row


def test_default_is_read_only(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(run,'prepare',lambda:pytest.fail('Default must not prepare'))
    monkeypatch.setattr(run,'batch',lambda *a:pytest.fail('Default must not integrate'))
    assert run.main(['--out',str(tmp_path/'absent')])==0
    assert not (tmp_path/'absent').exists()


def fake_fixture(tmp_path,monkeypatch):
    protocol={'code_sha256':run.source_id(),'jobs':run.make_jobs(('toy',))[:2]}
    monkeypatch.setattr(run,'prepare',lambda:(protocol,{},None,{}, {},{}))
    ready=tmp_path/'prepared';ready.mkdir();(ready/'manufactured_waves.npz').write_bytes(b'toy')
    atomic_json(ready/'manifest.json',{'protocol':protocol,'manufactured_arrays_sha256':sha256(ready/'manufactured_waves.npz')})
    monkeypatch.setattr(run,'PREFLIGHT',ready)
    monkeypatch.setattr(run,'report',lambda out,state:atomic_json(out/'state.json',state))
    return protocol


def fake_case(folder,*args):
    folder.mkdir(parents=True,exist_ok=True);atomic_json(folder/'config.json',{'toy':True})
    (folder/'year1.npz').write_bytes(b'toy evidence')
    row={'case_config_sha256':sha256(folder/'config.json'),'evidence_sha256':{'year1.npz':sha256(folder/'year1.npz')}}
    atomic_json(folder/'summary.json',row);return row


def test_budget_resume_and_completed_batch_are_read_only(tmp_path,monkeypatch):
    fake_fixture(tmp_path,monkeypatch);calls=[]
    def partial(folder,*args):
        calls.append(folder.name)
        if len(calls)==2:raise model.base.BudgetStop()
        return fake_case(folder)
    out=tmp_path/'result'
    assert run.batch(out,case_runner=partial)['status']=='budget_reached'
    assert run.batch(out,case_runner=partial)['status']=='complete'
    assert len(calls)==3
    before={name:sha256(out/name) for name in ('state.json','manifest.json','progress.json')}
    assert run.batch(out,case_runner=lambda *a:pytest.fail('Completed case reran'))['status']=='complete'
    assert before=={name:sha256(out/name) for name in before}
    (out/'cases'/calls[0]/'year1.npz').write_bytes(b'changed')
    with pytest.raises(ValueError):run.batch(out,case_runner=lambda *a:pytest.fail('Corrupt evidence reran'))


def test_physics_failure_stops_batch_and_requires_diagnosis(tmp_path,monkeypatch):
    fake_fixture(tmp_path,monkeypatch)
    def fail(*args):raise FloatingPointError('incompatible cloud dose')
    out=tmp_path/'failed';state=run.batch(out,case_runner=fail)
    assert state['status']=='needs_diagnosis' and 'cloud dose' in state['error']
    with pytest.raises(ValueError,match='inspection'):run.batch(out,case_runner=fake_case)


@pytest.mark.parametrize('hours',[0.,-1.,4.1,np.nan,np.inf])
def test_invalid_budget_prevents_preparation(hours,tmp_path,monkeypatch):
    monkeypatch.setattr(run,'prepare',lambda:pytest.fail('Invalid budget'))
    with pytest.raises(ValueError,match='budget'):run.batch(tmp_path/'bad',hours)


def test_stale_prepared_evidence_rejected(tmp_path,monkeypatch):
    fake_fixture(tmp_path,monkeypatch)
    (run.PREFLIGHT/'manufactured_waves.npz').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='stale'):run.batch(tmp_path/'bad',case_runner=fake_case)


def test_completed_parent_paths_rejected_before_preparation(monkeypatch):
    monkeypatch.setattr(run,'prepare',lambda:pytest.fail('Protected path'))
    for path in ('output/v10_flux_transport_lab','output/v10_spatial_humidity/nested','output'):
        with pytest.raises(ValueError,match='Preserve'):run.batch(run.ROOT/path)
