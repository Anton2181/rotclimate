import json
from pathlib import Path
import pytest
from rotclimate.evidence_audit import numeric_leaves,classify,constants,audit


def test_numeric_inventory_excludes_booleans_and_preserves_paths():
    assert list(numeric_leaves({'x':True,'a/b':[3,{'~':4.}]}))==[('/a~1b/0',3),('/a~1b/1/~0',4.)]


def test_specific_fit_does_not_promote_neighbouring_scenarios():
    rules=[dict(pattern='/*',status='scenario',note='default'),dict(pattern='/a',status='earth_fit',note='fitted',evidence=['paper'])]
    assert classify('/a',rules)['status']=='earth_fit'
    assert classify('/b',rules)['status']=='scenario'
    assert classify('/c',[])['status']=='unreviewed'


def test_evidence_claims_and_ambiguity_are_rejected():
    with pytest.raises(ValueError):classify('/a',[dict(pattern='/a',status='earth_fit')])
    with pytest.raises(ValueError):classify('/a',[dict(pattern='/a',status='scenario'),dict(pattern='/a',status='definition')])


def test_python_inventory_never_executes_model_code(tmp_path):
    p=tmp_path/'model.py';p.write_text("raise RuntimeError('never execute')\nA=2\nB=missing*3\nC={'x':4}\n")
    values,unresolved=constants(p)
    assert values=={'A':2,'C':{'x':4}} and unresolved[0]['name']=='B'


def test_missing_evidence_reference_fails(tmp_path):
    (tmp_path/'params.json').write_text('{"a":1}')
    spec=dict(scope='test',components=[dict(id='m',label='m',validation='',observables='',next_test='',sources=[dict(file='params.json',rules=[dict(pattern='/a',status='earth_fit',evidence=['absent'])])])])
    with pytest.raises(ValueError):audit(tmp_path,spec)


def test_production_scenario_defaults_stay_explicit():
    root=Path(__file__).resolve().parents[1];spec=json.loads((root/'calibration/earth_components_20261105/evidence_spec.json').read_text());result=audit(root,spec)
    selected={r['pointer']:r for r in result['parameters'] if r['source']=='data/settlement_labour_model.json'}
    assert selected['/worker_fraction_of_reference_rural_people']['status']=='scenario'
    assert selected['/worker_fraction_of_reference_rural_people']['value']==.4
    assert all(r['status']=='scenario' for r in selected.values())
    assert len(result['components'])==11
