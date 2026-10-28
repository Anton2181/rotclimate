"""Independent variable-capacity enthalpy roots and precipitation energy."""
import numpy as np
import pytest
from scipy.optimize import brentq
from rotclimate.column_thermodynamics import CP,LV,EPSILON
from rotclimate.moist_enthalpy import (CP_LIQUID,CP_VAPOR,REFERENCE_K,equilibrate_moist,
    gas_enthalpy,liquid_enthalpy,moist_falling_rain)
from rotclimate.phase_adjustment import saturation_vapor_mass


@pytest.mark.parametrize('rh,liquid,liquid_t',[(1.5,0.,290.),(.2,1.,250.),(.2,40.,250.)])
def test_moist_equilibrium_matches_independent_enthalpy_brent_root(rh,liquid,liquid_t):
    t,m,p=290.,2200.,90000.;w=rh*saturation_vapor_mass(t,m,p)
    def h(temp,vap,liq):
        return (CP*m+1850*vap)*(temp-273.15)+2.5e6*vap+4186*liq*(temp-273.15)
    h0=(CP*m+1850*w)*(t-273.15)+2.5e6*w+4186*liquid*(liquid_t-273.15)
    def temp_for_x(x):return 273.15+(h0-2.5e6*(w+x))/(CP*m+1850*(w+x)+4186*(liquid-x))
    def f(x):
        temp=temp_for_x(x);es=611.2*np.exp(17.67*(temp-273.15)/(temp-29.65))
        return w+x-m*.622*es/(p-es)
    if liquid and f(liquid)<=0:x=liquid
    elif f(0)>0:x=brentq(f,-w,0.,xtol=1e-13)
    else:x=brentq(f,0.,liquid,xtol=1e-13)
    out=equilibrate_moist(t,w,m,p,liquid,liquid_t)
    assert out.vapor_kg_m2==pytest.approx(w+x,abs=1e-11)
    assert out.temperature_k==pytest.approx(temp_for_x(x),abs=1e-11)
    assert h(out.temperature_k,out.vapor_kg_m2,out.liquid_kg_m2)==pytest.approx(h0,abs=1e-6)
    assert out.vapor_kg_m2+out.liquid_kg_m2==pytest.approx(w+liquid,abs=1e-12)


def test_cold_incoming_rain_cools_more_than_warm_rain_at_same_water_supply():
    cold=equilibrate_moist(298.,2.,2200.,90000.,1.,250.)
    warm=equilibrate_moist(298.,2.,2200.,90000.,1.,298.)
    assert cold.liquid_kg_m2==warm.liquid_kg_m2==0
    assert cold.temperature_k<warm.temperature_k
    # When all liquid evaporates, the heat difference survives exactly in gas.
    difference=gas_enthalpy(warm.temperature_k,warm.vapor_kg_m2,2200.)-gas_enthalpy(cold.temperature_k,cold.vapor_kg_m2,2200.)
    assert difference==pytest.approx(4186*48.,abs=1e-6)


def test_ground_rain_exports_its_actual_sensible_enthalpy():
    t=np.array([290.,250.]);m=np.array([2500.,6500.]);p=np.array([90000.,40000.])
    w=saturation_vapor_mass(t,m,p)*[.99,1.6]
    out=moist_falling_rain(t,w,m,p)
    assert out.ground_rain_kg_m2>0 and out.ground_rain_enthalpy_j_m2>0
    assert out.ground_rain_enthalpy_j_m2==pytest.approx(4186*out.ground_rain_kg_m2*(out.temperature_k[0]-273.15),rel=1e-14)
    initial=gas_enthalpy(t,w,m).sum();final=gas_enthalpy(out.temperature_k,out.vapor_kg_m2,m).sum()
    assert final+out.ground_rain_enthalpy_j_m2==pytest.approx(initial,abs=1e-6)
    assert abs(final-initial)>1000 # omitting precipitation enthalpy fails materially
    assert w.sum()==pytest.approx(out.vapor_kg_m2.sum()+out.ground_rain_kg_m2,abs=1e-11)
    assert out.gas_sensible_change_j_m2.sum()+out.ground_rain_enthalpy_j_m2==pytest.approx(LV*out.ground_rain_kg_m2,abs=1e-6)


def test_complete_reevaporation_preserves_gas_enthalpy_but_dry_heat_sum_is_not_total_heat():
    t=np.array([300.,245.]);m=np.array([2500.,6500.]);p=np.array([90000.,40000.])
    w=np.array([1.,1.4*saturation_vapor_mass(t[1],m[1],p[1])])
    out=moist_falling_rain(t,w,m,p)
    assert out.ground_rain_kg_m2==0 and out.ground_rain_enthalpy_j_m2==0
    assert gas_enthalpy(out.temperature_k,out.vapor_kg_m2,m).sum()==pytest.approx(gas_enthalpy(t,w,m).sum(),abs=1e-6)
    assert out.dry_equivalent_heat_j_m2[1]>0 and out.dry_equivalent_heat_j_m2[0]<0
    assert abs(out.dry_equivalent_heat_j_m2.sum())>100 # not a thermodynamic net source


@pytest.mark.parametrize('changes',[dict(liquid_kg_m2=-1),dict(liquid_temperature_k=np.nan),dict(vapor_kg_m2=-1),dict(dry_mass_kg_m2=0)])
def test_invalid_moist_phase_rejected(changes):
    args=dict(temperature_k=290.,vapor_kg_m2=2.,dry_mass_kg_m2=2200.,pressure_pa=90000.)
    args.update(changes)
    with pytest.raises(ValueError):equilibrate_moist(**args)
