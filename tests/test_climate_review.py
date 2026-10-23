import copy
import hashlib
import json

import pytest

from scripts.review_climate_round import assess, baseline_seeds


def measurements():
    return dict(zonefit=.5, covered_score=.5, numerics=dict(all_checks_passed=True),
        zone_accuracy=.55, zone_recall=dict(cold_dry=.4, hot_dry=.6),
        mediterranean=dict(cs_share=.8, dry_share=.04),
        coverage=dict(outside_share=.012), strict=dict(score=.51, macro_hard=.35))


def test_better_headline_cannot_hide_class_or_numerical_regressions():
    base = measurements()
    new = copy.deepcopy(base);new['zonefit'] = .6
    assert assess(base, new, 'free')['eligible']
    new['zone_recall']['hot_dry'] = .55
    assert not assess(base, new, 'free')['eligible']
    new = copy.deepcopy(base);new['zonefit'] = .6
    new['numerics']['all_checks_passed'] = False
    assert not assess(base, new, 'earth')['eligible']


def test_whittaker_must_improve_its_score_without_more_grey_land():
    base = measurements()
    new = copy.deepcopy(base);new['covered_score'] = .52
    new['coverage']['outside_share'] = .013
    review = assess(base, new, 'whittaker')
    assert not review['eligible'] and any('outside-diagram' in s for s in review['failures'])
    new['coverage']['outside_share'] = .011
    assert assess(base, new, 'whittaker')['eligible']


def test_layout_ids_are_verified_from_either_checkpoint_format(tmp_path):
    path = tmp_path/'checkpoints'/'baseline.pkl'
    assert baseline_seeds(dict(identity=dict(seeds=[1,2,3])), path) == [1,2,3]
    protocol = dict(seeds=[1,2,3], name='test')
    (tmp_path/'protocol.json').write_text(json.dumps(protocol))
    key = hashlib.sha256(json.dumps(protocol, sort_keys=True).encode()).hexdigest()
    assert baseline_seeds(dict(identity=key), path) == [1,2,3]
    with pytest.raises(ValueError, match='verifiable'):
        baseline_seeds(dict(identity='other protocol'), path)
