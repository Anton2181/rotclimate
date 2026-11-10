"""Integrity checks for study reporting and paired finalist replays."""
from pathlib import Path
import sys
import json
import pickle
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from report_joint_ocean_land_refit import eligible, read_records
from check_joint_ocean_land_finalists import paired, verify_replay, verify_optimizer_checkpoint


def test_partial_last_write_does_not_hide_completed_corruption(tmp_path):
    path = tmp_path/'evals.jsonl'
    path.write_text('{"n":0}\n{"n":')
    assert read_records(path) == [{'n': 0}]
    path.write_text('{"n":0}\n{"n":\n')
    with pytest.raises(ValueError):
        read_records(path)
    path.write_text('{"n":0}\n{"n":0}\n')
    with pytest.raises(ValueError, match='Nonsequential'):
        read_records(path)


def test_aggregate_guards_accept_tradeoff_and_reject_excessive_component():
    assert eligible(dict(S=.994, T_relative=.009, P_relative=-.021))
    assert not eligible(dict(S=.994, T_relative=.011, P_relative=-.023))
    assert not eligible(dict(cost=99, failed=['one']))


def row(t, p, case='same', cells=10):
    return dict(temperature=dict(monthly_mae_C=t), rain=dict(loss=p),
                case_identity=case, cells=cells)


def test_paired_scores_require_actual_input_and_cell_identity():
    reference = dict(one=row(2, .5), two=row(4, 1))
    candidate = dict(one=row(1, .5), two=row(4, .9))
    result = paired(reference, candidate)
    assert result['S'] == pytest.approx(.5*(2.5/3)+.5*(.7/.75))
    candidate['one']['case_identity'] = 'other'
    with pytest.raises(ValueError, match='geography'):
        paired(reference, candidate)
    candidate['one']['case_identity'] = 'same'; candidate['one']['cells'] = 11
    with pytest.raises(ValueError, match='geography'):
        paired(reference, candidate)


def test_finalist_replay_rejects_score_drift():
    rows = dict(one=row(2, .5))
    verify_replay(rows, dict(one=[2+1e-12, .5]), 'test')
    with pytest.raises(ValueError, match='replay differs'):
        verify_replay(rows, dict(one=[2.001, .5]), 'test')


def test_real_pickle_tuple_vs_json_history_and_checkpoint_corruption(tmp_path):
    best=dict(n=0, cost=1., regions={'one':(2.,.5)})
    public=json.loads(json.dumps(best))
    records=[dict(public,n=i,cost=1+i) for i in range(17)]
    es=SimpleNamespace(countiter=2,_told=[])
    chain=dict(records=records,best=public)
    def save(pending=None, count=17):
        (tmp_path/'state.pkl').write_bytes(pickle.dumps((es,pending or [],best,count,None)))
    save()
    verify_optimizer_checkpoint(tmp_path,chain)
    best['regions']['one']=(2.1,.5);save()
    with pytest.raises(ValueError,match='disagrees'):
        verify_optimizer_checkpoint(tmp_path,chain)
    best['regions']['one']=(2.,.5);save(pending=[.2])
    with pytest.raises(ValueError,match='generations'):
        verify_optimizer_checkpoint(tmp_path,chain)
    save(count=16)
    with pytest.raises(ValueError,match='generations'):
        verify_optimizer_checkpoint(tmp_path,chain)
