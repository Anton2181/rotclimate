"""Check every typed comparison row and provider completion marginal."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/continuous_food_visit_calendars_20261112'


def main():
    r=json.loads((OUT/'results.json').read_text());funded=json.loads((OUT/'funded_results.json').read_text());checks=0
    for original in funded['rows']:
        key=original['key'];fr=next(v for v in r['visit_rows'] if v['key']==key and v['stage']=='funded')
        for name,value in original.items():assert fr[name]==value
        assert fr['funded_visits']==original['completed_visits'] and fr['qualified_visits'] is None and fr['physically_scheduled_visits'] is None
        for policy in ('baseline','joint'):
            a=dict(np.load(OUT/key/policy/'fields.npz'));v=next(v for v in r['visit_rows'] if v['key']==key and v['stage']=='policy' and v['policy']==policy)
            for name,value in [('mandatory_complete_providers',a['mandatory_complete'].sum()),('food_no_shortage_providers',a['C__no_shortage'].sum()),('qualified_providers',a['qualified'].sum()),('missing_collector_trips',a['missing_trips'].sum())]:assert v[name]==int(value)
            assert v['actual_visit_hours']==float(a['visit_hours'].sum());checks+=1
        s=dict(np.load(OUT/key/'selected_fields.npz'));v=next(v for v in r['visit_rows'] if v['key']==key and v['stage']=='selected')
        for name,value in [('mandatory_complete_providers',s['selected_mandatory_complete'].sum()),('food_no_shortage_providers',s['selected_food_no_shortage'].sum()),('qualified_providers',s['qualified'].sum()),('joint_policy_providers',s['policy'].sum()),('physically_scheduled_visits',s['provider_physical_visits'].sum())]:assert v[name]==int(value)
        np.testing.assert_array_equal(s['qualified'],s['selected_mandatory_complete']&s['selected_food_no_shortage']);np.testing.assert_array_equal(s['food_no_shortage'],s['selected_food_no_shortage'])
        with np.load(OUT/'funded_fields.npz') as z:provider=z[key+'__provider_for_target'];valid=z[key+'__served']
        for month in range(12):
            completed=np.bincount(provider[month][s['served'][month]],minlength=len(s['policy']))
            np.testing.assert_array_equal(s['provider_completed_visits'][month],completed)
        np.testing.assert_array_equal(s['original_funded'],valid)
        assert v['baseline_tasks_lost']==0 and np.all(s['added_task_counts']>=0)
        checks+=2
    assert checks==32
    write(OUT/'summary_review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),typed_visit_rows_checked=32,
        funded_rows_exact=True,all_provider_counts_and_work_totals_checked=True,selected_point_completion_marginals_exact=True,selected_food_physical_and_combined_flags_separate=True))
    print('All32typed visit rows and provider completion marginals checked.')


if __name__=='__main__':main()
