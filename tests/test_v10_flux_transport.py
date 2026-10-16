"""Known transport solutions, coupled bounds and unchanged toy clouds only."""
from dataclasses import replace
import numpy as np
import pytest
from experiments import v10_flux_transport as m, v10_transport_lab as lab
from scripts import audit_v10_flux_transport as audit


@pytest.mark.parametrize('direction',[-1,1])
def test_nonuniform_mass_conservation_and_affine_tracer_relation(direction):
    rng=np.random.default_rng(412)
    mesh=replace(m.periodic_mesh(32,direction),mass=rng.uniform(.5,2.,32))
    theta=rng.uniform(280.,320.,32)
    values=np.array([theta,.001+.00002*(theta-280.),2*theta-10])
    initial=values.copy(); dt=.5*mesh.mass.min()
    for _ in range(40):
        before=values.copy();values,amount,ledger=m.transport(values,mesh,dt)
        for k in (0,1):
            lo=np.minimum.reduce([before[k],np.roll(before[k],1),np.roll(before[k],-1)])
            hi=np.maximum.reduce([before[k],np.roll(before[k],1),np.roll(before[k],-1)])
            assert (values[k]>=lo-1e-10).all() and (values[k]<=hi+1e-10).all()
        np.testing.assert_allclose(values[1],.001+.00002*(values[0]-280.),atol=1e-16,rtol=0)
        np.testing.assert_allclose(values[2],2*values[0]-10,atol=1e-11,rtol=0)
        assert ((ledger['face_coefficient']>=0)&(ledger['face_coefficient']<=1)).all()
    np.testing.assert_allclose(np.sum(mesh.mass*(values-initial),axis=1),0,atol=2e-10,rtol=0)


def test_random_sharp_nonnegative_tracers_remain_bounded_without_clipping():
    rng=np.random.default_rng(671);mesh=m.periodic_mesh(64)
    values=np.array([rng.uniform(275.,320.,64),rng.choice([0.,.001,.01],64)])
    initial=values.copy()
    for _ in range(200):
        values,_,_=m.transport(values,mesh,.5/64)
        assert values[1].min()>=0.
    assert values[0].min()>=initial[0].min()-1e-10
    assert values[0].max()<=initial[0].max()+1e-10
    assert values[1].max()<=initial[1].max()+1e-12


@pytest.mark.parametrize('layers',[4,32,128,256])
def test_uniform_theta_roundoff_cannot_throttle_moisture_correction(layers):
    d,g,state,flow=lab.original.fixture(layers)
    mesh=m.closed_mesh(d,g,flow)
    theta=(lab.base.temperature(state.energy,g.mass,state.water,g.height_m)+273.15)/m.thermal.exner(g.pressure)
    q=state.water/g.mass;dt=min(60.,lab.base.stable_step(flow,g.mass,d))
    both,_,_=m.transport(np.array([theta.ravel(),q.ravel()]),mesh,dt)
    scalar,_,_=m.transport(q.reshape(1,-1),mesh,dt,bounded=1)
    np.testing.assert_allclose(both[1],scalar[0],atol=1e-15,rtol=0)


@pytest.mark.parametrize('cells',[16,32,64,128])
def test_smooth_known_translation_improves_over_upwind(cells):
    old=lab.periodic(cells,'upwind','smooth');new=lab.periodic(cells,'coupled_fct','smooth')
    assert new['theta_mean_absolute_error_k']<old['theta_mean_absolute_error_k']
    assert new['vapor_mean_absolute_error_g_kg']<old['vapor_mean_absolute_error_g_kg']
    assert new['rain_g_per_kg']==0
    assert abs(new['water_error_kg_kg'])<1e-11 and abs(new['enthalpy_error_j_kg'])<1e-6


@pytest.mark.parametrize('cells',[16,32,64,128])
def test_saturated_contact_false_rain_reduced_but_not_declared_eliminated(cells):
    old=lab.periodic(cells,'upwind');new=lab.periodic(cells,'coupled_fct')
    assert 0<new['rain_g_per_kg']<old['rain_g_per_kg']
    assert abs(new['water_error_kg_kg'])<1e-11 and abs(new['enthalpy_error_j_kg'])<1e-6


@pytest.mark.parametrize('scheme',lab.SCHEMES)
def test_periodic_reversal_and_half_step_preserve_accounting(scheme):
    a=lab.periodic(32,scheme);b=lab.periodic(32,scheme,direction=-1)
    assert a['rain_g_per_kg']==pytest.approx(b['rain_g_per_kg'],abs=1e-9)
    half=lab.periodic(32,scheme,courant=.25)
    assert abs(half['water_error_kg_kg'])<1e-11 and abs(half['enthalpy_error_j_kg'])<1e-6


