"""Dry pressure-law, explicit energy-exchange and manufactured resume tests."""
from dataclasses import replace
import numpy as np
import pytest
from experiments import v10_pressure_thermo as m
from scripts import audit_v10_pressure_law as audit, check_v10_pressure_thermo as runner
from tests.test_v10_mass_projection import fixture
from rotclimate_v10.core import DAY


@pytest.mark.parametrize('mode', ['flat', 'tilted_isobar', 'isentropic_hill', 'pressure_transfer'])
def test_dry_law_matches_constant_pressure_and_poisson_transfer(mode):
    result = audit.manufactured_probe(mode)
    assert result['new_max_expected_temperature_error_c'] < 1e-10
    assert abs(result['theta_transport_error_kg_k_m2']) < 1e-7
    assert abs(result['energy_error_j_m2']) < 1e-5
    if mode == 'tilted_isobar':
        assert result['old_max_expected_temperature_error_c'] > .01
        expected_work = m.coordinates.P0*1000*8*result['dt_s']/(7*60000)
        assert result['new_work_j_m2'] == pytest.approx(expected_work, abs=1e-6)


def test_geopotential_shape_does_not_impose_extra_dry_heating_at_fixed_pressure():
    case, p, s, g, air = fixture(False)
    p.mixing_ratio[:] = 0.
    flow = m.winds.mass_model.flow_at(case.domain, p, s, [], 0., g)
    shifted = replace(g, height_m=g.height_m+np.linspace(0, 800, case.domain.land.shape[1])[None, None, :])
    outputs = []
    for geometry in (g, shifted):
        state = m.initial_state(case.domain, p, s, geometry, air)
        record = m.advance(state, case.domain, p, s, flow, 60., 0., air, physics=False, geometry=geometry)
        outputs.append(record[2])
    np.testing.assert_allclose(outputs[0], outputs[1], atol=1e-10)


def test_pressure_law_preserves_water_transport_and_closes_moist_step():
    case, p, s, g, air = fixture()
    state = m.initial_state(case.domain, p, s, g, air)
    state.water += g.mass*.02;state.energy += m.base.LV*g.mass*.02
    flow = m.winds.mass_model.flow_at(case.domain, p, s, [], 0., g)
    dt = min(300., m.base.stable_step(flow, g.mass, case.domain))
    old = m.coordinates.advance(state, case.domain, p, s, flow, dt, 0., air, physics=False, geometry=g)
    dry = m.advance(state, case.domain, p, s, flow, dt, 0., air, physics=False, geometry=g)
    np.testing.assert_allclose(old[0].water, dry[0].water, atol=1e-12)
    wet = m.advance(state, case.domain, p, s, flow, dt, 0., air, geometry=g)
    assert wet[0].water.min() >= 0 and wet[1].max() > 0
    assert abs(wet[4]['water_error_mm']) < 1e-9
    assert abs(wet[4]['energy_error_j_m2']) < 1e-5 and wet[-1] < 1e-9
    assert wet[6].shape[0] == len(m.PROCESSES) == 6
    # The work term is necessary, not an unrecorded residual or a zeroed budget.
    assert abs(wet[4]['prescribed_flow_work_j_m2']) > 1.


def test_thermo_step_enforces_cfl_and_valid_pressure():
    case, p, s, g, air = fixture()
    state = m.initial_state(case.domain, p, s, g, air)
    flow = m.winds.mass_model.flow_at(case.domain, p, s, [], 0., g)
    with pytest.raises(ValueError, match='CFL'):
        m.advance(state, case.domain, p, s, flow, 2*m.base.stable_step(flow, g.mass, case.domain), 0., air, geometry=g)
    with pytest.raises(ValueError, match='Positive pressure'):
        m.exner(np.array([0.]))


