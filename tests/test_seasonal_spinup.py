import numpy as np
import pytest
from rotclimate.seasonal import integration_order,CycleMonitor,LIMITS


@pytest.mark.parametrize('steps,primer',[(25,8),(73,24),(17,8)])
def test_default_keeps_the_exact_legacy_calendar(steps,primer):
    order,record_start=integration_order(steps,primer,0)
    assert order==list(range(steps-primer,steps))+list(range(steps))
    assert record_start==primer


def test_added_years_preserve_recorded_seasons_and_never_use_negative_indices():
    order,start=integration_order(5,12,3)
    assert all(0<=k<5 for k in order)
    assert order[start:]==list(range(5))
    assert all(b==(a+1)%5 for a,b in zip(order,order[1:]))
    assert len(order)==12+5*4


@pytest.mark.parametrize('years',[-1,True,1.5])
def test_fractional_negative_and_boolean_year_counts_are_rejected(years):
    with pytest.raises(ValueError):integration_order(25,8,years)


def fields(offset=0.):return {name:np.full((4,5),offset) for name in LIMITS}


def test_repeating_seasonal_forcing_passes_without_requiring_constant_weather():
    monitor=CycleMonitor(3,np.ones((4,5),bool))
    for _ in range(2):
        for season in range(3):monitor.update(season,fields(season*10.))
    report=monitor.report()
    assert report['checked'] and report['domain_repeats']
    assert all(row['domain_max_abs']==0 for row in report['comparisons'][-1]['fields'].values())


def test_stable_temperature_and_rain_cannot_hide_a_drifting_soil_reservoir():
    monitor=CycleMonitor(2,np.ones((4,5),bool))
    for season in range(2):monitor.update(season,fields())
    for season in range(2):
        values=fields();values['soil_water'][2,2]=1.;monitor.update(season,values)
    assert not monitor.report()['domain_repeats']
    assert monitor.report()['comparisons'][-1]['fields']['soil_water']['map_land_max_abs']==1.


def test_a_later_complete_cycle_can_converge_after_an_earlier_failure():
    monitor=CycleMonitor(2,np.ones((4,5),bool))
    for year in [0.,1.,1.]:
        for season in range(2):monitor.update(season,fields(year))
    assert [c['domain_repeats'] for c in monitor.report()['comparisons']]==[False,True]


def test_incomplete_or_misaligned_cycle_is_not_certified():
    monitor=CycleMonitor(2,np.ones((4,5),bool))
    monitor.update(0,fields())
    assert not monitor.report()['checked']
    with pytest.raises(ValueError):monitor.update(0,fields())


def test_required_repeatability_cannot_certify_an_unchecked_default_run():
    from types import SimpleNamespace
    from rotclimate.config import Params
    from rotclimate.model import ClimateModel
    model=ClimateModel.__new__(ClimateModel)
    model.p=Params(seasonal_require_convergence=True);model.g=SimpleNamespace()
    with pytest.raises(ValueError,match='at least one extra'):model.run()
