import numpy as np
import pytest
from harvest.flood_timing import crop_flood_timing


def test_before_sowing_and_standing_crop_are_separate():
    q=np.zeros(12);q[8]=10.;r=crop_flood_timing(q)
    assert r['pre_sowing_excess_share'][10]==1. and r['standing_crop_excess_share'][10]==0. and r['compatibility'][10]==1.
    assert r['standing_crop_excess_share'][8]==1. and r['compatibility'][8]==0.


def test_january_wrap_uses_previous_year_months():
    q=np.zeros(12);q[11]=10.;r=crop_flood_timing(q)
    assert r['pre_sowing_excess_share'][0]==1. and r['standing_crop_excess_share'][0]==0.


def test_uniform_and_dry_flow_do_not_create_a_flood():
    for q in (np.zeros(12),np.ones(12)*9.):
        r=crop_flood_timing(q);assert not r['seasonal_excess_present'];assert not r['compatibility'].any()


def test_rotation_and_unit_scaling_invariant():
    q=np.array([1,1,2,4,6,4,2,1,1,1,1,1.]);r=crop_flood_timing(q)
    for name in ('pre_sowing_excess_share','standing_crop_excess_share','compatibility'):
        np.testing.assert_allclose(crop_flood_timing(np.roll(q,5))[name],np.roll(r[name],5))
        np.testing.assert_allclose(crop_flood_timing(q*1e100)[name],r[name])


def test_vector_columns_and_extreme_finite_flow():
    q=np.zeros((12,2));q[8,0]=np.finfo(float).max;q[4,1]=1.;r=crop_flood_timing(q)
    for j in range(2):
        a=crop_flood_timing(q[:,j]);np.testing.assert_array_equal(r['compatibility'][:,j],a['compatibility'])
    assert np.isfinite(r['compatibility']).all() and np.all((r['compatibility']>=0)&(r['compatibility']<=1))


@pytest.mark.parametrize('args',[
    dict(monthly_flow=np.ones(11)),dict(monthly_flow=np.r_[np.nan,np.ones(11)]),
    dict(monthly_flow=-np.ones(12)),dict(monthly_flow=np.ones(12),crop_months=True),
    dict(monthly_flow=np.ones(12),crop_months=10),dict(monthly_flow=np.ones(12),lead_months=0),
])
def test_invalid_or_overlapping_windows_refused(args):
    with pytest.raises(ValueError):crop_flood_timing(**args)
