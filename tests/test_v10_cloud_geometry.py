"""Passive cloud-path identities, exact replay/resume and evidence safeguards."""
from types import SimpleNamespace
import json
import numpy as np
import pytest

from experiments import v10_cloud_geometry as model
from scripts import replay_v10_cloud_geometry as runner
from tests.test_v10_split_column import five_fixture
from tests.test_v10_spatial_humidity_review import saved
from rotclimate_v10.earth import atomic_json, sha256


def test_saturation_only_after_face_is_an_actual_rain_subset_not_new_rain():
    case, p, setting, g, air, circulation = five_fixture(False)
    b = model.base; t = np.full_like(g.mass, 20.); q = np.full_like(g.mass, .001)
    dry = lambda pressure: (t[0]+273.15)*(pressure/g.pressure[0])**(287.05/b.CP)-273.15
    q[0] = .5*(b.saturation(dry(g.interfaces_pa[1]), g.interfaces_pa[1])+b.saturation(dry(g.pressure[1]), g.pressure[1]))
    before = b.State(g.mass*q, g.mass*(b.CP*(t+273.15)+b.G*g.height_m)+b.LV*g.mass*q, np.zeros(case.domain.land.shape))
    flow = SimpleNamespace(vertical=np.zeros((4,)+case.domain.land.shape)); flow.vertical[0] = .001
    target, _ = model.physics.coordinates.targets(case.domain, p, setting, 0., air)
    parcel = model.physics.ascending_condensate(before, setting, flow, 60., g, target, 'parcel_lower')
    assert parcel[1].min() > 0 and not parcel[[0, 2, 3, 4]].any()
    collector = model.Collector(case.domain, g, setting, p, air, edges=np.arange(13)*60.)
    original = [array.copy() for array in (before.water, before.energy, before.soil, parcel)]
    collector.add(before, before, parcel, parcel, flow, None, {}, 60., 0.)
    for old, actual in zip(original, (before.water, before.energy, before.soil, parcel)):
        np.testing.assert_array_equal(old, actual)
    a = collector.arrays['metrics']
    np.testing.assert_array_equal(a[0, 2], parcel[1:4])
    np.testing.assert_array_equal(a[0, 3], a[0, 2])
    rain = np.zeros((12,)+case.domain.land.shape); rain[0] = parcel.sum(0)
    collector.validate_months(1, before.water, rain)
    row = collector.summary({'domain': np.ones(case.domain.land.shape, bool)}, [0], [1])['regions']['domain']
    assert row['winter']['parcel_rain_first_saturation_above_face_fraction'] == pytest.approx(1.)
    assert row['summer']['parcel_rain_over_upward_vapor'] is None
    assert row['winter']['parcel_rain_over_upward_vapor'] < 1.
    damaged = {k:v.copy() for k,v in collector.arrays.items()}; damaged['metrics'][0, 3] *= 2
    bad = model.Collector(case.domain, g, setting, p, air, saved=damaged, edges=np.arange(13)*60.)
    with pytest.raises(ValueError, match='subset'):
        bad.validate_months(1, before.water, rain)
    with pytest.raises(ValueError, match='reconstruct'):
        collector.add(before, before, parcel, np.zeros_like(parcel), flow, None, {}, 60., 60.)


