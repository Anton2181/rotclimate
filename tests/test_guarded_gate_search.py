from dataclasses import asdict
import json

import pytest

from scripts import guarded_gate_search as G
from scripts.local_benchmark_protocol import case_hash, file_hash, identity
from rotclimate.config import Params


def setup(tmp_path,monkeypatch):
    from test_earth import _toy_case
    case=_toy_case();params=Params()
    monkeypatch.setattr(G,'ROOT',tmp_path)
    monkeypatch.setattr(G,'load_params',lambda _:params)
    monkeypatch.setattr(G.earth,'REGIONS',{})
    monkeypatch.setattr(G.earth,'region_case',lambda *args:case)
    source=tmp_path/'source.py';source.write_text('# frozen physics\n')
    script=tmp_path/'scripts/gate_calibrate.py';script.parent.mkdir();script.write_text('# frozen search\n')
    wrapper=tmp_path/'scripts/guarded_gate_search.py';wrapper.write_text('# frozen guard\n')
    monkeypatch.setattr(G,'__file__',str(wrapper))
    old=tmp_path/'old';old.mkdir();new=tmp_path/'reference';new.mkdir()
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(dict(start='params.json',reference='old')))
    protocol=dict(params=json.loads(json.dumps(asdict(params))),sources={'source.py':file_hash(source)},
                  region_specs={'california':{}},cell_km=56.)
    row=dict(status='passed',numerics=dict(all_checks_passed=True),temperature=dict(monthly_mae_C=2.),
             rain=dict(loss=.5),case_identity=case_hash(case))
    summary=dict(complete=True,identity=identity(protocol),regions=dict(california=row))
    (new/'protocol.json').write_text(json.dumps(protocol));(new/'summary.json').write_text(json.dumps(summary))
    (old/'summary.json').write_text(json.dumps(summary))
    return plan,new,case,source


def test_guard_accepts_reproduced_inputs_and_normalizes_tuple_parameters(tmp_path,monkeypatch):
    p,r,case,source=setup(tmp_path,monkeypatch)
    result=G.manifest(p,r)
    assert result['cases']['california']==case_hash(case)
    assert result['sources']['source.py']==file_hash(source)


def test_guard_rejects_changed_derived_forcing(tmp_path,monkeypatch):
    p,r,case,source=setup(tmp_path,monkeypatch)
    case.grid.cloud_ref=case.grid.elev.copy()
    with pytest.raises(ValueError,match='regional forcing has changed'):G.manifest(p,r)


def test_guard_rejects_changed_code(tmp_path,monkeypatch):
    p,r,case,source=setup(tmp_path,monkeypatch);source.write_text('# changed\n')
    with pytest.raises(ValueError,match='scientific input has changed'):G.manifest(p,r)


def test_guard_rejects_a_reference_that_no_longer_matches_the_search_objective(tmp_path,monkeypatch):
    p,r,case,source=setup(tmp_path,monkeypatch)
    old=tmp_path/'old/summary.json';data=json.loads(old.read_text())
    data['regions']['california']['rain']['loss']=.4;old.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='planned objective'):G.manifest(p,r)
