import pytest

from rotclimate.config import Params
from rotclimate.joint import SHARED_FIELDS, validate_partition
from rotclimate.model import ClimateModel


def r39():
    return Params.from_json('calibration/local_accuracy_20261023/r39_params.json')


def test_new_switches_default_off_and_are_classified():
    p = Params()
    assert p.dry_heating == 0.0 and p.dry_heating_chi0 == 0.0 and p.wind_source == 'model'
    validate_partition()
    assert {'dry_heating', 'dry_heating_chi0', 'wind_source'} <= SHARED_FIELDS
    p = r39()
    assert p.dry_heating == 0.0 and p.wind_source == 'model'


@pytest.mark.parametrize('changes, message', [
    (dict(wind_source='reanalysis'), 'wind_source must be'),
    (dict(wind_source='observed'), 'needs an Earth grid with obs_wind'),
    (dict(dry_heating=-1.0), 'dry_heating must be'),
    (dict(dry_heating=3.0, soil_bucket_mm=0.0), 'needs the soil bucket'),
    (dict(dry_heating=3.0, dry_heating_chi0=1.0), 'dry_heating_chi0 must be'),
    (dict(dry_heating=3.0, dry_heating_chi0=0.6, continentality=0.0), 'advected land share'),
])
def test_invalid_switches_are_refused_before_any_run(changes, message):
    with pytest.raises(ValueError, match=message):
        ClimateModel(r39().replace(**changes))
