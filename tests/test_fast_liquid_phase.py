import numpy as np
import pytest
from rotclimate.fast_liquid_phase import equilibrium_enthalpy,enthalpy_phase_fast
from rotclimate.falling_water_energy import _equilibrium
from rotclimate.pressure_moist import enthalpy_phase,gas_energy
from rotclimate.phase_adjustment import _saturation


def reference(t,w,m,p,l=0.,tl=None):
    if tl is None:tl=t
    return _equilibrium(np.asarray(t,float),np.asarray(w,float),np.asarray(m,float),np.asarray(p,float),np.asarray(l,float),np.asarray(tl,float),extra_heat=0.,feedback_per_vapor_change=0.)


def test_clear_cells_skip_roots_and_reproduce_exact_reference():
    t=np.array([210.,250.,290.,320.]);m=np.full(4,1500.);p=np.array([30000.,50000.,90000.,100000.]);w=.3*m*_saturation(t,p)
    r=equilibrium_enthalpy(t,w,m,p);old=reference(t,w,m,p)
    assert r.certificate['root_cells']==0 and r.certificate['maximum_newton_iterations']==0
    for a,b in zip([r.temperature_k,r.vapor_kg_m2,r.liquid_kg_m2,r.vapor_change_kg_m2],old[:4]):np.testing.assert_array_equal(a,b)


@pytest.mark.parametrize('seed',[7,192,611])
def test_random_pressure_enthalpy_equilibria_against_frozen_bisection(seed):
    rng=np.random.default_rng(seed);n=600;t=rng.uniform(180,330,n);m=rng.uniform(100,3000,n);p=rng.uniform(10000,110000,n)
    w=m*rng.uniform(0,.04,n);l=rng.uniform(0,20,n);tl=rng.uniform(150,330,n)
    r=equilibrium_enthalpy(t,w,m,p,l,tl);old=reference(t,w,m,p,l,tl)
    np.testing.assert_allclose(r.temperature_k,old[0],rtol=1e-11,atol=1e-9)
    np.testing.assert_allclose(r.vapor_kg_m2,old[1],rtol=1e-9,atol=1e-10)
    np.testing.assert_allclose(r.liquid_kg_m2,old[2],rtol=1e-9,atol=1e-10)
    np.testing.assert_allclose(r.vapor_kg_m2+r.liquid_kg_m2,w+l,rtol=1e-13,atol=1e-12)
    assert r.certificate['maximum_saturation_error_fraction']<=1e-9


def test_near_saturation_and_cold_rain_endpoint_states():
    t=np.array([180.,220.,280.,330.,180.]);p=np.array([100000.,60000.,90000.,10000.,10000.]);m=np.full(5,1000.)
    w=m*_saturation(t,p);w[3]=1.;w*=np.array([1-1e-12,1+1e-12,1.,1.,1.]);l=np.array([0.,1e-10,1.,0.,100.]);tl=np.array([180.,150.,320.,330.,150.])
    r=equilibrium_enthalpy(t,w,m,p,l,tl);old=reference(t,w,m,p,l,tl)
    np.testing.assert_allclose(r.temperature_k,old[0],atol=1e-9)
    np.testing.assert_allclose(r.vapor_kg_m2,old[1],atol=1e-10)


def test_multilevel_cold_rain_re_evaporation_and_actual_energy_water():
    p=np.broadcast_to(np.array([93000.,76000.,60000.,45000.])[:,None,None],(4,3,4)).copy();m=np.full(p.shape,1200.)
    t=np.broadcast_to(np.array([295.,280.,260.,240.])[:,None,None],p.shape).copy();w=m*_saturation(t,p)*np.array([.2,.6,1.4,1.8])[:,None,None]
    fast=enthalpy_phase_fast(t,w,m,p);old=enthalpy_phase(t,w,m,p)
    for a,b in zip(fast,old):np.testing.assert_allclose(a,b,rtol=1e-9,atol=1e-8)
    nt,nw,rain,h=fast
    np.testing.assert_allclose(nw.sum(0)+rain,w.sum(0),rtol=1e-12)
    np.testing.assert_allclose(gas_energy(nt,nw,m).sum(0)+h,gas_energy(t,w,m).sum(0),rtol=1e-12)


def test_scalar_and_invalid_state():
    r=equilibrium_enthalpy(290.,10.,1500.,90000.);old=reference(290.,10.,1500.,90000.)
    np.testing.assert_allclose(r.temperature_k,old[0],atol=1e-9)
    with pytest.raises(ValueError):equilibrium_enthalpy(290.,-1.,1500.,90000.)


def test_zero_newton_budget_uses_exact_reference_fallback():
    t=np.array([240.,280.]);m=np.full(2,1500.);p=np.array([40000.,90000.]);w=2*m*_saturation(t,p)
    r=equilibrium_enthalpy(t,w,m,p,maximum_newton_iterations=0);old=reference(t,w,m,p)
    assert r.certificate['bisection_fallback_cells']==2
    for a,b in zip([r.temperature_k,r.vapor_kg_m2,r.liquid_kg_m2,r.vapor_change_kg_m2],old[:4]):np.testing.assert_array_equal(a,b)


def test_strided_inputs_and_scalar_fallback():
    t=np.arange(24,dtype=float).reshape(4,6)[:,::2]+260.;m=np.full(t.shape,1500.);p=np.full(t.shape,80000.);w=1.3*m*_saturation(t,p)
    r=equilibrium_enthalpy(t,w,m,p,maximum_newton_iterations=0);old=reference(t,w,m,p)
    np.testing.assert_array_equal(r.temperature_k,old[0]);np.testing.assert_array_equal(r.vapor_kg_m2,old[1])
    r=equilibrium_enthalpy(280.,30.,1500.,90000.,maximum_newton_iterations=0);old=reference(280.,30.,1500.,90000.)
    np.testing.assert_array_equal(r.temperature_k,old[0]);np.testing.assert_array_equal(r.vapor_kg_m2,old[1])
