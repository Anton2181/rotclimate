from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from polity import directed_trade as directed
from polity import trade


def network(n=80, bump=0.):
    a = np.arange(n - 1); b = a + 1
    costs = np.r_[np.full(n - 1, 1.), np.full(n - 1, 2.)]
    costs[0] += bump
    graph = csr_matrix((costs, (np.r_[a, b], np.r_[b, a])), shape=(n, n))
    return SimpleNamespace(base=graph, n_cells=n)


def test_market_access_resumes_after_an_interrupted_batch_without_double_counting(tmp_path, monkeypatch):
    nets = [network(), network(bump=1.)]
    towns = np.arange(60); people = np.arange(80, dtype=float)
    expected = trade.market_access(nets, towns, people, [2., 10.])
    original = trade.dijkstra; calls = 0
    def interrupted(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 3: raise RuntimeError('interrupted process')
        return original(*args, **kwargs)
    monkeypatch.setattr(trade, 'dijkstra', interrupted)
    with pytest.raises(RuntimeError, match='interrupted'):
        trade.market_access(nets, towns, people, [2., 10.], checkpoint_dir=tmp_path)
    assert list(tmp_path.rglob('*.npz'))
    calls = 0
    def counting(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(trade, 'dijkstra', counting)
    actual = trade.market_access(nets, towns, people, [2., 10.], checkpoint_dir=tmp_path)
    np.testing.assert_array_equal(actual, expected)
    assert calls < 6  # Fewer than the full two-season, three-batch calculation.
    calls = 0
    np.testing.assert_array_equal(trade.market_access(nets, towns, people, [2., 10.], checkpoint_dir=tmp_path), expected)
    assert calls == 0
    changed = [network(bump=10.), nets[1]]
    np.testing.assert_array_equal(trade.market_access(changed, towns, people, [2., 10.], checkpoint_dir=tmp_path),
                                  trade.market_access(changed, towns, people, [2., 10.]))


def test_directed_routes_resume_exactly_and_reject_old_graph_or_population_cache(tmp_path, monkeypatch):
    nets = [network(), network(bump=1.)]; towns = np.arange(60); mass = 1. + towns.astype(float)
    expected = directed.gravity_routes(nets, towns, mass, scale=20., sources=30)
    original = directed.dijkstra; calls = 0
    def interrupted(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 55: raise RuntimeError('interrupted process')
        return original(*args, **kwargs)
    monkeypatch.setattr(directed, 'dijkstra', interrupted)
    with pytest.raises(RuntimeError, match='interrupted'):
        directed.gravity_routes(nets, towns, mass, scale=20., sources=30, checkpoint_dir=tmp_path)
    calls = 0
    def counting(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(directed, 'dijkstra', counting)
    actual = directed.gravity_routes(nets, towns, mass, scale=20., sources=30, checkpoint_dir=tmp_path)
    for a, b in zip(actual, expected): np.testing.assert_array_equal(a, b)
    assert calls < 120
    calls = 0
    directed.gravity_routes(nets, towns, mass, scale=20., sources=30, checkpoint_dir=tmp_path)
    assert calls == 0
    for changed_nets, changed_mass in [([network(bump=10.), nets[1]], mass), (nets, mass * 2)]:
        expected = directed.gravity_routes(changed_nets, towns, changed_mass, scale=20., sources=30)
        actual = directed.gravity_routes(changed_nets, towns, changed_mass, scale=20., sources=30, checkpoint_dir=tmp_path)
        for a, b in zip(actual, expected): np.testing.assert_array_equal(a, b)


def test_invalid_archive_cannot_become_cached_trade_output(tmp_path):
    from polity import checkpoints
    checkpoint = checkpoints.slot(tmp_path, 'example', [network()], [np.array([1])], {})
    checkpoints.write(checkpoint, ma=np.ones(2))
    assert checkpoints.read(checkpoint) is not None
    checkpoint[0].write_bytes(b'incomplete archive')
    assert checkpoints.read(checkpoint) is None
    np.savez(checkpoint[0], identity='wrong inputs', ma=np.zeros(2))
    assert checkpoints.read(checkpoint) is None
