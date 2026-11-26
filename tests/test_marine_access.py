import numpy as np
import pytest

from scripts.marine_access import backtrace,production_geometry,SEA,EXIT,CALM,LIMIT


@pytest.mark.parametrize('step',[.25,.125])
def test_westerly_flow_reaches_west_sea_but_easterly_flow_leaves_domain(step):
    land=np.ones((9,9),bool);land[:,:3]=False
    u=np.ones(land.shape);v=np.zeros_like(u)
    kwargs=dict(cell_km=1.,step_km=step,horizon_km=8.)
    a=backtrace(land,u,v,[[4,5]],**kwargs);b=backtrace(land,-u,v,[[4,5]],**kwargs)
    assert a['status'][0]==SEA and land[a['sea_r'][0],a['sea_c'][0]]==False
    assert 2.5<=a['distance_km'][0]<=2.5+step
    assert b['status'][0]==EXIT


def test_northward_wind_comes_from_southern_rows():
    land=np.ones((9,9),bool);land[6:]=False
    r=backtrace(land,np.zeros((9,9)),np.ones((9,9)),[[3,4]],cell_km=1.,step_km=.25,horizon_km=8.)
    assert r['status'][0]==SEA and r['sea_r'][0]>=6


def test_alongshore_flow_does_not_become_marine_from_a_nearby_sea():
    land=np.ones((21,9),bool);land[:,:3]=False
    r=backtrace(land,np.zeros(land.shape),np.ones(land.shape),[[10,4]],cell_km=1.,step_km=.25,horizon_km=4.)
    assert r['status'][0]==LIMIT and r['distance_km'][0]==4


def test_calm_and_off_domain_remain_distinct_from_resolved_land_path():
    land=np.ones((5,5),bool);zero=np.zeros((5,5))
    calm=backtrace(land,zero,zero,[[2,2]],cell_km=1.,step_km=.25,horizon_km=8.)
    edge=backtrace(land,np.ones((5,5)),zero,[[2,2]],cell_km=1.,step_km=.25,horizon_km=8.)
    assert calm['status'][0]==CALM and calm['distance_km'][0]==0
    assert edge['status'][0]==EXIT and edge['sea_r'][0]==-1


def test_production_geometry_exposes_virtual_exterior_sea_on_all_land_grid():
    g=production_geometry(np.ones((5,5),bool),56.,567.)
    assert not g['has_sea'] and not g['nearest_valid_sea'].any()
    assert (g['nearest_r']<0).any()


def test_trajectory_crosses_bent_channel_in_spatially_varying_flow():
    land=np.ones((21,21),bool);land[0,:]=False
    rr,cc=np.indices(land.shape);u=.1*(cc-10);v=-np.ones(land.shape)
    r=backtrace(land,u,v,[[10,11]],cell_km=1.,step_km=.125,horizon_km=15.)
    assert r['status'][0]==SEA and r['sea_r'][0]==0


def test_invalid_winds_or_nonland_start_are_rejected():
    land=np.ones((5,5),bool);land[:,0]=False;zero=np.zeros((5,5))
    with pytest.raises(ValueError,match='scored land'):
        backtrace(land,zero,zero,[[2,0]],cell_km=1.,step_km=.25,horizon_km=2.)
    bad=zero.copy();bad[0,0]=np.nan
    with pytest.raises(ValueError,match='Finite winds'):
        backtrace(land,bad,zero,[[2,2]],cell_km=1.,step_km=.25,horizon_km=2.)
