import json
import sys

import pytest

from rotclimate.config import Params
from scripts import earth_calibrate as E


def test_earth_calibration_preserves_the_verified_start_profile(monkeypatch, capsys):
    path = 'atlases/earth_fit/params.json'
    monkeypatch.setattr(sys, 'argv', ['earth_calibrate', '--start', path, '--physics', 'storm_water',
        '--out', 'unused', '--plan', '--set', '{"eddy_moisture_scheme":"conservative"}'])
    monkeypatch.setattr(E.mp, 'get_context', lambda *args:pytest.fail('Plan started a worker'))
    E.main()
    config = json.loads(capsys.readouterr().out)
    original = Params.from_json(path)
    for key in ['solver_rtol', 'solver_require_convergence', 'solver_max_iter', 't_require_convergence',
                't_iters', 'moisture_residual_tol', 'moisture_require_convergence', 'picard_iters']:
        assert config['params'][key] == getattr(original, key)
    assert config['params']['eddy_moisture_scheme'] == 'conservative'
    assert len(config['space']) == 8


def test_unverified_old_profiles_keep_historical_earth_defaults(tmp_path, monkeypatch, capsys):
    path = tmp_path/'old.json'
    Params().to_json(path)
    monkeypatch.setattr(sys, 'argv', ['earth_calibrate', '--start', str(path), '--out', 'unused', '--plan'])
    E.main()
    config = json.loads(capsys.readouterr().out)
    for key, value in E.NUMERICS.items(): assert config['params'][key] == value


@pytest.mark.parametrize('before,after', [('rainfall','climate'), ('climate','rainfall')])
def test_resuming_with_a_different_objective_is_rejected_in_both_directions(tmp_path, monkeypatch, before, after):
    (tmp_path/'calibration_config.json').write_text(json.dumps(dict(objective=before)))
    monkeypatch.setattr(sys, 'argv', ['earth_calibrate', '--start', 'atlases/earth_fit/params.json',
        '--objective', after, '--out', str(tmp_path), '--resume'])
    monkeypatch.setattr(E.mp, 'get_context', lambda *a:pytest.fail('Started a mixed-objective worker'))
    with pytest.raises(ValueError, match='objective changed'): E.main()


@pytest.mark.parametrize('budget,count', [(1,1), (8,1), (9,9), (18,17)])
def test_earth_budget_is_not_exceeded_and_the_initial_fit_is_saved(tmp_path, monkeypatch, budget, count):
    pytest.importorskip('cma')
    from dataclasses import asdict
    calls = []
    class Pool:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def map(self, fn, jobs, chunksize=1): return [fn(job) for job in jobs]
    class Context:
        def Pool(self, workers): return Pool()
    def evaluate(job):
        x, base, regions, cell = job
        p = E.physics(x, Params(**base))
        cost = .5 if not calls else .6
        calls.append(cost)
        region = dict(climate_distance=cost, koppen_full_model=dict(exact=1., cs_retained=1.),
                      temperature=dict(bias_C=0.), rain=dict(sim_mean_annual_mm=500., obs_mean_annual_mm=500.))
        return dict(params=asdict(p), cost=cost, regions={r:region for r in regions})
    monkeypatch.setattr(E, 'evaluate', evaluate)
    monkeypatch.setattr(E.mp, 'get_context', lambda *args:Context())
    monkeypatch.setattr(sys, 'argv', ['earth_calibrate', '--start', 'atlases/earth_fit/params.json',
        '--physics', 'storm_water', '--regions', 'california', '--out', str(tmp_path),
        '--evals', str(budget), '--popsize', '8', '--workers', '1'])
    E.main()
    rows = [json.loads(line) for line in (tmp_path/'evals.jsonl').read_text().splitlines()]
    assert len(rows) == len(calls) == count <= budget
    assert json.loads((tmp_path/'best_params.json').read_text()) == rows[0]['params']
