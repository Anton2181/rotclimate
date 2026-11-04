import numpy as np
import pytest
from polity.administrative_hierarchy import hierarchy,minimum_graph,parent_times,reply_times


def test_directed_legs_and_reply_use_the_same_parent():
    # Capital0 <-> province1 <-> seat2, each direction has its own cost.
    graph,_=minimum_graph(4,[(np.array([0,1,1,2]),np.array([1,0,2,1]),np.array([2.,3.,5.,7.]))])
    times=parent_times(graph,1,0,[1,2,3])
    assert np.array_equal(times[0],[2,0,0,3])
    assert np.array_equal(times[1],[2,5,7,3])
    local,chain=reply_times(times)
    assert local[1]==12 and chain[1]==17
    assert np.isinf(chain[2]) and not np.isnan(chain).any()


def test_parallel_alternatives_and_added_edges_cannot_worsen_travel():
    edges=(np.array([0,0,1]),np.array([1,1,2]),np.array([8.,2.,3.]))
    old,removed=minimum_graph(3,[edges]);assert removed==1 and old[0,1]==2
    new,_=minimum_graph(3,[edges,(np.array([0]),np.array([2]),np.array([1.]))])
    from scipy.sparse.csgraph import dijkstra
    assert np.all(dijkstra(new,indices=0)<=dijkstra(old,indices=0))
    assert np.isinf(dijkstra(new,indices=2)[0])


def test_hierarchy_retains_unresolved_seats_and_does_not_assign_nearest_parent():
    rows=[dict(source_id='CAPITAL',name='Capital',map_name='A',marker_id='M',status='matched',province='P',provincial_seat=True,x=0,y=0),
        dict(source_id='C2',name='Disputed',status='ambiguous',province='P',x=None,y=None),
        dict(source_id='C3',name='Missing province',status='matched',map_name='C',marker_id='N',province='Unknown',x=1,y=1)]
    h=hierarchy(dict(commanderies=rows,markers=[dict(id='M',kind='imperial capital')]))
    assert [r['status'] for r in h['links']]==['located','unresolved_seat','unresolved_province']
    assert h['links'][2]['province_id'] is None
    assert h['links'][0]['local_self_link'] and h['links'][0]['imperial_self_link']
    rows.append(dict(rows[0],source_id='duplicate'))
    with pytest.raises(ValueError):hierarchy(dict(commanderies=rows,markers=[dict(id='M',kind='imperial capital')]))


def test_bad_edges_and_leg_shapes_fail_explicitly():
    with pytest.raises(ValueError):minimum_graph(2,[(np.array([0]),np.array([1]),np.array([-1.]))])
    with pytest.raises(ValueError):reply_times([1,2])
