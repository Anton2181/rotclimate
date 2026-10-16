"""Passive tracers, physical equality, source budgets and bounded resume."""
from dataclasses import replace
import json
import numpy as np
import pytest
from experiments import v10_water_sources as m
from scripts import check_v10_water_sources as runner
from tests.test_v10_mass_projection import fixture
from rotclimate_v10.earth import atomic_json, sha256
from rotclimate_v10.core import DAY


def make_state(case, p, s, g, air, dry=False):
    state = m.initial_state(case.domain, p, s, g, air)
    if dry:
        state.energy -= m.base.LV*state.water
        state.water[:] = 0.;state.tags[:] = 0.
    return state


def zero_flow(case, g):
    projection = m.model.ColumnProjection(case.domain, g)
    return projection.project(np.zeros_like(projection.mx), np.zeros_like(projection.my))


@pytest.mark.parametrize('mode', ['uniform', 'spatial'])
def test_passive_step_preserves_physics_and_per_source_water(mode):
    case, p, s, g, air = fixture()
    state = make_state(case, p, s, g, air)
    weights = np.random.default_rng(3).uniform(.1, 1, state.tags.shape)
    state.tags = weights/weights.sum(0)*state.water[None]
    wind = np.full((12, 2, 4)+case.domain.land.shape, 4.)
    flow = m.model.flow_at(case.domain, p, s, [], 0., g, wind, wind_mode=mode)
    dt = min(300., m.base.stable_step(flow, g.mass, case.domain))
    expected = m.model.advance(state, case.domain, p, s, flow, dt, 0., air, geometry=g)
    result = m.advance(state, case.domain, p, s, flow, dt, 0., air, g)
    for field in ('water', 'energy', 'soil'):
        np.testing.assert_array_equal(getattr(result[0], field), getattr(expected[0], field))
    for a,b in zip(result[1:4], expected[1:4]):
        np.testing.assert_array_equal(a, b)
    assert result[4] == expected[4]
    np.testing.assert_allclose(result[0].tags.sum(0), result[0].water, atol=1e-12)
    np.testing.assert_allclose(result[8].sum(0), result[1], atol=1e-12)
    assert result[-1]['max_step_source_error_mm'] < 1e-10
    assert result[-1]['import_mm'][1] > 0
    np.testing.assert_array_equal(result[-1]['import_mm'][[0, 2, 3]], 0.)
    net = result[-1]['export_mm'].sum()-result[-1]['import_mm'].sum()
    assert net == pytest.approx(result[4]['boundary_export_mm'], abs=1e-10)


def test_proportional_rainout_preserves_known_source_mixture():
    case, p, s, g, air = fixture(False)
    state = make_state(case, p, s, g, air)
    state.soil[:] = 0.
    water = g.mass*.04
    state.energy += m.base.LV*(water-state.water);state.water = water
    state.tags[:] = 0.;state.tags[1] = .25*water;state.tags[2] = .75*water
    result = m.advance(state, case.domain, p, s, zero_flow(case, g), 300., 0., air, g)
    assert result[1].max() > 0
    np.testing.assert_allclose(result[8][1], .25*result[1], atol=1e-10)
    np.testing.assert_allclose(result[8][2], .75*result[1], atol=1e-10)
    assert result[8][0].max() == result[8][3].max() == 0.


@pytest.mark.parametrize('ocean,source', [(True, 2), (False, 3)])
def test_evaporation_gets_latest_entry_source_not_soil_ancestry(ocean, source):
    case, p, s, g, air = fixture(False)
    case.domain.land[:] = not ocean
    state = make_state(case, p, s, g, air, dry=True)
    state.soil[:] = 75. if not ocean else 0.
    result = m.advance(state, case.domain, p, s, zero_flow(case, g), 300., 0., air, g)
    assert result[0].water.sum() > 0
    np.testing.assert_allclose(result[0].tags[source], result[0].water, atol=1e-12)
    assert result[-1]['evaporation_mm'][source] > 0
    assert np.count_nonzero(result[0].tags.sum(axis=(1, 2, 3))) == 1