def test_two_dimensional_diagonal_translation_uses_one_multidimensional_budget():
    n=16;ids=np.arange(n*n).reshape((n,n));mass=np.full(n*n,1./n**2)
    mesh=m.Mesh(mass,np.concatenate([ids.ravel(),ids.ravel()]),
        np.concatenate([np.roll(ids,-1,axis=1).ravel(),np.roll(ids,-1,axis=0).ravel()]),
        np.full(2*n*n,1./n),np.ones(2*n*n,bool),(n,n))
    yy,xx=np.meshgrid((np.arange(n)+.5)/n,(np.arange(n)+.5)/n,indexing='ij')
    wave=(np.sin(2*np.pi*(xx+yy))*np.sinc(1/n)**2).ravel()
    initial=np.array([300.+8*wave,.004+.001*wave]);new=initial.copy();old=initial.copy();dt=.25/n
    for _ in range(4*n):
        new,_,_=m.transport(new,mesh,dt)
        low,_=m.flux_proposals(old,mesh,dt)
        old-=mesh.divergence(low)/mesh.mass
    assert abs(new[0]-initial[0]).mean()<abs(old[0]-initial[0]).mean()
    np.testing.assert_allclose(new[1],.004+.001*(new[0]-300.)/8,atol=1e-16,rtol=0)
    np.testing.assert_allclose(np.sum(mass*(new-initial),axis=1),0,atol=1e-11,rtol=0)


@pytest.mark.parametrize('layers',[4,32,128])
def test_graph_matches_frozen_closed_flow_and_dry_constant_theta(layers):
    d,g,state,flow=lab.original.fixture(layers,vapor=False)
    mesh=m.closed_mesh(d,g,flow)
    assert abs(mesh.divergence(mesh.rate)).max()<1e-12
    result=lab.column(layers,'bulk','coupled_fct',vapor=False,physics=False)
    theta=(lab.base.temperature(result['state'].energy,g.mass,result['state'].water,g.height_m)+273.15)/m.thermal.exner(g.pressure)
    np.testing.assert_allclose(theta,lab.original.THETA,atol=1e-8,rtol=0)
    assert result['rain_mm']==result['remaining_vapor_mm']==0.


@pytest.mark.parametrize('mode',['bulk','unmixed'])
@pytest.mark.parametrize('factor',[1.,.5])
def test_closed_cloud_trajectory_keeps_original_rule_and_budgets(mode,factor):
    result=lab.column(32,mode,'coupled_fct',factor)
    assert 0<result['rain_mm']<result['initial_vapor_mm']
    assert result['rain_mm']+result['remaining_vapor_mm']==pytest.approx(result['initial_vapor_mm'],abs=1e-9)
    assert abs(result['energy_error_j_m2'])<1e-3
    assert result['maximum_step_temperature_ledger_error_c']<1e-9
    if mode=='bulk':assert result['parcel_rain_mm']==0.


def test_upwind_column_control_remains_exact_frozen_laboratory():
    old=lab.original.run(16,'unmixed');new=lab.column(16,'unmixed','upwind')
    for key in ('rain_mm','pressure_work_j_m2','steps','water_error_mm','energy_error_j_m2'):
        assert old[key]==new[key]
    for key in ('water','energy','soil'):
        np.testing.assert_array_equal(getattr(old['state'],key),getattr(new['state'],key))


def test_new_periodic_upwind_recovers_old_contact_stencil():
    old=lab.original.advect_contact(32,.5);new=lab.periodic(32,'upwind')
    assert old['rain_g_per_kg_initial_dry_air']==pytest.approx(new['rain_g_per_kg'],abs=1e-9)
    np.testing.assert_allclose(old['final_vapor_ratio'],new['final_vapor_ratio'],atol=1e-12,rtol=0)


@pytest.mark.parametrize('dt',[0.,-1.,np.nan,np.inf,1.])
def test_invalid_step_rejected(dt):
    with pytest.raises(ValueError):m.transport(np.ones((2,16)),m.periodic_mesh(16),dt)


def test_unbalanced_and_open_meshes_rejected():
    mesh=m.periodic_mesh(16)
    bad=mesh.rate.copy();bad[0]*=2
    with pytest.raises(ValueError,match='balanced'):replace(mesh,rate=bad).validate()
    d,g,state,flow=lab.original.fixture(4)
    bad_x=flow.x.copy();bad_x[...,0]=1.
    with pytest.raises(ValueError,match='open'):m.closed_mesh(d,g,replace(flow,x=bad_x))


def test_default_read_only_and_parent_outputs_protected(tmp_path,monkeypatch,capsys):
    monkeypatch.setattr(audit,'analyse',lambda:({'all_development_gates_pass':True},{}))
    monkeypatch.setattr(audit,'markdown',lambda _: 'toy audit')
    monkeypatch.setattr(audit,'plot',lambda *a:pytest.fail('Read-only invocation'))
    assert audit.main(['--out',str(tmp_path/'absent')])==0
    assert not (tmp_path/'absent').exists()
    monkeypatch.setattr(audit,'analyse',lambda:pytest.fail('Reject before work'))
    for path in ('output/v10_cloud_lab','output/v10_cloud_geometry/nested','output'):
        with pytest.raises(ValueError,match='Preserve'):
            audit.main(['--write','--out',str(audit.ROOT/path)])


def test_stale_saved_parent_rejected_before_any_manufactured_run(tmp_path,monkeypatch):
    folder=tmp_path/'output/v10_cloud_lab';folder.mkdir(parents=True)
    (folder/'audit.json').write_text('{"code_sha256":"stale"}')
    monkeypatch.setattr(audit,'ROOT',tmp_path)
    monkeypatch.setattr(lab,'periodic',lambda *a,**kw:pytest.fail('Reject stale evidence first'))
    with pytest.raises(ValueError,match='Parent laboratory'):
        audit.analyse()
