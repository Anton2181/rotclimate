import json
from pathlib import Path

import pytest

from polity.role_evidence import association_blocks, compile_role_evidence, occupation_window

ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = json.loads((ROOT/'calibration/roman_rural_roles_20261110/crosswalk.json').read_text())


def test_roles_coexist_without_duplicate_allocations_or_institutions():
    result = compile_role_evidence('1', ['Military', 'Rural settlement'],
        ['farm', 'farm', 'fort', 'shrine'], '-100', '400', CROSSWALK, domestic='Yes')
    assert len(result.channels) == len(set(result.channels))
    assert {'military_context', 'residential_context', 'ritual_funerary_context'} <= set(result.channels)
    assert result.physical_place is None and result.role_time == 'undated'
    assert result.site_time == 'span_compatible'
    assert set(result.date_flags) == {'start_left_censored', 'end_period_convention'}


def test_no_administration_market_or_manned_fort_inference_from_context():
    result = compile_role_evidence('1', [], ['villa', 'roadside settlement', 'hillfort', 'jetty'],
        50, 350, CROSSWALK)
    assert 'military_context' not in result.channels
    assert not any(s in channel for channel in result.channels for s in ['market','administrat','authority'])
    assert result.unknown_labels == ()


def test_unknown_role_is_explicit_and_no_domestic_is_not_absence():
    result = compile_role_evidence('1', [], ['new type'], None, 400, CROSSWALK, domestic='No')
    assert result.unknown_labels == ('minor:new type',)
    assert result.channels == () and result.site_time == 'unknown'


@pytest.mark.parametrize('start,end,state', [('',400,'unknown'), (0,400,'ambiguous_zero'),
    (300,100,'invalid_interval'), (201,350,'outside_recorded_span'), (-100,400,'span_compatible'),
    (float('nan'),400,'unknown'), (50,200,'span_compatible')])
def test_time_states_do_not_turn_uncertainty_into_absence(start,end,state):
    assert occupation_window(start,end)[0] == state


def test_shared_associations_block_transitively_without_defining_places():
    records = ['1','2','3','4','5','6']
    associations = [('1','HERMON','A','17'),('2','HERMON','A','17'),
        ('2','OASIS','','project-1'),('3','OASIS','','project-1'),
        ('4','HERMON','B','17'),('5','HEREV','A','17'),('6','HERMON','A','')]
    forward = association_blocks(records, associations)
    assert forward == association_blocks(reversed(records), reversed(associations))
    assert forward['1'] == forward['2'] == forward['3']
    assert len({forward[i] for i in ['1','4','5','6']}) == 4
    # Source observations remain distinct even when their blocking keys coincide.
    assert len(forward) == len(records)


def test_association_orphans_and_missing_record_ids_fail_explicitly():
    with pytest.raises(ValueError,match='missing record'):
        association_blocks(['1'], [('2','HERMON','A','17')])
    with pytest.raises(ValueError,match='record ID'):
        compile_role_evidence('', [], [], 50, 300, CROSSWALK)
    with pytest.raises(ValueError,match='target year'):
        occupation_window(50,300,float('inf'))
