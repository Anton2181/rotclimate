from dataclasses import asdict
import json
from pathlib import Path

import pytest

from scripts import check_storm_balance as storm


def row(params, dry=.12, cold=.68, hot=.57, accuracy=.5):
    return dict(params=asdict(params), accuracy=accuracy,
                zone_recall=dict(cold_dry=cold, hot_dry=hot),
                mediterranean=dict(dry_share=dry, cs_share=.4))


def prepared(tmp_path):
    p = storm.night.Params.from_json('calibration/round20_retrograde_local_shortlist.json')
    p = p.replace(storm_width=6.0834929141882)
    candidate = p.replace(storm_asym=.1, storm_width=5.77931826847879)
    controls = {s:dict(status='ok', input_id=f'anchor-{s}',
                      row=row(p.replace(beyond_seed=s, t_iters=384 if s == 402 else 192)))
                for s in (*storm.DEVELOPMENT, *storm.VALIDATION)}
    plan = dict(source=str(tmp_path/'original'), retry_source=str(tmp_path/'retry'),
                source_id='source', diagnostic_id='script', candidate=asdict(candidate),
                changes_from_anchor=dict(storm_asym=.1, storm_width=candidate.storm_width),
                development=list(storm.DEVELOPMENT), validation=list(storm.VALIDATION),
                warmup_steps=50, guards=storm.night.GUARDS,
                control_inputs={str(s):d['input_id'] for s,d in controls.items()},
                control_temperature_caps={str(s):d['row']['params']['t_iters'] for s,d in controls.items()},
                note='Validation worlds already examined; candidate finer grid not checked.')
    # A manifest round trip should not alter cache/provenance comparison.
    return json.loads(json.dumps(plan)), controls


def test_read_only_plan_does_not_start_simulations_or_write(tmp_path, monkeypatch):
    plan, controls = prepared(tmp_path)
    monkeypatch.setattr(storm, 'load_inputs', lambda *args:(plan,controls))
    monkeypatch.setattr(storm, 'run_checks', lambda *args:pytest.fail('Plan launched checks'))
    out = tmp_path/'new'
    assert storm.main(['--out',str(out)]) == 0
    assert not out.exists()


def test_each_pair_has_matching_numerics_and_only_two_physics_changes(tmp_path):
    plan, controls = prepared(tmp_path)
    for seed, control in controls.items():
        trial = storm.params_for(plan, seed)
        anchor = control['row']['params']
        actual = json.loads(json.dumps(asdict(trial)))
        expected = json.loads(json.dumps(anchor))
        assert {k for k,v in actual.items() if v != expected[k]} == {'storm_asym','storm_width'}
        assert trial.t_iters == (384 if seed == 402 else 192)
        j = storm.case_job(plan,tmp_path/'new','trial',seed)
        assert j['spinup'] == 50
        old = storm.night.job('trial',trial,50,tmp_path/'new',plan['source_id'])
        assert j['input_id'] != old['input_id']  # wrapper provenance is included


