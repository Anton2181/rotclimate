import numpy as np
import pytest
from polity.seasonal_access import cyclic_isolation,seasonal_access


def test_cyclic_isolation_wraps_across_year_boundary():
    access=np.array([False,False,True,True,False,False])
    assert cyclic_isolation(access)==4
    assert cyclic_isolation(np.roll(access,2))==4


def test_always_and_never_accessible():
    r=seasonal_access(np.array([[1.,np.inf]]*12))
    assert r.access_mask.tolist()==[4095,0]
    assert r.accessible_months.tolist()==[12,0]
    assert r.longest_isolation.tolist()==[0,12]
    assert r.effective_days[0]==pytest.approx(1.) and np.isinf(r.effective_days[1])


def test_annual_mean_is_not_year_round_connection():
    r=seasonal_access(np.array([0.,0.]+[np.inf]*10))
    assert r.effective_days==pytest.approx(np.log(6)) and r.annual_threshold
    assert r.accessible_months==2 and r.longest_isolation==10


def test_more_access_cannot_increase_longest_isolation():
    days=np.array([[3.,5.],[1.,5.],[3.,1.],[3.,5.]])
    old=seasonal_access(days);new=seasonal_access(np.maximum(days-2,0))
    assert np.all(new.accessible_months>=old.accessible_months)
    assert np.all(new.longest_isolation<=old.longest_isolation)


@pytest.mark.parametrize('days',[[np.nan],[-1.],[],[0.]*13])
def test_invalid_time_fields_rejected(days):
    with pytest.raises(ValueError):seasonal_access(days)
