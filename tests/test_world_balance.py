from dataclasses import asdict
import pytest
from rotclimate.config import Params
from scripts.check_r39_world_balance import blend_world,blend_metrics


def test_geometry_path_preserves_all_physics_and_planet_properties():
    a=Params(retrograde=True,tilt=33.5,solar_flux=1.0,tier_tops=(50,500,1000,2400))
    b=a.replace(lat_center=a.lat_center+2,beyond_east_land=.6,tier_tops=(60,600,1100,2600))
    result=blend_world(a,b,.5)
    assert result.tier_tops==(55,550,1050,2500)
    changed={k for k,v in asdict(result).items() if v!=getattr(a,k)}
    assert changed=={'lat_center','beyond_east_land','tier_tops'}


@pytest.mark.parametrize('change',[dict(solar_flux=1.01),dict(tilt=24),dict(precip_tau_days=7)])
def test_geometry_interpolation_rejects_changed_shared_physics(change):
    a=Params()
    with pytest.raises(ValueError):blend_world(a,a.replace(**change),.5)


def test_ranking_summary_does_not_average_numerical_certificates_or_mutate_inputs():
    a=dict(zonefit=.18,recall=dict(tree=.04),numerics=dict(all_checks_passed=True))
    b=dict(zonefit=.20,recall=dict(tree=.06),numerics=dict(all_checks_passed=True))
    result=blend_metrics(a,b,.5)
    assert result['recall']['tree']==.05
    assert 'numerics' not in result
    assert a['recall']['tree']==.04
