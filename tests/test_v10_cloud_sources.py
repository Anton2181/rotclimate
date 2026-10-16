"""Donor-source attribution, unchanged physics, binary resume and batch guards."""
from copy import deepcopy
import numpy as np
import pytest
from experiments import v10_cloud_sources as m
from scripts import replay_v10_cloud_sources as r
from tests.test_v10_parcel_condensation import cloudy_fixture
from tests.test_v10_delivery_diagnostics import toy
from tests.test_v10_event_forcing import ToyDriver
from rotclimate_v10.earth import atomic_json,sha256


def test_parcel_rain_inherits_ascending_donor_before_recipient_mixing():
    case,p,s,g,air,before,f,q=cloudy_fixture();c=m.Collector(case.domain,g,initial_water=before.water)
    c.arrays['tags'][:]=0.;c.arrays['tags'][1,0]=before.water[0];c.arrays['tags'][3,1:]=before.water[1:]
    c.arrays['initial_store']=c.arrays['tags'].sum(axis=(1,2,3))/case.domain.land.size
    result=m.physics.advance(before,case.domain,p,s,f,60.,0.,air,geometry=g,boundary=q,condensation_mode='parcel_lower')
    saved=deepcopy(result)
    c.add(before,result[0],result[5],result[8],f,q,result[4],60.,0.)
    assert result[8][1].min()>0.
    np.testing.assert_allclose(c.arrays['tagged_rain'][0,1,1],result[8][1],atol=1e-12,rtol=0)
    assert not c.arrays['tagged_rain'][0,3,1].any()
    np.testing.assert_allclose(c.arrays['tags'].sum(0),result[0].water,atol=1e-12,rtol=0)
    for name in ('water','energy','soil'):np.testing.assert_array_equal(getattr(result[0],name),getattr(saved[0],name))
    for i in (1,2,3,5,6,8):np.testing.assert_array_equal(result[i],saved[i])
    assert c.arrays['maximum_errors'].max()<1e-9


@pytest.mark.parametrize('mode',m.MODES)
def test_tiny_source_year_is_exact_and_resumes_both_physics_and_tags(mode,tmp_path,monkeypatch):
    case,p,s,g,air,flows,a=toy();d=case.domain
    monkeypatch.setattr(m,'EDGES',a['edges']);monkeypatch.setattr(m.physics,'EDGES',a['edges'])
    initial=m.core.initial_state(d,p,s,g,air);driver=ToyDriver(d,flows,a)
    expected=m.physics.year(d,p,s,initial,air,case.score_mask,g,driver,condensation_mode=mode)
    c=m.Collector(d,g,initial_water=initial.water)
    full=m.year(d,p,s,initial,air,case.score_mask,g,driver,condensation_mode=mode,collector=c)
    r.run.previous.replay.verify_physical(full,expected);c.validate_months(12,full[0].water,full[1])
    interrupted=[False];part=m.Collector(d,g,initial_water=initial.water)
    def save(*record):
        r.write_checkpoint(tmp_path,record,part)
        if record[-1]['month']==2:interrupted[0]=True
    with pytest.raises(m.base.BudgetStop):m.year(d,p,s,initial,air,case.score_mask,g,driver,condensation_mode=mode,collector=part,save_month=save,should_stop=lambda:interrupted[0])
    physical,restored=r.read_checkpoint(tmp_path,case,g)
    resumed=m.year(d,p,s,initial,air,case.score_mask,g,driver,checkpoint=physical,condensation_mode=mode,collector=restored)
    r.run.previous.replay.verify_physical(resumed,expected)
    for key in c.arrays:np.testing.assert_array_equal(c.arrays[key],restored.arrays[key])
    r.write_checkpoint(tmp_path,resumed,restored,completed=True)
    masks={'all':np.ones(d.land.shape,bool)};summary=restored.summary(masks,np.arange(6),np.arange(6,12))
    assert sum(summary['regions']['all']['winter_rain_mm_by_source'])==pytest.approx(expected[1][:6].sum(0).mean(),abs=1e-8)
    assert max(abs(v) for v in summary['annual_source_error_mm'])<1e-7
    (tmp_path/'year1.npz').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='integrity'):r.read_checkpoint(tmp_path,case,g,completed=True)


def test_source_store_validation_rejects_missing_or_negative_arrays():
    case,p,s,g,air,flows,a=toy();initial=m.core.initial_state(case.domain,p,s,g,air)
    c=m.Collector(case.domain,g,initial_water=initial.water)
    bad=deepcopy(c.arrays);bad['tags'][0,0,0,0]=-1.
    with pytest.raises(ValueError,match='Negative'):m.Collector(case.domain,g,saved=bad)
    bad=deepcopy(c.arrays);bad.pop('tagged_rain')
    with pytest.raises(ValueError,match='checkpoint'):m.Collector(case.domain,g,saved=bad)


def mock_batch(tmp_path,monkeypatch):
    protocol={'code_sha256':r.source_id(),'jobs':[{'key':'california_bulk'},{'key':'iberia_parcel_lower'}]}
    monkeypatch.setattr(r,'prepare',lambda:(protocol,{},None,{},{},{}))
    prepared=tmp_path/'prepared';atomic_json(prepared/'manifest.json',{'protocol':protocol});monkeypatch.setattr(r,'PREFLIGHT',prepared)
    return protocol


def fake_case(folder):
    folder.mkdir(parents=True,exist_ok=True);atomic_json(folder/'config.json',{'toy':True});(folder/'year1.npz').write_bytes(b'toy')
    row={'physical_reproduction_exact':True,'regions':{'reference_arid':{'summer_rain_mm_by_source':[0.,1.,2.,3.]}},
        'case_config_sha256':sha256(folder/'config.json'),'evidence_sha256':{'year1.npz':sha256(folder/'year1.npz')}}
    atomic_json(folder/'summary.json',row);return row


def test_replay_batch_budget_resume_and_evidence_guards(tmp_path,monkeypatch):
    mock_batch(tmp_path,monkeypatch);calls=[]
    def case(folder,job,*args):
        calls.append(job['key'])
        if len(calls)==2:raise m.base.BudgetStop()
        return fake_case(folder)
    out=tmp_path/'result'
    assert r.batch(out,case_runner=case)['status']=='budget_reached'
    assert r.batch(out,case_runner=case)['status']=='complete' and calls==['california_bulk','iberia_parcel_lower','iberia_parcel_lower']
    (out/'cases/california_bulk/year1.npz').write_bytes(b'changed')
    assert r.batch(out,case_runner=case)['status']=='needs_diagnosis'


def test_deadline_and_stale_preflight_prevent_new_year(tmp_path,monkeypatch):
    protocol=mock_batch(tmp_path,monkeypatch);ticks=[0.]
    def clock():v=ticks[0];ticks[0]=r.BUDGET+1.;return v
    state=r.batch(tmp_path/'result',case_runner=lambda *a:pytest.fail('No time'),clock=clock)
    assert state['status']=='budget_reached' and not state['cases']
    protocol['changed']=True
    with pytest.raises(ValueError,match='stale'):r.batch(tmp_path/'other')


def test_default_is_read_only(tmp_path,monkeypatch):
    monkeypatch.setattr(r,'prepare',lambda:pytest.fail('Unexpected preparation'))
    monkeypatch.setattr(r,'batch',lambda *a:pytest.fail('Unexpected annual replay'))
    out=tmp_path/'absent'
    assert r.main(['--out',str(out)])==0 and not out.exists()
