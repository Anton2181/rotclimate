import numpy as np
import pytest

from polity.earth_component_work import component_work


def run(*,energy=(100.,100.),area=(1.,1.),listed=(400.,400.),reap=(20.,20.),phase=(3,3),rural=2.5,hours=600):
    column=lambda a:np.array(a)[:,None]
    return component_work(column(energy),column(area),column(listed),column(reap),column(phase),np.array([rural]),hours=hours)


def test_components_cannot_each_claim_the_full_annual_workforce():
    w=run()
    assert w.workers[0]==1 and w.annual_available[0]==600
    assert w.retained[0]==.75
    np.testing.assert_array_equal(w.produced_components[:,0],[75,75])
    assert w.annual_used[0]==600


def test_same_month_reaping_is_shared_and_distinct_months_keep_one_annual_budget():
    common=dict(listed=(200.,200.),reap=(200.,200.))
    same=run(**common,phase=(3,3));separate=run(**common,phase=(3,8))
    assert same.retained[0]==.6 and separate.retained[0]==1
    assert same.monthly_peak_used[3,0]==240
    np.testing.assert_array_equal(separate.monthly_peak_used[[3,8],0],[200,200])
    assert separate.annual_used[0]==400 and separate.annual_available[0]==600


def test_zero_energy_component_is_not_an_independent_crop_activity():
    w=run(energy=(100,0),area=(1,10000),phase=(3,-1))
    np.testing.assert_array_equal(w.active_area[:,0],[1,0])
    assert w.retained[0]==1 and w.annual_used[0]==400
    assert w.produced_total[0]==100


def test_zero_workforce_cannot_produce_or_duplicate_grain():
    w=run(rural=0)
    assert w.retained[0]==0 and w.produced_total[0]==0
    assert w.annual_used[0]==0 and w.monthly_peak_used.sum()==0


def test_common_retention_preserves_component_mix_in_300h_stress():
    w=run(energy=(100,300),hours=300)
    np.testing.assert_array_equal(w.produced_components[:,0],[37.5,112.5])
    assert w.annual_used[0]==300


def test_unavailable_cell_retains_zero_and_requires_no_calendar():
    w=run(energy=(0,0),area=(0,0),listed=(0,0),reap=(0,0),phase=(-1,-1))
    assert w.retained[0]==0 and w.produced_total[0]==0


@pytest.mark.parametrize('kwargs',[{'phase':(12,3)},{'area':(0,1)},{'listed':(0,400)},{'reap':(401,20)},{'rural':-1},{'hours':500}])
def test_invalid_physical_activity_is_rejected(kwargs):
    with pytest.raises(ValueError):run(**kwargs)
