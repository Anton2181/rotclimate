"""Independent limits for actual multi-source two-reservoir moisture equations."""
import numpy as np
import pytest
from scipy.ndimage import gaussian_filter
from rotclimate.config import Params
from rotclimate.layer_transport import LayerFluxSolver,return_branches
from rotclimate.reservoir_moisture import solve_reservoir_moisture
from rotclimate.reservoir_transport import ReservoirTransport,solve_block
from rotclimate.column_mass import ColumnMassProjection
from rotclimate.storms import conservative_exchange
from rotclimate.transport import vapor_face_fluxes,face_divergence


def params(**changes):
    return Params(moisture_diffusion=0.,moisture_relaxation=.15,moisture_residual_tol=1e-8,
        moisture_require_convergence=True,picard_iters=2048,moisture_reservoir_mixing_days=5.,
        convective_rain=0.,subcloud_evaporation=0.).replace(**changes)


def solver(shape=(5,6),mass=None,winds=None):
    mass=np.ones(shape) if mass is None else mass
    zero=np.zeros(shape);winds=((zero,zero),(zero,zero)) if winds is None else winds
    s=LayerFluxSolver(*shape,56000.,column_mass=mass)
    s.set_layers(((.625,*winds[0]),(.375,*winds[1])))
    s.rtol=1e-11;s.max_iter=2000;s.require_convergence=True;s.recover=True
    return s


def test_land_supply_vertical_exchange_and_drying_have_independent_two_box_solution():
    s=solver();shape=s.column_mass.shape;zero=np.zeros(shape)
    result=solve_reservoir_moisture(s,params(),zero,zero,zero,zero,np.ones(shape)/86400.,
        np.ones(shape)*1000.,zero,1.,np.ones(shape)*14.,np.ones(shape)*14.,
        sink=np.ones(shape)/(50*86400.),lower_capacity_fraction=.625,ocean_lower_fraction=.625)
    expected=np.linalg.solve([[.17,-.05],[-.15,.07]],[1.,0.])
    np.testing.assert_allclose(result.layer_water[:,1:-1,1:-1],np.broadcast_to(expected[:,None,None],(2,3,4)),atol=1e-6)
    np.testing.assert_array_equal(result.rain,0.)
    np.testing.assert_allclose(result.evaporation,1.)
    assert result.converged and result.certificate['all_layer_checks_passed']
    assert result.certificate['max_scaled_column_residual']<=1e-8


def test_ocean_exchange_responds_to_lower_humidity_and_has_exact_steady_budget():
    s=solver();shape=s.column_mass.shape;zero=np.zeros(shape);ones=np.ones(shape)
    result=solve_reservoir_moisture(s,params(),zero,zero,ones/(2*86400.),20*ones,zero,
        1000*ones,zero,1.,14*ones,14*ones,sink=ones/(50*86400.),
        lower_capacity_fraction=.625,ocean_lower_fraction=.625)
    # Ocean coefficient .5/.625=.8/day; vertical exchange .15/.05/day.
    expected=np.linalg.solve([[.97,-.05],[-.15,.07]],[10.,0.])
    np.testing.assert_allclose(result.layer_water[:,1:-1,1:-1],np.broadcast_to(expected[:,None,None],(2,3,4)),atol=1e-6)
    np.testing.assert_allclose(result.evaporation[1:-1,1:-1],.5*(20-expected[0]/.625),atol=1e-7)
    np.testing.assert_allclose(result.evaporation[1:-1,1:-1],result.water[1:-1,1:-1]/50,atol=1e-7)


def test_uniform_q_equilibrium_with_terrain_counterflow_diffusion_and_storms():
    shape=(7,9);projection=ColumnMassProjection(np.tile(np.linspace(0,3000,9),(7,1)),56000.)
    u=np.full(shape,6.);v=np.zeros(shape);ub,vb,_=projection.project(u,v)
    branches,_,_=return_branches(u,v,ub,vb,.2);winds=[(a,b) for _,a,b in branches]
    s=solver(shape,projection.mass,winds);p=params(moisture_diffusion=60000.)
    loss,mix=conservative_exchange(np.full(shape,1e-5),lambda a:gaussian_filter(a,1,mode='reflect'),projection.mass)
    known=12*projection.mass;zero=np.zeros(shape)
    result=solve_reservoir_moisture(s,p,u,v,zero,zero,zero,np.full(shape,1000.),zero,1.,known,known,
        exchange=loss,mix=mix,lower_capacity_fraction=.25,ocean_lower_fraction=.25)
    np.testing.assert_allclose(result.layer_water,np.stack([.25*known,.75*known]),atol=1e-8)
    assert result.converged and result.certificate['maximum_absolute_layer_residual_mm_day']<1e-8


