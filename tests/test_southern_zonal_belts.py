"""Background wind belts must obey equatorial reflection in a symmetric world."""
from dataclasses import replace
import numpy as np
import pytest
from rotclimate.config import Params
from rotclimate.model import ClimateModel


def symmetric_wind(latitude,season,*,retrograde=False,north_bearing=0.):
    model=ClimateModel.__new__(ClimateModel)
    model.p=Params(itcz_mean=0.,itcz_shift=0.,itcz_shift_ocean=-1.,itcz_mean_land=-90.,
        trade_land=0.,trade_heat_low=0.,monsoon_westerly=0.,zonal_land_friction=0.,
        hadley_edge=30.,hadley_shift=5.,retrograde=retrograde,north_bearing=north_bearing)
    model.lat=np.asarray(latitude,float)
    model.hadley_scale=1.
    model.itcz_anchor=None
    return model.zonal_wind(season)[:2]


def test_equinox_westerlies_and_polar_belts_in_both_hemispheres():
    u,v=symmetric_wind([[-75.,-45.,45.,75.]],0.)
    np.testing.assert_allclose(u,[[-3.,7.,7.,-3.]],rtol=0.,atol=1e-14)
    np.testing.assert_allclose(v,[[.9,-1.05,1.05,-.9]],rtol=0.,atol=1e-14)


@pytest.mark.parametrize('season',[-1.,-.5,0.,.5,1.])
@pytest.mark.parametrize('retrograde',[False,True])
def test_season_reversed_equatorial_symmetry(season,retrograde):
    latitude=np.array([[5.,15.,25.,35.,45.,55.,65.,75.,85.]])
    un,vn=symmetric_wind(latitude,season,retrograde=retrograde)
    us,vs=symmetric_wind(-latitude,-season,retrograde=retrograde)
    np.testing.assert_allclose(us,un,rtol=0.,atol=1e-14)
    np.testing.assert_allclose(vs,-vn,rtol=0.,atol=1e-14)


def test_common_map_rotation_of_southern_belts():
    u,v=symmetric_wind([[-75.,-45.]],.5)
    rotated_u,rotated_v=symmetric_wind([[-75.,-45.]],.5,north_bearing=37.)
    th=np.deg2rad(37.)
    np.testing.assert_allclose(rotated_u,u*np.cos(th)+v*np.sin(th),rtol=0.,atol=1e-14)
    np.testing.assert_allclose(rotated_v,-u*np.sin(th)+v*np.cos(th),rtol=0.,atol=1e-14)


def r58_belt_fixture(season,retrograde,bearing):
    from pathlib import Path
    from types import SimpleNamespace
    model=ClimateModel.__new__(ClimateModel)
    root=Path(__file__).resolve().parents[1]
    model.p=Params.from_json(root/'calibration/local_accuracy_20261023/r58_params.json').replace(
        retrograde=bool(retrograde),north_bearing=float(bearing))
    model.lat=np.tile(np.arange(-89.,90.)[:,None],(1,4))
    model.hadley_scale=model.p.planet_radius**-.5
    model.land_broad=np.broadcast_to([0.,.3,.7,1.],model.lat.shape).copy()
    model.land_friction=model.land_broad.copy()
    model.itcz_anchor=.5*model.land_broad
    model.g=SimpleNamespace(cell_km=56.,land=model.land_broad>.5)
    model.last_pres=200.*np.cos(np.deg2rad(model.lat))*model.land_broad+100.*np.sin(np.deg2rad(model.lat))
    return model


def test_northern_bytes_unchanged_on_mixed_hemisphere_grid():
    from pathlib import Path
    path=Path(__file__).parent/'fixtures/southern_zonal_belts_northern.npz'
    with np.load(path) as golden:
        for k,(season,retrograde,bearing) in enumerate(golden['profiles']):
            model=r58_belt_fixture(season,retrograde,bearing)
            u,v,phi_i,phi_h=model.zonal_wind(float(season))
            mask=model.lat>=0
            for name,actual in [('u',u[mask]),('v',v[mask]),('phi_i',np.broadcast_to(phi_i,model.lat.shape)[mask]),('phi_h',np.asarray(phi_h))]:
                expected=golden[name][k]
                assert actual.shape==expected.shape and actual.dtype==expected.dtype
                assert actual.tobytes()==expected.tobytes(),(k,name)
