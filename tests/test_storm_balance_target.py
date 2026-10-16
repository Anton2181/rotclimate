from dataclasses import asdict
import json
from pathlib import Path

import pytest

from scripts import continue_storm_balance as target


def row(params=None, dry=.12, cold=.68, hot=.57, accuracy=.5):
    return dict(params={} if params is None else asdict(params), accuracy=accuracy,
                zone_recall=dict(cold_dry=cold, hot_dry=hot),
                mediterranean=dict(dry_share=dry, cs_share=.4))


def prepared(tmp_path):
    p = target.night.Params.from_json('calibration/round20_retrograde_local_shortlist.json')
    p = p.replace(storm_width=6.0834929141882)
    candidate = p.replace(storm_asym=.1, storm_width=5.77931826847879)
    dry = {1:.12, 301:.0367, 302:.0154, 401:.0227, 402:.0311}
    controls = {s:dict(status='ok', input_id=f'anchor-{s}',
                      row=row(p.replace(beyond_seed=s,t_iters=384 if s == 402 else 192),dry=dry[s]))
                for s in dry}
    reused = {s:dict(status='ok',input_id=f'original-trial-{s}',
                    row=row(candidate.replace(beyond_seed=s),dry=.0361 if s == 301 else .0187))
              for s in (301,302)}
    plan = dict(source=str(tmp_path/'original'), retry_source=str(tmp_path/'retry'),
                completed_source=str(tmp_path/'completed'), source_id='source',
                original_diagnostic_id='old-script', diagnostic_id='new-script',
                candidate=asdict(candidate), warmup_steps=50,
                control_temperature_caps={str(s):d['row']['params']['t_iters'] for s,d in controls.items()},
                guards={'med_dry_limit':'max(anchor dry share, 0.05)', 'worst_med_dry_must_improve':True},
                user_preference='Allow 5% on already-good worlds; improve the worst world.',
                note='Original rejection retained; candidate finer grid untested.')
    return json.loads(json.dumps(plan)), controls, reused


@pytest.mark.parametrize('anchor_dry,trial_dry,allowed',[
    (.0154,.0187,True), (.0154,.05,True), (.0154,.05001,False),
    (.12,.119,True), (.12,.12001,False),
])
def test_user_target_rule_allows_only_the_declared_mediterranean_tradeoff(anchor_dry,trial_dry,allowed):
    assert (not target.guard_failures(row(dry=trial_dry),row(dry=anchor_dry))) == allowed


def test_other_guards_and_original_policy_are_unchanged():
    a, b = row(dry=.0154), row(dry=.0187)
    assert target.night.guard_failures(b,a)  # original experiment stays rejected
    assert not target.guard_failures(b,a)
    assert target.night.GUARDS['med_dry_max_increase'] == 0
    assert target.guard_failures(row(dry=.0187,cold=.65),a)
    assert target.guard_failures(row(dry=.0187,hot=.53),a)
    assert target.guard_failures(row(dry=.0187,accuracy=.48),a)
    b['mediterranean']['cs_share'] = .37
    assert target.guard_failures(b,a)


def test_read_only_plan_starts_nothing_and_writes_nothing(tmp_path,monkeypatch):
    plan, controls, reused = prepared(tmp_path)
    monkeypatch.setattr(target,'load_inputs',lambda *args:(plan,controls,reused))
    monkeypatch.setattr(target,'run_checks',lambda *args:pytest.fail('Plan launched work'))
    out = tmp_path/'new'
    assert target.main(['--out',str(out)]) == 0
    assert not out.exists()


