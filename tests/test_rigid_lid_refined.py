import numpy as np
from scipy.sparse import bmat,csc_matrix,eye
from rotclimate.rigid_lid_refined import RefinedSaddleSolve,RefinedRigidLidMoistModel
from rotclimate.rigid_lid_moist import RigidLidMoistModel
from rotclimate.pressure_moist import gas_energy


def test_mixed_scale_saddle_rowwise_residual_and_constraint():
    rng=np.random.default_rng(813);n=75;k=20
    a=rng.normal(size=(n,n));a=np.eye(n)+.03*(a-a.T);d=rng.normal(size=(k,n))*1e-6
    matrix=bmat([[csc_matrix(a),csc_matrix(-d.T)],[csc_matrix(d),csc_matrix((k,k))]],format='csc')
    rhs=np.r_[rng.normal(size=n)*1e4,np.zeros(k)]
    solver=RefinedSaddleSolve(matrix);x=solver.solve(rhs)
    assert solver.calls[0]['final_rowwise_backward_error']<=8*np.finfo(float).eps
    np.testing.assert_allclose(d@x[:n],0,atol=1e-16)
    # An independently row-scaled dense solve avoids reproducing the sparse
    # solver's mixed-unit conditioning in the comparison.
    dense=matrix.toarray();scale=np.max(abs(dense),axis=1)
    expected=np.linalg.solve(dense/scale[:,None],rhs/scale)
    np.testing.assert_allclose(x,expected,rtol=1e-10,atol=1e-6)
    np.testing.assert_array_equal(solver.solve(np.zeros(n+k)),np.zeros(n+k))


def test_refined_solver_recovers_small_core_limit_without_changing_equations():
    p=[101325,85000,65000,40000];args=(p,(4,5),200000,1e-4)
    old=RigidLidMoistModel(*args);new=RefinedRigidLidMoistModel(*args)
    t=np.broadcast_to(np.array([290.,270.,245.])[:,None,None],old.mass.shape).copy()+np.arange(20).reshape(4,5)[None]*.1
    a=old.advance(old.initial_state(t,old.mass*.002),120);b=new.advance(new.initial_state(t,new.mass*.002),120)
    for key in ['temperature_k','vapor_kg_m2','u_east','v_south','ground_rain_kg_m2']:
        np.testing.assert_allclose(getattr(a,key),getattr(b,key),rtol=1e-11,atol=1e-10)
    assert b.certificate['saddle_refinement']['maximum_final_rowwise_backward_error']<1e-15


def test_larger_mixed_barotropic_baroclinic_case_native_continuity_and_energy():
    p=[101325,85493.75,72694.9450895894,61812.179739202256,52558.61407423528,44690.34945959743,38000]
    shape=(15,17);f=np.linspace(3e-5,1.2e-4,np.prod(shape)).reshape(shape)
    m=RefinedRigidLidMoistModel(p,shape,224000,f,phase_enabled=False)
    rng=np.random.default_rng(861);u=rng.normal(size=(6,15,18));v=rng.normal(size=(6,16,17));u[:,:,[0,-1]]=0;v[:,[0,-1]]=0
    u,v,_=m.project_initial_wind(u,v)
    t=np.broadcast_to(np.linspace(290,240,6)[:,None,None],m.mass.shape).copy();t+=np.sin(np.arange(255).reshape(shape))[None]*2
    s=m.initial_state(t,0,u,v);x=m._velocity(u,v);initial=gas_energy(t,s.vapor_kg_m2,m.mass).sum()+.5*np.dot(x,x)
    for _ in range(12):
        s=m.advance(s,450)
        div=(np.diff(s.u_east,axis=2)+np.diff(s.v_south,axis=1))/m.dx
        m.column.upward_mass_flux(div) # native tolerance unchanged
        assert s.certificate['maximum_column_mass_divergence_kg_m2_s']<1e-13
    x=m._velocity(s.u_east,s.v_south);final=gas_energy(s.temperature_k,s.vapor_kg_m2,m.mass).sum()+.5*np.dot(x,x)
    np.testing.assert_allclose(final,initial,rtol=1e-12)
