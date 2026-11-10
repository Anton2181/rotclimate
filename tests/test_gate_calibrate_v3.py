"""The search objective must rank candidates by the adopted release policy."""
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.gate_calibrate import score
from scripts.gate_v3 import score as release_score


def test_v3_accepts_overall_gain_despite_a_worse_group():
    groups = dict(training=['a', 'b', 'c'], holdout=['d'])
    ref = {n: (2., 1.) for n in 'abcd'}
    candidate = {**{n: (1.6, .8) for n in 'abc'}, 'd': (2.2, 1.1)}
    old, _ = score(candidate, ref, groups)
    new, info = score(candidate, ref, groups, policy='v3')
    assert old == pytest.approx(1.075)
    assert new == pytest.approx(.875)
    assert info['groups']['holdout'] == pytest.approx(1.1)
    assert info['penalty'] == 0


def test_v3_retired_regions_have_equal_weight_without_group_penalties():
    ref = {n: (2., 1.) for n in 'abc'}
    candidate = dict(a=(1., .5), b=(2.2, 1.1), c=(2.2, 1.1))
    cost, info = score(candidate, ref, dict(dev=['a']), dict(retired=['b', 'c']), policy='v3')
    assert cost == pytest.approx(.9)
    assert info['S31'] == .5
    assert info['n_regions'] == 3
    assert info['penalty'] == 0
    # Legacy plans keep their original objective, including the extra-group penalty.
    assert score(candidate, ref, dict(dev=['a']), dict(retired=['b', 'c']))[0] == pytest.approx(.7)


def test_v3_keeps_temperature_and_rain_safeguards_separate():
    cost, info = score(dict(a=(1., 1.1)), dict(a=(2., 1.)), dict(dev=['a']), policy='v3')
    assert info['S'] == pytest.approx(.8)
    assert info['penalty'] == pytest.approx(.18)
    assert cost == pytest.approx(.98)


@pytest.mark.parametrize('errors,groups,extra', [
    ({'a': (np.nan, 1.)}, {'dev': ['a']}, {}),
    ({'a': (-1., 1.)}, {'dev': ['a']}, {}),
    ({'a': (1., 1.)}, {'dev': ['a']}, {'retired': ['a']}),
    ({}, {'dev': ['a']}, {}),
])
def test_v3_rejects_invalid_or_reweighted_measurements(errors, groups, extra):
    with pytest.raises(ValueError):
        score(errors, {'a': (2., 1.)}, groups, extra, policy='v3')


def test_search_score_matches_independent_r42_release_gate():
    root = Path(__file__).resolve().parents[1]
    run = root / 'output/desert_refit3_20261101/v3'
    reference, candidate, extra = {}, {}, {}
    for part in ['dev31', 'retired_a', 'retired_b', 'retired_c']:
        rows = []
        for fit, dest in [('r41', reference), ('candidate', candidate)]:
            data = json.loads((run / f'{fit}_{part}/summary.json').read_text())['regions']
            dest.update(data)
            rows = list(data)
        if part != 'dev31':
            extra[part] = rows
    policy = json.loads((root / 'calibration/local_accuracy_20261023/policy_v3.json').read_text())
    def metrics(rows):
        return {n: (r['temperature']['monthly_mae_C'], r['rain']['loss']) for n, r in rows.items()}
    cost, info = score(metrics(candidate), metrics(reference), policy['groups'], extra, policy='v3')
    release = release_score(reference, candidate, list(reference))
    assert info['n_regions'] == 49
    assert info['S'] == pytest.approx(release['S'], abs=1e-14)
    assert cost == pytest.approx(.9626111459489867, abs=1e-14)


def test_full_search_records_control_and_resumes_without_changing_objective(tmp_path, monkeypatch):
    """Exercise the real CMA/log/state path without running 49 climate models."""
    import sys
    from scripts import gate_calibrate as G
    root = Path(__file__).resolve().parents[1]
    frozen = json.loads((root / 'calibration/r42_multistart_20261102/plan_1.json').read_text())
    frozen['evals'] = 2
    paths = [frozen['reference'], *(v['reference'] for v in frozen['extra_groups'].values())]
    errors = {}
    for path in paths:
        data = json.loads((root / path / 'summary.json').read_text())
        dest = tmp_path / path; dest.mkdir(parents=True)
        (dest / 'summary.json').write_text(json.dumps(data))
        errors.update({n: (r['temperature']['monthly_mae_C'], r['rain']['loss']) for n, r in data['regions'].items()})
    for path in [frozen['start'], 'calibration/local_accuracy_20261023/policy_v3.json', *(v['spec'] for v in frozen['extra_groups'].values())]:
        dest = tmp_path / path; dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes((root / path).read_bytes())
    script = tmp_path / 'scripts/gate_calibrate.py'; script.parent.mkdir()
    for name in ['gate_calibrate.py', 'rainfall_metrics.py', 'benchmark_local.py','local_benchmark_protocol.py','earth_benchmark.py']:
        (script.parent / name).write_bytes((root / 'scripts' / name).read_bytes())
    monkeypatch.setattr(G, 'ROOT', tmp_path)
    monkeypatch.setattr(G, '__file__', str(script))
    class Pool:
        def __init__(self, workers): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def map(self, function, jobs): return [(n, errors[n]) for n, *_ in jobs]
    monkeypatch.setattr(G, 'Pool', Pool)
    plan = tmp_path / 'plan.json'; plan.write_text(json.dumps(frozen))
    out = tmp_path / 'search'
    args = ['gate_calibrate.py', '--plan', str(plan), '--out', str(out)]
    monkeypatch.setattr(sys, 'argv', args)
    G.main()
    rows = [json.loads(line) for line in (out / 'evals.jsonl').read_text().splitlines()]
    assert [r['n'] for r in rows] == [0, 1]
    assert all(r['n_regions'] == 49 and r['S'] == 1 for r in rows)
    assert (out / 'state.pkl').is_file()
    monkeypatch.setattr(sys, 'argv', args + ['--resume'])
    G.main()
    assert len((out / 'evals.jsonl').read_text().splitlines()) == 2
    frozen['scoring_policy'] = 'v3'
    frozen['sigma'] = .3
    plan.write_text(json.dumps(frozen))
    with pytest.raises(ValueError, match='changed'):
        G.main()


