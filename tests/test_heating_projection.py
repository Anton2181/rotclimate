"""Physical units, heat recovery and independent log-pressure integration."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import CP,G,RD
from rotclimate.heating_projection import pressure_layer_mass,project_layer_heating


def test_uniform_specific_heating_has_analytic_hydrostatic_thickness_tendency():
    edges=np.array([100000.,75000.,40000.,10000.])
    mass=np.diff(-edges)/G;per_kg=.004
    out=project_layer_heating(edges,mass*per_kg)
    assert out.forcing_m2_s3==pytest.approx(RD*per_kg/CP*np.log(10),rel=1e-14)
    np.testing.assert_allclose(out.temperature_tendency_k_s,per_kg/CP,rtol=1e-14)
    assert out.column_heating_w_m2==pytest.approx(per_kg*90000/G,rel=1e-14)


def test_vertical_heating_dipole_changes_thickness_even_when_column_heat_is_zero():
    edges=np.array([100000.,75000.,10000.]);heat=np.array([-60.,60.])
    out=project_layer_heating(edges,heat)
    assert out.column_heating_w_m2==0
    assert out.forcing_m2_s3>0
    dt=600.;temp=np.array([292.,250.])
    before=RD*np.sum(temp*np.log(edges[:-1]/edges[1:]))
    after=RD*np.sum((temp+out.temperature_tendency_k_s*dt)*np.log(edges[:-1]/edges[1:]))
    assert (after-before)/dt==pytest.approx(out.forcing_m2_s3,rel=1e-10)


def test_resolved_layer_averages_converge_to_independent_continuous_pressure_integral():
    # Heating per dry kg = s0*p/ps, whose integral against dlogp is analytic.
    s0=.005;ps=100000.;pt=10000.;expected=RD*s0/CP*(1-pt/ps)
    errors=[]
    for n in [4,8,16]:
        edges=np.linspace(ps,pt,n+1)
        heat=s0*(edges[:-1]**2-edges[1:]**2)/(2*ps*G)
        out=project_layer_heating(edges,heat)
        errors.append(abs(out.forcing_m2_s3-expected))
    assert errors[1]<.3*errors[0] and errors[2]<.3*errors[1]


def test_heat_projection_supports_spatial_pressure_without_changing_column_input():
    ps=np.array([[101325.,85000.],[95000.,70000.]])
    edges=np.stack([ps,ps-.25*(ps-10000.),np.full_like(ps,10000.)])
    heat=np.array([[[20.,30.],[40.,50.]],[[5.,10.],[15.,20.]]])
    out=project_layer_heating(edges,heat)
    np.testing.assert_allclose(out.layer_mass_kg_m2,pressure_layer_mass(edges),rtol=1e-15)
    np.testing.assert_allclose(CP*out.layer_mass_kg_m2*out.temperature_tendency_k_s,heat,rtol=1e-15)
    np.testing.assert_array_equal(out.column_heating_w_m2,heat.sum(0))


@pytest.mark.parametrize('edges',[np.array([10000.,75000.,100000.]),np.array([100000.,100000.,10000.]),np.array([100000.,75000.,0.])])
def test_invalid_pressure_rejected(edges):
    with pytest.raises(ValueError):project_layer_heating(edges,np.ones(2))
