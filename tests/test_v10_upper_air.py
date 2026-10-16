"""Manufactured tests only; no regional climate integrations."""
import numpy as np
import pytest
from experiments import v10_upper_air as experiment, v10_column as base
from experiments.v10_time import step_length
from scripts import check_v10_upper_air as runner, overnight_v10 as night
from scripts.review_v10_overnight import error_statistics
from rotclimate_v10.core import Domain, DAY


def fixture():
    land = np.ones((3, 4), bool)
    domain = Domain('california', land, np.zeros(land.shape), np.full(land.shape, 37.),
        np.full((12,)+land.shape, 15.), 60000., 60000.)
    profile = base.Profile(np.tile([-3., -10., -20., -45.], (12, 1)),
        np.tile([.006, .004, .002, .0004], (12, 1)),
        np.tile([4., 6., 8., 12.], (12, 1)), np.zeros((12, 4)),
        np.array([500., 1500., 3000., 9000.]))
    return domain, profile, base.Settings(storm_rate_month=0)


@pytest.mark.parametrize('fragment', [.0014742516214028, .00598946213722229, .005069])
def test_boundary_fragment_is_legal_and_no_time_is_discarded(fragment):
    edge = 961200.
    t = edge-fragment
    dt = step_length(t, 2160., edge, edge+10800.)
    assert 0 < dt < .01
    assert t+dt == edge


@pytest.mark.parametrize('values', [(2, 1, 2, 3), (2, -1, 4, 5), (2, np.inf, 4, 5)])
def test_invalid_clock_still_fails(values):
    with pytest.raises((ValueError, RuntimeError)):
        step_length(*values)


def test_only_upper_target_changes():
    domain, profile, settings = fixture()
    old, _ = base.targets(domain, profile, settings, 0.)
    local = np.full((12, 4)+domain.land.shape, -15.)
    new, surface = experiment.targets(domain, profile, settings, 0., local)
    np.testing.assert_array_equal(new[:2], old[:2])
    np.testing.assert_array_equal(new[2:], -15.)
    np.testing.assert_array_equal(surface, 15.)


@pytest.mark.parametrize('wet', [False, True])
def test_instrumented_closure_matches_frozen_step_and_closes_ledgers(wet):
    domain, profile, settings = fixture()
    domain.elevation_m[1, 1:3] = 1000
    state = base.initial_state(domain, profile, settings)
    if wet:
        mass, _ = base.masses(domain)
        state.water += .02*mass
        state.energy += .02*mass*base.LV
    flow = base.flow_at(domain, profile, settings, [], 0.)
    mass, _ = base.masses(domain)
    dt = min(300., base.stable_step(flow, mass, domain))
    old = base.advance(state, domain, profile, settings, flow, dt, 0.)
    new = experiment.advance(state, domain, profile, settings, flow, dt, 0.)
    for key in ('water', 'energy', 'soil'):
        np.testing.assert_allclose(getattr(old[0], key), getattr(new[0], key), rtol=1e-13, atol=1e-7)
    for i in (1, 2, 3):
        np.testing.assert_allclose(old[i], new[i], rtol=1e-13, atol=1e-11)
    assert abs(new[4]['water_error_mm']) < 1e-9
    assert abs(new[4]['energy_error_j_m2']) < 1e-5
    assert new[-1] < 1e-9
    np.testing.assert_allclose(new[5].sum(0), new[1], atol=1e-12)


def test_corrected_target_step_remains_budgeted():
    domain, profile, settings = fixture()
    state = base.initial_state(domain, profile, settings)
    flow = base.flow_at(domain, profile, settings, [], 0.)
    local = np.full((12, 4)+domain.land.shape, -30.)
    result = experiment.advance(state, domain, profile, settings, flow, 300., 0., local)
    assert result[0].water.min() >= 0
    assert abs(result[4]['energy_error_j_m2']) < 1e-5
    assert result[-1] < 1e-9


