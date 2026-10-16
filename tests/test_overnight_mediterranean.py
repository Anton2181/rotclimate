from dataclasses import asdict
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import time

import numpy as np
from PIL import Image
import pytest

from scripts import overnight_mediterranean as night


def base():
    return night.Params.from_json('calibration/round20_retrograde_local_shortlist.json')


def row(dry=.12, cold=.68, hot=.57):
    return dict(accuracy=.5, zone_recall=dict(cold_dry=cold,hot_dry=hot),
                mediterranean=dict(dry_share=dry,cs_share=.4))


def test_sweep_covers_every_declared_bound_and_joint_probe_without_changing_geometry():
    p=base(); trials=night.sweep(p)
    assert len(night.SPACE)==24 and len(trials)==64
    assert asdict(trials['joint_01'])==asdict(night.sweep(p)['joint_01'])
    for name,q in trials.items():
        assert all(v==asdict(p)[k] for k,v in asdict(q).items() if k not in night.SPACE)
        assert all(lo<=getattr(q,k)<=hi for k,(lo,hi) in night.SPACE.items())
    for k,(lo,hi) in night.SPACE.items():
        assert getattr(trials[k+'_low'],k)==lo
        assert getattr(trials[k+'_high'],k)==hi
        if getattr(p,k)!=lo:
            assert {n for n,v in asdict(trials[k+'_low']).items() if v!=asdict(p)[n]}=={k}


def test_joint_latin_hypercube_stratifies_each_parameter():
    trials=night.sweep(base())
    for key,(lo,hi) in night.SPACE.items():
        bins=[int(16*(getattr(trials[f'joint_{i:02d}'],key)-lo)/(hi-lo)) for i in range(1,17)]
        assert sorted(bins)==list(range(16))


def test_failed_missing_and_damaged_worlds_cannot_be_qualified():
    good={s:dict(status='ok',row=row()) for s in night.TRAIN}
    candidate={s:dict(status='ok',row=row(dry=.05)) for s in night.TRAIN}
    assert night.qualifies(candidate,good,night.TRAIN)
    candidate[302]=dict(status='failed',error='solver')
    assert not night.qualifies(candidate,good,night.TRAIN)
    candidate[302]=dict(status='ok',row=row(dry=.01,cold=.50))
    assert not night.qualifies(candidate,good,night.TRAIN)
    del candidate[302]
    assert not night.qualifies(candidate,good,night.TRAIN)


def test_budget_does_not_start_a_case_that_would_use_the_reserve(tmp_path):
    recorded=[]
    j=night.job('test',base(),50,tmp_path,'source')
    answers=night.run_jobs([j],1,time.monotonic()-1,tmp_path,recorded.append)
    assert answers['test']['status']=='deferred_budget'
    assert recorded==list(answers.values())


def test_cache_requires_settings_source_and_matching_fields_and_deduplicates_aliases(tmp_path):
    (tmp_path/'cases').mkdir()
    p=base(); j=night.job('one',p,8,tmp_path,'source')
    fields=tmp_path/'fields.npz'
    np.savez(fields,params_json=json.dumps(asdict(p)))
    d=dict(name='one',status='ok',input_id=j['input_id'],fields=str(fields),row=row())
    night.atomic_json(tmp_path/'cases/one.json',d)
    assert night.cached(night.job('alias',p,8,tmp_path,'source'))['name']=='alias'
    assert night.cached(night.job('one',p,50,tmp_path,'source')) is None
    assert night.cached(night.job('one',p,8,tmp_path,'changed')) is None
    np.savez(fields,params_json=json.dumps(asdict(p.replace(beyond_seed=402))))
    assert night.cached(j) is None


def test_worker_records_numerical_failure_without_a_valid_score(monkeypatch,tmp_path):
    from scripts import diagnose_numerics
    monkeypatch.setattr(night,'source_id',lambda:'source')
    def fail(*args,**kwargs):
        raise RuntimeError('Temperature failed')
    monkeypatch.setattr(diagnose_numerics,'diagnose',fail)
    d=night.worker(night.job('bad',base(),50,tmp_path,'source'))
    assert d['status']=='failed' and 'row' not in d
    assert 'Temperature failed' in (tmp_path/'cases/bad.json').read_text()


