from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

import pytest

from rotclimate.config import Params
from scripts import check_rainfall_transfer as T
from scripts.rainfall_metrics import LOSS_SPEC, loss


def setup_check(tmp_path, monkeypatch):
    bench = tmp_path/'benchmark'; (bench/'cases').mkdir(parents=True)
    params = json.loads(json.dumps(asdict(Params.from_json('atlases/earth_fit/params.json'))))
    candidate = tmp_path/'candidate.json'; candidate.write_text(json.dumps(params))
    protocol = dict(fits=dict(baseline=params, candidate=params), rainfall_loss=LOSS_SPEC,
                    cell_km=28, regions=['california'], region_specs=dict(california={}))
    (bench/'protocol.json').write_text(json.dumps(protocol))
    identity = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    row = json.loads(Path('output/climate_physics_20261023/rainfall_baseline/cases/baseline_california.json').read_text())
    row['identity'] = identity
    for fit in ['baseline', 'candidate']:
        row['fit'] = fit
        (bench/'cases'/f'{fit}_california.json').write_text(json.dumps(row))
    out = tmp_path/'review.json'
    monkeypatch.setattr(sys, 'argv', ['check', '--benchmark', str(bench), '--candidate', str(candidate), '--out', str(out)])
    return bench, out


def test_transfer_requires_actual_paired_nonincreasing_rainfall_errors(tmp_path, monkeypatch):
    bench, out = setup_check(tmp_path, monkeypatch)
    T.main()
    assert json.loads(out.read_text())['passed']
    path = bench/'cases/candidate_california.json'; row = json.loads(path.read_text())
    row['rainfall']['monthly_mae_mm'] *= 1.1
    row['climate']['rain']['monthly_mae_mm'] = row['rainfall']['monthly_mae_mm']
    row['rainfall']['loss'] = loss(row['climate'])
    path.write_text(json.dumps(row)); T.main()
    review = json.loads(out.read_text())
    assert not review['passed']
    assert 'monthly_mae_mm increased' in review['failures']


def test_transfer_cannot_use_a_different_selected_candidate(tmp_path, monkeypatch):
    bench, out = setup_check(tmp_path, monkeypatch)
    candidate = tmp_path/'candidate.json'; p = json.loads(candidate.read_text()); p['ocean_rh'] += .01
    candidate.write_text(json.dumps(p))
    with pytest.raises(ValueError, match='selected candidate'): T.main()


def test_failed_solver_cannot_pass_new_geography_check(tmp_path, monkeypatch):
    bench, out = setup_check(tmp_path, monkeypatch)
    path = bench/'cases/candidate_california.json'; row = json.loads(path.read_text())
    row['numerics']['all_checks_passed'] = False
    path.write_text(json.dumps(row)); T.main()
    assert not json.loads(out.read_text())['passed']
