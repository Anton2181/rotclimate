"""Independent dry limits, moist enthalpy differential and stability controls."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import CP,RD,LV,EPSILON
from rotclimate.moist_enthalpy import CP_VAPOR,REFERENCE_K,liquid_enthalpy,gas_enthalpy
from rotclimate.parcel_stability import parcel_profile,diagnose_parcel,_positive_linear_integral
from rotclimate.phase_adjustment import saturation_vapor_mass


def test_dry_parcel_matches_exact_adiabatic_power_law():
    p=np.geomspace(100000.,20000.,40);out=parcel_profile(p,300.,0.,max_log_pressure_step=.01)
    np.testing.assert_allclose(out.temperature_k,300*(p/p[0])**(RD/CP),rtol=2e-12)
    assert not out.lcl_in_column


def test_saturated_parcel_matches_actual_enthalpy_minus_exported_liquid_differential():
    p=np.array([100000.,99999.]);t=300.;r=float(saturation_vapor_mass(t,1.,p[0]))
    out=parcel_profile(p,t,r,max_log_pressure_step=1e-5);t1,r1=out.temperature_k[1],out.vapor_mixing_ratio[1]
    gas_change=gas_enthalpy(t1,r1,1.)-gas_enthalpy(t,r,1.)
    rain_export=liquid_enthalpy(.5*(t+t1),r-r1)
    compression=RD*.5*(t+t1)*np.log(p[1]/p[0])
    assert gas_change+rain_export==pytest.approx(compression,abs=1e-7)


def test_dry_neutral_environment_has_no_buoyancy():
    p=np.geomspace(100000.,25000.,40);env=300*(p/p[0])**(RD/CP);out=diagnose_parcel(p,env,np.zeros_like(p))
    assert out.positive_buoyancy_energy_j_kg<1e-6
    assert out.negative_buoyancy_energy_j_kg<1e-6


def test_isothermal_environment_negative_integral_matches_exact_dry_solution():
    x=np.linspace(0,1,257);p=100000*np.exp(-x);t=np.full_like(p,300.);out=diagnose_parcel(p,t,np.zeros_like(p))
    k=RD/CP;expected=RD*300*(1-(1-np.exp(-k))/k)
    assert out.positive_buoyancy_energy_j_kg==0
    assert out.negative_buoyancy_energy_j_kg==pytest.approx(expected,rel=2e-6)


def test_wet_stable_conditional_and_dry_controls_have_expected_stability_order():
    p=np.geomspace(100000.,38000.,30);wet=float(saturation_vapor_mass(300.,1.,p[0]));r=np.full_like(p,wet)
    stable=diagnose_parcel(p,300*(p/p[0])**.08,r)
    conditional=diagnose_parcel(p,300*(p/p[0])**.18,r)
    dry=diagnose_parcel(p,300*(p/p[0])**.18,np.zeros_like(p))
    assert stable.positive_buoyancy_energy_j_kg<1e-6
    assert conditional.positive_buoyancy_energy_j_kg>100
    assert dry.positive_buoyancy_energy_j_kg<1e-6


def test_sign_crossing_integral_splits_at_actual_zero():
    value=_positive_linear_integral(np.array([2.,-1.]),np.array([-2.,3.]),np.array([1.,2.]))
    np.testing.assert_allclose(value,[.5,2.25],atol=1e-15)


def test_coarse_column_resolves_inhibition_below_the_lcl_inside_first_pressure_interval():
    p=np.array([100000.,80000.,60000.,38000.]);t=300*(p/p[0])**.18
    q=.88*float(saturation_vapor_mass(t[0],1.,p[0]));out=diagnose_parcel(p,t,np.full_like(t,q))
    assert out.positive_buoyancy_energy_j_kg>100
    assert out.negative_buoyancy_energy_j_kg>1
    assert len(out.pressure_pa)>len(p)


def test_cloud_base_event_split_keeps_coarse_and_fine_parcel_paths_consistent():
    p=np.geomspace(100000.,38000.,20);q=.88*float(saturation_vapor_mass(300.,1.,p[0]))
    coarse=parcel_profile(p,300.,q,max_log_pressure_step=.04)
    fine=parcel_profile(p,300.,q,max_log_pressure_step=.002)
    np.testing.assert_allclose(coarse.temperature_k,fine.temperature_k,atol=2e-6)


def test_supersaturated_source_and_bad_pressure_order_are_rejected():
    p=np.array([100000.,80000.]);r=float(saturation_vapor_mass(300.,1.,p[0]))
    with pytest.raises(ValueError):parcel_profile(p,300.,r*1.1)
    with pytest.raises(ValueError):parcel_profile(p[::-1],300.,r)
