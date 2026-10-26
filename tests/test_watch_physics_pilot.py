"""Exercise actual isolated child cleanup, not climate integrations."""
import json
import time
from scripts import watch_physics_pilot as monitor


def fixture(tmp_path,monkeypatch,source):
    (tmp_path/'scripts').mkdir();(tmp_path/'rotclimate').mkdir()
    (tmp_path/'scripts/check_vapor_flux.py').write_text(source)
    for name in ['paired_physics_pilot.py','check_surface_momentum.py']:(tmp_path/'scripts'/name).write_text('# fixture\n')
    core=tmp_path/'rotclimate/core.py';core.write_text('# original\n')
    (tmp_path/'physics.json').write_text('{}')
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(dict(profiles={'reference':{}},regions=['toy'],physics='physics.json')))
    monkeypatch.setattr(monitor,'ROOT',tmp_path)
    monkeypatch.setattr(monitor.subprocess,'check_output',lambda *a,**kw:'test-source\n')
    return plan,tmp_path/'results',core


def test_completed_child_has_accurate_atomic_status(tmp_path,monkeypatch):
    source="""import sys,json
from pathlib import Path
p=Path(sys.argv[sys.argv.index('--out')+1])/'reference';p.mkdir()
(p/'toy.json').write_text(json.dumps(dict(status='passed')))
"""
    plan,out,_=fixture(tmp_path,monkeypatch,source)
    sleep=time.sleep;monkeypatch.setattr(monitor.time,'sleep',lambda _:sleep(.02))
    monitor.run(plan,out,1)
    result=json.loads((out/'status.json').read_text())
    assert result['state']=='complete' and result['completed_runs']==result['planned_runs']==1 and result['passed_runs']==1


def test_changed_source_stops_only_its_own_child_group(tmp_path,monkeypatch):
    plan,out,core=fixture(tmp_path,monkeypatch,'import time\ntime.sleep(20)\n')
    sleep=time.sleep
    def change(_):core.write_text('# changed input\n');sleep(.02)
    monkeypatch.setattr(monitor.time,'sleep',change)
    monitor.run(plan,out,1)
    result=json.loads((out/'status.json').read_text())
    assert result['state']=='stopped_source_change' and 'core.py' in result['reason']


def test_budget_stop_preserves_partial_results(tmp_path,monkeypatch):
    plan,out,_=fixture(tmp_path,monkeypatch,'import time\ntime.sleep(20)\n')
    monitor.run(plan,out,1e-8)
    result=json.loads((out/'status.json').read_text())
    assert result['state']=='stopped_budget' and result['completed_runs']==0 and result['planned_runs']==1
