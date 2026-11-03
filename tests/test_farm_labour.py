"""Resource limits, deadlines and simultaneous human/animal operations."""
import numpy as np
import pytest

from harvest.labour import FarmOperation,plan_farm,minimum_farm_work,InfeasibleFarmPlan


def test_idle_season_cannot_replace_missed_harvest():
    ops=[FarmOperation('Harvest',0,[False,True],[10.])]
    p=plan_farm([100.],ops,land_hectares=10,available_hours=[[1000.],[5.]])
    assert p.hectares==pytest.approx([.5])
    assert p.output==pytest.approx(50)
    assert p.resource_hours_used[:,0]==pytest.approx([0,5])


def test_competing_tasks_share_window_hours():
    ops=[FarmOperation('Sow',0,[True],[4.]),FarmOperation('Harvest',0,[True],[6.])]
    p=plan_farm([100],ops,land_hectares=10,available_hours=[[10.]])
    assert p.land_used==pytest.approx(1.)
    assert p.output==pytest.approx(100.)


def test_human_and_ox_work_must_be_available_together():
    op=FarmOperation('Plough',0,[True,True],[2.,1.])
    p=plan_farm([10],[op],land_hectares=10,available_hours=[[0,10],[10,0]])
    assert p.output==0
    p=plan_farm([10],[op],land_hectares=10,available_hours=[[10,10],[0,0]])
    assert p.land_used==pytest.approx(5.)


def test_land_and_both_crop_activities_share_resources():
    ops=[FarmOperation('A',0,[True],[1.]),FarmOperation('B',1,[True],[3.])]
    p=plan_farm([10,20],ops,land_hectares=4,available_hours=[[8.]])
    assert p.hectares==pytest.approx([2.,2.])
    assert p.output==pytest.approx(60)
    assert p.land_output_marginal==pytest.approx(5)
    assert p.work_output_marginals[0,0]==pytest.approx(5)


def test_all_operations_completed_and_calendar_origin_invariant():
    ops=[FarmOperation('Prep',0,[True,False,False],[3.]),FarmOperation('Harvest',0,[False,True,True],[4.])]
    available=np.array([[12.],[3.],[5.]])
    p=plan_farm([10.],ops,land_hectares=20,available_hours=available)
    rotated=[FarmOperation(o.name,o.activity,np.roll(o.allowed,1),o.hours_per_hectare) for o in ops]
    r=plan_farm([10.],rotated,land_hectares=20,available_hours=np.roll(available,1,axis=0))
    assert p.output==pytest.approx(20.)
    assert r.output==pytest.approx(p.output)
    assert np.max(np.abs(p.task_residual))<1e-9
    assert np.all(p.completed_hectares[~np.asarray(ops[0].allowed),0]==0)


def test_relaxing_work_or_window_never_reduces_food():
    op=FarmOperation('Harvest',0,[True,False],[4.])
    baseline=plan_farm([10.],[op],land_hectares=5,available_hours=[[4.],[4.]])
    wider=plan_farm([10.],[FarmOperation('Harvest',0,[True,True],[4.])],land_hectares=5,available_hours=[[4.],[4.]])
    more=plan_farm([10.],[op],land_hectares=5,available_hours=[[8.],[4.]])
    assert wider.output==more.output==2*baseline.output


def test_zero_land_work_or_productivity_creates_no_food():
    op=FarmOperation('Harvest',0,[True],[1.])
    assert plan_farm([10.],[op],land_hectares=0,available_hours=[[100.]]).output==0
    assert plan_farm([10.],[op],land_hectares=100,available_hours=[[0.]]).output==0
    assert plan_farm([0.],[op],land_hectares=100,available_hours=[[100.]]).output==0


@pytest.mark.parametrize('change',[
    {'land_hectares':-1},{'land_hectares':np.inf},{'available_hours':[[-1.]]},
    {'available_hours':[[np.nan]]},{'output_per_hectare':[-1.]},
    {'operations':[]},{'operations':[FarmOperation('Task',0,[1],[1.])]},
    {'operations':[FarmOperation('Task',0,[False],[1.])]},
    {'operations':[FarmOperation('Task',0,[True],[0.])]},
    {'operations':[FarmOperation('Task',True,[True],[1.])]},
    {'operations':[FarmOperation('Task',1,[True],[1.])]},
])
def test_invalid_scenario_rejected(change):
    kwargs=dict(output_per_hectare=[10.],operations=[FarmOperation('Task',0,[True],[1.])],land_hectares=1,available_hours=[[10.]])
    kwargs.update(change)
    with pytest.raises(ValueError):plan_farm(**kwargs)


