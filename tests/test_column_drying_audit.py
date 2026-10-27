"""Manufactured monthly ledgers and covariance, without Earth cache or integration."""
import numpy as np
import pytest
from scripts.audit_column_drying import (check_source_closure, effective_sink_rates,
                                         check_layer_water)


def ledger():
    shape=(12,2,3)
    fields={name:np.full(shape,value) for name,value in {
        'evaporation':10.,'advection':3.,'diffusion':.5,'storm_exchange':-1.,
        'column_drying':-4.,'monsoon_drying':-1.,'convergence_import':0.,
        'simulated':8.5,'observed':9.,'residual':0.}.items()}
    mask=np.array([[True,True,False],[True,False,False]])
    # Excluded ocean/border cells must not contaminate the scored-domain check.
    for field in fields.values():field[:,~mask]=np.nan
    return fields,mask


def test_signed_ledger_counts_monsoon_only_inside_total_drying():
    fields,mask=ledger()
    check_source_closure(fields,mask)
    fields['simulated'][:,mask]-=1.  # Incorrectly subtracting monsoon twice.
    with pytest.raises(ValueError):check_source_closure(fields,mask)


def test_drying_subset_and_nonfinite_data_fail_closed():
    fields,mask=ledger()
    fields['monsoon_drying'][:,mask]=-5.  # Larger removal than the total.
    with pytest.raises(ValueError):check_source_closure(fields,mask)
    fields,mask=ledger();fields['evaporation'][0,0,0]=np.nan
    with pytest.raises(ValueError):check_source_closure(fields,mask)


def test_effective_sink_is_water_weighted_not_mean_prescribed_rate():
    # Two equal-duration states: (W,k)=(1,.2),(10,0). The monthly product
    # is mean(kW)=.1, so k_eff=.1/5.5, rather than mean(k)=.1 per day.
    days=np.full(12,30.)
    rate,tau=effective_sink_rates(np.full((12,1),-3.),np.full((12,1),5.5),days)
    np.testing.assert_allclose(rate,.1/5.5)
    np.testing.assert_allclose(tau,55.)
    zero_rate,zero_tau=effective_sink_rates(np.zeros((12,1)),np.ones((12,1)),days)
    np.testing.assert_array_equal(zero_rate,0.)
    assert np.isinf(zero_tau).all()
    # Twelve spatial cells must not make a trailing-axis broadcast look valid.
    variable_days=np.arange(1.,13.)
    rate,_=effective_sink_rates(-np.broadcast_to(variable_days[:,None],(12,12)),
                                np.ones((12,12)),variable_days)
    np.testing.assert_allclose(rate,1.)
    with pytest.raises(ValueError):
        effective_sink_rates(np.zeros((12,1)),np.ones((12,1)),np.ones(11))


def test_empty_water_does_not_identify_a_removal_coefficient():
    rate,tau=effective_sink_rates(np.zeros((12,1)),np.zeros((12,1)),30.)
    assert np.isnan(rate).all() and np.isnan(tau).all()
    with pytest.raises(ValueError):
        effective_sink_rates(-np.ones((12,1)),np.zeros((12,1)),30.)


def test_saved_layer_sum_accepts_roundoff_but_rejects_missing_water():
    layers=np.ones((12,2,2,3))
    total=layers.sum(1)
    check_layer_water(total,layers)
    with pytest.raises(ValueError):check_layer_water(total+.01,layers)
    with pytest.raises(ValueError):check_layer_water(total,layers.swapaxes(0,1))
