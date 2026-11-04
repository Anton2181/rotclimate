import numpy as np
import pytest
from harvest.mobility_landscape import sample_landscape,trace_move
from harvest.seasonal_mobility import seasonal_circuit


def test_wider_landscape_does_not_pool_grazing_cells_and_lattices_nest():
    land=np.ones((13,13),bool);elev=np.zeros_like(land,float)
    sparse=sample_landscape(elev,land,(6,6),radius=5,stride=4,cell_km=1)
    dense=sample_landscape(elev,land,(6,6),radius=5,stride=4,offsets=((0,0),(2,2)),cell_km=1)
    np.testing.assert_array_equal(sparse.rows,dense.rows);np.testing.assert_array_equal(sparse.columns,dense.columns)
    assert set(sparse.candidates).issubset(dense.candidates)
    assert len(dense.candidates)>len(sparse.candidates)
    # Every candidate is ONE actual fine cell. The transit graph has more
    # cells, whose resources are not silently assigned to those candidates.
    assert len(dense.candidates)<len(dense.rows)
    p=trace_move(dense,dense.home,0)
    assert p[0]==dense.candidates[dense.home] and p[-1]==dense.candidates[0]
    assert all(max(abs(dense.rows[a]-dense.rows[b]),abs(dense.columns[a]-dense.columns[b]))==1 for a,b in zip(p,p[1:]))


def test_landscape_excludes_islands_and_cannot_cut_a_water_corner():
    land=np.zeros((5,5),bool);land[1,1]=True;land[2,2]=True
    world=sample_landscape(np.zeros((5,5)),land,(1,1),radius=3,stride=1,cell_km=1)
    assert len(world.rows)==1 and world.home==0
    assert trace_move(world,0,0)==[0]


def test_additional_bases_cannot_reduce_optimal_feeding():
    shape=(13,13);z=np.zeros(shape);land=np.ones(shape,bool)
    sparse=sample_landscape(z,land,(6,6),radius=5,stride=4,cell_km=1)
    dense=sample_landscape(z,land,(6,6),radius=5,stride=4,offsets=((0,0),(2,2)),cell_km=1)
    rng=np.random.default_rng(16);supply=rng.uniform(0,45,(12,len(sparse.rows)))
    def solve(w):return seasonal_circuit(supply[:,w.candidates],w.travel,w.home,daily_need=1,reserve_days=0,year_days=360)
    assert solve(dense).objective_unmet<=solve(sparse).objective_unmet+1e-9


def test_transit_budget_is_not_straight_line_distance():
    land=np.ones((9,9),bool);land[1:8,4]=False
    world=sample_landscape(np.zeros((9,9)),land,(4,2),radius=5,stride=1,cell_km=1,level_speed_km_day=1,maximum_move_days=3)
    j=int(np.flatnonzero((world.rows[world.candidates]==4)&(world.columns[world.candidates]==6))[0])
    assert not np.isfinite(world.travel[world.home,j])
    with pytest.raises(ValueError):trace_move(world,world.home,j)


def test_expanding_extent_retains_all_original_reachable_bases():
    z=np.zeros((21,21));land=np.ones(z.shape,bool)
    local=sample_landscape(z,land,(10,10),radius=3,stride=1,cell_km=1)
    regional=sample_landscape(z,land,(10,10),radius=8,stride=4,include_radius=3,cell_km=1)
    coords=lambda a:{(int(a.rows[i]),int(a.columns[i])) for i in a.candidates}
    assert coords(local).issubset(coords(regional))
    assert len(regional.candidates)>len(local.candidates)
