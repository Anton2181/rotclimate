import numpy as np
from rotclimate import pressure_moist,pressure_boundary,convective_adjustment,surface_coupling,open_mean_boundary
from rotclimate.phase_backend import make_phase_backend
from rotclimate.fast_liquid_phase import enthalpy_phase_fast
from rotclimate.surface_coupling import SurfaceState


def setup(model_type):
    p=[101325,85000,65000,40000];shape=(4,5);u=np.zeros((3,4,6));v=np.zeros((3,5,5));u[:,:,[0,-1]]=3.
    m=model_type(p,shape,200000,1e-4,u_boundary=u,v_boundary=v,external_temperature_k=280.,external_mixing_ratio=.003,momentum_drag_s=1/86400)
    u,v,_=m.project_initial_wind(u,v);t=np.broadcast_to(np.array([298.,267.,237.])[:,None,None],m.mass.shape).copy()+np.arange(20).reshape(shape)[None]*.05
    a=m.initial_state(t,m.mass*np.array([.015,.004,.0001])[:,None,None],u,v)
    s=SurfaceState(np.full(shape,300.),np.full(shape,50.),np.full(shape,2e6))
    return m,a,s


def forcing():return dict(longwave_optical_depth=[.3,.2,.1],shortwave_optical_depth=[.02,.02,.02],reference_height_m=700.,roughness_m=.01,scalar_roughness_m=.001,solar_in_w_m2=350.,longwave_in_w_m2=20.)


def trajectory(model_type,advance,steps=3):
    m,a,s=setup(model_type);rain=np.zeros(m.shape);h=np.zeros(m.shape)
    for _ in range(steps):
        r=advance(m,a,s,120,**forcing());a,s=r.atmosphere,r.surface;rain+=r.rain_kg_m2;h+=r.rain_enthalpy_j_m2
        assert abs(r.certificate['actual_total_energy_source_residual_j_m2'])<1e-4
        assert abs(r.certificate['actual_total_water_source_residual_kg_m2'])<1e-9
    return a,s,rain,h


def test_isolated_dependencies_keep_original_bodies_and_namespaces():
    original=[pressure_moist.enthalpy_phase,pressure_boundary.enthalpy_phase,convective_adjustment.enthalpy_phase,surface_coupling.enthalpy_phase,open_mean_boundary.enthalpy_phase]
    b=make_phase_backend(enthalpy_phase_fast,name='candidate')
    assert all(v['same_code_object'] for v in b.body_sources.values())
    assert b.model_type.advance.__globals__ is not open_mean_boundary.OpenMeanRigidLidModel.advance.__globals__
    assert b.model_type.advance.__globals__['enthalpy_phase'] is enthalpy_phase_fast
    assert b.adjustment.__globals__['enthalpy_phase'] is enthalpy_phase_fast
    assert b.surface_forcing.__globals__['enthalpy_phase'] is enthalpy_phase_fast
    assert b.surface_coupled.__globals__['advance_boundary_with_convection'] is b.advance_with_convection
    trajectory(b.model_type,b.surface_coupled)
    assert original==[pressure_moist.enthalpy_phase,pressure_boundary.enthalpy_phase,convective_adjustment.enthalpy_phase,surface_coupling.enthalpy_phase,open_mean_boundary.enthalpy_phase]


def test_reference_binding_reproduces_original_complete_trajectory_byte_exact():
    b=make_phase_backend();old=trajectory(open_mean_boundary.OpenMeanRigidLidModel,surface_coupling.advance_surface_coupled);new=trajectory(b.model_type,b.surface_coupled)
    for a,c in zip([old[0].temperature_k,old[0].vapor_kg_m2,old[0].u_east,old[0].v_south,old[1].temperature_k,old[1].liquid_kg_m2,old[2],old[3]],
                   [new[0].temperature_k,new[0].vapor_kg_m2,new[0].u_east,new[0].v_south,new[1].temperature_k,new[1].liquid_kg_m2,new[2],new[3]]):
        assert a.dtype==c.dtype and a.shape==c.shape and a.tobytes()==c.tobytes()


def test_fast_backend_complete_moist_trajectory_matches_reference():
    b=make_phase_backend(enthalpy_phase_fast,name='candidate');old=trajectory(open_mean_boundary.OpenMeanRigidLidModel,surface_coupling.advance_surface_coupled,12);new=trajectory(b.model_type,b.surface_coupled,12)
    pairs=[(old[0].temperature_k,new[0].temperature_k),(old[0].vapor_kg_m2,new[0].vapor_kg_m2),(old[0].u_east,new[0].u_east),(old[0].v_south,new[0].v_south),(old[1].temperature_k,new[1].temperature_k),(old[1].liquid_kg_m2,new[1].liquid_kg_m2),(old[2],new[2])]
    for a,c in pairs:np.testing.assert_allclose(a,c,rtol=1e-10,atol=2e-8)
    np.testing.assert_allclose(old[3],new[3],rtol=1e-10,atol=1e-3)


def test_all_phase_stages_use_selected_callable():
    calls=[]
    def counted(*args):calls.append(args[0].shape);return pressure_moist.enthalpy_phase(*args)
    b=make_phase_backend(counted,name='counted');m,a,s=setup(b.model_type)
    b.surface_forcing(m,a,s,120,**forcing());after_surface=len(calls);assert after_surface>0
    m.advance(a,120);after_dynamics=len(calls);assert after_dynamics>after_surface
    b.adjustment(a.temperature_k,a.vapor_kg_m2,m.mass,m.column.centers_pa);assert len(calls)>after_dynamics
