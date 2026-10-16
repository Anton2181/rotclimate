"""Manufactured four-layer and overnight orchestration tests. No Earth runs."""
from dataclasses import replace
import json
from pathlib import Path
import numpy as np
import pytest

from experiments import v10_column as m
from scripts import overnight_v10 as n
from rotclimate_v10.core import Domain,DAY,tracer_flux
from rotclimate_v10.earth import EarthCase


def fixture(land=True):
    shape = (4,4);mask = np.full(shape,land,dtype=bool)
    d = Domain('california',mask,np.zeros(shape),np.full(shape,37.),np.full((12,)+shape,15.),60000.,60000.)
    profile = m.Profile(np.tile([-3.,-10.,-20.,-45.],(12,1)),np.tile([.006,.004,.002,.0004],(12,1)),
        np.tile([4.,6.,8.,12.],(12,1)),np.zeros((12,4)),np.array([500.,1500.,3000.,9000.]))
    case = EarthCase(d,np.full(shape,-125.),np.full((12,)+shape,20.),mask.copy(),np.zeros(shape),np.zeros(shape,bool))
    return case,profile,m.Settings(storm_rate_month=0)


def zero_flow(d):
    ny,nx = d.land.shape
    return m.balanced(np.zeros((4,ny,nx+1)),np.zeros((4,ny+1,nx)),d.dx,d.dy)


def test_shallow_return_does_not_force_deep_terrain_ascent():
    case,p,s = fixture();d = case.domain;d.elevation_m[1:3,1:3] = 2500.
    f = m.flow_at(d,p,s,[],0.)
    assert abs(f.vertical[0]).max()>0
    np.testing.assert_allclose(f.vertical[1:],0,atol=1e-15)
    deep = m.flow_at(d,p,replace(s,terrain='deep'),[],0.)
    assert abs(deep.vertical[-1]).max()>0
    for flow in (f,deep):
        div = m.divergence(flow.x,flow.y,d.dx,d.dy)
        np.testing.assert_allclose(div.sum(0),0,atol=1e-14)
        vertical = np.concatenate([np.zeros((1,4,4)),flow.vertical,np.zeros((1,4,4))])
        np.testing.assert_allclose(div+vertical[1:]-vertical[:-1],0,atol=1e-14)


def test_vectorized_flux_matches_frozen_transport_per_layer():
    case,p,s = fixture();d = case.domain;mass,_ = m.masses(d)
    rng = np.random.default_rng(5);water = rng.uniform(1,10,mass.shape)
    x = rng.normal(0,1000,(4,4,5));y = rng.normal(0,1000,(4,5,4));b = np.full_like(water,.005)
    fx,fy = m.flux(water,mass,x,y,b)
    for k in range(4):
        ox,oy = tracer_flux(water[k],mass[k],x[k],y[k],b[k])
        np.testing.assert_array_equal(fx[k],ox);np.testing.assert_array_equal(fy[k],oy)


def test_compensated_closed_flow_preserves_constant_mixing_ratio_and_mse():
    case,p,s = fixture();d = case.domain;mass,_ = m.masses(d)
    x = np.zeros((4,4,5));y = np.zeros((4,5,4));rng = np.random.default_rng(4)
    x[0,:,1:-1] = rng.normal(0,2000,(4,3));x[1] = -x[0]
    flow = m.balanced(x,y,d.dx,d.dy)
    state = m.State(mass*.002,mass*320000,np.zeros((4,4)))
    new,rain,_,_,budget = m.advance(state,d,p,s,flow,m.stable_step(flow,mass,d),0.,physics=False)
    np.testing.assert_allclose(new.water,state.water,atol=1e-12)
    np.testing.assert_allclose(new.energy,state.energy,atol=1e-6)
    assert abs(budget['water_error_mm'])<1e-12 and abs(budget['energy_error_j_m2'])<1e-5
    assert rain.max()==0


@pytest.mark.parametrize('land',[True,False])
def test_layer_rain_and_evaporation_close_water_and_energy(land):
    case,p,s = fixture(land);d = case.domain;mass,_ = m.masses(d);state = m.initial_state(d,p,s)
    state.water[0] += mass[0]*.02;state.energy[0] += m.LV*mass[0]*.02
    new,rain,_,_,b = m.advance(state,d,p,s,zero_flow(d),3600.,0.)
    assert rain.min()>0 and new.water.min()>=0 and new.soil.min()>=0
    assert abs(b['water_error_mm'])<1e-9 and abs(b['energy_error_j_m2'])<1e-5


