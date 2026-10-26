from copy import deepcopy
from types import SimpleNamespace
import numpy as np
import pytest
from rotclimate.config import Params
from scripts.add_initialization_check import validate_pair


def pair():
    p=Params();grid=SimpleNamespace(**{name:np.ones((3,3)) for name in ['land','land_frac','elev','elev_max','lat','inmap','target']})
    base=SimpleNamespace(params=p.replace(downsample=16),days=np.arange(25),grid=grid,numerics=dict(all_checks_passed=True))
    warm=deepcopy(base);warm.params=base.params.replace(seasonal_spinup_years=3)
    return p,base,warm


def test_matching_fixed_layout_with_different_warmup_is_allowed():
    p,base,warm=pair();validate_pair(base,warm,p)


@pytest.mark.parametrize('changes',[dict(solar_flux=1.01),dict(beyond_seed=2),dict(north_bearing=1)])
def test_other_planets_layouts_or_orientations_cannot_be_attached(changes):
    p,base,warm=pair();warm.params=warm.params.replace(**changes)
    with pytest.raises(ValueError,match='physics and layout'):validate_pair(base,warm,p)


def test_changed_geography_or_unverified_run_cannot_be_attached():
    p,base,warm=pair();warm.grid.elev[1,1]=99
    with pytest.raises(ValueError,match='geography'):validate_pair(base,warm,p)
    p,base,warm=pair();warm.numerics['all_checks_passed']=False
    with pytest.raises(ValueError,match='Unverified'):validate_pair(base,warm,p)
