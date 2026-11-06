import math

import pytest

from harvest.soil_fertility import (Params, Pools, Season, add_fym, add_plant, co2_ratio, equilibrium, max_tsmd,
                                    rate_temperature, rothc_month, simulate)

MONTHS = [dict(T=t, rain=r, et=e, vegetated=v) for t, r, e, v in zip(
    [3.4, 3.6, 5.1, 7.3, 10.6, 13.6, 15.9, 15.4, 13.1, 9.7, 6.0, 4.1],
    [74, 59, 62, 51, 52, 57, 34, 55, 58, 56, 75, 71],
    [8, 10, 27, 49, 83, 99, 103, 91, 69, 34, 16, 8],
    [True] * 7 + [False] * 4 + [True])]


def test_rothc_constants_match_the_description():
    assert max_tsmd(23.4) == pytest.approx(-44.94, abs=0.01)       # RothC's Rothamsted example
    assert co2_ratio(23.4) == pytest.approx(3.51, abs=0.01)
    assert rate_temperature(9.25) == pytest.approx(47.91 / (1 + math.exp(106.06 / 27.52)))


def test_carbon_and_nitrogen_are_conserved_in_a_month():
    p = add_plant(Pools(bio=0.6, hum=28.0), 1.5, 40.0)
    p, s = add_fym(p, 3.0, 225.0)
    assert s == 0
    c0, n0 = p.active_c, p.organic_n
    q, net, co2, _ = rothc_month(p, 12.0, 60.0, 70.0, True, 23.4, 50.0)
    assert q.active_c + co2 == pytest.approx(c0, rel=1e-12)
    assert q.organic_n + net == pytest.approx(n0, rel=1e-12)


def test_immobilization_never_overdraws_mineral_n():
    p = add_plant(Pools(), 3.0, 150.0)                   # very N-poor straw
    q, net, _, _ = rothc_month(p, 15.0, 80.0, 60.0, False, 23.4, 1.0)
    assert net >= -1.0 - 1e-12


def test_hoosfield_equilibrium_is_near_the_rothc_example():
    # RothC description: 1.70 t C/ha/yr gives 33.8 t C/ha including 2.7 t IOM at Rothamsted
    plant = [(0.2125, 40.0)] * 7 + [(0.0, 40.0)] * 4 + [(0.2125, 40.0)]
    p = equilibrium(MONTHS, 23.4, plant=plant)
    assert 20.0 < p.active_c < 45.0


def test_plot_ledger_closes_and_manure_raises_yield():
    forcing = []
    for y in range(1900, 1930):
        for m, row in enumerate(MONTHS, 1):
            forcing.append(dict(year=y, month=m, T=row['T'], rain=row['rain'], et=row['et'],
                                drainage=max(row['rain'] - row['et'], 0) * 0.6))
    seasons = [Season('cereal', (y, 8), frozenset((y, m) for m in range(3, 8)),
                      frozenset([(y - 1, 10), (y - 1, 11), (y - 1, 12)] + [(y, m) for m in range(1, 8)]), 1.0)
               for y in range(1901, 1930)]
    start = equilibrium(MONTHS, 23.4, plant=[(0.2125, 40.0)] * 7 + [(0.0, 40.0)] * 4 + [(0.2125, 40.0)])
    par = Params(input_n=20.0, uptake_rate=0.4, kappa=3.0)
    nil = simulate(forcing, seasons, par, 23.4, 500.0, start=start)
    fym = simulate(forcing, seasons, par, 23.4, 500.0, start=start,
                   events={(y - 1, 10): [('fym', 3.0, 225.0)] for y in range(1901, 1930)})
    assert abs(nil['residual']) < 1e-6 and abs(fym['residual']) < 1e-6
    yn = [s['grain_t_ha'] for s in nil['seasons']][-10:]
    yf = [s['grain_t_ha'] for s in fym['seasons']][-10:]
    assert sum(yf) > 1.5 * sum(yn)
    assert all(g <= 3.0 + 1e-9 for g in yf)
