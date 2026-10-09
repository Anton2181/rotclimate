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
