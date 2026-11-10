import sys
from pathlib import Path

import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from audit_roman_rural_coordinates import national_grid, official_references, compare_axes


@pytest.mark.parametrize('reference,expected', [('SU8396104767',(483961,104767,1)),
    ('SP 05297 13465',(405297,213465,1)),('SE6338284074',(463382,484074,1)),
    ('SW 47 35',(147000,35000,1000)),('TQ5301865070',(553018,165070,1))])
def test_known_grid_squares_and_nominal_precision(reference,expected):
    assert national_grid(reference)==expected


@pytest.mark.parametrize('reference',['SI123456','ZZ123456','SU12345','51.8,-1.9','SU','SU123456789012'])
def test_bad_or_nonbritish_grid_notation_fails(reference):
    with pytest.raises(ValueError):national_grid(reference)


def test_multipoint_entry_retains_every_point_not_just_closest():
    html='<dl><dt>National Grid Reference:</dt><dd><span>SU 83961 04767</span>, SU 83961 08767</dd></dl>'
    refs=official_references(html);assert len(refs)==2
    result=compare_axes(483961,104767,refs)
    assert result['X_easting_Y_northing_metres']['distances_metres']==[0,4000]
    assert not result['X_easting_Y_northing_metres']['all_references_within_threshold']


def test_duplicate_identical_html_fields_allowed_but_conflicting_fields_fail():
    field='<dt>National Grid Reference:</dt><dd>SU 83961 04767</dd>'
    assert len(official_references(field*2))==1
    with pytest.raises(ValueError,match='unambiguous'):
        official_references(field+'<dt>National Grid Reference:</dt><dd>SW 47 35</dd>')
