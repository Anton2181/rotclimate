import numpy as np
import pytest
from harvest.field_support import field_support,fixed_rural_food


def test_peak_reaping_cannot_borrow_idle_winter_hours():
    args=dict(rural_need_kcal=[1e6],worker_fraction=1,ration_kcal_day=1e6/360,year_days=360,hours_worker_year=300,hours_worker_day=8)
    tight=field_support([1e6],[200],[80],harvest_days=5,**args)
    wide=field_support([1e6],[200],[80],harvest_days=10,**args)
    assert tight.retained[0]==.5 and wide.retained[0]==1
    assert tight.annual_hours_used[0]==100 and tight.reaping_hours_used[0]==40


def test_annual_and_reaping_hours_share_the_same_workers():
    a=field_support([1e6],[200],[80],rural_need_kcal=[1e6],worker_fraction=1,ration_kcal_day=1e6/360,year_days=360,hours_worker_year=100,harvest_days=30,hours_worker_day=8)
    assert a.retained[0]==.5 and a.annual_hours_used[0]==100 and a.reaping_hours_used[0]==40
    assert a.reaping_hours_available[0]==100
    assert a.produced_kcal[0]==500000


def test_food_claim_does_not_shrink_when_labour_curbs_harvest():
    a=fixed_rural_food(np.array([1000.]),np.array([1],np.uint16),np.array([600.]),loss_fraction_year=0)
    b=fixed_rural_food(np.array([500.]),np.array([1],np.uint16),np.array([600.]),loss_fraction_year=0)
    assert a.year.needed[0]==b.year.needed[0]==600
    assert a.exportable.sum()==pytest.approx(400)
    assert b.year.unmet[0]>0 and b.exportable.sum()==0


def test_no_workforce_creates_no_grain_but_does_not_erase_food_needs():
    a=field_support([1e6],[200],[80],rural_need_kcal=[600000.],worker_fraction=0)
    assert a.produced_kcal[0]==0 and a.rural_reference_people[0]>0
    b=fixed_rural_food(a.produced_kcal,np.array([1],np.uint16),np.array([600000.]))
    assert b.exportable.sum()==0 and b.year.unmet[0]==600000


def test_more_time_never_reduces_supported_activity():
    rng=np.random.default_rng(4);n=50;annual=rng.uniform(1e4,1e6,n);listed=rng.uniform(100,400,n);reap=listed*.2
    a=field_support(annual,listed,reap,rural_need_kcal=annual*.6,hours_worker_year=300,harvest_days=10)
    b=field_support(annual,listed,reap,rural_need_kcal=annual*.6,hours_worker_year=600,harvest_days=30)
    assert np.all(a.retained<=b.retained)
    assert np.all(b.annual_hours_used<=b.annual_hours_available+1e-7)
    assert np.all(b.reaping_hours_used<=b.reaping_hours_available+1e-7)


def test_impossible_resource_calendar_fails():
    with pytest.raises(ValueError):field_support([1e6],[10],[20],rural_need_kcal=[1e6])
    with pytest.raises(ValueError):field_support([1e6],[20],[10],rural_need_kcal=[1e6],hours_worker_year=4000)
