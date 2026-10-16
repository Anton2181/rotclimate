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


@pytest.mark.skipif(not (earth.WORLDCLIM / "wc2.1_5m_prec.zip").exists(), reason="WorldClim cache not downloaded")
def test_southern_regions_are_mirrored_into_the_north():
    case = earth.region_case("chile", cell_km=56, pad_km=560)
    g = case.grid
    m = g.inmap & g.land
    assert (g.lat > 0).all() and g.lat[0].mean() > g.lat[-1].mean()        # poleward is up, as in the north
    assert not g.land[g.ny // 2, :g.pad].any()                              # the Pacific is still to the west
    # the model calendar's July is the observed January: mirrored summer is warm and dry
    T, P = case.obs_T[:, m], case.obs_P[:, m]
    assert T[6].mean() > T[0].mean() + 5 and P[6].mean() < P[0].mean()
    p = earth.earth_params(Params(), case)
    assert p.lat_center == 34.0 and p.perihelion_after_solstice > 180


def test_sverdrup_sinking_dries_equatorward_flow_and_wets_poleward_flow():
    case = _toy_case()
    base = Params(steps_per_year=13, t_iters=6, picard_iters=2, monsoon_strength=2.0)
    off = earth.run_case(base, case, steps=13)
    on = earth.run_case(base.replace(sverdrup=1.0), case, steps=13)
    land = case.grid.land
    v = off.v[:, land]
    ratio = on.P[:, land] / np.maximum(off.P[:, land], 1e-6)
    strong = off.P[:, land] > 0.05
    assert np.median(ratio[(v < -1.0) & strong]) < 1.0 < np.median(ratio[(v > 1.0) & strong])
    # the new genes default to the old fixed behaviour
    p = Params()
    assert (p.sverdrup, p.subsidence_width, p.storm_seasonality) == (0.0, 6.0, 0.3)


def test_subsidence_drying_and_circulation_lag_keep_the_moisture_equation_closed():
    case = _toy_case()
    base = Params(steps_per_year=13, t_iters=6, picard_iters=64, moisture_residual_tol=0.01,
                  moisture_require_convergence=True, solver_rtol=1e-6)
    off = earth.run_case(base, case, steps=13)
    on = earth.run_case(base.replace(subsidence_drying=0.2, circulation_lag_days=50.0), case, steps=13)
    land = case.grid.land
    assert on.P[:, land].mean() < off.P[:, land].mean()       # drier under the highs, and still converged
    assert (Params().subsidence_drying, Params().circulation_lag_days) == (0.0, 30.0)


def test_continentality_widens_the_seasons_deep_inland_and_narrows_them_on_the_windward_coast():
    case = _toy_case()                         # latitude 37 N: in the westerlies
    g = case.grid
    g.land[:, 10:] = True                      # an ocean to the west, a continent to the east edge
    g.land_frac = g.land.astype(float)
    g.elev = g.elev_max = np.where(g.land, 300.0, 0.0)
    base = Params(steps_per_year=13, t_iters=6, picard_iters=2, hadley_edge=28.0, hadley_shift=3.0,
                  westerly_speed=8.0, monsoon_strength=0.0)
    off = earth.run_case(base, case, steps=13)
    on = earth.run_case(base.replace(continentality=1.5), case, steps=13)
    row = g.ny // 2
    swing = lambda r, c: float(r.T[:, row, c].max() - r.T[:, row, c].min())
    assert swing(on, 10) < swing(off, 10)      # windward coast: sea air, milder seasons
    assert swing(on, 28) > swing(off, 28)      # ~1,000 km downwind of the coast: harsher seasons
    assert Params().continentality == 0.0


def test_upwelling_cools_a_west_coast_sea_under_equatorward_wind_only():
    case = _toy_case()
    g = case.grid
    g.land[:, :] = False
    g.land[:, 15:] = True                      # sea to the west, land to the east: a west coast
    g.land_frac = g.land.astype(float)
    g.elev = g.elev_max = np.where(g.land, 100.0, 0.0)
    from rotclimate.model import ClimateModel
    p = earth.earth_params(Params(steps_per_year=13, upwelling=4.0), case)
    m = ClimateModel(p, grid=g)
    ox, oy = m.offshore
    near = m.upwelling_weight > 0.5
    assert near.any() and np.allclose(ox[near], -1.0, atol=0.05)        # offshore = west
    ue, ve = np.zeros_like(g.lat), np.full_like(g.lat, -5.0)            # wind toward the equator
    ek_x, ek_y = ve, -ue                                                # Ekman transport, right of the wind
    assert (ek_x * ox + ek_y * oy)[near].mean() > 4.0                   # offshore: upwelling
    assert Params().upwelling == 0.0
