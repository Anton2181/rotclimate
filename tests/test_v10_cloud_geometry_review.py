"""Independent saved geometry checks and bounds on separately recorded subsets."""
import json
import numpy as np
import pytest
from scripts import review_v10_cloud_geometry as review
from tests.test_v10_spatial_humidity_review import saved
from rotclimate_v10.earth import atomic_json, atomic_npz, sha256


def test_marginal_bounds_contain_all_possible_weighted_intersections():
    # Four nonuniform populations: neither, first only, second only, both.
    rng = np.random.default_rng(5)
    for _ in range(100):
        weights = rng.random(4); weights /= weights.sum()
        lo, hi = review.overlap_bounds(weights[1]+weights[3], weights[2]+weights[3])
        assert lo-1e-14 <= weights[3] <= hi+1e-14
    assert review.overlap_bounds(.9494, .9980) == pytest.approx([.9474, .9494])
    assert review.overlap_bounds(None, .5) is None
    with pytest.raises(ValueError):
        review.overlap_bounds(1.1, .5)


@pytest.fixture
def geometry_saved(saved, tmp_path, monkeypatch):
    run = review.run; source, parent_prepared = saved
    _, inputs, setting, old_initials, _, originals, profiles = parent_prepared
    _, state, _, _, records, _, _, _, _ = run.review.load_verified(source, parent_prepared)
    monkeypatch.setattr(run.model.physical, 'EDGES', np.arange(13)*12*3600.)
    job = dict(key='california_uniform', region='california', variant='uniform', mode='parcel_lower', source_case='control', source_year=1)
    initials = {job['key']: old_initials['california_parcel_lower']}; finals = {job['key']: records['control']}
    tables = {'california': run.forcing.read_calendar(None, None)[0]}
    protocol = {'code_sha256': run.source_id(), 'jobs': [job]}
    out = tmp_path/'geometry'; atomic_json(out/'manifest.json', protocol)
    row = run.replay_case(out/'cases'/job['key'], job, inputs, setting, initials, finals, originals, tables,
        lambda: False, lambda *args: None, lambda *args: None, protocol['code_sha256'])
    atomic_json(out/'state.json', {'status': 'complete', 'cases': {job['key']: row}})
    monkeypatch.setattr(run.model.physical, 'year', lambda *args, **kwargs: pytest.fail('Review must not integrate'))
    return out, (protocol, inputs, setting, initials, finals, originals, tables)


def test_saved_actual_replay_verifies_without_integration(geometry_saved):
    out, prepared = geometry_saved
    protocol, state, inputs, records, collectors, seconds, errors, paths = review.load_verified(out, prepared)
    assert len(records) == len(collectors) == 1
    assert max(paths) < 1e-6
    assert max(abs(e['water_mm']) for e in errors) < 1e-6


@pytest.mark.parametrize('change', ['summary', 'pressure_weight', 'subset', 'missing_case'])
def test_rejects_rehashed_diagnostic_corruption(geometry_saved, change):
    out, prepared = geometry_saved; folder = out/'cases/california_uniform'
    state = json.loads((out/'state.json').read_text()); row = state['cases']['california_uniform']
    if change == 'missing_case':
        state['cases'].clear()
    elif change == 'summary':
        row['regions']['coast']['winter']['total_rain_mm'] += 1.
    else:
        with np.load(folder/'year1.npz', allow_pickle=False) as a:
            arrays = {key:a[key].copy() for key in a.files}
        metric = 5 if change == 'pressure_weight' else 3
        arrays['geometry_metrics'][0, metric, 0, 0, 0] += 1000.
        atomic_npz(folder/'year1.npz', **arrays)
        meta = json.loads((folder/'year1.json').read_text()); meta['array_sha256'] = sha256(folder/'year1.npz')
        atomic_json(folder/'year1.json', meta)
        row['evidence_sha256'] = {name:sha256(folder/name) for name in ('year1.json', 'year1.npz')}
    atomic_json(folder/'summary.json', row); atomic_json(out/'state.json', state)
    with pytest.raises(ValueError):
        review.load_verified(out, prepared)


def test_default_is_read_only_and_write_cannot_overlap_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(review, 'analyse', lambda *args: {})
    monkeypatch.setattr(review, 'markdown', lambda *args: 'review')
    absent = tmp_path/'absent'
    assert review.main(['--out', str(absent)]) == 0 and not absent.exists()
    for source, out in ((absent, absent), (absent, absent/'child'), (absent/'child', absent), (review.run.PREFLIGHT, review.run.PREFLIGHT/'child')):
        with pytest.raises(ValueError, match='Preserve'):
            review.main(['--source', str(source), '--out', str(out), '--write'])
