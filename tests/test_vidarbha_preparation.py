import sys
from pathlib import Path
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_vidarbha_preparation import read_table,inspect_table


def test_documented_coordinate_axes_are_checked_without_silent_swapping():
    raw=b'SiteCode,YCoord,Xcoord,RecordedDate\na,80,20,Early Historic\nb,20,80,Medieval\n'
    result,ids=inspect_table(raw)
    assert result['plausible_documented_axis_pairs']==1
    assert result['plausible_swapped_axis_pairs']==1
    assert result['date_text_flags']['early_historic']==1
    assert ids=={'a','b'}


def test_empty_csv_tail_does_not_hide_unlabelled_nonempty_data():
    raw=b'SiteCode,YCoord,Xcoord,,,\na,80,20,,orphan,\n'
    headers,rows,format_=read_table(raw)
    assert headers==['SiteCode','YCoord','Xcoord']
    assert format_['blank_header_columns']==3
    assert format_['nonempty_unnamed_cells']==1
    assert rows[0]['SiteCode']=='a'


def test_duplicate_ids_are_retained_and_reported_not_merged():
    result,ids=inspect_table(b'SiteCode,YCoord,Xcoord\na,80,20\na,81,20\n')
    assert result['rows']==2 and result['duplicate_site_id_rows']==1
    assert len(ids)==1


def test_duplicate_named_headers_are_rejected():
    with pytest.raises(ValueError,match='Duplicate named'):
        read_table(b'SiteCode,YCoord,YCoord\na,80,20\n')
