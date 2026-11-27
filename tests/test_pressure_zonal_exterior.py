"""Known exterior/kernel limits for the explicit pressure-boundary hypothesis."""
import numpy as np
from experiments.pressure_zonal_exterior import pressure_field
from scripts.circulation_components import pressure_velocity


def test_zero_thermal_anomaly_cannot_generate_pressure_or_wind():
    p=pressure_field(np.zeros((7,9)),2.,.5,1.8,.4)
    np.testing.assert_array_equal(p,np.zeros((7,9)))
    for a in pressure_velocity(p,30.,1e-5,56000.,7.292e-5,1.2):np.testing.assert_array_equal(a,p)


def test_uniform_finite_warm_patch_has_expected_missing_gaussian_mass():
    # Explicit separable kernel sum, rather than another Gaussian-filter call.
    sigma=2.;radius=int(4*sigma+.5)
    axis=np.arange(-radius,radius+1);kernel=np.exp(-.5*(axis/sigma)**2);kernel/=kernel.sum()
    p=pressure_field(np.ones((7,9)),sigma,.5,1.,0.)
    for row,col in [(0,0),(3,4),(6,8)]:
        ymass=kernel[(axis>=-row)&(axis<=6-row)].sum()
        xmass=kernel[(axis>=-col)&(axis<=8-col)].sum()
        np.testing.assert_allclose(p[row,col],-100*ymass*xmass,atol=5e-14,rtol=0)
    assert p[3,4]<p[0,0] # A finite warm patch has pressure gradients at its edge.


def test_pressure_wind_retains_signed_frictional_momentum_balance():
    a=np.arange(63.).reshape(7,9)/20
    p=pressure_field(a,2.,.5,1.8,.4)
    latitude=np.linspace(-10,40,7)[:,None];eps=np.full((7,9),1.4e-5)
    u,v=pressure_velocity(p,latitude,eps,56000.,7.292e-5,1.2)
    f=2*7.292e-5*np.sin(np.radians(latitude))
    px=np.gradient(p,axis=1)/56000.;py=-np.gradient(p,axis=0)/56000.
    np.testing.assert_allclose(eps*u-f*v,-px/1.2,atol=1e-18,rtol=1e-13)
    np.testing.assert_allclose(f*u+eps*v,-py/1.2,atol=1e-18,rtol=1e-13)
