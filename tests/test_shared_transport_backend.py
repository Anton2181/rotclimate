import numpy as np
import pytest
from scipy.sparse import csc_matrix,diags
from scipy.sparse.linalg import spsolve
from rotclimate.shared_transport_backend import ScopedTransportFactors,make_shared_transport_backend
from rotclimate.phase_backend import bind_dependencies,make_phase_backend
from rotclimate.fast_liquid_phase import enthalpy_phase_fast
from rotclimate.multilevel_transport import solve_multilevel
from rotclimate.pressure_boundary import baroclinic_lower_wind_seed
from rotclimate.surface_coupling import SurfaceState


def test_exact_factor_match_and_inplace_mutation_invalidation():
    f=ScopedTransportFactors();a=diags([2.,3.,4.],format='csc');b=np.array([1.,2.,3.])
    np.testing.assert_allclose(f.solve(a,b),spsolve(a,b),rtol=1e-14)
    np.testing.assert_allclose(f.solve(a.copy(),b*2),spsolve(a,b*2),rtol=1e-14)
    assert f.factorizations==1 and f.hits==1
    a.data[0]+=1.;np.testing.assert_allclose(f.solve(a,b),spsolve(a,b),rtol=1e-14)
    assert f.factorizations==2
    changed=csc_matrix([[0.,1.,0.],[1.,3.,0.],[0.,0.,4.]])
    np.testing.assert_allclose(f.solve(changed,b),spsolve(changed,b),rtol=1e-14);assert f.factorizations==3


def test_two_scalar_quantities_reuse_actual_air_operator_and_preserve_fluxes():
    mass0=np.array([1600.,2500.,2300.]);shape=(3,4,5);m=np.broadcast_to(mass0[:,None,None],shape).copy()
    u,v=baroclinic_lower_wind_seed(np.full(shape[1:],2.),np.full(shape[1:],-1.),mass0)
    f=ScopedTransportFactors();new=bind_dependencies(solve_multilevel,spsolve=f.solve)
    for q,outside in [(.003,.006),(280000.,300000.)]:
        source=m*q/120.;a=solve_multilevel(m,u,v,200000.,source,1/120,outside);b=new(m,u,v,200000.,source,1/120,outside)
        for key in ['amount','reaction_loss','east_tracer_flux','south_tracer_flux','upward_tracer_flux','upward_dry_mass_flux']:
            np.testing.assert_allclose(getattr(a,key),getattr(b,key),rtol=1e-12,atol=1e-6)
    assert f.solves==2 and f.factorizations==1 and f.hits==1


def test_failed_factorization_cannot_reuse_a_stale_factor_on_retry():
    factors=ScopedTransportFactors();good=diags([2.,3.],format='csc');rhs=np.array([2.,6.])
    np.testing.assert_array_equal(factors.solve(good,rhs),[1.,2.])
    singular=diags([0.,3.],format='csc')
    for _ in range(2):
        with pytest.raises(RuntimeError,match='singular'):factors.solve(singular,rhs)
    np.testing.assert_array_equal(factors.solve(good,rhs),[1.,2.])
    assert factors.factorizations==1 and factors.hits==1


def trajectory(backend):
    u=np.zeros((3,4,6));v=np.zeros((3,5,5));u[:,:,[0,-1]]=3.
    m=backend.model_type([101325,85000,65000,40000],(4,5),200000,1e-4,u_boundary=u,v_boundary=v,external_temperature_k=280,external_mixing_ratio=.003,momentum_drag_s=1/86400)
    u,v,_=m.project_initial_wind(u,v);t=np.broadcast_to(np.array([298.,267.,237.])[:,None,None],m.mass.shape).copy()+np.arange(20).reshape(4,5)[None]*.05
    a=m.initial_state(t,m.mass*np.array([.015,.004,.0001])[:,None,None],u,v);s=SurfaceState(np.full((4,5),300.),np.full((4,5),50.),np.full((4,5),2e6));rain=np.zeros((4,5));certs=[]
    for _ in range(8):
        r=backend.surface_coupled(m,a,s,120,longwave_optical_depth=[.3,.2,.1],shortwave_optical_depth=[.02,.02,.02],reference_height_m=700,roughness_m=.01,solar_in_w_m2=350,longwave_in_w_m2=20)
        a,s=r.atmosphere,r.surface;rain+=r.rain_kg_m2;certs.append(r.certificate)
    return a,s,rain,certs


def test_complete_cached_trajectory_matches_and_keeps_conservation():
    old=trajectory(make_phase_backend(enthalpy_phase_fast,name='reference'));new=trajectory(make_shared_transport_backend())
    for a,b in [(old[0].temperature_k,new[0].temperature_k),(old[0].vapor_kg_m2,new[0].vapor_kg_m2),(old[0].u_east,new[0].u_east),(old[0].v_south,new[0].v_south),(old[1].temperature_k,new[1].temperature_k),(old[1].liquid_kg_m2,new[1].liquid_kg_m2),(old[2],new[2])]:np.testing.assert_allclose(a,b,rtol=1e-11,atol=1e-8)
    for c in new[3]:
        f=c['dynamics_before_surface_return']['dynamics_before_adjustment']['transport_factor_reuse']
        assert f['solves']>=2 and f['factorizations']<=f['solves']/2 and f['exact_matrix_reuses']>=f['solves']/2
        assert abs(c['actual_total_energy_source_residual_j_m2'])<1e-4
        assert abs(c['actual_total_water_source_residual_kg_m2'])<1e-9


def test_reference_mode_and_original_transport_namespace_unchanged():
    import rotclimate.multilevel_transport as module
    original=module.spsolve;f=ScopedTransportFactors(reuse=False);a=diags([2.,3.],format='csc')
    f.solve(a,[1.,2.]);f.solve(a,[2.,3.]);assert f.factorizations==2 and f.hits==0
    trajectory(make_shared_transport_backend(reuse=False,name='reference'))
    assert module.spsolve is original
