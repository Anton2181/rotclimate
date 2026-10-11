"""Fast checks of the pieces everything else rests on (run: python -m pytest -q)."""
import numpy as np
import pytest

from rotclimate import calendar as cal
from rotclimate.config import Params


# ------------------------------------------------------------------ calendar
def test_calendar_is_an_earth_year_of_73_weeks():
    assert cal.YEAR_DAYS == 365
    groups = cal.month_slices(73)
    assert [len(g) for g in groups] == [7] * 10 + [3]


def test_season_names_match_the_astronomy():
    ws = Params().winter_solstice_day
    m, d, _ = cal.month_of_day(int(ws))
    assert (m.name, d) == ("Titian Marigold", 23)                  # early winter
    assert cal.month_of_day(int(ws + 365 / 4))[0].name == "Iris Rose"        # middle spring
    assert cal.month_of_day(int(ws + 365 / 2))[0].name == "Amber Zinnia"     # early summer
    assert cal.month_of_day(int(ws + 3 * 365 / 4))[0].name == "Lilac Crocus"  # middle fall


# ------------------------------------------------------------------ koppen
def _city(name, country):
    from rotclimate.analogs import load_reference

    return next(r for r in load_reference() if r["name"] == name and r["country"] == country)


@pytest.mark.parametrize("city, country, expected", [
    ("Moscow", "Russia", "Dfb"), ("Cairo", "Egypt", "BWh"), ("London", "UK", "Cfb"),
    ("Riyadh", "Saudi Arabia", "BWh"), ("Shanghai", "China", "Cfa"), ("Cape Town", "South Africa", "Csb"),
    ("Athens", "Greece", "Csa"), ("Kunming", "China", "Cwb"),
])
def test_koppen_classifies_real_cities(city, country, expected):
    assert _city(city, country)["koppen"] == expected


# ------------------------------------------------------------------ solver
def test_sweep_solver_matches_direct_solve():
    from rotclimate.solver import AdvectionSolver

    rng = np.random.default_rng(0)
    ny, nx = 40, 50
    s = AdvectionSolver(ny, nx, 20000.0)
    s.rtol = 1e-7
    u, v = rng.normal(0, 5, (ny, nx)), rng.normal(0, 5, (ny, nx))
    lam = np.full((ny, nx), 1 / (2 * 86400.0))
    b = rng.uniform(0, 30, (ny, nx))
    sol = s.solve(u, v, 4e4, lam, lam * b, b, max_iter=5000)
    ref = s._direct(*s.coefficients(u, v, 4e4, lam), lam * b, b)
    assert np.abs(sol - ref).max() < 1e-3


# ------------------------------------------------------------------ hydrology
def test_drainage_conserves_water_and_runs_downhill():
    from rotclimate.hydrology import _accumulate, drainage

    ny, nx = 30, 40
    yy, xx = np.mgrid[0:ny, 0:nx]
    elev = 10.0 * xx + np.random.default_rng(1).uniform(0, 1, (ny, nx))   # rises to the east
    land = np.ones((ny, nx), bool)
    land[:, 0] = False                                                   # sea on the west edge
    recv, order = drainage(elev, land)
    src = np.where(land, 1.0, 0.0).ravel()
    acc = _accumulate(order, recv, src)
    outlets = recv < 0
    assert acc[outlets].sum() == pytest.approx(src.sum())                # nothing lost or created
    has = recv >= 0
    assert (elev.ravel()[recv[has]] <= elev.ravel()[has] + 1e-6).mean() > 0.95


# ------------------------------------------------------------------ geography, names
def test_target_zones_and_place_names_load():
    from rotclimate.geography import load_places, target_fullres

    t = target_fullres()
    assert set(np.unique(t)) == set(range(8))
    names = {p["name"] for p in load_places()}
    assert len(names) > 140 and {"Yasna", "Harran", "Bahir Dar"} <= names


