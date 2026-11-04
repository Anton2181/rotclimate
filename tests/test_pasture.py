import numpy as np
import pytest
from harvest.pasture import forage_allocation,seasonal_forage,feed_diagnostics


def test_crop_and_grazing_land_are_disjoint_and_units_are_explicit():
    annual,crop,remaining=forage_allocation([1000,1000],[0,1],[1,1],aboveground_share=1,usable_share=1)
    np.testing.assert_allclose(annual,[1_000_000,400_000])
    np.testing.assert_allclose(crop+remaining,1)


def test_phenology_conserves_annual_budget_without_fabricating_cold_growth():
    t=np.tile([15.,-5.,-5.],(12,1));p=np.ones_like(t)*50
    supply,resolved=seasonal_forage(t,p,np.array([1200.,1200.,0.]))
    np.testing.assert_allclose(supply[:,0],100)
    assert resolved.tolist()==[True,False,True]
    assert np.isnan(supply[:,1]).all() and np.all(supply[:,2]==0)


def test_equal_annual_supply_can_have_different_seasonal_feed_gaps():
    supply=np.full((12,2),100.);supply[:,1]=0;supply[0,1]=1200
    r=feed_diagnostics(supply)
    np.testing.assert_allclose(r.annual_feed_units,1200/(6.25*365))
    np.testing.assert_allclose(r.lean_growth_fraction,[1,0])
    np.testing.assert_allclose(r.minimum_reserve_days,[0,11*365/12])
    np.testing.assert_array_equal(r.shortfall_bins,[0,9])
    assert r.maximum_ledger_residual<1e-9


def test_repeating_year_has_no_free_initial_stock_or_calendar_origin_effect():
    supply=np.zeros((12,1));supply[2]=1200
    a=feed_diagnostics(supply);b=feed_diagnostics(np.roll(supply,5,axis=0))
    np.testing.assert_allclose(a.minimum_reserve_days,b.minimum_reserve_days)
    np.testing.assert_array_equal(a.shortfall_bins,b.shortfall_bins)
    c=feed_diagnostics(supply*10)
    np.testing.assert_allclose(c.minimum_reserve_days,a.minimum_reserve_days)
    np.testing.assert_allclose(c.annual_feed_units,a.annual_feed_units*10)
    d=feed_diagnostics(supply,buffer_days=365)
    assert d.shortfall_bins[0]==0


def test_zero_forage_and_unknown_seasons_do_not_get_fake_zero_reserve_scores():
    r=feed_diagnostics(np.column_stack([np.zeros(12),np.full(12,np.nan)]))
    assert r.annual_feed_units[0]==0 and np.isnan(r.annual_feed_units[1])
    assert np.isnan(r.minimum_reserve_days).all() and np.isnan(r.shortfall_bins).all()


def test_invalid_shared_land_and_seasonal_inputs_are_rejected():
    with pytest.raises(ValueError):forage_allocation(1000,1.1,.2)
    with pytest.raises(ValueError):feed_diagnostics(np.ones((12,1)),demand_fraction=1.1)
    bad=np.ones((12,1));bad[0]=np.nan
    with pytest.raises(ValueError):feed_diagnostics(bad)
