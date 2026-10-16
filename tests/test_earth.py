import numpy as np
import pytest

from rotclimate import earth
from rotclimate.config import Params
from rotclimate.geography import Grid
from rotclimate.koppen import monthly_stats


def test_projection_round_trip_and_true_distances():
    lat0, lon0 = 37.0, -118.8
    lat = np.array([37.0, 40.0, 33.5, 36.2])
    lon = np.array([-118.8, -124.0, -114.0, -119.5])
    x, y = earth.forward(lat, lon, lat0, lon0)
    back_lat, back_lon = earth.inverse(x, y, lat0, lon0)
    assert np.allclose(back_lat, lat, atol=1e-9) and np.allclose(back_lon, lon, atol=1e-9)
    # azimuthal equidistant: distance from the centre is the great-circle distance
    p, p0 = np.radians(lat), np.radians(lat0)
    gc = earth.R_EARTH_KM * np.arccos(np.clip(np.sin(p0) * np.sin(p)
                                              + np.cos(p0) * np.cos(p) * np.cos(np.radians(lon - lon0)), -1, 1))
    assert np.allclose(np.hypot(x, y), gc, atol=1e-6)
    assert y[1] > 0 and x[1] < 0 and x[2] > 0          # north is up, east is right


def _toy_case():
    """A small continent with an ocean margin, scored against its own run."""
    ny, nx, cell = 24, 30, 60.0
    land = np.zeros((ny, nx), bool)
    land[6:18, 8:24] = True
    lat = 37.0 + (ny / 2 - 0.5 - np.arange(ny))[:, None] * cell / 111.195 * np.ones((1, nx))
    inmap = np.zeros_like(land)
    inmap[5:19, 6:24] = True
    elev = np.where(land, 300.0, 0.0)
    g = Grid(params=None, f=1, pad=5, ny=ny, nx=nx, cell_km=cell, land=land, land_frac=land.astype(float),
             elev=elev, elev_max=elev, lat=lat, inmap=inmap, target=np.zeros((ny, nx), np.int8),
             rivers=np.zeros((ny, nx)), lake=np.zeros((ny, nx), bool))
    nan = np.full((12, ny, nx), np.nan)
    case = earth.EarthCase(name="california", grid=g, lon=np.zeros((ny, nx)), obs_T=nan, obs_P=nan,
                           coast_km=np.where(land, 60.0, 0.0))
    return case


def test_model_runs_on_a_supplied_grid_and_scores_itself_perfectly():
    case = _toy_case()
    base = Params(steps_per_year=13, t_iters=6, picard_iters=2)
    res = earth.run_case(base, case, steps=13)
    assert res.T.shape[1:] == case.grid.land.shape          # the supplied grid, not the fantasy map
    p = res.params
    assert (p.tilt, p.year_days, p.retrograde, p.north_bearing) == (23.44, 365, False, 0.0)
    st = monthly_stats(res.T, res.P, res.days, p.year_days, summer_solstice=p.winter_solstice_day + p.year_days / 2)
    land = case.grid.land[None]
    case.obs_T = np.where(land, st["Tm"], np.nan)
    case.obs_P = np.where(land, st["Pm"], np.nan)
    case.grid.target = earth.observed_zones(case.obs_T, case.obs_P, case.grid)
    r = earth.compare(res, case)
    assert r["climate_distance"] == pytest.approx(0.0, abs=1e-9)
    assert r["temperature"]["rmse_C"] == pytest.approx(0.0, abs=1e-9)
    assert r["koppen_full_model"]["exact"] == 1.0
    assert r["zones"]["strict_agreement"] == 1.0
    assert r["scored_land_cells"] == int((case.grid.inmap & case.grid.land).sum())
    # a uniform 2.5 C warm error is one unit of climate distance
    case.obs_T = case.obs_T - 2.5
    assert earth.climate_distance(res, case) == pytest.approx(1.0, rel=1e-6)


@pytest.mark.skipif(not (earth.WORLDCLIM / "wc2.1_5m_prec.zip").exists(), reason="WorldClim cache not downloaded")
def test_california_case_matches_the_geography():
    case = earth.region_case("california", cell_km=56, pad_km=560)
    g = case.grid
    m = g.inmap & g.land
    assert 150 < m.sum() < 400
    # the Pacific is west of the scored box, the Sierra rises above 2 km
    assert not g.land[g.ny // 2, :g.pad].any()
    assert g.elev[m].max() > 2000
    # observed: wet north-west coast, dry south-east desert, Mediterranean coast
    ann = np.nansum(case.obs_P, 0)
    assert ann[m].max() > 1000 and ann[m].min() < 150
    codes = np.array(earth.CODES)[earth.classify(np.nan_to_num(case.obs_T), np.nan_to_num(case.obs_P),
                                                  earth.summer_months(365, 12, 172.0))]
    assert np.char.startswith(codes[m], "Cs").mean() > 0.2
    assert np.char.startswith(codes[m], "BW").mean() > 0.1
