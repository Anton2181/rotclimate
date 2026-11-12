"""Place identity grouping and the key-join audit's own classification rules."""
import importlib.util
from pathlib import Path
import sys

import numpy as np
import pytest

from polity.settlement_place_groups import place_groups
from polity.settlement_size_evidence import HousingSample

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    sys.path.insert(0, str(ROOT / 'scripts'))
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def test_repeated_estimates_for_one_place_form_one_group():
    groups = place_groups(['sample', 'visible', 'other'], {'sample': 'Hanson2016_385', 'visible': 'Hanson2016_385'})
    assert groups == {'Hanson2016_385': ['sample', 'visible'], 'unjoined:other': ['other']}


def test_unjoined_samples_never_merge_or_pass_as_joined():
    groups = place_groups(['a', 'b'], {})
    assert groups == {'unjoined:a': ['a'], 'unjoined:b': ['b']}
    with pytest.raises(ValueError, match='certified place identity'):
        place_groups(['a'], {'a': 'unjoined:a'})


@pytest.mark.parametrize('sites,identities', [(['a', 'a'], {}), ([''], {}), (['a'], {'b': 'Hanson2016_1'}),
                                              (['a'], {'a': ''}), (['a'], {'a': 7})])
def test_invalid_identity_inputs_refused(sites, identities):
    with pytest.raises(ValueError):
        place_groups(sites, identities)


def test_joined_identity_does_not_clear_any_year_gate():
    x = HousingSample('Hanson2016_790', 4, .25, 45., 'dated excavation')
    assert place_groups([x.site_id], {x.site_id: 'Hanson2016_790'}) == {'Hanson2016_790': [x.site_id]}
    assert set(x.blockers(150)) == {'sample_phase_unresolved', 'site_representativeness_unresolved',
                                    'contemporaneous_extent_unresolved'}


def test_name_classes_keep_real_differences():
    j = load('join_settlement_size_identity')
    assert j.agreement('Corinium', 'Corinium') == 'exact'
    assert j.agreement('Augusta Praetoria', 'augusta-praetoria') == 'equal_after_normalisation'
    assert j.agreement('Thmuïs', 'Thmuis') == 'equal_after_normalisation'
    assert j.agreement('Corinium', 'Corinium Dobunnorum') == 'different'


def test_fraction_classes_have_exact_boundaries():
    j = load('join_settlement_size_identity')
    assert [j.fraction_class(f) for f in (.00025, .0099999, .01, .0999, .1, .999, 1)] == [
        'below_1_percent', 'below_1_percent', '1_to_below_10_percent', '1_to_below_10_percent',
        '10_to_below_100_percent', '10_to_below_100_percent', 'whole_stated_extent']


def test_association_handles_ties_and_perfect_order():
    j = load('join_settlement_size_identity')
    x = np.array([1., 2, 2, 3, 4, 5, 6, 7]); up = j.association(x, x * 3)
    assert up['spearman_rho'] == pytest.approx(1) and up['n'] == 8
    assert up['permutation_p_two_sided'] < .01
    down = j.association(x, -x)
    assert down['spearman_rho'] == pytest.approx(-1)
    flat = j.association(np.arange(8.), np.array([3., 1, 4, 1, 5, 9, 2, 6]))
    assert 0 < flat['permutation_p_two_sided'] <= 1


def test_review_xml_reader_matches_spreadsheet_library(tmp_path):
    openpyxl = pytest.importorskip('openpyxl')
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Cities'
    ws.append(['Primary Key', 'Area']); ws.append(['Hanson2016_1', 18]); ws.append(['Hanson2016_2', 'NULL'])
    ws.append(['Hanson2016_3', -350.5]); ws.append(['Hanson2016_4', None])
    path = tmp_path / 'tiny.xlsx'; wb.save(path)
    table = load('review_settlement_size_identity').sheets(path)['Cities']
    assert table[0] == ['Primary Key', 'Area'] and table[1] == ['Hanson2016_1', 18]
    assert table[2][1] == 'NULL' and float(table[3][1]) == -350.5 and table[4] == ['Hanson2016_4']