def test_hex_grid_fit_is_a_regular_hexagon():
    import json
    from pathlib import Path

    g = json.loads((Path(__file__).resolve().parent.parent / "data" / "hexgrid.json").read_text())
    assert g["dy"] / g["dx"] == pytest.approx(np.sqrt(3) / 2, rel=0.02)


# ------------------------------------------------------------------ analogues
def test_a_city_is_its_own_best_analogue():
    from rotclimate.analogs import top_analogs

    r = _city("Tbilisi", "Georgia")
    best = top_analogs(r["T12"], r["P12"], 1)[0]
    assert best["name"] == "Tbilisi" and best["similarity"] == pytest.approx(100.0)


def test_analogues_are_distinct_places():
    """No duplicate entries, and a result list never shows two places within 100 km."""
    from collections import Counter

    from rotclimate.analogs import _km, load_reference, top_analogs

    ref = load_reference()
    dup = [k for k, n in Counter((r["name"], r["country"]) for r in ref).items() if n > 1]
    assert not dup
    r = _city("Houston", "USA")
    top = top_analogs(r["T12"], r["P12"], 6)
    pos = {(x["name"], x["country"]): x for x in ref}
    pts = [pos[(a["name"], a["country"])] for a in top]
    for i in range(len(pts)):
        for j in range(i):
            assert _km(pts[i]["lat"], pts[i]["lon"], pts[j]["lat"], pts[j]["lon"]) >= 100.0


# ------------------------------------------------------------------ end to end
def test_coarse_model_run_is_physical():
    from rotclimate.model import ClimateModel
    from rotclimate.score import evaluate

    p = Params.from_json("calibration/best_params.json").replace(downsample=16, steps_per_year=13,
                                                                 picard_iters=1)
    r = ClimateModel(p).run()
    land = r.grid.land & r.grid.inmap
    assert np.isfinite(r.T).all() and np.isfinite(r.P).all()
    assert -40 < r.T[:, land].min() and r.T[:, land].max() < 50
    assert (r.P >= 0).all()
    ev = evaluate(r)
    assert 0.2 < ev["total"] <= 1.0


# ------------------------------------------------------------------ day/night range
def test_diurnal_range_desert_swings_more_than_rainy_coast():
    import numpy as np

    from rotclimate.diurnal import available, dtr

    if not available():
        pytest.skip("data/dtr_knn.npz not built")
    season = np.cos(np.linspace(0, 2 * np.pi, 12, endpoint=False))
    T_desert = (24 - 9 * season)[:, None]
    T_coast = (11 - 4 * season)[:, None]
    desert = dtr(T_desert, np.full((12, 1), 4.0), 600.0, 600.0, 32.0)
    coast = dtr(T_coast, np.full((12, 1), 120.0), 20.0, 2.0, 50.0)
    assert desert.mean() > coast.mean() + 4.0
    assert 3.0 < coast.mean() < 12.0 and 10.0 < desert.mean() < 24.0


def test_fast_gaussian_matches_scipy():
    import numpy as np
    from scipy import ndimage as ndi

    from rotclimate.model import gauss

    a = np.random.default_rng(3).normal(size=(97, 151)).cumsum(1)
    for sigma in (2.0, 8.5, 21.0):
        assert np.abs(gauss(a, sigma) - ndi.gaussian_filter(a, sigma, mode="nearest")).max() < 1e-9


# ------------------------------------------------------------------ wet-ground cooling (v8)
def test_wet_ground_cools_humid_summers_only():
    from rotclimate.analogs import model_bins
    from rotclimate.model import ClimateModel

    p = Params.from_json("calibration/best_params.json").replace(downsample=16, steps_per_year=13,
                                                                 picard_iters=1)
    runs = [ClimateModel(p.replace(wet_cooling=w)).run() for w in (0.0, 0.6)]
    land = runs[0].grid.land & runs[0].grid.inmap
    bins = [model_bins(r.T, r.P, r.days, p.winter_solstice_day, p.year_days) for r in runs]
    (T0, P0), (T1, _) = bins
    hot0, hot1 = T0.max(0)[land], T1.max(0)[land]
    cold0, cold1 = T0.min(0)[land], T1.min(0)[land]
    wet = P0.sum(0)[land] > 1200
    dry = P0.sum(0)[land] < 400
    # summers cool, most where it rains; winters barely change
    assert (hot0 - hot1)[wet].mean() > 1.0
    assert (hot0 - hot1)[wet].mean() > (hot0 - hot1)[dry].mean()
    assert abs((cold0 - cold1).mean()) < 0.6 * (hot0 - hot1).mean()


