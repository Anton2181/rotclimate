"""Marine relaxation requires an actual sea; exercise genuine coupled solves."""
import numpy as np
import pytest

from rotclimate.model import ClimateModel
from test_earth import _toy_case
from test_transient_orography import strict_params


@pytest.mark.parametrize('land_mode', ['all_land', 'all_sea'])
def test_homogeneous_domain_cannot_invent_land_marine_exchange(land_mode):
    case = _toy_case()
    grid = case.grid
    grid.land[:] = land_mode == 'all_land'
    grid.land_frac[:] = grid.land
    grid.elev[:] = np.where(grid.land, 300., 0.)
    grid.elev_max[:] = grid.elev
    p = strict_params().replace(inflow_gain=1., inflow_sst=-100., inflow_km=1e6)
    active = ClimateModel(p, grid=grid)
    if land_mode == 'all_land':
        # An effective marine reach cannot exist without a real source. This
        # detects the fake EDT source before any coupled solve is attempted.
        assert not np.any(getattr(active, 'inflow_reach', np.zeros_like(grid.land)))
    a = active.run(diagnose_moisture=True)
    b = ClimateModel(p.replace(inflow_gain=0.), grid=grid).run(diagnose_moisture=True)
    assert a.numerics['all_checks_passed'] and b.numerics['all_checks_passed']
    assert not a.moisture_budget['marine_exchange'].any()
    for name in ['T', 'Tsl', 'P', 'W', 'E', 'u', 'v']:
        actual, reference = getattr(a, name), getattr(b, name)
        assert actual.dtype == reference.dtype and actual.shape == reference.shape
        assert actual.tobytes() == reference.tobytes(), name


def test_mixed_domain_retains_real_nearest_sea_sources():
    case = _toy_case()
    model = ClimateModel(strict_params().replace(inflow_gain=1.), grid=case.grid)
    near = model.inflow_near
    assert all((a >= 0).all() and (a < case.grid.land.shape[k]).all() for k, a in enumerate(near))
    assert (~case.grid.land[near]).all()
    assert (model.inflow_reach[case.grid.land] > 0).all()
    assert not model.inflow_reach[~case.grid.land].any()
