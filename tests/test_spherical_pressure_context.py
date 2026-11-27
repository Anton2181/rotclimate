"""Geometry/operator checks only; no regional climate or skill claims."""
import numpy as np
from experiments.spherical_pressure_context import sphere_grid,spherical_gaussian,pressure_from_global_anomaly


def test_exact_spherical_areas_and_constant_response():
    _,_,area=sphere_grid(10,20)
    np.testing.assert_allclose(area.sum(),4*np.pi,rtol=2e-15)
    constant=np.full((10,20),3.)
    np.testing.assert_allclose(spherical_gaussian(constant,1800.),constant,rtol=2e-15)
    np.testing.assert_allclose(pressure_from_global_anomaly(constant,2500.,800.,.7,.2),-210.,atol=1e-12)


def test_periodic_longitude_rotation_and_hemisphere_reflection():
    field=np.random.default_rng(0).normal(size=(10,20))
    filtered=spherical_gaussian(field,2200.)
    np.testing.assert_allclose(spherical_gaussian(np.roll(field,7,axis=1),2200.),
                               np.roll(filtered,7,axis=1),rtol=0.,atol=2e-14)
    np.testing.assert_allclose(spherical_gaussian(field[::-1],2200.),filtered[::-1],rtol=0.,atol=2e-14)


def test_broad_limit_is_area_weighted_not_pixel_weighted():
    field=np.zeros((10,20));field[-1]=8.
    _,_,area=sphere_grid(10,20)
    expected=(field*area).sum()/area.sum()
    result=spherical_gaussian(field,1e12)
    np.testing.assert_allclose(result,expected,atol=1e-14)
    assert abs(expected-field.mean())>.5


def test_off_crop_heat_low_changes_inside_without_local_anomaly():
    lat,lon,_=sphere_grid(20,40)
    field=np.where((lat>20)&(lat<40)&(lon>40)&(lon<70),8.,0.)
    crop=(lat>0)&(lat<20)&(lon>-10)&(lon<20)
    assert (field[crop]==0).all()
    pressure=pressure_from_global_anomaly(field,3000.,1000.,.7,.2)
    assert np.ptp(pressure[crop])>1.
    assert np.max(np.abs(pressure[crop]))>1.


def test_first_spherical_harmonic_converges_to_continuum_kernel():
    from scipy.integrate import quad
    sigma = 2500./6371.
    def kernel(theta):
        return np.exp(-.5*(theta/sigma)**2)*np.sin(theta)
    denominator = quad(kernel,0,np.pi,epsabs=1e-12)[0]
    multiplier = quad(lambda theta:kernel(theta)*np.cos(theta),0,np.pi,epsabs=1e-12)[0]/denominator
    errors=[]
    for nlat in [8,16,32]:
        lat,lon,_=sphere_grid(nlat,2*nlat)
        harmonic=np.cos(np.deg2rad(lat))*np.cos(np.deg2rad(lon))
        filtered=spherical_gaussian(harmonic,2500.)
        errors.append(float(np.max(np.abs(filtered-multiplier*harmonic))))
    assert errors[2]<errors[1]<errors[0]
    assert errors[2]<errors[0]/4
    assert errors[2]<.001
