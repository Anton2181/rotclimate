import pytest
from scripts.audit_r39_surroundings import paired_interval


def test_uniform_positive_gain_passes_and_is_order_independent():
    values=[.001,.002,.003,.004,.005,.006,.007,.008,.009]
    assert paired_interval(values)['passed']
    assert paired_interval(values)==paired_interval(list(reversed(values)))


def test_positive_mean_alone_cannot_pass_uncertain_layout_gains():
    result=paired_interval([-.03,-.02,0,0,.01,.01,.02,.03,.04])
    assert result['mean']>0 and result['lower']<0 and not result['passed']


def test_no_improvement_is_not_a_positive_uncertainty_result():
    assert not paired_interval([0.]*9)['passed']
    assert not paired_interval([-.01]*9)['passed']


def test_audit_budget_and_finite_inputs_are_required():
    with pytest.raises(ValueError):paired_interval([.01]*8)
    with pytest.raises(ValueError):paired_interval([.01]*8+[float('nan')])