def test_minimum_work_selects_output_per_work_unless_land_binds():
    ops=[FarmOperation('A',0,[True],[10.]),FarmOperation('B',1,[True],[20.])]
    ample=minimum_farm_work([100.,150.],ops,required_output=150,land_hectares=2,available_hours=[[100.]])
    scarce=minimum_farm_work([100.,150.],ops,required_output=150,land_hectares=1,available_hours=[[100.]])
    assert ample.hectares==pytest.approx([1.5,0])
    assert ample.resource_hours_used.sum()==pytest.approx(15.)
    assert ample.required_output_work_marginal==pytest.approx(.1)
    assert scarce.hectares==pytest.approx([0,1.])
    assert scarce.resource_hours_used.sum()==pytest.approx(20.)
    assert scarce.output==pytest.approx(150.)
    assert scarce.land_output_marginal is None and scarce.work_output_marginals is None


def test_food_target_infeasible_by_land_or_harvest_window_is_explicit():
    ops=[FarmOperation('Reap',0,[False,True],[10.])]
    for land,hours in [(1,[[1000.],[100.]]),(10,[[1000.],[5.]])]:
        with pytest.raises(InfeasibleFarmPlan):
            minimum_farm_work([100.],ops,required_output=150,land_hectares=land,available_hours=hours)


def test_zero_food_need_requires_no_work_and_cannot_hide_output():
    p=minimum_farm_work([100.],[FarmOperation('Task',0,[True],[10.])],required_output=0,land_hectares=10,available_hours=[[100.]])
    assert p.output==p.land_used==p.resource_hours_used.sum()==0


def test_minimizing_human_work_does_not_remove_animal_constraint():
    ops=[FarmOperation('Manual',0,[True],[10.,0.]),FarmOperation('Team',1,[True],[2.,10.])]
    p=minimum_farm_work([100.,100.],ops,required_output=100,land_hectares=10,available_hours=[[100.,5.]])
    assert p.hectares==pytest.approx([.5,.5])
    assert p.resource_hours_used[0]==pytest.approx([6.,5.])
    no_team=minimum_farm_work([100.,100.],ops,required_output=100,land_hectares=10,available_hours=[[100.,0.]])
    assert no_team.hectares==pytest.approx([1.,0.])
    assert no_team.resource_hours_used[0,0]==pytest.approx(10.)
    conserve_team=minimum_farm_work([100.,100.],ops,required_output=100,land_hectares=10,
        available_hours=[[100.,100.]],resource_index=1)
    assert conserve_team.hectares==pytest.approx([1.,0.])
    assert conserve_team.minimized_resource==1 and conserve_team.resource_hours_used[0,1]==0


def test_work_target_monotonic_and_calendar_rotation_invariant():
    ops=[FarmOperation('Reap',0,[True,False],[10.])];availability=np.array([[100.],[1.]])
    plans=[minimum_farm_work([100.],ops,required_output=need,land_hectares=10,available_hours=availability) for need in [50,100,200]]
    assert [p.resource_hours_used.sum() for p in plans]==pytest.approx([5,10,20])
    rotated=minimum_farm_work([100.],[FarmOperation('Reap',0,[False,True],[10.])],required_output=100,
        land_hectares=10,available_hours=np.roll(availability,1,axis=0))
    assert rotated.resource_hours_used.sum()==pytest.approx(10.)


@pytest.mark.parametrize('change',[
    {'required_output':-1},{'required_output':np.inf},{'required_output':np.nan},
    {'resource_index':True},{'resource_index':1.5},{'resource_index':1},{'resource_index':-1},
])
def test_invalid_work_target_or_resource_rejected(change):
    kwargs=dict(output_per_hectare=[100.],operations=[FarmOperation('Task',0,[True],[10.])],required_output=100.,land_hectares=10,available_hours=[[100.]])
    kwargs.update(change)
    with pytest.raises(ValueError):minimum_farm_work(**kwargs)