@pytest.mark.parametrize('failure,expected_calls,decision',[
    ('cold301',1,'rejected'), ('numerics301',1,'incomplete_numerics'),
    ('warmup',4,'unsettled'), ('fresh401',5,'rejected'),
    ('numerics402',6,'incomplete_numerics'), ('none',6,'qualified'),
])
def test_pipeline_stops_on_failed_checks_and_publishes_only_a_complete_fit(
        tmp_path, monkeypatch, failure, expected_calls, decision):
    plan, controls = prepared(tmp_path)
    monkeypatch.setattr(storm,'ensure_sources',lambda p:None)
    monkeypatch.setattr(storm.night,'stability',lambda *args:dict(passed=failure != 'warmup'))
    calls, exports = [], []
    def solve(j):
        calls.append(j)
        seed = j['params']['beyond_seed']
        if failure == 'numerics301' and seed == 301 or failure == 'numerics402' and seed == 402:
            return dict(name=j['name'],status='failed',error='Temperature failed',input_id=j['input_id'])
        damaged = failure == 'cold301' and seed == 301 or failure == 'fresh401' and seed == 401
        return dict(name=j['name'],status='ok',input_id=j['input_id'],
                    row=row(storm.night.Params(**j['params']),dry=.08,cold=.60 if damaged else .69),
                    fields='unused',transport='unused',result='unused')
    def publish(spec,out):
        exports.append(spec)
        assert spec['warmup_steps'] == 50 and spec['fresh_checks_complete']
        assert spec['fine_checks'] == dict(status='not_run_for_candidate',used=False)
        assert spec['params']['beyond_seed'] == 1
        return dict(status='published',selected=spec['selected'])
    monkeypatch.setattr(storm,'solve_case',solve)
    monkeypatch.setattr(storm,'publish',publish)
    out = tmp_path/'new'
    state = storm.run_checks(plan,controls,out)
    assert state['decision'] == decision and state['stage'] == 'complete'
    assert len(calls) == expected_calls
    assert calls[0]['params']['beyond_seed'] == 301  # prioritize the known troublesome world
    assert len(exports) == (1 if decision == 'qualified' else 0)
    if decision == 'qualified':
        assert calls[2]['full'] and calls[2]['transport'] and calls[2]['params']['beyond_seed'] == 1
        assert calls[3]['spinup'] == 25 and calls[3]['transport']
        assert not state['med_goal_met']  # improvement does not falsely certify the <=5% target
    # Repeating a completed run must not repeat simulations or replace the atlas again.
    again = storm.run_checks(plan,controls,out)
    assert again['decision'] == decision
    assert len(calls) == expected_calls


def test_modified_manifest_and_original_outputs_are_protected(tmp_path,monkeypatch):
    plan, controls = prepared(tmp_path)
    monkeypatch.setattr(storm,'ensure_sources',lambda p:None)
    monkeypatch.setattr(storm,'solve_case',lambda *args:pytest.fail('Invalid output reached solver'))
    with pytest.raises(ValueError,match='separate output'):
        storm.run_checks(plan,controls,Path(plan['source']))
    out = tmp_path/'new'
    out.mkdir()
    (out/'experiment.json').write_text(json.dumps(dict(plan,diagnostic_id='different-script')))
    with pytest.raises(ValueError,match='different experiment'):
        storm.run_checks(plan,controls,out)


def test_cached_control_needs_the_matching_warmup_and_rechecked_convergence(tmp_path,monkeypatch):
    plan, _ = prepared(tmp_path)
    j = storm.case_job(plan,tmp_path,'test',1)
    fields = tmp_path/'test_fields.npz'
    detail = dict(params=j['params'],run_settings=dict(spinup_steps_requested=50,
                  spinup_steps_observed=8,steps_per_year=25))
    path = tmp_path/'test_diagnostic.json'
    path.write_text(json.dumps(detail))
    monkeypatch.setattr(storm.night,'cached',lambda j:dict(status='ok',fields=str(fields)))
    with pytest.raises(ValueError,match='Wrong warm-up'):
        storm.load_checked(j)
    detail['run_settings']['spinup_steps_observed'] = 50
    path.write_text(json.dumps(detail))
    def reject(detail):
        raise RuntimeError('Recorded moisture solve did not converge')
    monkeypatch.setattr(storm.night,'checked_summary',reject)
    with pytest.raises(RuntimeError,match='did not converge'):
        storm.load_checked(j)


def test_source_changes_are_rejected(tmp_path,monkeypatch):
    plan, _ = prepared(tmp_path)
    monkeypatch.setattr(storm.night,'source_id',lambda:'changed')
    monkeypatch.setattr(storm,'script_id',lambda:plan['diagnostic_id'])
    with pytest.raises(ValueError,match='changed'):
        storm.ensure_sources(plan)
