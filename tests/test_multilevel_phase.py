"""Actual multi-interface rain transfer, drag feedback and static energy."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import G
from rotclimate.moist_enthalpy import gas_enthalpy,equilibrate_moist
from rotclimate.phase_adjustment import saturation_vapor_mass
from rotclimate.falling_water_energy import adjust_falling_water
from rotclimate.multilevel_phase import adjust_multilevel_fall


@pytest.mark.parametrize('lower_rh',[.1,.98])
def test_two_cell_limit_matches_existing_full_fall_energy_kernel(lower_rh):
    t=np.array([298.,250.]);m=np.array([2500.,6500.]);p=np.array([90000.,40000.]);z=np.array([1875.,9375.]);edges=np.array([0.,3750.,15000.])
    w=saturation_vapor_mass(t,m,p)*[lower_rh,1.6]
    old=adjust_falling_water(t,w,m,p,z,3750.)
    new=adjust_multilevel_fall(t,w,m,p,edges,z)
    for key in ['temperature_k','vapor_kg_m2','ground_rain_kg_m2','ground_rain_enthalpy_j_m2']:
        np.testing.assert_allclose(getattr(new,key),getattr(old,key),rtol=1e-12,atol=1e-9)
    np.testing.assert_allclose(new.fall_heat_j_m2,old.fall_dissipation_j_m2,rtol=1e-12,atol=1e-8)


def setup():
    t=np.array([300.,285.,268.,250.]);p=np.array([95000.,80000.,60000.,40000.]);m=np.array([1000.,2000.,3000.,2000.])
    edges=np.array([0.,1000.,3000.,6000.,10000.]);z=.5*(edges[:-1]+edges[1:])
    return t,p,m,edges,z


def test_four_layers_close_actual_water_rain_enthalpy_and_all_fall_potential():
    t,p,m,edges,z=setup();w=saturation_vapor_mass(t,m,p)*[.95,.98,1.4,1.8]
    out=adjust_multilevel_fall(t,w,m,p,edges,z)
    before=gas_enthalpy(t,w,m)+G*(m+w)*z;after=gas_enthalpy(out.temperature_k,out.vapor_kg_m2,m)+G*(m+out.vapor_kg_m2)*z
    assert out.ground_rain_kg_m2>0
    assert before.sum()==pytest.approx(after.sum()+out.ground_rain_enthalpy_j_m2,abs=2e-6)
    assert w.sum()==pytest.approx(out.vapor_kg_m2.sum()+out.ground_rain_kg_m2,abs=1e-11)
    assert out.fall_heat_j_m2.sum()==pytest.approx(G*np.sum((w-out.vapor_kg_m2)*z),abs=1e-7)
    assert np.all(out.fall_heat_j_m2>=0)
    # Actual adjacent-interface water transfer, including each cell's own phase.
    incoming=np.r_[out.downward_liquid_kg_m2[1:],0.]
    np.testing.assert_allclose(out.vapor_kg_m2-w,incoming-out.downward_liquid_kg_m2,atol=1e-12)


def test_dry_lower_layers_can_reevaporate_everything_without_losing_column_energy():
    t,p,m,edges,z=setup();w=saturation_vapor_mass(t,m,p)*[.01,.01,.1,1.2]
    out=adjust_multilevel_fall(t,w,m,p,edges,z)
    assert out.ground_rain_kg_m2==0
    assert out.condensation_kg_m2[-1]>0 and out.evaporation_kg_m2.sum()>0
    assert out.vapor_kg_m2.sum()==pytest.approx(w.sum(),abs=1e-12)
    assert out.fall_heat_j_m2.sum()>0


def test_zero_height_limit_matches_independent_sequential_moist_enthalpy_roots():
    t,p,m,edges,z=setup();w=saturation_vapor_mass(t,m,p)*[.95,.98,1.4,1.8]
    expected_t=np.empty(4);expected_w=np.empty(4);incoming=0.;liquid_t=t[-1]
    for k in range(3,-1,-1):
        state=equilibrate_moist(t[k],w[k],m[k],p[k],incoming,liquid_t)
        expected_t[k],expected_w[k]=state.temperature_k,state.vapor_kg_m2
        incoming,liquid_t=state.liquid_kg_m2,state.temperature_k
    out=adjust_multilevel_fall(t,w,m,p,edges*1e-10,z*1e-10)
    np.testing.assert_allclose(out.temperature_k,expected_t,rtol=1e-10,atol=1e-9)
    np.testing.assert_allclose(out.vapor_kg_m2,expected_w,rtol=1e-9,atol=1e-8)
    assert out.ground_rain_kg_m2==pytest.approx(incoming,abs=1e-8)


@pytest.mark.parametrize('invalid',[np.array([0,1000,3000,3000,10000.]),np.array([1,1000,3000,6000,10000.])])
def test_invalid_vertical_edges_are_rejected(invalid):
    t,p,m,edges,z=setup()
    with pytest.raises(ValueError):adjust_multilevel_fall(t,saturation_vapor_mass(t,m,p),m,p,invalid,z)
