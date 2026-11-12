import numpy as np
import pytest
from polity.settlement_feedback import FeedbackInputs
from polity.settlement_dispatch import DispatchFeedback
from polity.settlement_seeded_dispatch import ThresholdSeededDispatchFeedback


def narrow(model):
    x = FeedbackInputs(np.array([100.]), np.array([0]), np.array([100000.]), np.array([1], np.uint16),
        np.array([1e6]), np.array([250000.]), np.ones((12, 1), bool), np.array([100.]), np.array([True]), np.array([100000.]))
    return model(x, outward_days=np.ones((12, 1)), inward_days=np.ones((12, 1)), load_kcal=6000.,
        monthly_open=np.ones(12, bool), staff_hours_year=600., transfer_fraction=.5,
        hours_worker_year=36000 / 84.9, worker_fraction=1., kcal_day=1., year_days=360.,
        rural_store_days=360., export_store_days=360., destination_store_days=90., loss_fraction_year=0.,
        collection_fraction=1., retention=1., delay_bins=0, institutional_request=10., minimum_community=5.)


def test_existing_staff_boundary_rescues_a_narrow_feasible_interval_missed_by_64_grid():
    base = narrow(DispatchFeedback); old = base.solve(scan_intervals=64)
    assert old['total'][0] == 0
    model = narrow(ThresholdSeededDispatchFeedback); new = model.solve()
    assert new['threshold_seeded'][0] and new['preseed_total'][0] == 0
    assert new['total'][0] == pytest.approx(15.1, abs=1e-4)
    assert new['total'][0] >= 15 and new['staff'][0] == 10
    assert new['town_food'].unmet[0] < 1e-5 and new['source_supported'][0]
    assert new['rural'][0] + new['total'][0] == pytest.approx(100.)
    assert np.all(new['collection_hours'] <= new['staff_gross_hours'])


def test_no_threshold_seed_creates_population_when_the_finite_upper_is_too_small():
    model = narrow(ThresholdSeededDispatchFeedback)
    model.upper[:] = 14
    result = model.solve()
    assert result['total'][0] == 0 and not result['threshold_seeded'][0]


def test_scoped_version_does_not_change_original_dispatch_class():
    assert DispatchFeedback.solve.__qualname__ == 'DispatchFeedback.solve'
    model = narrow(ThresholdSeededDispatchFeedback); before = {k: np.array(v, copy=True) for k, v in vars(model.x).items()}
    model.solve()
    for k, value in before.items(): np.testing.assert_array_equal(getattr(model.x, k), value)


def test_versioned_adapter_restores_original_factory_when_writer_fails(monkeypatch, tmp_path):
    from scripts import build_seeded_dispatch as adapter
    original = adapter.BASE.DispatchFeedback
    def failed_writer(*args):
        assert adapter.BASE.DispatchFeedback is not original
        raise RuntimeError('manufactured writer failure')
    monkeypatch.setattr(adapter.BASE, 'run', failed_writer)
    with pytest.raises(RuntimeError, match='manufactured writer failure'):
        adapter.run('raw', 600, 120000, 'all_open', tmp_path)
    assert adapter.BASE.DispatchFeedback is original
