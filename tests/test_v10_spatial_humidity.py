"""Native humidity placement, exact old boundary, flow invariance and guards."""
from dataclasses import replace
import json
import numpy as np
import pytest
from experiments import v10_spatial_humidity as m
from scripts import check_v10_spatial_humidity as r,review_v10_cloud_sources as source_review
from tests.test_v10_event_forcing import calendar_fixture,ToyDriver
from tests.test_v10_split_column import five_fixture
from rotclimate_v10.earth import atomic_json,sha256


def toy_tables():
    d,p,s,g,air,flows,a,_=calendar_fixture();driver=ToyDriver(d,flows,a)
    q=.15*m.core.base.saturation(air[0],g.pressure);q[-1]=0.
    caps=.95*m.core.base.saturation(air[0],g.pressure)
    pattern=np.linspace(.5,1.5,d.land.shape[1])[None,None]
    tables,diag=m.build_tables(d,g,a,driver.at,lambda t:q,lambda t:q*pattern,lambda start,end:caps)
    return d,p,s,g,air,flows,a,tables,diag


def test_uniform_boundary_is_identical_local_changes_dose_and_matching_restores_it():
    d,p,s,g,air,flows,a,t,diag=toy_tables()
    np.testing.assert_array_equal(t['uniform'],a['boundary_lift16_aligned'])
    np.testing.assert_array_equal(t['target_local_matched'],a['monthly_import_target_mm'])
    assert not np.array_equal(t['local'],t['uniform']) and not np.allclose(t['target_local'],t['target_uniform'],rtol=1e-8,atol=0)
    assert diag['uniform_boundary_identical'] and diag['state_advances']==0
    for row in diag['monthly']:
        a,b=row['variants']['uniform'],row['variants']['local_matched']
        assert a['gross_import_mm']==pytest.approx(b['gross_import_mm'],abs=1e-10)
        for name,v in row['variants'].items():assert v['land_boundary_cell_import_mm']+v['marine_boundary_cell_import_mm']==pytest.approx(v['gross_import_mm'],abs=1e-10)


def test_zero_native_humidity_cannot_be_filled_to_make_a_matching_dose():
    d,p,s,g,air,flows,a,_=calendar_fixture();driver=ToyDriver(d,flows,a)
    q=.15*m.core.base.saturation(air[0],g.pressure);q[-1]=0.
    with pytest.raises(ValueError,match='infeasible'):
        m.build_tables(d,g,a,driver.at,lambda t:q,lambda t:np.zeros_like(q),lambda start,end:.95*m.core.base.saturation(air[0],g.pressure))


def test_native_sampling_uses_actual_pressures_and_leaves_unobserved_lid_dry():
    case,p,s,g,air,c=five_fixture(False)
    f=m.atmosphere.Field(np.full((12,8,2,2),.007),np.array([1000.,925.,850.,700.,600.,500.,400.,300.]),np.array([40.,30.]),np.array([230.,240.]),np.arange(12))
    profile=m.local_profile(case,g,{('california','shum'):f})
    np.testing.assert_allclose(profile[:,:4],.007,atol=1e-15)
    assert not profile[:,-1].any()
    bad=replace(g,pressure=g.pressure.copy());bad.pressure[0]=100001.
    with pytest.raises(ValueError,match='outside'):m.local_profile(case,bad,{('california','shum'):f})


