from copy import deepcopy
import pytest
from scripts.check_r39_world import world_failures,build_identity,assert_world_only
from rotclimate.config import Params


def baseline():
    return dict(zonefit=.2,accuracy=.4,recall=dict(cold_dry=.1,tree=.4),
                mediterranean=dict(dry_share=.05,cs_share=.75))


def test_native_objective_gain_cannot_pay_for_worse_strict_accuracy():
    ref=baseline();trial=deepcopy(ref);trial.update(zonefit=.22,accuracy=.399)
    assert 'Native strict accuracy worsened' in world_failures(trial,ref,native=True)


def test_native_gain_cannot_hide_loss_of_a_target_or_mediterranean_moisture():
    ref=baseline();trial=deepcopy(ref);trial['zonefit']=.22
    trial['recall']['tree']-=.021;trial['mediterranean']['dry_share']+=.006
    failures=world_failures(trial,ref,native=True)
    assert any('tree:' in x for x in failures)
    assert 'Mediterranean dry share exceeded allowance' in failures


def test_coarse_screen_allowance_is_not_a_native_publication_allowance():
    ref=baseline();trial=deepcopy(ref);trial.update(zonefit=.202,accuracy=.395)
    trial['recall']['tree']-=.025
    assert not world_failures(trial,ref,native=False)
    assert world_failures(trial,ref,native=True)


def test_checkpoint_identity_distinguishes_planet_and_layout_changes():
    p=Params();a=build_identity(p,[1,2,3])
    assert a!=build_identity(p,[1,2,4])
    assert a!=build_identity(p.replace(solar_flux=1.01),[1,2,3])


def test_finalist_cannot_change_planet_or_shared_physics_to_win():
    p=Params()
    with pytest.raises(ValueError,match='Locked planet'):
        assert_world_only(p.replace(solar_flux=1.01),p)
    with pytest.raises(ValueError,match='Shared physics'):
        assert_world_only(p.replace(orographic=p.orographic+1),p)
    assert_world_only(p.replace(lat_center=38,north_bearing=-10,downsample=8),p)