def test_atlas_swap_keeps_previous_data_and_rolls_back_a_failed_replacement(tmp_path,monkeypatch):
    current,staged,backup=tmp_path/'data',tmp_path/'next',tmp_path/'backup'
    current.mkdir();staged.mkdir()
    (current/'version').write_text('old');(staged/'version').write_text('new')
    rename=Path.rename
    def fail_stage(self,target):
        if self==staged:
            raise OSError('Injected rename failure')
        return rename(self,target)
    monkeypatch.setattr(Path,'rename',fail_stage)
    with pytest.raises(OSError):night.publish_folder(staged,current,backup)
    assert (current/'version').read_text()=='old' and not backup.exists()
    monkeypatch.setattr(Path,'rename',rename)
    night.publish_folder(staged,current,backup)
    assert (current/'version').read_text()=='new'
    assert (backup/'version').read_text()=='old'


def test_atlas_binary_validation_rejects_incomplete_array_data(tmp_path):
    from rotclimate.__main__ import numerical_settings
    p=base()
    meta=dict(numerics=numerical_settings(p),arrays=dict(T=dict(offset=0,shape=[4],dtype='int16')))
    (tmp_path/'atlas.json').write_text(json.dumps(meta));(tmp_path/'atlas.bin').write_bytes(b'12')
    with pytest.raises(ValueError,match='incomplete'):night.verify_atlas(tmp_path,p)


def test_default_plan_never_runs_or_writes(monkeypatch,tmp_path):
    out=tmp_path/'not-created'
    monkeypatch.setattr(sys,'argv',['overnight_mediterranean.py','--out',str(out)])
    def forbidden(*args,**kwargs):pytest.fail('Plan launched work')
    monkeypatch.setattr(night,'run_jobs',forbidden)
    monkeypatch.setattr(night.subprocess,'run',forbidden)
    night.main()
    assert not out.exists()


@pytest.mark.parametrize('fresh_damage,settled',[(False,True),(True,True),(False,False)])
def test_pipeline_selects_only_checked_candidate_and_exports_or_preserves_atlas(monkeypatch,tmp_path,fresh_damage,settled):
    # End-to-end orchestration with fake results; never call a real solver,
    # build a real atlas, spawn workers or touch the live atlas directory.
    p=base()
    monkeypatch.setattr(night,'source_id',lambda:'source')
    monkeypatch.setattr(night,'load_cached',lambda *args:None)
    monkeypatch.setattr(night,'sweep',lambda p:{'good':p.replace(eddy_rate=1.05),'bad':p.replace(eddy_rate=1.2)})
    monkeypatch.setattr(night,'stability',lambda *args:dict(passed=settled))
    def fake_jobs(jobs,workers,deadline,out,record,**kwargs):
        results={}
        for j in jobs:
            name=j['name']
            is_anchor='anchor' in name
            damaged='bad' in name or fresh_damage and name.startswith('fresh_good') and '_s401' in name
            dry=.12 if is_anchor else .02 if 'good' in name or 'bad' in name else .11
            d=dict(status='ok',name=name,row=row(dry=dry,cold=.45 if damaged else .68),
                   result=str(tmp_path/'fake_result.npz'),fields='unused',transport='unused',seconds=1.)
            results[name]=d;record(d)
        return results
    monkeypatch.setattr(night,'run_jobs',fake_jobs)
    exports=[]
    def fake_export(command,**kwargs):
        spec=json.loads(Path(command[-1]).read_text())
        exports.append(spec)
        night.atomic_json(tmp_path/'atlas_publication.json',dict(status='published',selected=spec['selected']))
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(night.subprocess,'run',fake_export)
    monkeypatch.setattr(sys,'argv',['overnight_mediterranean.py','--run','--out',str(tmp_path)])
    night.main()
    summary=json.loads((tmp_path/'summary.json').read_text())
    assert summary['stage']=='complete'
    if settled:
        assert exports and exports[-1]['selected']==('anchor' if fresh_damage else 'good')
        assert summary['atlas']['status']=='published'
    else:
        assert not exports and summary['atlas']['status']=='blocked_checks'
    assert 'bad' not in summary['training_qualified']
