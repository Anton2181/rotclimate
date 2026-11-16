import numpy as np
import pytest
from scipy.optimize import brentq

from polity.urban_concentration import area_from_people, redistribute
from polity.settlement_sizes import residents


def test_hand_allocation_and_saturation():
    np.testing.assert_allclose(redistribute([20]*3, [1,2,9], [0]*3, [100]*3, 100), [5,10,45])
    np.testing.assert_allclose(redistribute([20]*3, [1,2,9], [0]*3, [100,100,35], 100), [25/3,50/3,35])


def test_exact_identity_and_inactive():
    b = np.array([0., 123.456, 900.])
    np.testing.assert_array_equal(redistribute(b,b,[0,100,100],[0,1000,1000],2000),b)
    a = redistribute(b,[0,1,20],[0,100,100],[0,1000,1000],2000)
    assert a[0] == 0 and abs(a.sum()-b.sum()) < 1e-9
    assert redistribute([],[],[],[],0).size == 0


@pytest.mark.parametrize('reading', ['low', 'central'])
def test_inverse_against_scalar_root(reading):
    import math
    def direct(a):
        d = 100 if reading == 'low' else 100+400*max(0,min(1,math.log(max(a,1e-9)/50)/math.log(8)))
        return a*d
    p = np.array([0,100,5000,5001,17000,199999,200000,891500.])
    expected = [0 if x == 0 else brentq(lambda a: direct(a)-x,0,x/100+1) for x in p]
    np.testing.assert_allclose(area_from_people(p,reading),expected,atol=1e-10,rtol=1e-12)
    np.testing.assert_allclose(residents(area_from_people(p,reading),reading),p,atol=1e-8)


def test_random_bounded_root_oracle():
    rng = np.random.default_rng(51)
    for _ in range(30):
        lo = rng.uniform(0,100,15); hi = lo+rng.uniform(1,2000,15)
        b = lo+(hi-lo)*rng.random(15); w = np.exp(rng.normal(size=15))
        root = brentq(lambda v: sum(min(h,max(l,v*x)) for h,l,x in zip(hi,lo,w))-sum(b),0,max(hi/w),xtol=1e-10)
        expected = [min(h,max(l,root*x)) for h,l,x in zip(hi,lo,w)]
        np.testing.assert_allclose(redistribute(b,w,lo,hi,float(sum(b)+100)),expected,atol=1e-7,rtol=1e-10)


@pytest.mark.parametrize('b,w,lo,hi,p', [
    ([1],[1],[2],[3],10), ([4],[1],[0],[3],10),
    ([1],[0],[0],[3],10), ([1],[-1],[0],[3],10),
    ([1],[float('nan')],[0],[3],10), ([1],[1],[0],[3],.9),
    ([1],[1],[0],[3],float('inf')), ([0],[1],[0],[0],10),
    ([1,2],[1],[0],[3],10), ([[1]],[[1]],[[0]],[[3]],10),
])
def test_invalid_allocations(b,w,lo,hi,p):
    with pytest.raises(ValueError): redistribute(b,w,lo,hi,p)


@pytest.mark.parametrize('p,reading', [([-1],'central'),([float('nan')],'low'),([1],'other')])
def test_invalid_inverse(p,reading):
    with pytest.raises(ValueError): area_from_people(p,reading)
