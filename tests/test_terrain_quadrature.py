import numpy as np
import pytest
from experiments.terrain_quadrature import from_terrain,overlap_weights
from rotclimate.orography import terrain_uplift,validate_terrain_samples
from rotclimate.config import Params
from rotclimate.model import ClimateModel


def terrain():
    x=np.arange(-119.,120.,14.);y=x[::-1]
    xx,yy=np.meshgrid(x*1000,y*1000)
    return x,y,xx,yy


def test_smooth_plane_has_no_resolution_dependent_extra_uplift():
    x,y,xx,yy=terrain();height=.01*xx+.006*yy
    for step,centers in [(28.,np.array([-42,-14,14,42])),(56.,np.array([-28,28]))]:
        q=from_terrain(height,x,y,centers,centers[::-1],14.,step)
        np.testing.assert_allclose(terrain_uplift(q,8.,5.),.11,rtol=0,atol=1e-14)


def test_common_terrain_preserves_mean_capped_uplift_under_aggregation():
    x,y,xx,yy=terrain();height=500*np.sin(xx*2*np.pi/112000.)+200*np.cos(yy*2*np.pi/56000.)
    averages=[]
    for step,centers in [(28.,np.array([-42,-14,14,42])),(56.,np.array([-28,28]))]:
        q=from_terrain(height,x,y,centers,centers[::-1],14.,step)
        result=terrain_uplift(q,12.,3.);assert (result>=0).all() and (result<=.2).all()
        averages.append(result.mean())
    assert averages[0]==pytest.approx(averages[1],abs=1e-14)


def test_northward_sign_and_perpendicular_wind():
    x,y,xx,yy=terrain();q=from_terrain(.01*yy,x,y,[0.],[0.],14.,56.)
    assert terrain_uplift(q,0.,10.).item()==pytest.approx(.1)
    assert terrain_uplift(q,0.,-10.).item()==0
    assert terrain_uplift(q,10.,0.).item()==0


def test_wind_variations_and_pointwise_cap():
    q=np.array([[[[.01]], [[-.01]]],[[[0.]],[[0.]]],[[[.5]],[[.5]]]])
    assert terrain_uplift(q,0.,0.,wind_std=3.).item()==pytest.approx(.03/np.sqrt(2*np.pi),abs=1e-10)
    assert terrain_uplift(q,1000.,0.).item()==pytest.approx(.1)


def test_uncovered_and_overlapping_reference_cells_are_rejected():
    with pytest.raises(ValueError,match='cover'):overlap_weights([0.],[0.],14.,56.)
    with pytest.raises(ValueError,match='cover'):overlap_weights([0.,1.],[0.],14.,14.)


@pytest.mark.parametrize('bad',[np.full((3,1,2,2),np.nan),np.zeros((3,1,2,2))])
def test_invalid_terrain_weights_are_rejected(bad):
    with pytest.raises(ValueError):validate_terrain_samples(bad,(2,2))


def test_replaced_relief_cannot_be_counted_twice():
    with pytest.raises(ValueError,match='replaces'):
        ClimateModel(Params(orographic_scheme='terrain-quadrature',subgrid_orographic=1.))


def test_flat_quadrature_reproduces_legacy_coupled_fields_exactly():
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth
    case=_toy_case();g=case.grid;g.elev[:]=0;g.elev_max[:]=0
    g.terrain_slopes=np.zeros((3,1,*g.land.shape));g.terrain_slopes[2]=1.
    p=strict_params().replace(subgrid_orographic=0.)
    a=ClimateModel(earth.earth_params(p,case),grid=g).run()
    b=ClimateModel(earth.earth_params(p.replace(orographic_scheme='terrain-quadrature'),case),grid=g).run()
    assert a.numerics['all_checks_passed'] and b.numerics['all_checks_passed']
    for field in ['T','P','W','u','v','E']:
        np.testing.assert_array_equal(getattr(a,field),getattr(b,field))


def test_new_uplift_is_a_sink_in_the_solved_vapor_equation():
    from test_earth import _toy_case
    from test_transient_orography import strict_params
    from rotclimate import earth
    case=_toy_case();g=case.grid;g.elev[:]=0;g.elev_max[:]=0
    g.terrain_slopes=np.zeros((3,2,*g.land.shape))
    g.terrain_slopes[0,0]=.02;g.terrain_slopes[0,1]=-.02;g.terrain_slopes[2]=.5
    p=strict_params().replace(subgrid_orographic=0.,orographic_scheme='terrain-quadrature')
    r=ClimateModel(earth.earth_params(p,case),grid=g).run(diagnose_moisture=True)
    old=ClimateModel(earth.earth_params(p.replace(orographic_scheme='legacy'),case),grid=g).run()
    assert r.numerics['all_checks_passed'] and old.numerics['all_checks_passed']
    assert np.max(np.abs(r.P-old.P))>1e-4
    sl=(slice(None),)+g.map_slice()
    residual=r.moisture_budget['absolute_residual']/np.maximum(r.P[sl]+np.abs(r.E[sl]),.1)
    assert residual.max()<=p.moisture_residual_tol*1.0001
    assert r.W.min()>=0 and r.P.min()>=0


def test_input_identity_tracks_fine_terrain_changes():
    from test_earth import _toy_case
    from scripts.local_benchmark_protocol import case_hash
    case=_toy_case();before=case_hash(case)
    case.grid.terrain_slopes=np.zeros((3,1,*case.grid.land.shape));case.grid.terrain_slopes[2]=1.
    prepared=case_hash(case);assert prepared!=before
    case.grid.terrain_slopes[0,0,0,0]=.01
    assert case_hash(case)!=prepared
