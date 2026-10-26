"""Known nonlinear column rain and independently balanced layer equations."""
import numpy as np
import pytest
from rotclimate.config import Params
from rotclimate.moisture import rain_coefficient
from experiments.two_reservoir_transport import VerticalTransport
from experiments.condensing_reservoirs import solve_column_rain
from test_vertical_transport import setup_case


def params(**updates):
    return Params(moisture_diffusion=0.,moisture_relaxation=.15,moisture_residual_tol=1e-8,
                  picard_iters=2048,rh_threshold=.4,precip_tau_days=2.).replace(**updates)


def quiet_operator(mix=0.):
    shape=(5,6);zero=np.zeros(shape)
    return VerticalTransport(np.ones(shape),(zero,zero),(zero,zero),56000.,mixing_rate=mix)


def test_nonlinear_column_overflow_has_exact_known_total_and_layer_water():
    op=quiet_operator();known=8*op.layer_mass;source=6*op.layer_mass/86400.
    result=solve_column_rain(op,params(),source,2.,0.,known,guess=.8*known)
    np.testing.assert_allclose(result.water,known,atol=1e-7)
    np.testing.assert_allclose(result.layer_rain[:,1:-1,1:-1],6*op.layer_mass[:,1:-1,1:-1],atol=1e-7)
    assert result.scaled_residual<=1e-8


def test_no_cloud_rain_vertical_mix_matches_independent_two_box_equations():
    op=quiet_operator(mix=1/(5*86400.));source=np.zeros((2,)+op.shape);source[0]=1/86400.
    boundary=14*np.broadcast_to(np.array([.625,.375])[:,None,None],source.shape)
    result=solve_column_rain(op,params(),source,1000.,0.,boundary,drying=1/(50*86400.))
    # Independent daily exchange equations: .15 lower->upper, .05 return.
    expected=np.linalg.solve([[.17,-.05],[-.15,.07]],[1.,0.])
    np.testing.assert_allclose(result.water[:,1:-1,1:-1],np.broadcast_to(expected[:,None,None],(2,3,4)),atol=1e-6)
    np.testing.assert_array_equal(result.layer_rain,0)
    assert np.max(np.abs((source-result.water/(50*86400.))[:,1:-1,1:-1].sum(0)))<1e-12


def test_full_nonlinear_equilibrium_over_terrain_preserves_known_uniform_specific_humidity():
    op=setup_case();known=7*op.layer_mass;p=params(moisture_diffusion=60000.)
    saturation=6*op.mass;coefficient=rain_coefficient(known.sum(0),saturation,.5,1.,p.rh_threshold,p.precip_tau_days)
    source=(coefficient+1/(20*86400.))*known
    result=solve_column_rain(op,p,source,saturation,.5,known,drying=1/(20*86400.),guess=.9*known)
    np.testing.assert_allclose(result.water,known,atol=2e-7)
    terms,boundary=op.terms(result.water,diffusion=p.moisture_diffusion)
    residual=(source-result.water/(20*86400.))[:,1:-1,1:-1]*86400.+terms*86400.-result.layer_rain[:,1:-1,1:-1]
    assert np.max(np.abs(residual))<1e-7
    np.testing.assert_allclose(residual.sum(),(source-result.water/(20*86400.))[:,1:-1,1:-1].sum()*86400.+boundary.sum()*86400.-result.layer_rain[:,1:-1,1:-1].sum(),atol=1e-12)


def test_iteration_limit_cannot_be_accepted_on_a_small_damped_update():
    op=quiet_operator();known=8*op.layer_mass
    with pytest.raises(RuntimeError,match='nonlinear equation failed'):
        solve_column_rain(op,params(picard_iters=1,moisture_relaxation=1e-6),6*op.layer_mass/86400.,2.,0.,known,guess=.8*known)


@pytest.mark.parametrize('capacity',[0.,np.nan])
def test_invalid_saturation_rejected(capacity):
    op=quiet_operator();water=op.layer_mass.copy()
    with pytest.raises(ValueError,match='positive saturation'):
        solve_column_rain(op,params(),water/86400.,capacity,.5,water)