@pytest.mark.parametrize('failure,expected_calls,decision',[
    ('none',4,'qualified'), ('cold301',0,'rejected'), ('numerics1',1,'incomplete_numerics'),
    ('tied_worst',1,'not_better'), ('warmup',2,'unsettled'),
    ('fresh401',3,'rejected'), ('numerics402',4,'incomplete_numerics'),
])
def test_continuation_reuses_two_cases_and_requires_every_remaining_check(
        tmp_path,monkeypatch,failure,expected_calls,decision):
    plan, controls, reused = prepared(tmp_path)
    monkeypatch.setattr(target,'ensure_sources',lambda plan:None)
    monkeypatch.setattr(target.night,'stability',lambda *args:dict(passed=failure != 'warmup'))
    if failure == 'cold301':
        reused[301]['row']['zone_recall']['cold_dry'] = .60
    calls, exports = [], []
    def solve(j):
        calls.append(j)
        seed = j['params']['beyond_seed']
        assert seed not in (301,302)  # completed long runs must never be repeated
        assert j['params']['t_iters'] == (384 if seed == 402 else 192)
        if failure == 'numerics1' and seed == 1 or failure == 'numerics402' and seed == 402:
            return dict(name=j['name'],status='failed',error='Temperature failed',input_id=j['input_id'])
        dry = .12 if failure == 'tied_worst' else .09 if seed == 1 else .03 if seed == 401 else .04
        cold = .60 if failure == 'fresh401' and seed == 401 else .69
        return dict(name=j['name'],status='ok',input_id=j['input_id'],
                    row=row(target.night.Params(**j['params']),dry=dry,cold=cold),
                    fields='unused',transport='unused',result='unused')
    def publish(spec,out):
        exports.append(spec)
        assert spec['followup']['guards'] == plan['guards']
        assert spec['fresh_checks_complete'] and spec['warmup_steps'] == 50
        assert not spec['fine_checks']['used']
        return dict(status='published')
    monkeypatch.setattr(target.storm,'solve_case',solve)
    monkeypatch.setattr(target.storm,'publish',publish)
    out = tmp_path/'new'
    state = target.run_checks(plan,controls,reused,out)
    assert state['decision'] == decision and state['stage'] == 'complete'
    assert len(calls) == expected_calls
    assert len(exports) == (1 if decision == 'qualified' else 0)
    if decision == 'qualified':
        assert state['development_worst']['passed'] and state['final_worst']['passed']
        assert not state['med_goal_met']  # 9% remains above the 5% final goal
        assert calls[0]['full'] and calls[0]['transport'] and calls[0]['spinup'] == 50
        assert calls[1]['spinup'] == 25 and calls[1]['transport']
    assert target.run_checks(plan,controls,reused,out)['decision'] == decision
    assert len(calls) == expected_calls


def test_earlier_outputs_and_policy_manifest_are_protected(tmp_path,monkeypatch):
    plan, controls, reused = prepared(tmp_path)
    monkeypatch.setattr(target,'ensure_sources',lambda plan:None)
    monkeypatch.setattr(target.storm,'solve_case',lambda *args:pytest.fail('Invalid output reached worker'))
    with pytest.raises(ValueError,match='separate output'):
        target.run_checks(plan,controls,reused,Path(plan['completed_source']))
    out = tmp_path/'new'
    out.mkdir()
    (out/'experiment.json').write_text(json.dumps(dict(plan,user_preference='different policy')))
    with pytest.raises(ValueError,match='another policy'):
        target.run_checks(plan,controls,reused,out)


def test_continuation_loads_cases_with_original_wrapper_identity(tmp_path,monkeypatch):
    plan, controls, reused = prepared(tmp_path)
    old = dict(plan,diagnostic_id='original-wrapper',guards=target.night.GUARDS)
    monkeypatch.setattr(target.storm,'load_inputs',lambda *args:(old,controls))
    completed = tmp_path/'completed'
    completed.mkdir()
    (completed/'experiment.json').write_text(json.dumps(old))
    (completed/'comparison.json').write_text(json.dumps(dict(stage='complete',decision='rejected')))
    calls = []
    def checked(j):
        seed = j['params']['beyond_seed']
        expected = target.storm.case_job(old,completed,f'train_storm_balance_s{seed}',seed)
        assert j['input_id'] == expected['input_id']
        calls.append(seed)
        return reused[seed]
    monkeypatch.setattr(target.storm,'load_checked',checked)
    result, _, loaded = target.load_inputs(plan['source'],plan['retry_source'],completed)
    assert calls == [301,302] and loaded == reused
    assert result['original_diagnostic_id'] == 'original-wrapper'
    assert old['guards']['med_dry_max_increase'] == 0
    assert 'med_dry_max_increase' not in result['guards']