def test_manufactured_year_resumes_new_work_and_six_process_ledger(tmp_path, monkeypatch):
    case, p, s, g, air = fixture()
    p.eastward[:] = 0.;p.northward[:] = 0.
    wind = np.zeros((12, 2, 4)+case.domain.land.shape)
    monkeypatch.setattr(m.base, 'stable_step', lambda *a: DAY)
    state = m.initial_state(case.domain, p, s, g, air)
    full = m.year(case.domain, p, s, 41, state, air, case.score_mask, g, wind)
    stopped = [False]
    def save(*record):
        runner.night.write_checkpoint(tmp_path, 1, record)
        if record[-1]['month'] == 2:
            stopped[0] = True
    with pytest.raises(m.base.BudgetStop):
        m.year(case.domain, p, s, 41, state, air, case.score_mask, g, wind,
            save_month=save, should_stop=lambda: stopped[0])
    result = m.year(case.domain, p, s, 41, state, air, case.score_mask, g, wind,
        checkpoint=runner.night.read_checkpoint(tmp_path, 1, case.domain.land.shape))
    for field in ('water', 'energy', 'soil'):
        np.testing.assert_allclose(getattr(result[0], field), getattr(full[0], field), atol=1e-9)
    assert result[-1]['diagnostics'] == full[-1]['diagnostics']
    assert result[-1]['budget'] == full[-1]['budget']
    assert 'prescribed_flow_work_j_m2' in result[-1]['budget']
    assert abs(result[-1]['budget']['annual_energy_error_j_m2']) < 1


def test_flow_modes_match_their_frozen_controls():
    case, p, s, g, air = fixture()
    wind = np.ones((12, 2, 4)+case.domain.land.shape)
    for mode in ('uniform', 'spatial'):
        actual = m.flow_at(case.domain, p, s, [], 0., g, wind, wind_mode=mode)
        expected = (m.winds.mass_model.flow_at(case.domain, p, s, [], 0., g) if mode == 'uniform'
            else m.winds.flow_at(case.domain, p, s, [], 0., g, wind))
        np.testing.assert_allclose(actual.x, expected.x, atol=1e-12)
        np.testing.assert_allclose(actual.vertical, expected.vertical, atol=1e-12)


def test_default_prints_without_launch_or_write(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'run', lambda *a: pytest.fail('Unexpected seasonal run'))
    out = tmp_path/'absent'
    assert runner.main(['--out', str(out)]) == 0
    assert not out.exists()


def test_four_case_batch_resumes_and_rejects_changed_provenance(tmp_path, monkeypatch):
    case, profile, s, g, air = fixture()
    wind = np.zeros((12, 2, 4)+case.domain.land.shape)
    inputs = dict.fromkeys(('california', 'iberia'), (case, profile, g, air, wind))
    settings = dict.fromkeys(('uniform', 'spatial'), s)
    summary = {'score': 2., 'annual_rain_ratio': 1., 'wet_reference_coverage': 1.,
        'settling': {'passed': True}, 'eligible': True, 'evidence_sha256': {}}
    baselines = {r+'_'+k: summary for r in inputs for k in settings}
    expected = {'code_sha256': runner.source_id(), 'inputs': {r: runner.geometry_rules.array_id(runner.input_arrays(g, air, wind)) for r in inputs}}
    monkeypatch.setattr(runner, 'prepare', lambda *a: (expected, inputs, settings, baselines))
    calls = []
    def fake(folder, *args):
        calls.append(folder.name)
        if len(calls) == 2:
            raise m.base.BudgetStop()
        return summary.copy()
    out = tmp_path/'batch'
    assert runner.run(out, tmp_path, case_runner=fake)['status'] == 'budget_reached'
    assert runner.run(out, tmp_path, case_runner=fake)['status'] == 'complete'
    assert calls.count('california_uniform') == 1 and len(set(calls)) == 4
    expected['changed'] = True
    with pytest.raises(ValueError, match='changed'):
        runner.run(out, tmp_path, case_runner=fake)
