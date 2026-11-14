from decimal import Decimal

import numpy as np
import pytest

from harvest.crop_stage import StageCurve


def test_published_fao30_values_and_total_integral():
    curve = StageCurve((25,25,30,20), .15,1.14,.25)
    np.testing.assert_allclose(curve.value([12,37,65,90]), [.15,.6252,1.14,.695], atol=2e-15)
    assert curve.integral(0,100) == pytest.approx(67.975, abs=2e-13)
    assert curve.mean(0,100) == pytest.approx(.67975)


def test_exact_stage_boundaries_and_endpoint_continuity():
    curve = StageCurve((25,25,30,20), .15,1.14,.25)
    np.testing.assert_allclose(curve.value(curve.edges_days), [.15,.15,1.14,1.14,.25])
    for edge in curve.edges_days[1:-1]:
        assert curve.value(edge-1e-9) == pytest.approx(curve.value(edge+1e-9),abs=2e-10)


def test_independent_decimal_integrals_across_arbitrary_boundaries():
    rng = np.random.default_rng(15114)
    for case in range(100):
        lengths = [Decimal(int(v))/10 for v in rng.integers(1,1000,4)]
        levels = [Decimal(int(v))/100 for v in rng.integers(0,150,3)]
        curve = StageCurve(tuple(map(float,lengths)), *map(float,levels))
        edges = [Decimal(0)]
        for v in lengths:edges.append(edges[-1]+v)
        for k in range(20):
            a,b = sorted([edges[-1]*Decimal(int(v))/10000 for v in rng.integers(0,10001,2)])
            expected = Decimal(0)
            endpoints = [(levels[0],levels[0]),(levels[0],levels[1]),(levels[1],levels[1]),(levels[1],levels[2])]
            for j,(u,v) in enumerate(endpoints):
                lo,hi = max(a,edges[j]), min(b,edges[j+1])
                if hi > lo:
                    left = u+(v-u)*(lo-edges[j])/lengths[j]
                    right = u+(v-u)*(hi-edges[j])/lengths[j]
                    expected += (hi-lo)*(left+right)/2
            assert curve.integral(float(a),float(b)) == pytest.approx(float(expected),abs=2e-12,rel=1e-12)


def test_fractional_clock_conserves_integral_and_actual_step_mean():
    curve = StageCurve((25,25,30,20), .15,1.14,.25)
    edges = np.unique(np.r_[np.arange(0,100,.37),curve.edges_days])
    areas = curve.integral(edges[:-1],edges[1:])
    means = curve.mean(edges[:-1],edges[1:])
    np.testing.assert_allclose(areas,means*np.diff(edges),atol=2e-15)
    assert areas.sum() == pytest.approx(curve.integral(0,100),abs=2e-12)
    assert curve.integral(37,37) == 0


def test_constant_curve_broadcasting_and_no_input_mutation():
    lengths = np.array([.1,2.3,5.7,.9]); before=lengths.copy()
    curve = StageCurve(lengths,.75,.75,.75)
    np.testing.assert_array_equal(lengths,before)
    lengths[0]=500
    np.testing.assert_allclose(curve.value([0,.7,8.99]),.75)
    np.testing.assert_allclose(curve.integral([0,1,2],3),[2.25,1.5,.75])
    np.testing.assert_allclose(curve.mean([0,1,2],3),.75)


@pytest.mark.parametrize('lengths', [(1,2,3), (0,1,2,3),(-1,1,2,3),(1,np.nan,2,3),(1,np.inf,2,3),(True,1,2,3)])
def test_invalid_durations_refused(lengths):
    with pytest.raises(ValueError):StageCurve(lengths,.15,1.1,.15)


@pytest.mark.parametrize('coefficients', [(-.1,1,.1),(.1,np.nan,.1),(.1,1,np.inf),(.1,True,.1)])
def test_invalid_coefficients_refused(coefficients):
    with pytest.raises(ValueError):StageCurve((1,2,3,4),*coefficients)


@pytest.mark.parametrize('age', [-1,101,np.nan,np.inf])
def test_invalid_crop_ages_refused(age):
    curve=StageCurve((25,25,30,20),.15,1.14,.25)
    with pytest.raises(ValueError):curve.value(age)
    with pytest.raises(ValueError):curve.integral(0,age)


def test_reversed_or_empty_mean_intervals_refused():
    curve=StageCurve((25,25,30,20),.15,1.14,.25)
    with pytest.raises(ValueError):curve.integral(20,10)
    with pytest.raises(ValueError):curve.mean(10,10)
    with pytest.raises(ValueError):curve.mean(20,10)
