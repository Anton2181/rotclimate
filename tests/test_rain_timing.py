from decimal import Decimal
import numpy as np
import pytest
from harvest.field_clock import field_clock
from harvest.rain_timing import COUNTS, event_edges, event_windows, timed_rain

BINS = np.linspace(0, 365, 13)


def common_clock(extra=()):
    return field_clock(BINS, event_edges_days=np.concatenate([event_edges(BINS), np.asarray(extra, float)]))


def totals(seed=3, fields=5):
    return np.random.default_rng(seed).uniform(0, 90, (12, fields))


@pytest.mark.parametrize('count', [None, 1, 2, 4])
def test_nonnegative_and_exact_bin_field_totals(count):
    clock = common_clock([212.9166667, 304.1666667, 91.25]); p = totals()
    rain = timed_rain(clock, p, count)
    assert rain.shape == (len(clock.step_days), 5) and (rain >= 0).all()
    for b in range(12):
        assert np.allclose(rain[clock.bin_index == b].sum(0), p[b], rtol=1e-12, atol=1e-10)


@pytest.mark.parametrize('count', COUNTS)
def test_support_and_duration(count):
    clock = common_clock(); rain = timed_rain(clock, np.ones((12, 1)), count)[:, 0]
    wet = rain > 0; windows = event_windows(BINS, count)
    assert np.isclose(clock.step_days[wet].sum(), 12 * count * 1.0)
    for step in np.flatnonzero(wet):
        a, z = clock.edges_days[step], clock.edges_days[step + 1]
        assert any(a >= s - 1e-12 and z <= e + 1e-12 for _, s, e in windows)
    centres = [(s + e) / 2 for b, s, e in windows if b == 0]
    assert np.allclose(centres, [BINS[1] * (j + .5) / count for j in range(count)])


def test_arbitrary_fractional_clock_without_event_edges():
    clock = field_clock(BINS, event_edges_days=[13.37, 200.123], max_step_days=0.73); p = totals(7, 3)
    for count in COUNTS:
        rain = timed_rain(clock, p, count)
        assert np.allclose(np.array([rain[clock.bin_index == b].sum(0) for b in range(12)]), p, rtol=1e-12, atol=1e-10)


def test_zero_rain_and_one_dimensional_totals():
    clock = common_clock()
    assert not timed_rain(clock, np.zeros((12, 4)), 2).any()
    one = timed_rain(clock, np.arange(12.0), 4)
    assert one.shape == (len(clock.step_days),) and np.isclose(one.sum(), 66.0)


def test_invalid_inputs():
    clock = common_clock()
    for bad in (0, -1, 1.5, True):
        with pytest.raises(ValueError):
            timed_rain(clock, np.ones((12, 1)), bad)
    with pytest.raises(ValueError):
        timed_rain(clock, -np.ones((12, 1)), 1)
    with pytest.raises(ValueError):
        timed_rain(clock, np.ones((11, 1)), 1)
    with pytest.raises(ValueError):
        timed_rain(clock, np.full((12, 1), np.nan), 1)
    with pytest.raises(ValueError):
        event_windows(BINS, 40)          # forty one-day events do not fit a 30-day bin


def test_decimal_overlap_reference():
    clock = common_clock([100.3]); p = [Decimal(str(v)) for v in (3.5, 0, 12.25, 40, 7, 0.125, 9, 55, 2, 1, 8, 33)]
    for count in COUNTS:
        got = timed_rain(clock, np.array([float(v) for v in p]), count)
        edges = [Decimal(repr(float(v))) for v in clock.edges_days]; bins = [Decimal(repr(float(v))) for v in BINS]
        for step in range(len(edges) - 1):
            want = Decimal(0)
            for b in range(12):
                for j in range(count):
                    centre = bins[b] + (Decimal(j) + Decimal('0.5')) / count * (bins[b + 1] - bins[b])
                    over = min(edges[step + 1], centre + Decimal('0.5')) - max(edges[step], centre - Decimal('0.5'))
                    if over > 0:
                        want += over / count * p[b]
            assert abs(Decimal(repr(float(got[step]))) - want) < Decimal('1e-9')


def test_inputs_not_mutated():
    clock = common_clock(); p = totals(); before = p.copy(); edges = clock.edges_days.copy()
    timed_rain(clock, p, 4); timed_rain(clock, p, None)
    assert np.array_equal(p, before) and np.array_equal(clock.edges_days, edges)
