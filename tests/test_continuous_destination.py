import numpy as np
import pytest

from polity.continuous_destination import ContinuousDestinationFeedback,continuous_food_ceiling
from polity.settlement_support import permanent_food_ceiling
from polity.settlement_feedback import FeedbackInputs


def fixture(**changes):
    x=FeedbackInputs(np.array([100.]),np.array([0]),np.array([72000.]),np.array([1],np.uint16),
        np.array([100.]),np.array([25.]),np.ones((12,1),bool),np.array([100.]),np.array([True]),np.array([72000.]))
    options=dict(outward_days=np.ones((12,1)),inward_days=np.ones((12,1)),load_kcal=6000.,monthly_open=np.ones(12,bool),
        transfer_fraction=.5,hours_worker_year=600,worker_fraction=1.,kcal_day=1.,year_days=360.,rural_store_days=360.,export_store_days=360.,destination_store_days=90.,
        loss_fraction_year=.05,collection_fraction=1.,retention=1.,delay_bins=0,institutional_request=10.,minimum_community=5.)
    options.update(changes);return ContinuousDestinationFeedback(x,**options)


def test_continuous_destination_keeps_finite_people_grain_staff_and_work():
    m=fixture();before={k:np.array(v,copy=True) for k,v in vars(m.x).items()};r=m.solve(scan_intervals=4,refinements=4)
    assert r['total'][0]>0 and r['staff'][0]==10
    assert r['total'][0]+r['rural'][0]==pytest.approx(100.)
    assert r['town_food'].unmet[0]<=1e-8*max(1.,r['town_food'].needed[0])
    assert np.all(r['collection_hours']<=r['staff_gross_hours']) and r['source_supported'][0]
    np.testing.assert_array_equal(r['plan'].food_year.unmet,r['town_food'].unmet)
    assert r['plan'].food_ceiling_people[0]>=r['total'][0]*(1-2e-8)
    for k,v in before.items():np.testing.assert_array_equal(getattr(m.x,k),v)


def test_continuous_food_check_cannot_reuse_monthly_meals_first_success():
    m=fixture();arrivals=np.full((12,1),30.);target=np.array([1.])
    result=m._food(arrivals,target,record=False)
    assert result.unmet[0]>0 and result.spoiled[0]>0


def test_displayed_ceiling_uses_new_inventory_and_zero_capacity_refuses_pulses():
    arrivals=np.full((12,2),30.)
    old=permanent_food_ceiling(arrivals,kcal_day=1.,year_days=360.,loss_fraction_year=.05)
    new=continuous_food_ceiling(arrivals,kcal_day=1.,year_days=360.,loss_fraction_year=.05)
    assert (new<old).all() and (new>0).all()
    zero=continuous_food_ceiling(arrivals,kcal_day=1.,year_days=360.,store_days=0.)
    assert not zero.any()


def test_zero_resources_and_bad_units_do_not_create_a_population():
    m=fixture(transfer_fraction=0.);r=m.solve(scan_intervals=4,refinements=0)
    assert not r['total'].any() and not r['flow']['origin_departures'].any()
    for kwargs in [dict(kcal_day=0),dict(store_days=-1),dict(loss_fraction_year=1)]:
        with pytest.raises(ValueError):continuous_food_ceiling(np.ones((12,1)),**kwargs)


def test_versioned_factory_restores_original_writer_on_failure(monkeypatch,tmp_path):
    from scripts import build_continuous_destination as adapter
    original=adapter.BASE.DispatchFeedback
    def fail(*args):
        assert adapter.BASE.DispatchFeedback is not original
        raise RuntimeError('manufactured writer failure')
    monkeypatch.setattr(adapter.BASE,'run',fail)
    with pytest.raises(RuntimeError,match='manufactured writer failure'):
        adapter.run('raw',600,tmp_path)
    assert adapter.BASE.DispatchFeedback is original