@pytest.mark.parametrize('variant,source_key', [('uniform', 'control'), ('local_matched', 'test')])
def test_exact_physical_replay_monthly_resume_and_completed_reuse(saved, variant, source_key, tmp_path, monkeypatch):
    source, prepared = saved
    _, inputs, setting, original_initials, _, originals, profiles = prepared
    protocol, state, _, _, records, _, _, _, _ = runner.review.load_verified(source, prepared)
    case, p, g, air, circulation = inputs['california']
    n = state['cases'][source_key]['years']
    before = original_initials['california_parcel_lower'] if n == 1 else runner.checkpoints.read_checkpoint(source/'cases'/source_key, n-1, case.domain.land.shape, completed=True)[0]
    tables = runner.forcing.read_calendar(None, None)[0]
    monkeypatch.setattr(model.physical, 'EDGES', np.arange(13)*12*3600.)
    job = dict(key='toy', region='california', variant=variant, mode='parcel_lower', source_case=source_key, source_year=n)
    stopped = [False]
    def progress(info):
        if info['month'] == 1:
            stopped[0] = True
    args = (inputs, setting, {'toy': before}, {'toy': records[source_key]}, originals, {'california': tables})
    folder = tmp_path/'replay'; code_id = runner.source_id()
    with pytest.raises(model.base.BudgetStop):
        runner.replay_case(folder, job, *args, lambda: stopped[0], lambda *args: None, progress, code_id)
    partial, collector = runner.read_checkpoint(folder, case, g, setting, p, air)
    # The frozen physical loop checks its stop flag every 32 steps; another
    # tiny month can finish before that check. Resume the last complete month.
    assert 1 <= partial[-1]['month'] < 12
    row = runner.replay_case(folder, job, *args, lambda: False, lambda *args: None, lambda *args: None, code_id)
    assert row['physical_reproduction_exact']
    final, collector = runner.read_checkpoint(folder, case, g, setting, p, air, completed=True)
    runner.forcing.replay.verify_physical(final, records[source_key])
    np.testing.assert_allclose(collector.arrays['layer_rain'].sum(1), final[1], atol=1e-9, rtol=0)
    monkeypatch.setattr(model.physical, 'year', lambda *args, **kwargs: pytest.fail('Completed replay must be reused'))
    assert runner.replay_case(folder, job, *args, lambda: False, lambda *args: None, lambda *args: None, code_id) == row
    runner.forcing.verify_completed(folder, row)
    (folder/'year1.npz').write_bytes(b'changed')
    with pytest.raises(ValueError):
        runner.forcing.verify_completed(folder, row)


def fixture(tmp_path, monkeypatch):
    protocol = {'code_sha256': runner.source_id(), 'jobs': [{'key': 'a'}, {'key': 'b'}]}
    monkeypatch.setattr(runner, 'prepare', lambda: (protocol, {}, None, {}, {}, {}, {}))
    prepared = tmp_path/'prepared'; atomic_json(prepared/'manifest.json', {'protocol': protocol})
    monkeypatch.setattr(runner, 'PREFLIGHT', prepared)
    monkeypatch.setattr(runner, 'report', lambda out, state: atomic_json(out/'state.json', state))
    return protocol


def fake_case(folder):
    atomic_json(folder/'config.json', {'toy': True}); (folder/'year1.npz').write_bytes(b'toy')
    row = {'case_config_sha256': sha256(folder/'config.json'), 'evidence_sha256': {'year1.npz': sha256(folder/'year1.npz')}}
    atomic_json(folder/'summary.json', row)
    return row


def test_batch_budget_resume_and_stale_guard(tmp_path, monkeypatch):
    protocol = fixture(tmp_path, monkeypatch); calls = []
    def case(folder, job, *args):
        calls.append(job['key'])
        if len(calls) == 2:
            raise model.base.BudgetStop()
        return fake_case(folder)
    out = tmp_path/'results'
    assert runner.batch(out, case_runner=case)['status'] == 'budget_reached'
    assert runner.batch(out, case_runner=case)['status'] == 'complete' and calls == ['a', 'b', 'b']
    (out/'cases/a/year1.npz').write_bytes(b'bad')
    assert runner.batch(out, case_runner=case)['status'] == 'needs_diagnosis'
    protocol['changed'] = True
    with pytest.raises(ValueError, match='stale'):
        runner.batch(tmp_path/'different', case_runner=case)


def test_protected_output_and_default_no_work(tmp_path, monkeypatch):
    fixture(tmp_path, monkeypatch)
    with pytest.raises(ValueError, match='Preserve'):
        runner.batch(runner.PREFLIGHT/'child')
    monkeypatch.setattr(runner, 'prepare', lambda: pytest.fail('Default must not prepare or integrate'))
    assert runner.main(['--out', str(tmp_path/'absent')]) == 0
    assert not (tmp_path/'absent').exists()
