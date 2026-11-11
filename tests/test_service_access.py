import numpy as np
from scipy.sparse.csgraph import dijkstra

from polity.service_access import walking_graph,bounded_roundtrips


def test_water_and_diagonal_corners_are_not_free_service_routes():
    land=np.array([[True,False],[False,True]])
    graph,speed=walking_graph(np.zeros((2,2)),land,np.zeros_like(land),9.)
    assert graph.nnz==0 and speed==0
    rows,cols,a,b=bounded_roundtrips(graph,[0],[3],2.)
    assert len(rows)==len(cols)==len(a)==len(b)==0


def test_uphill_and_return_legs_are_distinct_and_both_must_fit():
    graph,_=walking_graph([[0,900]],[[True,True]],[[False,False]],9.)
    forward=dijkstra(graph,indices=[0])[0,1];back=dijkstra(graph,indices=[1])[0,0]
    assert forward>back
    assert len(bounded_roundtrips(graph,[0],[1],(forward+back)/2)[0])==0
    rows,cols,a,b=bounded_roundtrips(graph,[0],[1],forward+1e-8)
    np.testing.assert_allclose(a,[forward]);np.testing.assert_allclose(b,[back])


def test_open_land_path_has_no_implicit_political_border_or_supply_role():
    graph,speed=walking_graph([[0,0,0]],[[True,True,True]],[[True,True,True]],9.)
    rows,cols,a,b=bounded_roundtrips(graph,[0],[2],1.)
    assert speed<=30+1e-10 and rows.tolist()==cols.tolist()==[0]
    np.testing.assert_allclose(a,[.6]);np.testing.assert_allclose(b,[.6])