def test_cfl_guard_and_repeatable_storms():
    case,p,s = fixture();s = replace(s,storm_rate_month=4.);d = case.domain
    assert m.events(d,s,41)==m.events(d,s,41)
    f = m.flow_at(d,p,s,m.events(d,s,41),0.);mass,_ = m.masses(d)
    with pytest.raises(ValueError,match='CFL'):
        m.advance(m.initial_state(d,p,s),d,p,s,f,m.stable_step(f,mass,d)*1.01,0.)


def test_resume_at_month_boundary_matches_uninterrupted_year(tmp_path,monkeypatch):
    case,p,s = fixture();p.eastward[:] = 0.;p.northward[:] = 0.
    d = case.domain;mass,_ = m.masses(d);target,_ = m.targets(d,p,s,0.)
    state = m.State(np.zeros_like(mass),mass*(m.CP*(target+273.15)+m.G*m.geometry(d,p)),np.zeros((4,4)))
    # Manufactured zero circulation permits a larger test step; physical CFL is zero.
    monkeypatch.setattr(m,'stable_step',lambda *args:DAY)
    full = m.year(d,p,s,41,state)
    stopped = [False]
    def save(st,rain,temp,ref,info):
        n.write_checkpoint(tmp_path,1,(st,rain,temp,ref,dict(info)))
        if info['month']==2:stopped[0] = True
    with pytest.raises(m.BudgetStop):m.year(d,p,s,41,state,save_month=save,should_stop=lambda:stopped[0])
    partial = n.read_checkpoint(tmp_path,1,d.land.shape)
    assert partial[-1]['month']==2
    resumed = m.year(d,p,s,41,state,checkpoint=partial)
    for actual,expected in zip(resumed[:4],full[:4]):
        if isinstance(actual,m.State):
            for key in ('water','energy','soil'):np.testing.assert_allclose(getattr(actual,key),getattr(expected,key),atol=1e-9)
        else:np.testing.assert_allclose(actual,expected,atol=1e-10)
    assert abs(resumed[-1]['budget']['annual_water_error_mm'])<1e-6
    assert abs(resumed[-1]['budget']['annual_energy_error_j_m2'])<1
    n.write_checkpoint(tmp_path,1,resumed,completed=True)
    (tmp_path/'year1.npz').write_bytes(b'corrupt')
    with pytest.raises(ValueError,match='integrity'):n.read_checkpoint(tmp_path,1,d.land.shape,completed=True)


def test_sweep_is_reproducible_and_has_declared_coverage():
    settings,anchors = n.design();assert n.design()==(settings,anchors)
    assert anchors==13 and len(settings)==157
    assert len(set(settings))==157
    for key in ('humidity_scale','storm_rate_month','storm_convergence_ms','storm_rotation_ms','storm_radius_km','terrain_drag_height_m',
                'relaxation_lower_days','relaxation_upper_days','terrain'):
        assert len({getattr(s,key) for s in settings[anchors:]})>=3
    pool = n.candidate_indices(settings)
    assert len(pool)==150 and all(settings[i].observed_wind and settings[i].observed_humidity and settings[i].observed_temperature for i in pool)


def test_rank_prioritizes_qualified_results_and_does_not_hide_diagnostics():
    rows = {n.job_id(i,'california',n.SCREEN,41):{'eligible':eligible,'settling':{'passed':True},'score':score}
        for i,eligible,score in ((0,False,1),(1,True,10),(2,True,8))}
    assert n.ranked(rows,range(3))==[2,1,0]


def test_dry_everywhere_cannot_qualify():
    case,p,s = fixture();d = case.domain;state = m.initial_state(d,p,s)
    temp = np.full((12,4,4,4),10.);record = (state,np.zeros((12,4,4)),temp,temp.copy(),{'budget':{}})
    row = n.summarize(record,case,{'passed':True},3)
    assert not row['eligible'] and not row['guards']['rain_amount'] and not row['guards']['wet_reference_coverage']


