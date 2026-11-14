import datetime as dt

import numpy as np
import pytest

from harvest.reference_eto import daily_reference,extraterrestrial_radiation
from harvest.reference_forcing import daily_from_radiation,mean_year_bin_totals,one_degree_cells


def test_earth_adapter_matches_frozen_reference_on_same_supplied_radiation():
    lat=np.array([24.,30.,34.]);day=np.array([15,180,300]);ra=extraterrestrial_radiation(lat,day)['ra_mj_m2_day']
    old=daily_reference(20.,10.,30.,1.,2.,100.,18.,lat,day,100.)
    new=daily_from_radiation(20.,10.,30.,1.,2.,100.,18.,ra,100.)
    for name,value in new.items():np.testing.assert_allclose(value,old[name],atol=2e-14,rtol=1e-14)


def test_world_radiation_is_used_without_earth_calendar_or_geometry():
    ra=np.array([10.,20.,40.]);before=ra.copy()
    r=daily_from_radiation(20.,10.,30.,1.,2.,100.,10.,ra,100.)
    np.testing.assert_array_equal(ra,before)
    np.testing.assert_array_equal(r['ra_mj_m2_day'],ra)
    np.testing.assert_allclose(r['hargreaves_mm_day']/ra,np.full(3,r['hargreaves_mm_day'][0]/10))
    assert len(set(r['rso_mj_m2_day']))==3


@pytest.mark.parametrize('ra',[0,-1,np.nan,None])
def test_missing_or_invalid_world_radiation_is_rejected(ra):
    with pytest.raises(ValueError):daily_from_radiation(20,10,30,1,2,100,20,ra,100)


def test_leap_year_month_totals_preserve_mean_annual_amount():
    dates=[dt.date(2020,1,1)+dt.timedelta(days=i) for i in range(731)]
    years=np.array([d.year for d in dates]);months=np.array([d.month-1 for d in dates])
    amount=np.column_stack([np.ones(731),np.arange(731)/100])
    original=amount.copy();totals=mean_year_bin_totals(years,months,amount)
    assert totals[1,0]==28.5 and totals[:,0].sum()==365.5
    np.testing.assert_allclose(totals.sum(0),amount.sum(0)/2)
    np.testing.assert_array_equal(amount,original)


def test_non_earth_period_labels_and_bin_count_do_not_invent_calendar():
    result=mean_year_bin_totals([7,7,8,8],[0,1,0,1],[0.,4.,2.,6.],bin_count=2)
    np.testing.assert_array_equal(result,[1.,5.])


def test_monthly_amounts_remain_conserved_when_model_steps_are_fractional():
    from harvest.field_clock import field_clock
    clock=field_clock(np.linspace(0,365,13),event_edges_days=[365*10.5/12,365*2.5/12])
    amounts=np.arange(24).reshape(12,2)+10.
    rates=clock.repeat_bin_values(amounts/np.diff(clock.bin_edges_days)[:,None])
    for month in range(12):
        select=clock.bin_index==month
        np.testing.assert_allclose((rates[select]*clock.step_days[select,None]).sum(0),amounts[month],rtol=2e-14)


@pytest.mark.parametrize('years,bins,amounts',[
    ([],[],[]),([1,1],[0,0],[1,1]),([1.,1.],[0,1],[1,1]),([1,1],[0.,1.],[1,1]),
    ([1,1],[0,2],[1,1]),([1,1],[0,1],[1,-1]),([1,1],[0,1],[1,np.nan]),
    ([1,1],[0,1],[1]),
])
def test_invalid_or_missing_year_bins_are_explicit(years,bins,amounts):
    with pytest.raises(ValueError):mean_year_bin_totals(years,bins,amounts,bin_count=2)


def test_half_open_tiles_handle_boundaries_and_negative_coordinates():
    a,b=one_degree_cells([24.999,25,30.5,-.001], [31.99,32,31.5,-.001])
    np.testing.assert_array_equal(a,[24,25,30,-1]);np.testing.assert_array_equal(b,[31,32,31,-1])


@pytest.mark.parametrize('lat,lon',[(90,0),(-91,0),(0,180),(0,-181),(np.nan,0)])
def test_invalid_mapping_coordinates_are_rejected(lat,lon):
    with pytest.raises(ValueError):one_degree_cells(lat,lon)