def test_spatial_layer_fraction_is_applied_to_donor_water_before_flux():
    shape=(3,4);W=np.ones(shape)*10;W[:,2:]=20;f=np.ones(shape)*.8;f[:,2:]=.2
    u=np.ones(shape);v=np.zeros(shape)
    east,_=vapor_face_fluxes(W,u,v,layers=((f,u,v),(1-f,-u,v)),mass=np.ones(shape))
    # At the middle face: lower left donor8, opposed upper right donor16.
    assert east[1,1]==-8.


@pytest.mark.parametrize('seed',[8,9])
def test_spatial_fractions_matrix_matches_independent_directional_faces(seed):
    rng=np.random.default_rng(seed);shape=(7,9);mass=rng.uniform(.4,1.,shape);W=rng.uniform(1,20,shape)
    f=rng.uniform(.1,.9,shape);u,v=rng.normal(size=(2,)+shape)*4
    s=solver(shape,mass,((u,v),(-u/3,-v/3)));s.set_layers(((f,u,v),(1-f,-u/3,-v/3)))
    ce,cw,cs,cn,d=s.coefficients(u,v,60000.,1e-5)
    applied=(d*W+ce*np.roll(W,-1,1)+cw*np.roll(W,1,1)+cs*np.roll(W,-1,0)+cn*np.roll(W,1,0))[1:-1,1:-1]
    faces=[]
    for fraction,east,north in s.layers:
        q=fraction*W/mass;uf=.5*(east[:,:-1]+east[:,1:]);vf=-.5*(north[:-1]+north[1:])
        fx=.5*(mass[:,:-1]+mass[:,1:])*uf*np.where(uf>=0,q[:,:-1],q[:,1:])
        fy=.5*(mass[:-1]+mass[1:])*vf*np.where(vf>=0,q[:-1],q[1:])
        faces.append((fx,fy))
    fx=sum(x[0] for x in faces);fy=sum(x[1] for x in faces);q=W/mass
    fx-=60000*.5*(mass[:,:-1]+mass[:,1:])*np.diff(q,axis=1)/56000.
    fy-=60000*.5*(mass[:-1]+mass[1:])*np.diff(q,axis=0)/56000.
    expected=face_divergence(fx,fy,56000.)+1e-5*W[1:-1,1:-1]
    np.testing.assert_allclose(applied,expected,atol=1e-17)


def test_core_backend_keeps_sparse_fallback_without_numba(monkeypatch):
    import rotclimate.reservoir_transport as core
    shape=(5,6);zero=np.zeros(shape);op=ReservoirTransport(np.ones(shape),(zero,zero),(zero,zero),56000.)
    source=np.ones((2,)+shape)*1e-5;boundary=np.ones_like(source)
    monkeypatch.setattr(core,'HAVE_BLOCK_NUMBA',False)
    actual,c=solve_block(op,source,1e-5,boundary)
    expected,_=op.solve(source,1e-5,boundary)
    np.testing.assert_array_equal(actual,expected);assert c['method']=='sparse_no_numba'


@pytest.mark.parametrize('changes',[dict(moisture_reservoirs=True),dict(moisture_reservoirs='yes'),dict(moisture_reservoir_mixing_days=-1.)])
def test_unsupported_reservoir_configuration_rejected(changes):
    from rotclimate.model import ClimateModel
    with pytest.raises(ValueError):ClimateModel(Params(**changes))


def test_actual_coupled_reservoir_climate_has_individual_and_column_water_certificates():
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth
    from rotclimate.model import ClimateModel,ensemble_mean
    case=_toy_case();p=earth.earth_params(strict_params().replace(moisture_transport_form='flux',flux_convergence=0,
        eddy_moisture_scheme='conservative',moisture_mass_balance=True,moisture_two_layer=True,
        moisture_mass_tracer=True,moisture_reservoirs=True,moisture_relaxation=.1,picard_iters=1024),case)
    model=ClimateModel(p,grid=case.grid);result=model.run(diagnose_moisture=True)
    assert result.numerics['all_checks_passed']
    assert result.numerics['moisture_reservoirs']['all_layer_checks_passed']
    assert result.numerics['moisture_reservoirs']['max_scaled_layer_residual']<=p.moisture_residual_tol
    assert result.numerics['vapor_flux_budget']['max_scaled_equation_residual']<=p.moisture_residual_tol
    assert result.layer_water.shape==(result.nt,2,*case.grid.land.shape)
    np.testing.assert_allclose(result.layer_water.sum(1),result.W,rtol=2*np.finfo(np.float32).eps)
    # The old imposed humidity ratio must not control the solved state.
    other=ClimateModel(p.replace(moisture_upper_q_ratio=.8),grid=case.grid).run()
    np.testing.assert_array_equal(result.P,other.P);np.testing.assert_array_equal(result.W,other.W)
    mean=ensemble_mean([result,result])
    np.testing.assert_array_equal(mean.layer_water,result.layer_water)
