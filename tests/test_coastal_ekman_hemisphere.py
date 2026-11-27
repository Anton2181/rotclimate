"""Known-answer coastline tests exercise the production SST upwelling block."""
import numpy as np
import pytest
from rotclimate.model import ClimateModel
from test_earth import _toy_case
from test_transient_orography import strict_params


class SurfaceCaptured(Exception):
    pass


@pytest.mark.parametrize('latitude,retrograde,northward,cools', [
    (30., False, -5., True), (30., True, 5., True),
    (-30., False, 5., True), (-30., True, -5., True),
    (30., False, 5., False), (30., True, -5., False),
    (-30., False, -5., False), (-30., True, 5., False),
    (0., False, -5., False), (0., True, 5., False),
])
def test_west_coast_surface_responds_to_signed_coriolis(latitude, retrograde, northward, cools):
    grid = _toy_case().grid
    grid.land[:] = False
    grid.land[:, 15:] = True  # west coast: offshore is west
    grid.land_frac[:] = grid.land
    grid.elev[:] = 0.
    grid.elev_max[:] = 0.
    grid.lat[:] = latitude
    m = ClimateModel(strict_params().replace(upwelling=4., retrograde=retrograde), grid=grid)
    # Prescribe a constant known wind and20C uncoupled sea to isolate the first
    # production SST step. Stop at its existing diagnostic tap BEFORE any heat
    # or moisture solve. These are ten source snapshots, not climate reruns.
    zeros = np.zeros_like(grid.lat)
    m.zonal_wind = lambda season:(zeros, np.full_like(zeros, northward), zeros, zeros)
    m.sst = lambda day, zonal_sea, land:np.full_like(zeros, 20.)
    surface = []
    def capture(stage, day, value):
        if stage == 'sst':
            surface.append(value.copy())
            raise SurfaceCaptured
    m.tap = capture
    with pytest.raises(SurfaceCaptured):
        m.run()
    near = m.upwelling_weight > .5
    assert near.any()
    if cools:
        assert surface[0][near].mean() < 19.
    else:
        np.testing.assert_array_equal(surface[0], np.full_like(zeros, 20.))


def test_ekman_turn_commutes_with_map_rotation_and_preserves_northern_bytes():
    from rotclimate.winds import ekman_turn
    u = np.array([[0., -3., 4., -0.]])
    v = np.array([[2., 0., -5., -0.]])
    for retrograde in [False, True]:
        expected = (-v, u) if retrograde else (v, -u)
        for actual, old in zip(ekman_turn(u, v, 35., retrograde=retrograde), expected):
            assert actual.dtype == old.dtype and actual.tobytes() == old.tobytes()
    latitude = np.array([[35., -35., 0., -35.]])
    angle = np.radians(37.)
    rotate = lambda a,b:(a*np.cos(angle)+b*np.sin(angle), -a*np.sin(angle)+b*np.cos(angle))
    for retrograde in [False, True]:
        right_up = ekman_turn(*rotate(u, v), latitude, retrograde=retrograde)
        rotated = rotate(*ekman_turn(u, v, latitude, retrograde=retrograde))
        np.testing.assert_allclose(right_up, rotated, atol=2e-15, rtol=0)
