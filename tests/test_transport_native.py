import numpy as np
from scripts.transport_native import partial_flux,G


def test_partial_column_uses_pressure_overlap_and_simultaneous_products():
    ps=np.full((2,3),100000.);mass=np.stack([.25*ps,.75*ps])/G
    w=np.stack([mass*.01,mass*.02])
    winds=np.zeros((2,2,2,2,3));winds[0,:,0]=2.;winds[1,:,0]=8.
    pw,flux=partial_flux(w,winds,ps)
    np.testing.assert_allclose(pw[0],.01*62500/G)
    np.testing.assert_allclose(pw[1],.02*62500/G)
    actual=flux.mean(0)/pw.mean(0)
    np.testing.assert_allclose(actual[0],6.)
    # Product-of-means would incorrectly yield5m/s.
    assert np.max(np.abs(actual[0]-winds[:,:,0].mean((0,1))))>.9
    np.testing.assert_array_equal(actual[1],0.)


def test_pressure_partial_flux_adds_across_adjacent_intervals():
    rng=np.random.default_rng(8);ps=rng.uniform(75000,101325,(3,4))
    w=rng.uniform(1,30,(5,2,3,4));v=rng.uniform(-5,5,(5,2,2,3,4))
    a=partial_flux(w,v,ps);b=partial_flux(w,v,ps,92500,70000);c=partial_flux(w,v,ps,70000,30000)
    for whole,lower,upper in zip(a,b,c):np.testing.assert_allclose(whole,lower+upper,atol=1e-14)
