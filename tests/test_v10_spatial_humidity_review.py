"""Saved-evidence verification and cellwise seasonal decision criteria."""
from dataclasses import replace
import json
import numpy as np
import pytest
from experiments import v10_spatial_humidity as model
from scripts import review_v10_spatial_humidity as review
from tests.test_v10_split_column import five_fixture
from rotclimate_v10.earth import atomic_json, sha256


def test_seasonal_error_does_not_cancel_overwet_and_dry_cells():
    old = np.full((12, 1, 2), 10.); new = old.copy(); observed = old.copy()
    new[review.SUMMER, 0, 0] += 8.; new[review.SUMMER, 0, 1] -= 8.
    errors = review.seasonal_errors(old, new, observed, {'reference_arid': np.ones((1, 2), bool)})
    summer = errors['reference_arid']['summer']
    assert (new-observed).mean() == 0.
    assert summer['monthly_mae_change_mm'] == 8.
    assert summer['new_positive_bias_mm'] == summer['new_deficit_mm'] == 4.
    assert not review.process_screen('local_matched', 5., errors, True, True)['passes']


def test_primary_screen_preserves_coast_floor_and_requires_actual_arid_improvement():
    errors = {'reference_arid': {'summer': {'monthly_mae_change_mm': -1.}}}
    assert review.process_screen('local_matched', 2.18, errors, True, True)['passes']
    assert review.process_screen('local_matched', -2., errors, True, True)['passes']
    for variant, coast, settled, thermal in [('local', 3., True, True), ('local_matched', -2.01, True, True), ('local_matched', 3., False, True), ('local_matched', 3., True, False)]:
        assert not review.process_screen(variant, coast, errors, settled, thermal)['passes']
    assert not review.process_screen('local_matched', 1., {}, True, True)['passes']


@pytest.fixture
def saved(tmp_path, monkeypatch):
    run = review.run
    case, p, setting, g, air, circulation = five_fixture(False)
    case = replace(case, coast_distance_km=np.broadcast_to(np.array([50., 100., 200., 400., 500.]), case.domain.land.shape).copy())
    edges = np.arange(13, dtype=float)*12*3600.
    build = model.core.build_calendar
    monkeypatch.setattr(model.core, 'build_calendar', lambda *args, **kwargs: build(*args, **kwargs, edges=edges))
    monkeypatch.setattr(run.physics, 'EDGES', edges)
    original, _ = model.core.prepare_calendar(case, p, setting, g, air, circulation)
    q = model.core.core.boundary_ratio(case.domain, p, setting, g, air, 0.)
    profiles = np.broadcast_to(q, (12,)+q.shape).copy()
    tables, _ = model.prepare_tables(case, p, setting, g, air, circulation, original, profiles)
    driver = model.weather.Driver(original, case, p, setting, g, air, circulation, 16., 'aligned', 67)
    initial = run.physics.core.initial_state(case.domain, p, setting, g, air)
    anchor = run.physics.year(case.domain, p, setting, initial, air, case.score_mask, g, driver, condensation_mode='parcel_lower')
    jobs = [dict(key='control', region='california', mode='parcel_lower', variant='uniform', phase='control'),
            dict(key='test', region='california', mode='parcel_lower', variant='local_matched', phase='test')]
    protocol = {'code_sha256': run.source_id(), 'jobs': jobs, 'profile_array_sha256': {'california': 'toy'}}
    inputs = {'california': (case, p, g, air, circulation)}
    initials = {'california_parcel_lower': initial}; finals = {'california_parcel_lower': anchor}; originals = {'california': original}
    prepared = (protocol, inputs, setting, initials, finals, originals, {'california': profiles})
    preflight = tmp_path/'preflight'; monkeypatch.setattr(run, 'PREFLIGHT', preflight)
    atomic_json(preflight/'manifest.json', {'protocol': protocol})
    monkeypatch.setattr(run.run.previous, 'read_calendar', lambda *args: (tables, {}))
    out = tmp_path/'source'; atomic_json(out/'manifest.json', protocol)
    state = {'status': 'complete', 'cases': {}}
    for job in jobs:
        state['cases'][job['key']] = run.case_run(out/'cases'/job['key'], job, inputs, setting, initials, finals, originals, {'california': tables}, lambda: False, lambda *args: None, lambda *args: None, protocol['code_sha256'])
    atomic_json(out/'state.json', state)
    monkeypatch.setattr(run.physics, 'year', lambda *args, **kwargs: pytest.fail('Review must not integrate'))
    return out, prepared


def test_saved_review_reconstructs_actual_control_candidate_and_budgets(saved):
    out, prepared = saved
    protocol, state, inputs, finals, records, seconds, cycles, errors, dose = review.load_verified(out, prepared)
    assert len(records) == 2 and cycles == 1+state['cases']['test']['years']
    assert max(dose) < 1e-7
    assert max(abs(e['signed_temperature_c']) for e in errors) < 1e-8


@pytest.mark.parametrize('change', ['summary', 'thermal_ledger', 'evidence'])
def test_review_rejects_corruption_including_rehashed_diagnostics(saved, change):
    out, prepared = saved; folder = out/'cases'/'test'
    state = json.loads((out/'state.json').read_text()); row = state['cases']['test']
    if change == 'evidence':
        (folder/'year1.npz').write_bytes(b'corrupt')
    elif change == 'summary':
        row['coastal_winter_gain_mm'] += 1.
        atomic_json(folder/'summary.json', row); atomic_json(out/'state.json', state)
    else:
        path = folder/'year1.json'; meta = json.loads(path.read_text())
        meta['info']['diagnostics']['temperature_changes_scored_land_c'][0][0][0] += .5
        atomic_json(path, meta); row['evidence_sha256']['year1.json'] = sha256(path)
        atomic_json(folder/'summary.json', row); atomic_json(out/'state.json', state)
    with pytest.raises(ValueError):
        review.load_verified(out, prepared)


def test_default_is_read_only_and_write_cannot_overlap_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(review, 'analyse', lambda *args: ({}, {}, {}))
    monkeypatch.setattr(review, 'markdown', lambda *args: 'review')
    out = tmp_path/'absent'
    assert review.main(['--out', str(out)]) == 0 and not out.exists()
    for source, output in [(out, out), (out, out/'child'), (out/'child', out), (review.run.PREFLIGHT, review.run.PREFLIGHT/'child')]:
        with pytest.raises(ValueError, match='Preserve'):
            review.main(['--source', str(source), '--out', str(output), '--write'])
