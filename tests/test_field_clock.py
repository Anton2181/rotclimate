import numpy as np
import pytest
from harvest.field_clock import FieldClock,field_clock


def test_fractional_capture_and_crop_windows_are_exact_and_disjoint():
    bins=np.linspace(0,365,13);a=365*7/12;b=365*10.5/12;c=365*2.5/12
    clock=field_clock(bins,event_edges_days=[a,b,c])
    flood=clock.cyclic_window(a,b);crop=clock.cyclic_window(b,c)
    assert not (flood&crop).any()
    assert clock.step_days[flood].sum()==pytest.approx(365*3.5/12)
    assert clock.step_days[crop].sum()==pytest.approx(365*4/12)
    assert b in clock.edges_days and clock.step_days.max()<=1


def test_each_bin_and_year_recover_multidimensional_input_totals():
    clock=field_clock(np.linspace(0,365.25,13),event_edges_days=[10.1,220.7])
    totals=np.arange(72).reshape(12,2,3);distributed=clock.spread_bin_totals(totals)
    for month in range(12):np.testing.assert_allclose(distributed[clock.bin_index==month].sum(0),totals[month],rtol=1e-14,atol=1e-12)
    np.testing.assert_allclose(distributed.sum(0),totals.sum(0),rtol=1e-14)


def test_rates_and_state_values_are_repeated_without_scaling():
    clock=field_clock(np.linspace(0,360,13),max_step_days=.5)
    values=np.arange(12)-5
    np.testing.assert_array_equal(clock.repeat_bin_values(values),values[clock.bin_index])
    assert clock.spread_bin_totals(np.ones(12))[0]==pytest.approx(.5/30)


def test_custom_calendar_and_fractional_last_day():
    bins=np.array([0,31,59,90,120,151,181,212,243,273,304,334,365.25])
    clock=field_clock(bins)
    assert clock.edges_days[-1]==365.25 and clock.step_days[-1]==.25
    assert np.isin(bins,clock.edges_days).all()


def test_full_and_empty_intervals_are_distinct():
    clock=field_clock(np.linspace(0,365,13))
    assert clock.cyclic_window(0,365).all() and not clock.cyclic_window(0,0).any()
    with pytest.raises(ValueError):clock.cyclic_window(10.1,20.1)


def test_soil_adapter_uses_each_segment_duration():
    from harvest.soil_drying import soil_profile,soil_state,soil_step
    clock=field_clock(np.linspace(0,2.5,13),event_edges_days=[.1,1.4])
    profile=soil_profile(.25,.1,2.,.1,9.);state=soil_state(profile,1.);uptake=0.
    for duration in clock.step_days:
        r=soil_step(profile,state,0.,1.,1.,1.,.55,step_days=float(duration))
        uptake+=float(r.root_uptake_mm);state=r.state
    assert uptake==pytest.approx(2.5)


@pytest.mark.parametrize('bins,events,step',[
    (np.linspace(0,365,12),[],1),(np.r_[np.zeros(2),np.linspace(1,365,11)],[],1),
    (np.linspace(1,365,13),[],1),(np.linspace(0,365,13),[-1],1),
    (np.linspace(0,365,13),[366],1),(np.linspace(0,365,13),[np.nan],1),
    (np.linspace(0,365,13),[],2),(np.linspace(0,365,13),[],0),
])
def test_invalid_clock_inputs_refused(bins,events,step):
    with pytest.raises(ValueError):field_clock(bins,event_edges_days=events,max_step_days=step)


def test_clock_cannot_skip_a_bin_boundary_or_accept_negative_totals():
    with pytest.raises(ValueError):FieldClock(np.linspace(0,365,13),np.arange(366))
    clock=field_clock(np.linspace(0,365,13))
    with pytest.raises(ValueError):clock.spread_bin_totals(-np.ones(12))
