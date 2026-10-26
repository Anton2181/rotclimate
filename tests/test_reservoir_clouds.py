import numpy as np
import pytest
from rotclimate.moisture import rain_coefficient
from experiments.reservoir_clouds import layer_rain_rate,solve_layer_rain
from test_condensing_reservoirs import params,quiet_operator
from test_vertical_transport import setup_case


def test_old_profile_exactly_recovers_column_rain_including_convective_water_floor():
    p=params();total=np.array([[0.,.01,.05,.1,.2,1.,20.,80.]])
    fraction=np.array([.625,.375]);water=fraction[:,None,None]*total
    closure=dict(conv=.36,r0=.68,evap=.37,T=22.,fT=.7)
    rate=layer_rain_rate(water,40.,fraction,p,.5,closure=closure)
    expected=rain_coefficient(total,40.,.5,1.,p.rh_threshold,p.precip_tau_days,closure)
    np.testing.assert_allclose(rate,np.broadcast_to(expected,rate.shape),rtol=1e-14,atol=1e-18)
    np.testing.assert_allclose((rate*water).sum(0),expected*total,rtol=1e-14,atol=1e-18)


def test_independent_layer_supersaturation_has_known_water_and_rain_solution():
    op=quiet_operator();fraction=np.array([.625,.375]);known=np.broadcast_to(np.array([6.,5.])[:,None,None],(2,)+op.shape)
    source=np.broadcast_to(np.array([1.,2.])[:,None,None]/86400.,known.shape)
    result=solve_layer_rain(op,params(),source,8.,0.,known,fraction,guess=.9*known)
    np.testing.assert_allclose(result.water,known,atol=1e-7)
    np.testing.assert_allclose(result.layer_rain[:,1:-1,1:-1],source[:,1:-1,1:-1]*86400.,atol=1e-7)


def test_layer_cloud_equation_with_terrain_and_donor_vertical_transport_has_known_solution():
    op=setup_case();known=7*op.layer_mass;p=params(moisture_diffusion=60000.)
    fraction=np.array([.625,.375]);saturation=6*op.mass;drying=1/(20*86400.)
    rate=layer_rain_rate(known,saturation,fraction,p,.5)
    source=(rate+drying)*known
    result=solve_layer_rain(op,p,source,saturation,.5,known,fraction,drying=drying,guess=.9*known)
    np.testing.assert_allclose(result.water,known,atol=2e-7)
    assert result.scaled_residual<=1e-8
    terms,boundary=op.terms(result.water,diffusion=p.moisture_diffusion)
    equation=(source-drying*result.water)[:,1:-1,1:-1]*86400.+terms*86400.-result.layer_rain[:,1:-1,1:-1]
    assert np.max(np.abs(equation))<1e-7
    assert abs(((source-drying*result.water)*86400.-result.layer_rain)[:,1:-1,1:-1].sum()+boundary.sum()*86400.)<1e-6


@pytest.mark.parametrize('fractions',[[0,1],[.4,.4],[.5,np.nan]])
def test_invalid_capacity_profile_rejected(fractions):
    with pytest.raises(ValueError,match='capacity fractions'):
        layer_rain_rate(np.ones((2,3,4)),40.,fractions,params(),.5)
