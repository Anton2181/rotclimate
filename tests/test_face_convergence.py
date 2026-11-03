import numpy as np
from scripts.diagnose_face_convergence import operator_difference


def test_uniform_water_difference_is_exact_compression():
    y,x=np.mgrid[:7,:9];u=np.asarray(4-x,float);v=np.asarray(y-3,float)
    delta,compression,remainder=operator_difference(np.full(u.shape,10.),u,v,56000.)
    np.testing.assert_allclose(delta[1:-1,1:-1],compression[1:-1,1:-1],atol=1e-14)
    np.testing.assert_allclose(compression[1:-1,1:-1],86400*20/56000,atol=1e-14)
    np.testing.assert_allclose(remainder[1:-1,1:-1],0,atol=1e-14)


def test_constant_wind_difference_vanishes_for_arbitrary_water():
    water=np.random.default_rng(3).uniform(0,40,(7,9));u=np.full(water.shape,2.);v=np.full(water.shape,-3.)
    for a in operator_difference(water,u,v,56000.):
        np.testing.assert_allclose(a[1:-1,1:-1],0,atol=1e-13)