def test_diagnostic_checkpoint_resume_matches_full_manufactured_year(tmp_path, monkeypatch):
    domain, profile, settings = fixture()
    profile.eastward[:] = 0
    monkeypatch.setattr(base, 'stable_step', lambda *args: DAY)
    mass, _ = base.masses(domain)
    old, _ = base.targets(domain, profile, settings, 0.)
    state = base.State(np.zeros_like(mass), mass*(base.CP*(old+273.15)+base.G*base.geometry(domain, profile)), np.zeros(domain.land.shape))
    local = np.broadcast_to(old, (12,)+old.shape).copy()
    full = experiment.year(domain, profile, settings, 41, state, local, domain.land)
    stopped = [False]
    def save(*record):
        night.write_checkpoint(tmp_path, 1, record)
        if record[-1]['month'] == 2:
            stopped[0] = True
    with pytest.raises(base.BudgetStop):
        experiment.year(domain, profile, settings, 41, state, local, domain.land,
            save_month=save, should_stop=lambda: stopped[0])
    partial = night.read_checkpoint(tmp_path, 1, domain.land.shape)
    resumed = experiment.year(domain, profile, settings, 41, state, local, domain.land, checkpoint=partial)
    for key in ('water', 'energy', 'soil'):
        np.testing.assert_allclose(getattr(full[0], key), getattr(resumed[0], key), atol=1e-9)
    for key in ('layer_rain_scored_land_mm', 'temperature_changes_scored_land_c'):
        np.testing.assert_allclose(full[-1]['diagnostics'][key], resumed[-1]['diagnostics'][key], atol=1e-10)
    assert abs(full[-1]['budget']['annual_water_error_mm']) < 1e-6


def test_reference_error_is_separate_from_imposed_target_error():
    actual = np.zeros((12, 4, 2, 2))
    fake = actual+17
    reference = actual+2
    mask = np.ones((2, 2), bool)
    assert error_statistics(actual, fake, mask)['lower_upper_abs_p95_c'] == [17., 17.]
    assert error_statistics(actual, reference, mask)['lower_upper_abs_p95_c'] == [2., 2.]


def test_default_plan_writes_nothing_and_runs_no_model(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, 'run', lambda *args: pytest.fail('Default launched model'))
    out = tmp_path/'no_write'
    assert runner.main(['--out', str(out)]) == 0
    assert not out.exists()


def test_two_case_runner_reuses_completed_case_after_budget_stop(tmp_path, monkeypatch):
    domain, profile, settings = fixture()
    from rotclimate_v10.earth import EarthCase
    case = EarthCase(domain, np.full(domain.land.shape, -125.),
        np.zeros((12,)+domain.land.shape), domain.land.copy(),
        np.zeros(domain.land.shape), np.zeros(domain.land.shape, bool))
    from dataclasses import asdict
    protocol = {'code_sha256': runner.source_id(), 'settings': asdict(settings)}
    names = ('california', 'iberia')
    monkeypatch.setattr(runner, 'prepare', lambda *_: (protocol,
        dict.fromkeys(names, case), dict.fromkeys(names, profile),
        dict.fromkeys(names, np.zeros((12, 4)+domain.land.shape)),
        {name: {'score': 10.} for name in names}))
    calls = []
    stop_once = [True]
    def fake_case(job, *args, **kwargs):
        calls.append(job)
        assert kwargs['max_years'] == 6
        if 'iberia' in job and stop_once[0]:
            stop_once[0] = False
            raise base.BudgetStop()
        return {'score': 8., 'annual_rain_ratio': 1., 'wet_reference_coverage': 1.,
            'settling': {'passed': True}, 'evidence_sha256': {}}
    monkeypatch.setattr(night, 'run_case', fake_case)
    out = tmp_path/'experiment'
    first = runner.run(out, tmp_path)
    assert first['status'] == 'budget_reached' and set(first['cases']) == {'california'}
    second = runner.run(out, tmp_path)
    assert second['status'] == 'complete' and len(second['cases']) == 2
    assert calls.count('upper_air_california_g60_s41') == 1
    protocol['settings'] = {**protocol['settings'], 'humidity_scale': .8}
    with pytest.raises(ValueError, match='changed'):
        runner.run(out, tmp_path)
