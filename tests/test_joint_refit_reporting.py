"""Integrity checks for study reporting and paired finalist replays."""
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
from report_joint_ocean_land_refit import eligible, read_records
from check_joint_ocean_land_finalists import paired, verify_replay


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
