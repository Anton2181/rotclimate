"""Equation reconstruction and observer isolation, not just exported schema."""
import numpy as np
from rotclimate.reservoir_moisture import solve_reservoir_moisture
from test_reservoir_moisture import solver,params
from scripts.transport_observer import TransportObserver


def run(observer=None):
    p=params(moisture_reservoir_rain_scheme='column-convection');s=solver()
    if observer is not None:s.reservoir_observer=observer
    zero=np.zeros(s.column_mass.shape);one=np.ones_like(zero)
    r=solve_reservoir_moisture(s,p,zero,zero,zero,zero,one/86400,1000*one,zero,1.,14*one,14*one,
        sink=one/(50*86400),lower_capacity_fraction=.625,ocean_lower_fraction=.625,
        closure=dict(conv=.3,r0=.68,fT=one,T=20*one,evap=.4))
    return r,s


def test_callback_cannot_mutate_current_or_next_state():
    expected,_=run();seen=[]
    def destroy(payload):
        seen.append(payload)
        for value in payload['fields'].values():value[...] = -1e6
        for value in payload['closure'].values():value[...] = -1e6
    actual,s=run(destroy)
    assert len(seen)==1
    for key in ('water','rain','layer_water','layer_rain','evaporation'):
        np.testing.assert_array_equal(getattr(actual,key),getattr(expected,key))
    np.testing.assert_array_equal(s.reservoir_water,expected.layer_water)
    assert actual.certificate==expected.certificate


def test_observer_reconstructs_actual_equation_and_rain_components():
    observer=TransportObserver(params(moisture_reservoir_rain_scheme='column-convection'))
    r,_=run(observer);f=observer.steps[0]
    np.testing.assert_array_equal(f['water'],r.layer_water)
    np.testing.assert_allclose(f['rain'],f['rain_dynamic']+f['rain_convective']+f['rain_overflow'],atol=1e-14)
    assert np.abs(f['residual']).max()<1e-8


def test_nonzero_counterflow_diffusion_and_storm_terms_reconstruct():
    from scipy.ndimage import gaussian_filter
    from rotclimate.column_mass import ColumnMassProjection
    from rotclimate.layer_transport import return_branches
    from rotclimate.storms import conservative_exchange
    shape=(7,9);projection=ColumnMassProjection(np.tile(np.linspace(0,3000,9),(7,1)),56000.)
    u=np.full(shape,6.);v=np.zeros(shape);ub,vb,_=projection.project(u,v)
    branches,_,_=return_branches(u,v,ub,vb,.2);winds=[(a,b) for _,a,b in branches]
    s=solver(shape,projection.mass,winds);p=params(moisture_diffusion=60000.,moisture_reservoir_rain_scheme='column-convection')
    o=TransportObserver(p);s.reservoir_observer=o
    loss,mix=conservative_exchange(np.full(shape,1e-5),lambda a:gaussian_filter(a,1,mode='reflect'),projection.mass)
    known=12*projection.mass;zero=np.zeros(shape)
    result=solve_reservoir_moisture(s,p,u,v,zero,zero,zero,np.full(shape,1000.),zero,1.,known,known,
        exchange=loss,mix=mix,lower_capacity_fraction=.25,ocean_lower_fraction=.25)
    f=o.steps[0]
    assert np.abs(f['vertical_water']).max()>0
    assert np.abs(f['advection']).max()>0
    np.testing.assert_allclose(result.layer_water,np.stack([.25*known,.75*known]),atol=1e-8)
    assert np.abs(f['residual']).max()<1e-8
