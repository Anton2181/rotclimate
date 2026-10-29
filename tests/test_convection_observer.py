import numpy as np
from rotclimate.shared_transport_backend import make_shared_transport_backend
from rotclimate.convection_observer import observe_convection
from test_shared_transport_backend import trajectory


def test_observer_copies_cannot_change_complete_coupled_trajectory():
    base=make_shared_transport_backend();records=[]
    def observer(record):
        records.append(record['certificate']['converged'])
        for value in record.values():
            if isinstance(value,np.ndarray):value.fill(-999)
        record['certificate']['converged']=False
    watched=observe_convection(base,observer);old=trajectory(base);new=trajectory(watched)
    for a,b in [(old[0].temperature_k,new[0].temperature_k),(old[0].vapor_kg_m2,new[0].vapor_kg_m2),(old[0].u_east,new[0].u_east),(old[0].v_south,new[0].v_south),(old[1].temperature_k,new[1].temperature_k),(old[1].liquid_kg_m2,new[1].liquid_kg_m2),(old[2],new[2])]:np.testing.assert_array_equal(a,b)
    assert records==[True]*8 and old[3]==new[3]
    assert base.advance_with_convection.__globals__['adjust_convection'] is base.adjustment
    assert watched.advance_with_convection.__code__ is base.advance_with_convection.__code__
    assert watched.surface_coupled.__code__ is base.surface_coupled.__code__


def test_nonconverged_target_keeps_result_and_original_controls():
    base=make_shared_transport_backend();records=[];watched=observe_convection(base,records.append)
    p=np.geomspace(100000,40000,21);t=np.linspace(305,210,21)[:,None,None];w=np.zeros_like(t);m=np.full_like(t,250.)
    expected=base.adjustment(t,w,m,p,max_sweeps=1);actual=watched.adjustment(t,w,m,p,max_sweeps=1)
    assert not expected.certificate['converged']
    np.testing.assert_array_equal(expected.temperature_k,actual.temperature_k)
    np.testing.assert_array_equal(records[0]['input_temperature'],t)
    assert records[0]['certificate']==expected.certificate and records[0]['controls']==dict(max_sweeps=1)
