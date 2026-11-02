import numpy as np
import pytest

from scripts.diagnose_r42_rain import SOURCES, balance_check, monthly


def test_monthly_budget_keeps_annual_integral_with_nonmonthly_steps():
    n = 25
    days = (np.arange(n) + .5) * 365 / n
    values = np.stack([np.linspace(-3, 4, n), np.linspace(10, 1, n)], axis=1)
    assert np.allclose(monthly(values, days, 365).mean(0), values.mean(0))


def test_monsoon_drying_is_not_counted_twice():
    budget = {k: np.ones((2, 3)) for k in SOURCES}
    budget.update(column_drying=np.full((2, 3), -2.), monsoon_drying=np.full((2, 3), -1.),
                  residual=np.full((2, 3), .25), absolute_residual=np.full((2, 3), .25))
    rain = sum(budget[k] for k in SOURCES) - budget['residual']
    result = balance_check(budget, rain)
    assert result['max_reconstruction_error_mm_day'] == 0
    assert result['max_absolute_equation_residual_mm_day'] == .25


def test_budget_rejects_an_omitted_source_instead_of_hiding_the_residual():
    budget = {k: np.zeros((2, 3)) for k in SOURCES}
    budget.update(evaporation=np.ones((2, 3)), residual=np.zeros((2, 3)), absolute_residual=np.zeros((2, 3)))
    with pytest.raises(ValueError, match='do not reconstruct'):
        balance_check(budget, np.zeros((2, 3)))
