"""Search regressions: restart preservation, budgets, and circular bearings."""
from dataclasses import asdict
import json

import numpy as np
import pytest

from rotclimate import calibrate as C
from rotclimate.config import Params


@pytest.fixture(autouse=True)
def restore_space():
    original = C.SPACE
    yield
    C._set_space(original)


@pytest.mark.parametrize("bearing, expected", [(330, -30), (360, 0), (-390, -30), (180, -180)])
def test_equivalent_bearings_survive_encoding(bearing, expected):
    C._set_space(C.SPACE_V9)
    p = C.decode(C.encode(Params(north_bearing=bearing)), Params())
    assert p.north_bearing == pytest.approx(expected)


def test_calibration_cli_plan_preserves_verified_numerics(monkeypatch,capsys):
    import sys
    from rotclimate.__main__ import numerical_settings
    path='calibration/round20_retrograde_seasonal_verified.json'
    monkeypatch.setattr(sys,'argv',['calibrate','--start',path,'--physics','v9','--plan'])
    monkeypatch.setattr(C,'calibrate',lambda *a,**kw: pytest.fail('Plan launched a calibration'))
    C.main()
    plan=json.loads(capsys.readouterr().out)
    assert numerical_settings(Params(**plan['params']))==numerical_settings(Params.from_json(path))


def test_sensitivity_cli_plan_preserves_verified_numerics(monkeypatch,capsys):
    import sys
    from scripts import sensitivity as S
    from rotclimate.__main__ import numerical_settings
    path='calibration/round20_retrograde_seasonal_verified.json'
    monkeypatch.setattr(sys,'argv',['sensitivity',path,'--physics','v9','--seeds','1','--plan'])
    monkeypatch.setattr(S.mp,'get_context',lambda *a: pytest.fail('Plan started workers'))
    S.main()
    plan=json.loads(capsys.readouterr().out)
    assert numerical_settings(Params(**plan['params']))==numerical_settings(Params.from_json(path))


def test_calibration_legacy_numerics_and_explicit_overrides(monkeypatch,capsys):
    import sys
    monkeypatch.setattr(sys,'argv',['calibrate','--plan','--physics','v9'])
    C.main()
    p=Params(**json.loads(capsys.readouterr().out)['params'])
    assert (p.downsample,p.steps_per_year,p.picard_iters)==(16,25,2)
    path='calibration/round20_retrograde_seasonal_verified.json'
    monkeypatch.setattr(sys,'argv',['calibrate','--plan','--start',path,'--picard','128','--downsample','4'])
    C.main()
    p=Params(**json.loads(capsys.readouterr().out)['params'])
    assert p.picard_iters==128 and p.downsample==4 and p.moisture_require_convergence


class SerialPool:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def map(self, fn, jobs, chunksize=1):
        return [fn(job) for job in jobs]

    def imap_unordered(self, fn, jobs, chunksize=1):
        return iter([fn(job) for job in reversed(jobs)])


@pytest.mark.parametrize("budget, count", [(1, 1), (8, 1), (9, 9), (18, 17)])
def test_restart_keeps_baseline_and_respects_budget(tmp_path, monkeypatch, budget, count):
    pytest.importorskip("cma")
    calls = []

    def worker(args):
        x, base, mode, space, seeds, cutoff = args
        calls.append(args)
        score = 0.5 if len(calls) == 1 else 0.3 - 0.001 * len(calls)
        return dict(score=score, mean=score, per_class={"med": score},
                    params=asdict(C.decode(x, Params(**base))))

    monkeypatch.setattr(C, "_worker", worker)
    def context(method):
        assert method == "spawn"
        return type("Context", (), {"Pool": lambda self, n: SerialPool()})()

    monkeypatch.setattr(C.mp, "get_context", context)
    best = C.calibrate(tmp_path, budget, Params(), popsize=8,
                       fixed={"retrograde": 0.75}, seeds=[1, 2, 3])
    rows = [json.loads(line) for line in (tmp_path / "evals.jsonl").read_text().splitlines()]
    assert len(calls) == len(rows) == count <= budget
    assert calls[0][-1] is None  # starting candidate must see every world
    assert best["score"] == 0.5
    assert rows[0]["stage"] == "initial"
    assert Params.from_json(tmp_path / "best_params.json").retrograde
    assert np.allclose(rows[0]["x"], best["x"])
    for row in rows:
        assert row["params"] == json.loads(json.dumps(asdict(C.decode(np.array(row["x"]), Params()))))
