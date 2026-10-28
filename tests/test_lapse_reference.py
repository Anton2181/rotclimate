"""Independent hydrostatic lapse/isothermal limits, stability and inversion."""
import numpy as np
import pytest
from scipy.optimize import brentq
from rotclimate.column_thermodynamics import CP,G,RD
from rotclimate.lapse_reference import lapse_reference,height_at_pressure


def test_troposphere_matches_exact_hydrostatic_power_law_and_theta_gradient():
    z=np.linspace(0,10000,101);out=lapse_reference(z,surface_temperature_k=300.,lapse_k_m=.006)
    expected_t=300-.006*z;expected_p=101325*(expected_t/300)**(G/(RD*.006))
    np.testing.assert_allclose(out.temperature_k,expected_t,rtol=1e-14)
    np.testing.assert_allclose(out.pressure_pa,expected_p,rtol=1e-14)
    np.testing.assert_allclose(out.stability_s2,G/expected_t*(G/CP-.006),rtol=1e-14)
    np.testing.assert_allclose(out.density_kg_m3,expected_p/(RD*expected_t),rtol=1e-14)


def test_isothermal_limit_has_analytic_pressure_and_positive_stability():
    z=np.array([0.,5000.,15000.]);out=lapse_reference(z,surface_temperature_k=280.,lapse_k_m=0.)
    np.testing.assert_allclose(out.pressure_pa,101325*np.exp(-G*z/(RD*280)),rtol=1e-14)
    np.testing.assert_allclose(out.stability_s2,G*G/(CP*280),rtol=1e-14)
    np.testing.assert_allclose(height_at_pressure(out.pressure_pa,surface_temperature_k=280.,lapse_k_m=0.),z,atol=1e-10)


def test_tropopause_temperature_and_pressure_are_continuous_and_stability_changes_explicitly():
    zt=(280-210)/.006;out=lapse_reference(np.array([zt-1e-5,zt,zt+1e-5]),surface_temperature_k=280.,tropopause_temperature_k=210.)
    assert np.ptp(out.temperature_k)<1e-6
    assert np.ptp(out.pressure_pa)<1e-3
    assert out.stability_s2[1]>out.stability_s2[0]
    assert out.temperature_k[1]==210.


@pytest.mark.parametrize('pressure',[85000.,30000.,10000.,5000.])
def test_pressure_depth_inverse_matches_independent_scalar_root(pressure):
    kwargs=dict(surface_temperature_k=285.,surface_pressure_pa=101325.,lapse_k_m=.006,tropopause_temperature_k=210.)
    exact=brentq(lambda z:float(lapse_reference(np.array(z),**kwargs).pressure_pa)-pressure,0,30000)
    actual=float(height_at_pressure(pressure,**kwargs))
    assert actual==pytest.approx(exact,abs=1e-8)


@pytest.mark.parametrize('gamma',[G/CP,.02,-.001])
def test_unstable_or_negative_reference_lapse_rejected_without_floor(gamma):
    with pytest.raises(ValueError):lapse_reference(np.array([0.,10000.]),lapse_k_m=gamma)
