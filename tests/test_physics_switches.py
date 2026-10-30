import pytest

from rotclimate.config import Params
from rotclimate.joint import SHARED_FIELDS, validate_partition
from rotclimate.model import ClimateModel


def r39():
    return Params.from_json('calibration/local_accuracy_20261023/r39_params.json')


def test_new_switches_default_off_and_are_classified():
    p = Params()
    assert p.dry_heating == 0.0 and p.dry_heating_chi0 == 0.0 and p.wind_source == 'model'
    assert p.monsoon_westerly == 0.0 and p.itcz_shift_ocean < 0
    validate_partition()
    assert {'dry_heating', 'dry_heating_chi0', 'wind_source', 'monsoon_westerly', 'itcz_shift_ocean', 'monsoon_pressure_hpa'} <= SHARED_FIELDS
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