# ------------------------------------------------------------------ map orientation (v9)
def test_north_bearing_rotates_latitude_and_coasts():
    from rotclimate.geography import build_grid, map_lat_range
    from rotclimate.model import ClimateModel

    p = Params.from_json("calibration/best_params.json").replace(downsample=16, steps_per_year=13,
                                                                 picard_iters=1)
    g0, g90, g180 = (build_grid(p.replace(north_bearing=b)) for b in (0.0, 90.0, 180.0))
    m = g0.inmap
    # north up: latitude falls down the rows; north to the right: it rises along them
    assert (np.diff(g0.lat[:, 0]) < 0).all() and np.allclose(g0.lat, g0.lat[:, :1])
    assert (np.diff(g90.lat[0]) > 0).all() and np.allclose(g90.lat, g90.lat[:1, :])
    assert np.allclose(g180.lat - p.lat_center, -(g0.lat - p.lat_center), atol=0.2)
    assert abs(g90.lat[m].max() - g90.lat[m].min() - np.subtract(*map_lat_range(p.replace(north_bearing=90))[::-1])) < 0.5
    # a full turn is no turn; turning the map round swaps west and east coasts
    s0 = ClimateModel(p).side
    assert np.allclose(ClimateModel(p.replace(north_bearing=360.0)).side, s0)
    s180 = ClimateModel(p.replace(north_bearing=180.0)).side
    assert np.allclose(s180, -s0, atol=1e-9)
    r = ClimateModel(p.replace(north_bearing=90.0)).run()
    land = r.grid.land & r.grid.inmap
    assert np.isfinite(r.T).all() and (r.P >= 0).all()
    # with north to the right, the right of the map is the cold side
    cols = np.flatnonzero(r.grid.inmap.any(0))
    left, right = cols[: cols.size // 5], cols[-cols.size // 5:]
    T = r.T.mean(0)
    assert T[:, left][land[:, left]].mean() > T[:, right][land[:, right]].mean() + 3


# ------------------------------------------------------------------ zone rules vs Koppen
def test_dry_zones_follow_koppen():
    from rotclimate.koppen import CODES, classify, climate_indices
    from rotclimate.score import memberships

    summer = np.array([False] * 3 + [True] * 6 + [False] * 3)
    season = -np.cos(2 * np.pi * (np.arange(12) + 0.5) / 12)
    def climate(mat, amp, p_summer, p_winter):
        Tm = (mat + amp / 2 * season)[:, None]
        Pm = np.where(summer, p_summer, p_winter).astype(float)[:, None]
        return Tm, Pm
    cases = {   # name: (climate, expected Koppen code)
        "cold steppe": (climate(9.0, 26.0, 25.0, 20.0), "BSk"),
        "hot desert": (climate(24.0, 16.0, 2.0, 8.0), "BWh"),
        "dry-summer continental": (climate(9.0, 28.0, 12.0, 75.0), "Dsa"),
        "warm-summer Mediterranean": (climate(14.0, 9.0, 8.0, 110.0), "Csb"),
    }
    for name, ((Tm, Pm), code) in cases.items():
        assert CODES[classify(Tm, Pm, summer)[0]] == code, name
        mem = {k: float(v[0]) for k, v in memberships(climate_indices(Tm, Pm, summer)).items()}
        best = max(mem, key=mem.get)
        expected = {"BSk": "cold_dry", "BWh": "hot_dry", "Csb": "med"}.get(code)
        if expected:
            assert best == expected, (name, mem)
        else:   # Dsa is not a dry climate: it must not read as cold and dry
            assert mem["cold_dry"] < 0.3, (name, mem)