def fake_summary(eligible=False):
    return {'eligible':eligible,'score':20.,'years':3,'settling':{'passed':True}}


def test_wall_limit_and_resume_do_not_repeat_completed_cases(tmp_path):
    case,p,s = fixture();now = [0.];calls = []
    def fake(job,*args):
        calls.append(job);now[0] += 1300.;return fake_summary()
    cases = {(r,spacing):case for r in ('california','iberia') for spacing in (n.SCREEN,60)};profiles = {r:p for r in ('california','iberia')}
    first = n.execute(tmp_path,[s],1,cases,profiles,1.,clock=lambda:now[0],case_runner=fake)
    assert first['status']=='budget_reached' and len(calls)==3
    second = n.execute(tmp_path,[s],1,cases,profiles,2.,clock=lambda:now[0],case_runner=fake)
    assert second['status']=='complete' and len(calls)==8 and len(set(calls))==8
    assert second['selected']['fine']==[]


def test_repeated_numerical_failure_stops_for_diagnosis(tmp_path):
    case,p,s = fixture();calls = []
    def fake(job,*args):calls.append(job);raise FloatingPointError('manufactured numerical failure')
    result = n.execute(tmp_path,[s,replace(s,terrain='deep'),replace(s,terrain='none')],3,
        {(r,n.SCREEN):case for r in ('california','iberia')},{r:p for r in ('california','iberia')},case_runner=fake)
    assert result['status']=='needs_diagnosis' and len(calls)==5


def test_default_is_read_only(tmp_path,monkeypatch):
    monkeypatch.setattr(n.audit,'saved_analysis',lambda *a:pytest.fail('unexpected preparation'))
    assert n.main(['--out',str(tmp_path/'out')])==0 and list(tmp_path.iterdir())==[]


def test_fine_grid_preparation_uses_raw_data_and_same_physical_inset(monkeypatch):
    calls = []
    def wc(raw,var,lon,lat):
        calls.append(var)
        if var=='elev':return np.zeros(lon.shape)
        return np.full((12,)+lon.shape,15. if var=='tavg' else 20.)
    monkeypatch.setattr(n,'read_wc',wc);monkeypatch.setattr(n,'read_sst',lambda path,lon,lat:np.full((12,)+lon.shape,15.))
    fine = n.prepare_grid('california',15,Path('/unused'))
    assert calls==['elev','tavg','prec'] and fine.domain.dx==15000.
    assert not fine.score_mask[:8].any() and fine.score_mask[8:-8,8:-8].all()


def test_checkpoint_interruption_between_array_and_pointer_keeps_old_month(tmp_path,monkeypatch):
    case,p,s = fixture();state = m.initial_state(case.domain,p,s)
    temp = np.zeros((12,4,4,4));rain = np.zeros((12,4,4))
    info = dict(month=2,totals={},maxw=0.,maxe=0.,continuity=0.,initial_water=0.,initial_energy=0.,steps=0)
    n.write_checkpoint(tmp_path,1,(state,rain,temp,temp,info))
    original = n.atomic_json
    monkeypatch.setattr(n,'atomic_json',lambda *args:(_ for _ in ()).throw(OSError('interrupted commit')))
    with pytest.raises(OSError,match='commit'):
        n.write_checkpoint(tmp_path,1,(state,rain,temp,temp,dict(info,month=3)))
    assert n.read_checkpoint(tmp_path,1,(4,4))[-1]['month']==2
    monkeypatch.setattr(n,'atomic_json',original)
    n.write_checkpoint(tmp_path,1,(state,rain,temp,temp,dict(info,month=3)))
    assert n.read_checkpoint(tmp_path,1,(4,4))[-1]['month']==3
    assert not (tmp_path/'year1_m02.npz').exists()


def test_storm_positions_are_identical_in_physical_coordinates_across_grids():
    case,p,s = fixture();s = replace(s,storm_rate_month=4.)
    a = m.events(case.domain,s,41,width_m=2000000.)
    d = replace(case.domain,dx=30000.)
    b = m.events(d,s,41,width_m=2000000.)
    np.testing.assert_allclose([e.x for e in a],[e.x for e in b],atol=1e-9)
    assert [e.day for e in a]==[e.day for e in b]