@pytest.mark.parametrize('mode',['bulk','parcel_lower'])
def test_native_driver_preserves_flow_and_real_case_control_and_restart(mode,tmp_path,monkeypatch):
    case,p,s,g,air,c=five_fixture(False)
    case=replace(case,coast_distance_km=np.broadcast_to(np.array([50.,100.,200.,400.,500.]),case.domain.land.shape).copy())
    edges=np.arange(13,dtype=float)*12*3600.;build=m.core.build_calendar
    monkeypatch.setattr(m.core,'build_calendar',lambda *a,**kw:build(*a,**kw,edges=edges))
    original,_=m.core.prepare_calendar(case,p,s,g,air,c)
    q=m.core.core.boundary_ratio(case.domain,p,s,g,air,0.)
    local=np.broadcast_to(q,(12,)+q.shape).copy()*np.linspace(.7,1.3,case.domain.land.shape[1])[None,None,None,:]
    tables,diag=m.prepare_tables(case,p,s,g,air,c,original,local)
    old=m.weather.Driver(original,case,p,s,g,air,c,16.,'aligned',67)
    for variant in m.VARIANTS:
        new=m.Driver(original,tables,variant,case,p,s,g,air,c)
        for time in (0.,10800.,86400.):
            f,b,end=old.at(time);other,bq,other_end=new.at(time)
            for field in ('x','y','vertical'):np.testing.assert_array_equal(getattr(f,field),getattr(other,field))
            assert end==other_end
            if variant=='uniform':np.testing.assert_array_equal(b,bq)
    monkeypatch.setattr(r.physics,'EDGES',edges)
    initial=r.physics.core.initial_state(case.domain,p,s,g,air)
    expected=r.physics.year(case.domain,p,s,initial,air,case.score_mask,g,old,condensation_mode=mode)
    job={'key':'toy_control','phase':'control','region':'california','mode':mode,'variant':'uniform'}
    args=({'california':(case,p,g,air,c)},s,{'california_'+mode:initial},{'california_'+mode:expected},
        {'california':original},{'california':tables},lambda:False,lambda *a:None,lambda *a:None,r.source_id())
    folder=tmp_path/'control';row=r.case_run(folder,job,*args)
    assert row['physical_control_exact'] and row['coastal_winter_gain_mm']==0.
    test=dict(job,key='toy_local',phase='test',variant='local_matched')
    candidate=r.case_run(tmp_path/'local',test,*args)
    assert 3<=candidate['years']<=6 and abs(candidate['boundary_import_change_fraction'])<1e-14
    r.run.previous.verify_completed(tmp_path/'local',candidate)
    monkeypatch.setattr(r.physics,'year',lambda *a,**kw:pytest.fail('Completed control must be reused'))
    assert r.case_run(folder,job,*args)==row


def test_fixed_twelve_case_plan():
    jobs=r.make_jobs(['california','iberia'])
    assert len(jobs)==len({j['key'] for j in jobs})==12
    assert all(j['phase']=='control' for j in jobs[:4])
    assert sum(j['variant']=='local_matched' for j in jobs)==4
    assert {j['mode'] for j in jobs}=={'bulk','parcel_lower'}


def fixture(tmp_path,monkeypatch):
    protocol={'code_sha256':r.source_id(),'jobs':[{'key':'first'},{'key':'second'}]}
    monkeypatch.setattr(r,'prepare',lambda:(protocol,{},None,{},{},{},{}))
    prepared=tmp_path/'prepared';atomic_json(prepared/'manifest.json',{'protocol':protocol});monkeypatch.setattr(r,'PREFLIGHT',prepared)
    return protocol


def fake_case(folder):
    folder.mkdir(parents=True,exist_ok=True);atomic_json(folder/'config.json',{'toy':True});(folder/'year1.npz').write_bytes(b'toy')
    row={'response':{'coast_winter_mm':1.},'coastal_winter_gain_mm':0.,'monthly_mae_change_mm':0.,
        'koppen_fixed_surface_temperature':{'target_mediterranean_to_arid':.9},'boundary_import_change_fraction':0.,'settling':{'passed':True},
        'case_config_sha256':sha256(folder/'config.json'),'evidence_sha256':{'year1.npz':sha256(folder/'year1.npz')}}
    atomic_json(folder/'summary.json',row);return row


def test_budget_resume_and_completed_evidence_guard(tmp_path,monkeypatch):
    fixture(tmp_path,monkeypatch);calls=[]
    def case(folder,job,*args):
        calls.append(job['key'])
        if len(calls)==2:raise r.physics.base.BudgetStop()
        return fake_case(folder)
    out=tmp_path/'result'
    assert r.batch(out,case_runner=case)['status']=='budget_reached'
    assert r.batch(out,case_runner=case)['status']=='complete' and calls==['first','second','second']
    (out/'cases/first/year1.npz').write_bytes(b'changed')
    assert r.batch(out,case_runner=case)['status']=='needs_diagnosis'


def test_deadline_stale_preflight_and_read_only_default(tmp_path,monkeypatch):
    protocol=fixture(tmp_path,monkeypatch);ticks=[0.]
    def clock():v=ticks[0];ticks[0]=r.BUDGET+1.;return v
    assert r.batch(tmp_path/'result',case_runner=lambda *a:pytest.fail('Out of time'),clock=clock)['status']=='budget_reached'
    protocol['changed']=True
    with pytest.raises(ValueError,match='stale'):r.batch(tmp_path/'other')
    monkeypatch.setattr(r,'prepare',lambda *a:pytest.fail('Unexpected preparation'))
    assert r.main(['--out',str(tmp_path/'absent')])==0 and not (tmp_path/'absent').exists()


def test_source_fractions_are_last_entry_amounts_and_zero_rain_has_no_fractions():
    fractions=source_review.fractions([0.,64.68,14.59,7.08])
    assert sum(fractions.values())==pytest.approx(1.)
    assert fractions['boundary']==pytest.approx(64.68/86.35)
    assert source_review.fractions([0.,0.,0.,0.]) is None
