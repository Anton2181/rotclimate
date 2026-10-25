from dataclasses import asdict
import json
from types import SimpleNamespace

import numpy as np
import pytest

from scripts import benchmark_local as B
from scripts.local_benchmark_protocol import case_hash, freeze
from rotclimate.config import Params


def test_tied_rainfall_ranks_and_undefined_constant_patterns():
    assert B.spearman(np.array([1,1,2,3]), np.array([1,2,2,3])) == pytest.approx(5/6)
    assert B.spearman(np.ones(4), np.arange(4)) is None
    assert B.temperature_metrics(np.ones((12,4)), np.ones((12,4)))['anomaly_pattern_r'] is None


def test_manifest_rejects_changed_inputs_and_unversioned_old_results(tmp_path):
    path = tmp_path/'protocol.json'
    first = freeze(path, dict(params=dict(ocean_rh=.71), regions=['california']))
    assert freeze(path, dict(params=dict(ocean_rh=.71), regions=['california'])) == first
    with pytest.raises(ValueError, match='inputs changed'):
        freeze(path, dict(params=dict(ocean_rh=.72), regions=['california']))
    old = tmp_path/'old';old.mkdir();(old/'summary.json').write_text('{}')
    with pytest.raises(ValueError, match='no manifest'): freeze(old/'protocol.json', {})


def setup_case(tmp_path, monkeypatch, passed=True):
    from test_earth import _toy_case
    case = _toy_case()
    case.obs_T[:] = 10; case.obs_P[:] = 30
    p = Params()
    calls = []
    def run(*args, **kwargs):
        calls.append(1)
        return SimpleNamespace(params=p, T=np.ones((2, *case.grid.land.shape))*10,
            P=np.ones((2,*case.grid.land.shape)), days=np.array([0.,180.]),
            numerics=dict(all_checks_passed=passed))
    monkeypatch.setattr(B.earth, 'region_case', lambda *a, **kw:case)
    monkeypatch.setattr(B.earth, 'run_case', run)
    monkeypatch.setattr(B, 'monthly_stats', lambda *a, **kw:dict(Tm=case.obs_T.copy(), Pm=case.obs_P.copy()))
    (tmp_path/'cells').mkdir();(tmp_path/'cases').mkdir()
    job = ('california',asdict(p),56.,str(tmp_path),{},'frozen-run')
    return case, calls, job


def test_resume_reuses_only_complete_verified_cells_and_rejects_changed_geography(tmp_path, monkeypatch):
    case, calls, job = setup_case(tmp_path, monkeypatch)
    first = B.one(job); second = B.one(job)
    assert first == second and len(calls) == 1
    assert first['status'] == 'passed'
    assert first['rain']['loss'] == 0
    cells = tmp_path/'cells/california.npz'
    with cells.open('ab') as stream: stream.write(b'altered')
    B.one(job)
    assert len(calls) == 2
    case.obs_P[0,0,0] += 1
    with pytest.raises(ValueError, match='regional inputs differ'): B.one(job)


def test_failed_certificate_is_saved_without_an_accuracy_score(tmp_path, monkeypatch):
    _, calls, job = setup_case(tmp_path, monkeypatch, passed=False)
    row = B.one(job)
    assert row['status'] == 'failed'
    assert row['numerics']['all_checks_passed'] is False
    assert 'rain' not in row
    assert json.loads((tmp_path/'cases/california.json').read_text()) == row
    assert not (tmp_path/'cells/california.npz').exists()


def test_grid_identity_tracks_observations_and_fetch_beyond_the_region():
    from test_earth import _toy_case
    case = _toy_case(); before = case_hash(case)
    case.grid.chi_far = np.ones_like(case.grid.elev)
    assert case_hash(case) != before
    before = case_hash(case);case.obs_P[:] = 1
    assert case_hash(case) != before


@pytest.mark.parametrize('field',['chi_pole','sea_reach','cloud_ref','descent','sea_depth'])
def test_grid_identity_tracks_newer_physical_forcing(field):
    from test_earth import _toy_case
    case = _toy_case()
    before = case_hash(case)
    setattr(case.grid,field,np.ones_like(case.grid.elev))
    populated = case_hash(case)
    assert populated != before
    getattr(case.grid,field)[0,0] += .1
    assert case_hash(case) != populated