def test_analytic_boundary_transport_without_physics_has_no_evaporation_or_rain():
    case, p, s, g, air = fixture(False)
    state = make_state(case, p, s, g, air)
    flow = m.model.winds.mass_model.flow_at(case.domain, p, s, [], 0., g)
    dt = min(300., m.base.stable_step(flow, g.mass, case.domain))
    result = m.advance(state, case.domain, p, s, flow, dt, 0., air, g, physics=False)
    assert result[-1]['import_mm'][1] > 0 and result[-1]['export_mm'][0] > 0
    assert result[1].max() == 0.
    assert result[-1]['evaporation_mm'].max() < 1e-12


def test_inconsistent_source_stores_are_rejected():
    case, p, s, g, air = fixture()
    state = make_state(case, p, s, g, air)
    state.tags[0] *= .9
    with pytest.raises(ValueError, match='sum'):
        m.advance(state, case.domain, p, s, zero_flow(case, g), 60., 0., air, g)


def test_manufactured_year_matches_frozen_physics_and_resumes_exactly(tmp_path, monkeypatch):
    case, p, s, g, air = fixture(False)
    p.eastward[:] = 0.;p.northward[:] = 0.
    wind = np.full((12, 2, 4)+case.domain.land.shape, 2.)
    edges = np.arange(13, dtype=float)*DAY  # Small manufactured calendar, not a regional run.
    monkeypatch.setattr(m, 'EDGES', edges);monkeypatch.setattr(m.model, 'EDGES', edges)
    state = make_state(case, p, s, g, air)
    full = m.year(case.domain, p, s, 41, state, air, case.score_mask, g, wind)
    physical = m.model.year(case.domain, p, s, 41, state, air, case.score_mask, g, wind)
    runner.verify_anchor(full, physical)
    assert full[-1]['budget'] == physical[-1]['budget']
    stopped = [False]
    def save(*record):
        runner.write_checkpoint(tmp_path, 1, record)
        if record[-1]['month'] == 4:
            stopped[0] = True
    with pytest.raises(m.base.BudgetStop):
        m.year(case.domain, p, s, 41, state, air, case.score_mask, g, wind,
            save_month=save, should_stop=lambda: stopped[0])
    partial = runner.read_checkpoint(tmp_path, 1, case.domain.land.shape)
    assert partial[-1]['month'] == 4
    resumed = m.year(case.domain, p, s, 41, state, air, case.score_mask, g, wind, checkpoint=partial)
    for field in ('water', 'energy', 'soil', 'tags'):
        np.testing.assert_array_equal(getattr(resumed[0], field), getattr(full[0], field))
    for a,b in zip(resumed[1:-1], full[1:-1]):
        np.testing.assert_array_equal(a, b)
    assert resumed[-1] == full[-1]
    assert max(abs(v) for v in full[-1]['sources']['annual_error_mm']) < 1e-8
    runner.write_checkpoint(tmp_path, 1, full, completed=True)
    loaded = runner.read_checkpoint(tmp_path, 1, case.domain.land.shape, completed=True)
    np.testing.assert_array_equal(loaded[0].tags, full[0].tags)
    loaded[-1]['sources']['end_store_mm'][0] += .1
    with pytest.raises(ValueError, match='disagrees with stores'):
        runner.validate_record(loaded, case.domain.land.shape, completed=True)
    loaded[-1]['sources']['end_store_mm'][0] -= .1
    loaded[-1]['sources']['max_step_error_mm'] = float('nan')
    with pytest.raises(ValueError, match='tolerances'):
        runner.validate_record(loaded, case.domain.land.shape, completed=True)
    (tmp_path/'year1.npz').write_bytes(b'corrupted')
    with pytest.raises(ValueError, match='integrity'):
        runner.read_checkpoint(tmp_path, 1, case.domain.land.shape, completed=True)


