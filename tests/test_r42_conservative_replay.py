import json
from pathlib import Path
import subprocess

import numpy as np
import pytest

from scripts import run_r42_conservative_replay as replay


def test_damped_control_checks_forcing_and_observations_as_well_as_prediction_drift(tmp_path, monkeypatch):
    monkeypatch.setattr(replay, 'ROOT', tmp_path)
    reference = tmp_path / 'reference'; (reference / 'cells').mkdir(parents=True)
    candidate = tmp_path / 'candidate'; (candidate / 'cells').mkdir(parents=True)
    fields = {k: np.zeros(2) for k in ['i', 'j', 'To', 'Po', 'lat', 'lon', 'elev', 'elev_max', 'coast_km']}
    np.savez(reference / 'cells/test.npz', **fields, Ts=np.zeros((12, 2)), Ps=np.ones((12, 2)))
    (reference / 'summary.json').write_text(json.dumps({'regions': {'test': {'case_identity': 'same'}}}))
    np.savez(candidate / 'cells/test.npz', **fields, Ts=np.full((12, 2), .005), Ps=np.full((12, 2), 1.02))
    refs = {'test': {'reference': 'reference'}}
    summary = {'regions': {'test': {'case_identity': 'same'}}}
    limits = {'max_T_c': .01, 'max_P_mm_month': .05}
    assert replay.numerical_drift(refs, summary, candidate, limits)['passes']
    summary['regions']['test']['case_identity'] = 'changed'
    with pytest.raises(ValueError, match='forcing identity'):
        replay.numerical_drift(refs, summary, candidate, limits)
    summary['regions']['test']['case_identity'] = 'same'
    np.savez(candidate / 'cells/test.npz', **{**fields, 'Po': np.ones(2)}, Ts=np.zeros((12, 2)), Ps=np.ones((12, 2)))
    with pytest.raises(ValueError, match='inputs differ'):
        replay.numerical_drift(refs, summary, candidate, limits)


def test_replay_commit_excludes_unrelated_staged_work(tmp_path):
    def git(*args):return subprocess.check_output(['git', *args], cwd=tmp_path, text=True)
    git('init', '-q'); git('config', 'user.name', 'Test'); git('config', 'user.email', 'test@example.org')
    unrelated = tmp_path / 'user.txt'; unrelated.write_text('before')
    git('add', '.'); git('commit', '-qm', 'base')
    unrelated.write_text('user edit'); git('add', 'user.txt')
    folder = tmp_path / replay.PREFIX; folder.mkdir(parents=True)
    artifact = folder / 'results.json'; artifact.write_text('{}')
    replay.publish_results(tmp_path, [artifact])
    assert git('show', 'HEAD:user.txt') == 'before'
    assert git('diff', '--cached', '--name-only').strip() == 'user.txt'
    with pytest.raises(ValueError, match='unrelated'):
        replay.publish_results(tmp_path, [unrelated])


def test_declared_profiles_construct_and_keep_earth_planet_parameters():
    from test_earth import _toy_case
    from scripts.earth_benchmark import load_params
    from rotclimate import earth
    from rotclimate.model import ClimateModel
    root = Path(__file__).resolve().parents[1]
    plan = json.loads((root / 'calibration/r42_conservative_replay_20261102/plan.json').read_text())
    base = load_params(root / plan['params']); case = _toy_case()
    fields = ['tilt', 'retrograde', 'eccentricity', 'year_days', 'solar_flux', 'greenhouse_wm2', 'planet_radius']
    expected = earth.earth_params(base, case)
    for overrides in plan['profiles'].values():
        p = earth.earth_params(base.replace(**overrides), case)
        assert all(getattr(p, k) == getattr(expected, k) for k in fields)
        assert p.wind_source == p.sst_source == 'model'
        ClimateModel(p, grid=case.grid)
