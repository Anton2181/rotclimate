"""Known limiting rates ensure component units and attenuation are explicit."""
import numpy as np
from scripts.rain_closure_components import components


def closure(conv=0.,cap=0.,evap=0.):
    return dict(conv=np.array([conv]),r0=np.array([.5]),fT=np.array([1.]),
        T=np.array([20.]),cap=np.array([cap]),evap=np.array([evap]))


def test_subthreshold_column_has_no_base_rain():
    r=components(np.array([10.]),np.array([100.]),4.,3.,.3,2.,closure())
    for name in ['base','convective','overflow']:np.testing.assert_array_equal(r[name],[0.])


def test_supersaturation_removes_excess_column_mm_per_day_without_tau_factor():
    r=components(np.array([150.]),np.array([100.]),0.,1.,.3,7.,closure())
    np.testing.assert_allclose(r['overflow'],[50.],atol=1e-13,rtol=0)
    np.testing.assert_array_equal(r['base']+r['convective'],[0.])


def test_base_rate_has_days_and_explicit_humidity_instability_factors():
    r=components(np.array([10.]),np.array([20.]),4.,3.,0.,2.,closure())
    np.testing.assert_allclose(r['base'],[10*4*3*.5**1.5/2],rtol=1e-15)


def test_convective_cap_precedes_subcloud_loss_and_cancels_column_unit():
    r=components(np.array([50.]),np.array([100.]),0.,1.,.3,7.,closure(100.,4.,.5))
    expected=4*np.tanh(100/4)*np.exp(-.5*24*50/3000)
    np.testing.assert_allclose(r['convective'],[expected],rtol=1e-15)
