"""Independent saturation roots, actual water/enthalpy and falling-rain limits."""
import numpy as np
import pytest
from scipy.optimize import brentq

from rotclimate.column_thermodynamics import CP, EPSILON, LV, specific_saturation
from rotclimate.phase_adjustment import equilibrate_liquid, falling_rain_column, saturation_vapor_mass


def independent_sat(t,m,p):
    es=611.2*np.exp(17.67*(t-273.15)/(t-29.65))
    return m*EPSILON*es/(p-es)


def test_dry_basis_saturation_matches_specific_humidity_conversion():
    t=np.array([230.,270.,300.]);p=np.array([25000.,60000.,95000.]);m=np.array([1500.,3000.,2200.])
    q=specific_saturation(t,p)
    np.testing.assert_allclose(saturation_vapor_mass(t,m,p),m*q/(1-q),rtol=1e-14)


@pytest.mark.parametrize('state',[(290.,90000.,2000.,.5,0.),(290.,90000.,2000.,1.5,0.),
                                (298.,85000.,2500.,.2,2.),(298.,85000.,2500.,.2,40.)])
def test_unique_phase_root_matches_independent_scalar_brent_and_energy(state):
    t,p,m,rh,liquid=state;water=rh*independent_sat(t,m,p)
    def f(x):return water+x-independent_sat(t-LV*x/(CP*m),m,p)
    if liquid and f(liquid)<=0:change=liquid
    elif f(0)>0:change=brentq(f,-water,0.,xtol=1e-13)
    elif liquid:change=brentq(f,0.,liquid,xtol=1e-13)
    else:change=0.
    out=equilibrate_liquid(t,water,m,p,liquid)
    assert out.vapor_kg_m2==pytest.approx(water+change,abs=1e-11)
    assert out.temperature_k==pytest.approx(t-LV*change/(CP*m),abs=1e-11)
    assert out.liquid_kg_m2==pytest.approx(liquid-change,abs=1e-11)
    assert CP*m*(out.temperature_k-t)+LV*(out.vapor_kg_m2-water)==pytest.approx(0.,abs=1e-6)
    assert out.vapor_kg_m2+out.liquid_kg_m2==pytest.approx(water+liquid,abs=1e-12)


def test_all_available_rain_evaporates_without_inventing_water():
    out=equilibrate_liquid(300.,1.,2000.,90000.,.5)
    assert out.vapor_kg_m2==1.5 and out.liquid_kg_m2==0.
    assert out.evaporated_kg_m2==.5 and out.condensed_kg_m2==0.
    assert out.temperature_k<300.


def test_condensation_feedback_removes_less_than_fixed_temperature_clipping():
    t,m,p=285.,2500.,85000.;sat=independent_sat(t,m,p)
    out=equilibrate_liquid(t,2*sat,m,p)
    assert 0<out.condensed_kg_m2<sat
    assert out.temperature_k>t
    assert out.vapor_kg_m2==pytest.approx(independent_sat(out.temperature_k,m,p),rel=1e-12)


def test_full_subcloud_evaporation_has_zero_ground_rain_with_opposing_heating():
    t=np.array([300.,245.]);m=np.array([2500.,6500.]);p=np.array([90000.,40000.])
    w=np.array([1.,1.4*independent_sat(t[1],m[1],p[1])])
    out=falling_rain_column(t,w,m,p)
    assert out.condensation_kg_m2[1]>0
    assert out.rain_evaporation_kg_m2[0]>0
    assert out.surface_rain_kg_m2==0
    assert out.sensible_heat_j_m2[1]>0 and out.sensible_heat_j_m2[0]<0
    assert out.sensible_heat_j_m2.sum()==pytest.approx(0.,abs=1e-7)
    assert out.vapor_kg_m2.sum()==pytest.approx(w.sum(),abs=1e-12)


def test_moist_lower_air_passes_some_upper_rain_and_column_budgets_close():
    t=np.array([290.,255.]);m=np.array([2500.,6500.]);p=np.array([90000.,40000.])
    w=np.array([.99*independent_sat(t[0],m[0],p[0]),1.6*independent_sat(t[1],m[1],p[1])])
    out=falling_rain_column(t,w,m,p)
    assert out.surface_rain_kg_m2>0
    assert out.surface_rain_kg_m2<out.condensation_kg_m2[1]
    assert w.sum()-out.vapor_kg_m2.sum()==pytest.approx(out.surface_rain_kg_m2,abs=1e-11)
    assert out.sensible_heat_j_m2.sum()==pytest.approx(LV*out.surface_rain_kg_m2,rel=1e-12)
    assert np.sum(CP*m*(out.temperature_k-t)+LV*(out.vapor_kg_m2-w))==pytest.approx(0.,abs=2e-6)


def test_both_layers_can_condense_without_double_counting_surface_water():
    t=np.array([285.,250.]);m=np.array([2000.,6000.]);p=np.array([90000.,40000.])
    w=1.4*saturation_vapor_mass(t,m,p)
    out=falling_rain_column(t,w,m,p)
    assert np.all(out.condensation_kg_m2>0)
    assert out.rain_evaporation_kg_m2.sum()==0
    assert out.surface_rain_kg_m2==pytest.approx(out.condensation_kg_m2.sum(),rel=1e-12)


@pytest.mark.parametrize('changes',[dict(vapor_kg_m2=-1),dict(dry_mass_kg_m2=0),
                                   dict(temperature_k=100),dict(liquid_kg_m2=-1),dict(pressure_pa=0)])
def test_invalid_column_rejected(changes):
    args=dict(temperature_k=290.,vapor_kg_m2=2.,dry_mass_kg_m2=2000.,pressure_pa=90000.)
    args.update(changes)
    with pytest.raises(ValueError):equilibrate_liquid(**args)
