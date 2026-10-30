import pytest

from rotclimate.config import Params
from rotclimate.joint import SHARED_FIELDS, validate_partition
from rotclimate.model import ClimateModel


def r39():
    return Params.from_json('calibration/local_accuracy_20261023/r39_params.json')


def test_new_switches_default_off_and_are_classified():
    p = Params()
    assert p.dry_heating == 0.0 and p.dry_heating_chi0 == 0.0 and p.wind_source == 'model'
    assert p.monsoon_westerly == 0.0 and p.itcz_shift_ocean < 0 and p.shelf_warm_currents == 0.0
    assert p.zonal_land_friction == 0.0 and p.ocean_column_air == 0.0
    validate_partition()
    assert {'dry_heating', 'dry_heating_chi0', 'wind_source', 'monsoon_westerly', 'itcz_shift_ocean', 'monsoon_pressure_hpa',
            'shelf_warm_currents', 'zonal_land_friction', 'ocean_column_air'} <= SHARED_FIELDS
    p = r39()
    assert p.dry_heating == 0.0 and p.wind_source == 'model'


@pytest.mark.parametrize('changes, message', [
    (dict(wind_source='reanalysis'), 'wind_source must be'),
    (dict(wind_source='observed'), 'needs an Earth grid with obs_wind'),
    (dict(dry_heating=-1.0), 'dry_heating must be'),
    (dict(dry_heating=3.0, soil_bucket_mm=0.0), 'needs the soil bucket'),
    (dict(dry_heating=3.0, dry_heating_chi0=1.0), 'dry_heating_chi0 must be'),
    (dict(dry_heating=3.0, dry_heating_chi0=0.6, continentality=0.0), 'advected land share'),
    (dict(monsoon_westerly=1.5), 'monsoon_westerly must be'),
    (dict(shelf_warm_currents=1.2), 'shelf_warm_currents must be'),
    (dict(zonal_land_friction=1.0), 'zonal_land_friction must be'),
    (dict(ocean_column_air=1.5), 'ocean_column_air must be'),
    (dict(ocean_column_air=0.5, column_saturation_scheme='pressure-moist'), 'ocean_column_air must be'),
    (dict(monsoon_westerly=0.7, monsoon_pressure_hpa=-1.0), 'monsoon_pressure_hpa must be'),
])
def test_invalid_switches_are_refused_before_any_run(changes, message):
    with pytest.raises(ValueError, match=message):
        ClimateModel(r39().replace(**changes))


def test_monsoon_westerlies_turn_only_cross_equatorial_trades():
    import numpy as np
    from types import SimpleNamespace

    p = r39().replace(retrograde=False, north_bearing=0.0)        # Earth's spin, as earth.earth_params sets
    lat = np.linspace(-30, 60, 91)[:, None] * np.ones((1, 3))
    fake = SimpleNamespace(p=p, lat=lat, hadley_scale=1.0, land_broad=np.zeros_like(lat),
                           g=SimpleNamespace(land=np.zeros(lat.shape, bool), cell_km=56.0))
    july = 1.0
    u0, v0, phi_i, _ = ClimateModel.zonal_wind(fake, july)
    fake.p = p.replace(monsoon_westerly=0.7)
    u1, v1, _, _ = ClimateModel.zonal_wind(fake, july)
    between = (lat > 0) & (lat < phi_i)
    assert (u1[between] > u0[between]).all() and (v1[between] >= v0[between] - 1e-12).all()
    assert np.array_equal(u1[~between], u0[~between]) and np.array_equal(v1[~between], v0[~between])


def test_monsoon_gate_follows_the_models_own_pressure():
    import numpy as np
    from types import SimpleNamespace

    p = r39().replace(retrograde=False, north_bearing=0.0, monsoon_westerly=0.7, monsoon_pressure_hpa=2.0)
    lat = np.linspace(40, -5, 46)[:, None] * np.ones((1, 4))            # rows run south, 1 degree apart
    g = SimpleNamespace(land=np.zeros(lat.shape, bool), cell_km=111.0)
    fake = SimpleNamespace(p=p, lat=lat, hadley_scale=1.0, land_broad=np.zeros_like(lat), g=g)
    plain, _, phi_i, _ = ClimateModel.zonal_wind(SimpleNamespace(**vars(fake), last_pres=None), 1.0)
    between = (lat > 0) & (lat < phi_i)
    heat_low = 100.0 * 5.0 * (lat - 40.0) / -1000.0 * 111.0        # pressure falling 5 hPa per 1,000 km poleward
    turned, _, _, _ = ClimateModel.zonal_wind(SimpleNamespace(**vars(fake), last_pres=heat_low), 1.0)
    high = ClimateModel.zonal_wind(SimpleNamespace(**vars(fake), last_pres=-heat_low), 1.0)[0]
    assert np.array_equal(plain, high)                                   # pressure rising poleward: trades stay
    assert (turned[between] > plain[between]).all()
    assert np.array_equal(turned[~between], plain[~between])


def test_shelf_rule_only_removes_warm_current_over_shallow_sea():
    import numpy as np
    from types import SimpleNamespace

    p = r39().replace(retrograde=False, north_bearing=0.0)
    lat = np.full((3, 4), 30.0)
    base = dict(lat=lat, side=np.array([[-1.0, -1.0, 1.0, 1.0]] * 3), gyre=None, enclosure=np.zeros_like(lat),
                sea_deep=None, lakeness=np.zeros_like(lat))
    deep = np.array([[0.0, 1.0, 0.0, 1.0]] * 3)
    To = np.full_like(lat, 20.0)
    plain = ClimateModel.sst(SimpleNamespace(p=p, shelf_deep=None, **base), 0.0, To, To)
    shelf = ClimateModel.sst(SimpleNamespace(p=p.replace(shelf_warm_currents=1.0), shelf_deep=deep, **base), 0.0, To, To)
    warm = plain > To                                   # west side of the basin (east coast of a continent)
    assert warm[:, :2].all() and not warm[:, 2:].any()
    assert np.allclose(shelf[:, 0], To[:, 0])             # warm current kept off the shelf
    assert np.array_equal(shelf[:, 1:], plain[:, 1:])     # deep warm water and cold currents unchanged


def test_land_friction_slows_the_zonal_belts_over_land_only():
    import numpy as np
    from types import SimpleNamespace

    p = r39().replace(retrograde=False, north_bearing=0.0)
    lat = np.linspace(-30, 70, 101)[:, None] * np.ones((1, 4))
    share = np.array([[0.0, 0.0, 0.5, 1.0]] * 101)          # sea, sea, coast, interior
    fake = SimpleNamespace(p=p, lat=lat, hadley_scale=1.0, land_broad=np.zeros_like(lat), land_friction=share,
                           g=SimpleNamespace(land=share > 0.4, cell_km=56.0))
    u0, v0, _, _ = ClimateModel.zonal_wind(fake, -1.0)
    fake.p = p.replace(zonal_land_friction=0.6)
    u1, v1, _, _ = ClimateModel.zonal_wind(fake, -1.0)
    assert np.array_equal(u1[:, :2], u0[:, :2]) and np.array_equal(v1[:, :2], v0[:, :2])
    assert np.allclose(u1[:, 2], 0.7 * u0[:, 2]) and np.allclose(u1[:, 3], 0.4 * u0[:, 3])
    assert np.allclose(v1[:, 3], 0.4 * v0[:, 3])