def test_seed41_anchor_check_rejects_changed_physics():
    case, p, s, g, air = fixture()
    state = make_state(case, p, s, g, air)
    arrays = (np.zeros((12,)+case.domain.land.shape),)*3
    physical = (state, *arrays, {})
    modified = m.State(state.water.copy(), state.energy.copy(), state.soil.copy(), state.tags.copy())
    modified.water[0, 0, 0] += 1e-5
    with pytest.raises(ValueError, match='physical state'):
        runner.verify_anchor((modified, *arrays, None, {}), physical)


def test_source_summary_uses_source_and_month_axes_without_mixing_cells():
    case, p, s, g, air = fixture()
    case.coast_distance_km[:, -1] = 400.
    rain = np.ones((12,)+case.domain.land.shape)*10
    tagged = np.zeros((12, len(m.SOURCES))+case.domain.land.shape)
    tagged[:, 1] = rain*.25;tagged[:, 2] = rain*.75
    rows = runner.source_summary((None, rain, None, None, tagged, {'sources': {}}), case)['rain']
    for row in rows.values():
        assert row['annual_rain_mm_by_source']['boundary'] == 30.
        assert row['winter_rain_mm_by_source']['ocean_evaporation'] == 45.
        assert row['annual_rain_fraction_by_source']['boundary'] == .25


def test_default_does_not_prepare_or_integrate(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'run', lambda *args: pytest.fail('Unexpected integration'))
    out = tmp_path/'absent'
    assert runner.main(['--out', str(out)]) == 0
    assert not out.exists()


def fake_protocol(monkeypatch):
    jobs = [dict(key=f'california_{mode}_s41', region='california', wind=mode, seed=41)
        for mode in ('uniform', 'spatial')]
    protocol = {'code_sha256': runner.source_id(), 'jobs': jobs}
    monkeypatch.setattr(runner, 'prepare', lambda: (protocol, {}, {}, {}, {}))
    return protocol


def fake_row():
    return {'annual_rain_ratio': .1, 'score': 30., 'settling': {'passed': True},
        'sources': {'rain': {'scored_land': {'annual_rain_fraction_by_source': dict(zip(m.SOURCES, (0., .5, .4, .1)))}}},
        'response': {'annual_rain_mm': 40., 'coast_winter_mm': 20.}, 'evidence_sha256': {}}


def test_batch_resume_and_protocol_corruption_rejection(tmp_path, monkeypatch):
    protocol = fake_protocol(monkeypatch);calls = []
    def fake(folder, job, *args):
        calls.append(job['key'])
        if len(calls) == 2:
            raise m.base.BudgetStop()
        folder.mkdir(parents=True, exist_ok=True)
        row = fake_row();(folder/'year1.npz').write_bytes(b'manufactured evidence')
        row['evidence_sha256']['year1.npz'] = sha256(folder/'year1.npz')
        atomic_json(folder/'summary.json', row)
        return row
    out = tmp_path/'out'
    assert runner.run(out, case_runner=fake)['status'] == 'budget_reached'
    assert runner.run(out, case_runner=fake)['status'] == 'complete'
    assert calls.count('california_uniform_s41') == 1
    (out/'cases/california_uniform_s41/year1.npz').write_bytes(b'corrupted')
    assert runner.run(out, case_runner=fake)['status'] == 'needs_diagnosis'
    assert len(calls) == 3
    protocol['changed'] = True
    with pytest.raises(ValueError, match='protocol changed'):
        runner.run(out, case_runner=fake)


def test_global_time_cap_prevents_starting_another_case(tmp_path, monkeypatch):
    fake_protocol(monkeypatch)
    times = iter([0., 2.5*3600+1, 2.5*3600+2])
    state = runner.run(tmp_path/'out', case_runner=lambda *a: pytest.fail('Budget already spent'), clock=lambda: next(times))
    assert state['status'] == 'budget_reached' and not state['cases']
