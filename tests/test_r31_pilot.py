import copy
import json
from pathlib import Path

import pytest

from scripts.review_r31_rainfall_pilot import assess
from scripts.local_benchmark_protocol import identity


def inputs():
    folder = Path('output/rainfall_r31_20261023/reference')
    reference = json.loads((folder/'summary.json').read_text())
    rp = json.loads((folder/'protocol.json').read_text())
    plan = json.loads(Path('calibration/rainfall_r31_20261023/plan.json').read_text())
    cp = copy.deepcopy(rp)
    cp['regions'] = plan['pilot_regions']
    cp['region_specs'] = {n:rp['region_specs'][n] for n in cp['regions']}
    cp['params'][plan['parameter']] = plan['candidates'][0]
    candidate = copy.deepcopy(reference)
    candidate['identity'] = identity(cp)
    candidate['regions'] = {n:candidate['regions'][n] for n in cp['regions']}
    for row in candidate['regions'].values():
        row['identity'] = candidate['identity']
        row['rain']['loss'] *= .98
        row['rain']['monthly_mae_mm'] *= .98
    return reference,candidate,rp,cp,plan


def test_pilot_can_advance_rainfall_gain_but_never_temperature_damage():
    b,c,bp,cp,p = inputs()
    assert assess(b,c,bp,cp,p)['eligible_for_dev31']
    for row in c['regions'].values(): row['temperature']['monthly_mae_C'] *= 1.02
    review = assess(b,c,bp,cp,p)
    assert not review['eligible_for_dev31']
    assert 'Temperature error increased by more than 1%' in review['failures']


def test_pilot_global_gain_cannot_hide_bad_regional_monthly_rainfall():
    b,c,bp,cp,p = inputs()
    c['regions']['california']['rain']['monthly_mae_mm'] *= 1.5
    review = assess(b,c,bp,cp,p)
    assert not review['eligible_for_dev31']
    assert 'california: monthly rainfall MAE regressed beyond protection' in review['failures']


def test_different_observation_inputs_cannot_be_a_pilot_gain():
    b,c,bp,cp,p = inputs()
    c['regions']['california']['case_identity'] = 'changed observations'
    with pytest.raises(ValueError, match='Unpaired observed'): assess(b,c,bp,cp,p)
