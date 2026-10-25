import numpy as np
from scipy import ndimage as ndi
from polity.routes import lines


def sea_lines(shape=(31,61),junction=False):
    h,w=shape
    x=np.arange(6,w-6);a=(h//2)*w+x[:-1];b=a+1
    if junction:
        y=np.arange(6,h//2+1);c=y[:-1]*w+w//2
        a=np.r_[a,c];b=np.r_[b,c+w]
    return [r for r in lines(dict(edges=(a,b,np.full(len(a),100.))),np.ones(shape,bool),shape) if r[0]=='sea']


def test_one_corridor_has_one_centerline_instead_of_a_copy_per_traffic_class():
    routes=sea_lines();assert routes
    seen=set()
    for kind,category,points,weight in routes:
        assert weight>0
        for a,b in zip(points,points[1:]):
            edge=tuple(sorted((a,b)))
            assert edge not in seen
            seen.add(edge)
    assert max(x for r in routes for y,x in r[2])-min(x for r in routes for y,x in r[2])>35


def test_short_junction_links_are_retained_in_the_sea_network():
    mask=np.zeros((31,61),bool)
    for _,_,points,_ in sea_lines(junction=True):
        for y,x in points:mask[y,x]=True
    assert mask.any()
    assert ndi.label(mask,structure=np.ones((3,3)))[1]==1


def test_empty_sea_routes_are_valid():
    empty=np.zeros(0,dtype=np.int64)
    assert lines(dict(edges=(empty,empty,np.zeros(0))),np.ones((20,20),bool),(20,20))==[]


def test_lane_rendering_does_not_depend_on_edge_arrow_orientation():
    shape=(31,61);water=np.ones(shape,bool);a=15*61+np.arange(6,54);b=a+1;f=np.full(len(a),100.)
    first=lines(dict(edges=(a,b,f)),water,shape)
    assert lines(dict(edges=(b,a,f)),water,shape)==first


def test_opposite_shipments_are_summed_before_traffic_classification():
    shape=(31,61);water=np.ones(shape,bool);a=15*61+np.arange(6,54);b=a+1
    merged=lines(dict(edges=(a,b,np.full(len(a),150.))),water,shape)
    separate=lines(dict(edges=(np.r_[a,b],np.r_[b,a],np.r_[np.full(len(a),100.),np.full(len(a),50.)])),water,shape)
    assert separate==merged
