"""Nested phase grids: independent per-parent energy, water and retained state."""
import numpy as np
import pytest
from rotclimate.column_thermodynamics import CP,G,LV
from rotclimate.moist_enthalpy import CP_VAPOR,REFERENCE_K
from rotclimate.lapse_reference import lapse_reference
from rotclimate.phase_adjustment import saturation_vapor_mass
from rotclimate.multilevel_phase import adjust_multilevel_fall
from rotclimate.sublayer_phase import refine_thermal,restrict_thermal,adjust_sublayer_phase


def energy(t,w,m,z):
    return (CP*m+CP_VAPOR*w)*(t-REFERENCE_K)+LV*w+G*(m+w)*z


def grids(n=4,factor=4,shape=(2,3)):
    c=np.linspace(0,8000,n+1);f=np.linspace(0,8000,n*factor+1);zf=.5*(f[:-1]+f[1:]);zc=.5*(c[:-1]+c[1:])
    ref=lapse_reference(zf);mf0=-np.diff(lapse_reference(f).pressure_pa)/G
    mf=np.broadcast_to(mf0.reshape((-1,)+(1,)*len(shape)),(n*factor,)+shape).copy()
    m=mf.reshape((n,factor)+shape).sum(1)
    p=np.broadcast_to(ref.pressure_pa.reshape((-1,)+(1,)*len(shape)),mf.shape).copy()
    t=np.broadcast_to((300-.006*zc).reshape((-1,)+(1,)*len(shape)),m.shape).copy()
    return c,f,zc,zf,m,mf,p,t


def test_parent_reconstruction_conserves_independent_actual_energy_and_water():
    c,f,zc,zf,m,mf,p,t=grids();q=np.array([.009,.003,.0004,0.])[:,None,None];w=m*q
    result=refine_thermal(t,w,m,c,f,mf)
    water=result.vapor_kg_m2.reshape(4,4,2,3).sum(1)
    actual=energy(result.temperature_k,result.vapor_kg_m2,mf,zf[:,None,None]).reshape(4,4,2,3).sum(1)
    np.testing.assert_allclose(water,w,rtol=1e-13,atol=1e-14)
    np.testing.assert_allclose(actual,energy(t,w,m,zc[:,None,None]),rtol=1e-13,atol=1e-7)
    assert result.vapor_kg_m2.min()==0.
    restricted=restrict_thermal(result.temperature_k,result.vapor_kg_m2,mf,f,c)
    np.testing.assert_allclose(restricted.temperature_k,t,atol=1e-12)
    np.testing.assert_allclose(restricted.vapor_kg_m2,w,atol=1e-13)


def test_supplied_temperature_shape_is_not_an_unbooked_heat_source():
    c,f,zc,zf,m,mf,p,t=grids(shape=());w=.002*m
    result=refine_thermal(t,w,m,c,f,mf,temperature_gradient_k_m=-.006)
    for k in range(4):
        np.testing.assert_allclose(np.diff(result.temperature_k[4*k:4*k+4])/np.diff(zf[4*k:4*k+4]),-.006,atol=1e-16)
    actual=energy(result.temperature_k,result.vapor_kg_m2,mf,zf).reshape(4,4).sum(1)
    np.testing.assert_allclose(actual,energy(t,w,m,zc),rtol=1e-13,atol=1e-7)


def test_no_refinement_recovers_actual_existing_phase_kernel():
    c,f,zc,zf,m,mf,p,t=grids(factor=1);w=saturation_vapor_mass(t,m,p)*1.05
    old=adjust_multilevel_fall(t,w,m,p,c)
    new=adjust_sublayer_phase(t,w,m,c,f,mf,p)
    np.testing.assert_allclose(new.temperature_k,old.temperature_k,atol=1e-10)
    np.testing.assert_allclose(new.vapor_kg_m2,old.vapor_kg_m2,atol=1e-11)
    np.testing.assert_allclose(new.ground_rain_kg_m2,old.ground_rain_kg_m2,atol=1e-11)
    np.testing.assert_allclose(new.ground_rain_enthalpy_j_m2,old.ground_rain_enthalpy_j_m2,atol=1e-6)


@pytest.mark.parametrize('rh',[.7,1.1])
def test_actual_nested_atmosphere_and_ground_rain_water_energy_budgets(rh):
    c,f,zc,zf,m,mf,p,t=grids();pc=lapse_reference(zc).pressure_pa[:,None,None]
    w=saturation_vapor_mass(t,m,pc)*rh
    result=adjust_sublayer_phase(t,w,m,c,f,mf,p)
    before=energy(t,w,m,zc[:,None,None]).sum(0)
    after=energy(result.temperature_k,result.vapor_kg_m2,m,zc[:,None,None]).sum(0)
    np.testing.assert_allclose(after+result.ground_rain_enthalpy_j_m2,before,rtol=1e-13,atol=1e-6)
    np.testing.assert_allclose(result.vapor_kg_m2.sum(0)+result.ground_rain_kg_m2,w.sum(0),atol=1e-12)
    if rh>1:assert result.ground_rain_kg_m2.max()>0


def test_saturated_fine_layers_can_restrict_to_supersaturated_mean_without_water_loss():
    c=np.array([0.,1000.,2000.]);f=np.linspace(0,2000,5);mf=np.full(4,250.);p=np.array([99500.,94500.,89500.,84500.])
    t=np.array([295.,275.,285.,265.]);w=saturation_vapor_mass(t,mf,p)
    result=restrict_thermal(t,w,mf,f,c)
    pc=np.sqrt(p.reshape(2,2).prod(1));mean_sat=saturation_vapor_mass(result.temperature_k,result.dry_mass_kg_m2,pc)
    assert np.any(result.vapor_kg_m2>mean_sat*1.05)
    np.testing.assert_allclose(result.vapor_kg_m2,w.reshape(2,2).sum(1),atol=1e-14)


def test_retained_fine_phase_state_is_equilibrated_without_reconstructing_coarse_means():
    c,f,zc,zf,m,mf,p,t=grids();w=saturation_vapor_mass(t,m,lapse_reference(zc).pressure_pa[:,None,None])*1.04
    first=adjust_sublayer_phase(t,w,m,c,f,mf,p)
    second=adjust_multilevel_fall(first.fine_phase.temperature_k,first.fine_phase.vapor_kg_m2,mf,p,f)
    np.testing.assert_allclose(second.temperature_k,first.fine_phase.temperature_k,atol=1e-10)
    np.testing.assert_allclose(second.vapor_kg_m2,first.fine_phase.vapor_kg_m2,atol=1e-10)
    assert np.max(second.ground_rain_kg_m2)<1e-10


@pytest.mark.parametrize('bad_grid',[np.array([0.,1500.,3000.,8000.]),np.array([0.,1000.,2000.,4000.])])
def test_non_nested_or_different_depth_grid_rejected(bad_grid):
    c,f,zc,zf,m,mf,p,t=grids()
    with pytest.raises(ValueError):refine_thermal(t,.001*m,m,c,bad_grid,mf)


def test_reference_mass_mismatch_rejected_without_renormalization():
    c,f,zc,zf,m,mf,p,t=grids()
    with pytest.raises(ValueError):refine_thermal(t,.001*m,m,c,f,mf*1.01)
