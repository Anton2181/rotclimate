"""Conservative subgrid bound and exact bulk regression, tiny inputs only."""
from copy import deepcopy
from dataclasses import replace
import numpy as np
import pytest
from experiments import v10_parcel_condensation as m
from scripts import replay_v10_delivery as replay
from tests.test_v10_split_column import five_fixture
from tests.test_v10_event_forcing import calendar_fixture,ToyDriver


@pytest.mark.parametrize('physics',[True,False])
def test_bulk_step_exact_frozen_parent(physics):
    case,p,s,g,air,c=five_fixture()
    state=m.core.initial_state(case.domain,p,s,g,air)
    f=m.core.flow_at(case.domain,p,s,[],0.,g,c[3],wind_mode='spatial',circulation=c)
    q=m.core.boundary_ratio(case.domain,p,s,g,air,0.)
    old=m.parent.advance(state,case.domain,p,s,f,60.,0.,air,physics=physics,geometry=g,boundary=q)
    new=m.advance(state,case.domain,p,s,f,60.,0.,air,physics=physics,geometry=g,boundary=q)
    for name in ('water','energy','soil'):np.testing.assert_array_equal(getattr(old[0],name),getattr(new[0],name))
    for i in (1,2,3,5,6):np.testing.assert_array_equal(old[i],new[i])
    assert old[4]==new[4] and old[7]==new[7] and not new[8].any()


def cloudy_fixture():
    case,p,s,g,air,c=five_fixture(False);d=case.domain
    t=np.broadcast_to(np.array([20.,10.,-10.,-30.,-55.])[:,None,None],g.mass.shape)
    air=np.broadcast_to(t,(12,)+t.shape).copy()
    q=.1*m.base.saturation(t,g.pressure);q[0]*=8
    water=q*g.mass
    state=m.base.State(water,g.mass*(m.base.CP*(t+273.15)+m.base.G*g.height_m)+m.base.LV*water,np.zeros(d.land.shape))
    x=np.zeros((5,4,6));x[0]=np.linspace(600.,-600.,6)[None];x[1]=-x[0]
    f=m.base.balanced(x,np.zeros((5,5,5)),d.dx,d.dy)
    return case,p,s,g,air,state,f,np.zeros_like(g.mass)


def test_parcel_forms_rain_while_mixed_cell_is_unsaturated_without_adding_water():
    case,p,s,g,air,state,f,q=cloudy_fixture();d=case.domain
    saved=deepcopy(state)
    bulk=m.advance(state,d,p,s,f,60.,0.,air,geometry=g,boundary=q)
    parcel=m.advance(state,d,p,s,f,60.,0.,air,geometry=g,boundary=q,condensation_mode='parcel_lower')
    assert bulk[1].max()==0. and parcel[8][1].min()>0.
    assert parcel[1].sum()>bulk[1].sum() and not parcel[8][4].any()
    assert parcel[0].water.min()>=0 and parcel[0].soil.min()>=0
    assert abs(parcel[4]['water_error_mm'])<1e-9 and abs(parcel[4]['energy_error_j_m2'])<1e-5
    assert parcel[7]<1e-9
    carried=np.maximum(f.vertical,0.)*60.*state.water[:-1]/g.mass[:-1]
    assert (parcel[8][1:]<=carried+1e-12).all()
    for name in ('water','energy','soil'):np.testing.assert_array_equal(getattr(state,name),getattr(saved,name))


def test_no_upward_flow_or_no_vapor_gives_no_parcel_rain():
    case,p,s,g,air,state,f,q=cloudy_fixture();target=air[0]
    quiet=m.base.balanced(np.zeros_like(f.x),np.zeros_like(f.y),case.domain.dx,case.domain.dy)
    assert not m.ascending_condensate(state,s,quiet,60.,g,target,'parcel_all').any()
    dry=m.base.State(np.zeros_like(state.water),state.energy-m.base.LV*state.water,state.soil)
    assert not m.ascending_condensate(dry,s,f,60.,g,target,'parcel_all').any()


def test_parcel_dose_is_proportional_to_existing_dry_mass_flux():
    case,p,s,g,air,state,f,q=cloudy_fixture()
    small=m.ascending_condensate(state,s,f,60.,g,air[0],'parcel_lower')
    doubled=replace(f,x=f.x*2,y=f.y*2,vertical=f.vertical*2)
    large=m.ascending_condensate(state,s,doubled,60.,g,air[0],'parcel_lower')
    np.testing.assert_array_equal(large,small*2)


@pytest.mark.parametrize('mode',m.MODES)
@pytest.mark.parametrize('factor',[1.,.5])
def test_tiny_year_closure_resume_and_exact_bulk_control(mode,factor,tmp_path,monkeypatch):
    d,p,s,g,air,flows,a,_=calendar_fixture();monkeypatch.setattr(m,'EDGES',a['edges']);monkeypatch.setattr(m.parent,'EDGES',a['edges'])
    state=m.core.initial_state(d,p,s,g,air);driver=ToyDriver(d,flows,a)
    full=m.year(d,p,s,state,air,d.land,g,driver,condensation_mode=mode,time_factor=factor)
    assert abs(full[-1]['budget']['annual_water_error_mm'])<1e-6
    assert abs(full[-1]['budget']['annual_energy_error_j_m2'])<1.
    if mode=='bulk' and factor==1.:
        old=m.parent.year(d,p,s,state,air,d.land,g,driver);replay.verify_physical(full,old)
    interrupted=[False]
    def save(*record):
        replay.run.parent.write_checkpoint(tmp_path,1,record)
        if record[-1]['month']==2:interrupted[0]=True
    with pytest.raises(m.base.BudgetStop):m.year(d,p,s,state,air,d.land,g,driver,condensation_mode=mode,time_factor=factor,save_month=save,should_stop=lambda:interrupted[0])
    partial=replay.run.parent.read_checkpoint(tmp_path,1,d.land.shape)
    resumed=m.year(d,p,s,state,air,d.land,g,driver,condensation_mode=mode,time_factor=factor,checkpoint=partial)
    replay.verify_physical(resumed,full)


def test_bad_closure_and_timestep_rejected():
    case,p,s,g,air,state,f,q=cloudy_fixture()
    with pytest.raises(ValueError,match='mode'):m.advance(state,case.domain,p,s,f,60.,0.,air,geometry=g,boundary=q,condensation_mode='unknown')
    with pytest.raises(ValueError,match='factor'):m.year(case.domain,p,s,state,air,case.score_mask,g,None,time_factor=.2)
