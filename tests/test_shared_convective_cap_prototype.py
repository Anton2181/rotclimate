"""Dimensional and limiting cases for an offline shared convection cap."""
import numpy as np
from experiments.shared_convective_cap_prototype import shared_cap_components


def run(**changes):
    inputs=dict(water=np.array([40.]),saturation=np.array([50.]),dynamics=2.,instability=3.,threshold=.3,tau_days=10.,raw_convection=7.,cap=5.,subcloud_survival=.8)
    inputs.update(changes)
    return shared_cap_components(**inputs)


def test_all_convective_enhancement_respects_one_existing_cap():
    r=run()
    assert 0<r['pre_subcloud_convective_mm_day'][0]<5
    # The ordinary humidity/dynamics rain remains outside the convection cap.
    assert r['total_rain'][0]>r['convective'][0]


def test_no_bulk_instability_recovers_original_explicit_convection_cap():
    r=run(instability=1.)
    np.testing.assert_allclose(r['convective'],5*np.tanh(7/5)*.8,rtol=1e-15)


def test_uncapped_case_preserves_both_original_enhancements():
    r=run(cap=0.)
    expected=(2*((.8-.3)/.7)**1.5*3*40/10+7)*.8
    np.testing.assert_allclose(r['total_rain'],expected,rtol=1e-15)


def test_dry_and_supersaturated_column_limits_do_not_lose_overflow():
    r=run(water=np.array([0.]),raw_convection=0.)
    np.testing.assert_array_equal(r['total_rain'],[0.])
    r=run(water=np.array([60.]),dynamics=0.,raw_convection=0.)
    np.testing.assert_allclose(r['overflow'],[10.],atol=0,rtol=0)


def test_near_zero_water_keeps_original_column_mass_conversion():
    r=run(water=np.array([.01]),dynamics=0.,instability=1.)
    np.testing.assert_allclose(r['convective'],5*np.tanh(7/5)*.1*.8,rtol=1e-15)
