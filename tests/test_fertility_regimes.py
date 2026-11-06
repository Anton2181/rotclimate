import numpy as np

from harvest.fertility_regimes import WHEAT_CURVE, equilibrium_yield, stretched_curve

T = np.array([2.6, 3.4, 5.0, 7.5, 10.7, 14.1, 16.0, 15.5, 13.2, 8.9, 5.9, 3.2])[:, None]
P = np.array([58, 42, 37, 47, 54, 59, 64, 65, 62, 75, 57, 51], float)[:, None]
E = np.array([6, 7, 20, 37, 62, 74, 77, 68, 52, 25, 12, 6], float)[:, None]
KW = dict(uptake_rate=0.15, kappa=2.26, season_bins=10, curve=WHEAT_CURVE, years=120, report_years=30)


def run(regime, **kw):
    return equilibrium_yield(T, P, E, np.array([7]), np.array([0.885]), regime=regime, **{**KW, **kw})


def test_curve_and_ordering():
    c = stretched_curve(WHEAT_CURVE, 9)
    assert np.all(np.diff(c) >= 0) and c[-1] == 1.0
    base = run(["crop"], input_n=27.5)["per_cropped_ha"][0]
    assert run(["crop"], input_n=52.4)["per_cropped_ha"][0] > base
    assert run(["crop"], input_n=27.5, manure_t=5.0)["per_cropped_ha"][0] > base
    leg = run(["crop", "crop", "clover"], input_n=27.5)
    assert leg["per_cropped_ha"][0] > base and abs(leg["cropped_share"] - 2 / 3) < 1e-9
    assert run(["crop"], input_n=200.0)["per_cropped_ha"][0] <= 2.26 * 0.885 + 1e-9


def test_vectorised_cells_are_independent():
    TT, PP, EE = (np.repeat(a, 3, axis=1) for a in (T, P, E))
    r = equilibrium_yield(TT, PP, EE, np.array([7, 7, 7]), np.array([0.885, 0.885, 0.4]), regime=["crop"], input_n=27.5, **KW)
    one = run(["crop"], input_n=27.5)["per_cropped_ha"][0]
    assert abs(r["per_cropped_ha"][0] - one) < 1e-12 and abs(r["per_cropped_ha"][1] - one) < 1e-12
