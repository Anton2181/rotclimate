"""Failure/recovery and accounting contracts; no climate integrations."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from padding_budget_capture import COMPONENTS, equation_check, exact, pending


def test_interrupted_attempt_is_not_automatically_retried(tmp_path):
    (tmp_path / 'attempt.json').write_text('{}')
    with pytest.raises(RuntimeError, match='Interrupted'):
        pending(tmp_path)


def test_failed_attempt_is_not_automatically_retried(tmp_path):
    (tmp_path / 'result.json').write_text(json.dumps(dict(status='failed')))
    with pytest.raises(RuntimeError, match='Preserve failed'):
        pending(tmp_path)


def test_byte_exact_requires_dtype_and_signed_zero():
    with pytest.raises(AssertionError):
        exact(np.array([0.]), np.array([-0.]))
    with pytest.raises(AssertionError):
        exact(np.array([1.], dtype='f4'), np.array([1.], dtype='f8'))


def test_equation_includes_signed_marine_exchange():
    t = {k:np.zeros((2, 2), dtype='f4') for k in COMPONENTS + ['residual']}
    t['evaporation'][:] = 3
    t['marine_exchange'][:] = -2
    assert equation_check(t, np.ones((2, 2)), .01) == 0
    t['marine_exchange'][:] = 0
    with pytest.raises(AssertionError, match='incomplete'):
        equation_check(t, np.ones((2, 2)), .01)


def test_cancelling_sources_do_not_inflate_residual_tolerance():
    t = {k:np.zeros((1, 1), dtype='f4') for k in COMPONENTS + ['residual']}
    t['evaporation'][:] = 100
    t['column_drying'][:] = -98.9
    t['residual'][:] = .1
    with pytest.raises(AssertionError, match='Strict'):
        equation_check(t, np.ones((1, 1)), .01)


def test_plan_has_six_fixed_cases_and_no_physical_overrides():
    p = Path(__file__).resolve().parents[1] / 'calibration/padding_budget_capture_20261127/plan.json'
    plan = json.loads(p.read_text())
    pairs = [(c['region'], c['pad_km']) for c in plan['cases']]
    assert len(pairs) == len(set(pairs)) == plan['maximum_additional_diagnostic_integrations'] == 6
    assert [c['pad_km'] for c in plan['cases']] == [1100.] * 3 + [4012.] * 3
    assert plan['policy']['parameter_overrides'] == plan['policy']['numerical_tolerance_changes'] == {}
