"""Rain drag heating, phase feedback and complete static-energy budgets."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import G
from rotclimate.moist_enthalpy import gas_enthalpy,moist_falling_rain
from rotclimate.phase_adjustment import saturation_vapor_mass
from rotclimate.falling_water_energy import adjust_falling_water


def column(lower_rh=.98):
    t=np.array([298.,250.]);m=np.array([2500.,6500.]);p=np.array([90000.,40000.])
    w=saturation_vapor_mass(t,m,p)*[lower_rh,1.6]
    return t,w,m,p


def test_drag_heating_closes_actual_static_energy_and_precipitation_export():
    t,w,m,p=column();z=np.array([1875.,9375.]);out=adjust_falling_water(t,w,m,p,z,3750.)
    before=gas_enthalpy(t,w,m)+G*(m+w)*z
    after=gas_enthalpy(out.temperature_k,out.vapor_kg_m2,m)+G*(m+out.vapor_kg_m2)*z
    assert after.sum()+out.ground_rain_enthalpy_j_m2==pytest.approx(before.sum(),abs=1e-6)
    assert w.sum()==pytest.approx(out.vapor_kg_m2.sum()+out.ground_rain_kg_m2,abs=1e-11)
    expected=G*(out.condensation_kg_m2[1]*7500+out.ground_rain_kg_m2*1875)
    assert out.fall_dissipation_j_m2.sum()==pytest.approx(expected,rel=1e-13)
    assert np.all(out.fall_dissipation_j_m2>0)
    assert out.fall_dissipation_j_m2[1]==pytest.approx(.75*G*7500*out.condensation_kg_m2[1],rel=1e-13)


def test_omitting_fall_work_fails_static_energy_budget_by_exact_released_potential():
    t,w,m,p=column();z=np.array([1875.,9375.]);old=moist_falling_rain(t,w,m,p)
    before=gas_enthalpy(t,w,m)+G*(m+w)*z
    after=gas_enthalpy(old.temperature_k,old.vapor_kg_m2,m)+G*(m+old.vapor_kg_m2)*z
    lost=before.sum()-after.sum()-old.ground_rain_enthalpy_j_m2
    release=G*(old.condensation_kg_m2[1]*7500+old.ground_rain_kg_m2*1875)
    assert lost==pytest.approx(release,rel=1e-12)
    assert lost>100000


def test_all_rain_reevaporates_but_fall_potential_heats_air_and_closes_static_budget():
    t,w,m,p=column(.1);z=np.array([1875.,9375.]);out=adjust_falling_water(t,w,m,p,z,3750.)
    assert out.ground_rain_kg_m2==0
    assert out.condensation_kg_m2[1]==pytest.approx(out.evaporation_kg_m2[0],rel=1e-12)
    assert gas_enthalpy(out.temperature_k,out.vapor_kg_m2,m).sum()-gas_enthalpy(t,w,m).sum()==pytest.approx(out.fall_dissipation_j_m2.sum(),abs=1e-6)


def test_drag_warming_reduces_upper_condensation_relative_to_no_dissipation():
    t,w,m,p=column();old=moist_falling_rain(t,w,m,p)
    out=adjust_falling_water(t,w,m,p,np.array([1875.,9375.]),3750.)
    assert out.condensation_kg_m2[1]<old.condensation_kg_m2[1]
    assert out.temperature_k[1]>old.temperature_k[1]


def test_small_heights_recover_previous_enthalpy_only_limit():
    t,w,m,p=column();old=moist_falling_rain(t,w,m,p)
    out=adjust_falling_water(t,w,m,p,np.array([1e-6,5e-6]),2e-6)
    np.testing.assert_allclose(out.temperature_k,old.temperature_k,rtol=1e-10,atol=1e-9)
    np.testing.assert_allclose(out.vapor_kg_m2,old.vapor_kg_m2,rtol=1e-9,atol=1e-8)


@pytest.mark.parametrize('interface',[1000.,11000.,np.nan])
def test_invalid_fall_geometry_rejected(interface):
    t,w,m,p=column()
    with pytest.raises(ValueError):adjust_falling_water(t,w,m,p,np.array([1875.,9375.]),interface)
