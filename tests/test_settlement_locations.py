import numpy as np
import pytest
from scipy.spatial.distance import pdist

from polity.settlement_locations import fixed_count_sites, site_fields


def test_count_independent_of_history_and_no_global_rng_mutation():
    score = np.ones((50, 70)); eligible = np.ones(score.shape, bool)
    history = np.exp(-np.indices(score.shape)[1] / 10)
    np.random.seed(812)
    before = np.random.get_state()
    a = fixed_count_sites(score, eligible, 100, 3, seed=7)
    b = fixed_count_sites(score, eligible, 100, 3, seed=7, history=history)
    after = np.random.get_state()
    assert len(a.towns) == len(b.towns) == 100
    assert a.shortfall == b.shortfall == 0
    assert a.towns != b.towns
    assert all(np.array_equal(x, y) for x, y in zip(before, after))
    assert b == fixed_count_sites(score, eligible, 100, 3, seed=7, history=history)
    assert np.mean(np.array(b.towns)[:, 1]) < np.mean(np.array(a.towns)[:, 1])


def test_exclusion_eligibility_and_shortfall_never_relaxed():
    mask = np.zeros((30, 40), bool); mask[2:26, 3:32] = True
    a = fixed_count_sites(np.ones(mask.shape), mask, 500, 2, min_spacing_km=8)
    assert all(mask[y, x] for y, x in a.towns)
    assert len(set(a.towns)) == len(a.towns)
    assert pdist(np.array(a.towns) * 2).min() > 8 - 1e-10
    assert a.shortfall == 500 - len(a.towns) > 0


def test_zero_budget_and_zero_support_do_not_invent_sites():
    score = np.ones((4, 4)); mask = score.astype(bool)
    assert not fixed_count_sites(score, mask, 0, 1).towns
    r = fixed_count_sites(score, mask, 3, 1, history=np.zeros_like(score))
    assert r.shortfall == 3 and r.eligible_cells == 0


def test_weight_rescaling_and_prefix_consistency():
    score = np.arange(1, 501, dtype=float).reshape(20, 25); mask = score > 0
    a = fixed_count_sites(score, mask, 30, 1, seed=19)
    b = fixed_count_sites(score * 100, mask, 40, 1, seed=19)
    assert a.towns == b.towns[:30]


def test_water_and_marked_anchors_are_respected():
    land = np.ones((90, 90), bool); density = np.full(land.shape, 20.)
    water = np.full(land.shape, 200.); water[:, 43:47] = 0
    score, eligible = site_fields(density, land, water, np.zeros_like(land),
                                 np.zeros(land.shape), 5, aridity=np.zeros(land.shape), marked=[(45,45)])
    placed = fixed_count_sites(score, eligible, 100, 5)
    assert not eligible[45,45]
    assert all(min(water[y,x], (min(y+1,x+1,90-y,90-x))*5) <= 40 for y,x in placed.towns)
    assert all(np.hypot(y-45,x-45)*5 > 40 for y,x in placed.towns)


@pytest.mark.parametrize('count,cell,spacing', [(-1,1,0),(1.5,1,0),(True,1,0),(1,0,0),(1,1,-1)])
def test_invalid_requests_fail(count, cell, spacing):
    with pytest.raises(ValueError):
        fixed_count_sites(np.ones((4,4)), np.ones((4,4),bool), count, cell, min_spacing_km=spacing)


def test_bad_history_or_scores_fail():
    mask=np.ones((4,4),bool)
    for prior in (np.ones((3,3)),np.full((4,4),np.nan),np.full((4,4),-1)):
        with pytest.raises(ValueError):
            fixed_count_sites(np.ones((4,4)),mask,2,1,history=prior)
    with pytest.raises(ValueError):
        fixed_count_sites(np.full((4,4),np.inf),mask,2,1)
