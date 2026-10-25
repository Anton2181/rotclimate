import numpy as np
import pytest
from experiments.orographic_moments import uplift_moments,rectangle_weights


def test_a_smooth_plane_has_no_unresolved_hill_increment_at_any_grid_size():
    x=(np.arange(336)+.5)*1000.;h=np.broadcast_to(.01*x,(112,336))
    for block in [7,14,28,56]:
        r=uplift_moments(h,1000.,block,u=10.)
        np.testing.assert_allclose(r['positive_ascent_ms'],.1,atol=1e-14)
        np.testing.assert_allclose(r['unresolved_positive_increment_ms'],0.,atol=1e-14)
        np.testing.assert_allclose(r['legacy_relief_m'],.01*1000*(block-1)/2.)


def test_sinusoidal_hill_uplift_matches_its_analytic_positive_mean():
    x=np.arange(400)*1000.;amplitude=200.;length=100000.;wind=10.
    h=np.broadcast_to(amplitude*np.sin(2*np.pi*x/length),(200,400))
    expected=wind*amplitude*(2*np.pi/length)/np.pi
    r=uplift_moments(h,1000.,20,u=wind)
    assert r['positive_ascent_ms'].mean()==pytest.approx(expected,rel=.003)
    assert r['unresolved_positive_increment_ms'].max()>0.


def test_aggregating_the_same_fine_terrain_preserves_mean_positive_ascent():
    rng=np.random.default_rng(45);h=rng.normal(0,200,(120,240))
    values=[]
    for block in [1,2,5,10,20,40]:
        r=uplift_moments(h,1000.,block,u=4.,v=7.)
        values.append(r['positive_ascent_ms'].mean())
        np.testing.assert_allclose(r['positive_ascent_ms'],
            np.maximum(r['mean_ascent_ms'],0.)+r['unresolved_positive_increment_ms'],atol=1e-14)
    np.testing.assert_allclose(values,values[0],rtol=1e-14)


def test_wind_direction_and_northward_coordinate_sign_are_explicit():
    y,x=np.mgrid[:60,:120];h=.01*x*1000.-.02*y*1000.
    north=uplift_moments(h,1000.,10,v=5.)
    south=uplift_moments(h,1000.,10,v=-5.)
    np.testing.assert_allclose(north['positive_ascent_ms'],.1,atol=1e-14)
    np.testing.assert_allclose(south['positive_ascent_ms'],0.,atol=1e-14)
    calm=uplift_moments(h,1000.,10)
    np.testing.assert_array_equal(calm['positive_ascent_ms'],0.)


@pytest.mark.parametrize('spacing,block',[(0.,10),(np.nan,10),(1000.,0),(1000.,7)])
def test_invalid_geometry_is_rejected(spacing,block):
    with pytest.raises(ValueError):uplift_moments(np.ones((60,120)),spacing,block)


def test_fractional_cells_preserve_the_same_rectangle_area_on_unaligned_grids():
    for cell in [14.,28.,56.]:
        x=np.arange(-1000.,1000.,cell)+7.25
        y=np.arange(-1000.,1000.,cell)-3.5
        xx,yy=np.meshgrid(x,y)
        weights=rectangle_weights(xx,yy,cell,173.,119.)
        assert weights.min()>=0. and weights.max()<=1.
        assert weights.sum()*cell**2==pytest.approx(346.*238.,rel=1e-13)