def test_resume_at_generation_boundary_preserves_the_random_trajectory(tmp_path, monkeypatch):
    import sys
    from scripts import gate_calibrate as G
    root=Path(__file__).resolve().parents[1]
    frozen=json.loads((root/'calibration/r42_multistart_20261102/plan_1.json').read_text())
    frozen.update(evals=5,popsize=2,seed=883)
    errors={}
    for path in [frozen['reference'],*(v['reference'] for v in frozen['extra_groups'].values())]:
        data=json.loads((root/path/'summary.json').read_text());dest=tmp_path/path;dest.mkdir(parents=True)
        (dest/'summary.json').write_text(json.dumps(data))
        errors.update({n:(r['temperature']['monthly_mae_C'],r['rain']['loss']) for n,r in data['regions'].items()})
    for path in [frozen['start'],'calibration/local_accuracy_20261023/policy_v3.json',*(v['spec'] for v in frozen['extra_groups'].values())]:
        dest=tmp_path/path;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes((root/path).read_bytes())
    script=tmp_path/'scripts/gate_calibrate.py';script.parent.mkdir()
    for name in ['gate_calibrate.py','rainfall_metrics.py','benchmark_local.py','local_benchmark_protocol.py','earth_benchmark.py']:
        (script.parent/name).write_bytes((root/'scripts'/name).read_bytes())
    monkeypatch.setattr(G,'ROOT',tmp_path);monkeypatch.setattr(G,'__file__',str(script))
    class Pool:
        def __init__(self, workers):pass
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def map(self,function,jobs):return [(n,errors[n]) for n,*_ in jobs]
    monkeypatch.setattr(G,'Pool',Pool)
    plan=tmp_path/'plan.json';plan.write_text(json.dumps(frozen))
    def run(out,*extra):
        monkeypatch.setattr(sys,'argv',['gate_calibrate.py','--plan',str(plan),'--out',str(out),*extra]);G.main()
    run(tmp_path/'continuous')
    run(tmp_path/'split','--through-eval','3')
    np.random.seed(999999)   # simulate a new process, not the original generator state
    run(tmp_path/'split','--resume')
    a=(tmp_path/'continuous/evals.jsonl').read_text();b=(tmp_path/'split/evals.jsonl').read_text()
    assert a==b


@pytest.mark.parametrize('knobs',[[['tilt',20,30]],[['solver_rtol',1e-8,1e-5]],[['wind_source',0,1]],
    [['sst_offset',-5,0],['sst_offset',-5,0]],[['sst_offset',0,1]]])
def test_verified_search_rejects_forcing_numerics_enums_and_changed_start(knobs):
    from rotclimate.config import Params
    from scripts.gate_calibrate import verified_search_profile
    p=Params.from_json('calibration/local_accuracy_20261023/r44_params.json')
    with pytest.raises(ValueError):verified_search_profile(p,knobs)


def test_actual_reference_case_mismatch_aborts_before_running_or_scoring(monkeypatch):
    from dataclasses import asdict
    from scripts import gate_calibrate as G
    from local_benchmark_protocol import case_hash
    from rotclimate.config import Params
    from test_earth import _toy_case
    case=_toy_case();called=[]
    monkeypatch.setattr(G.earth,'region_case',lambda *args:case)
    def failed(*args,**kw):called.append(True);raise RuntimeError('Numerical failure')
    monkeypatch.setattr(G.earth,'run_case',failed)
    with pytest.raises(ValueError,match='differ'):
        G.region_errors(('california',asdict(Params()),{},'wrong observations'))
    assert not called
    assert G.region_errors(('california',asdict(Params()),{},case_hash(case)))==('california',None)
    assert called==[True]
