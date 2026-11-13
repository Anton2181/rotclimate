"""Independent NEW funded-point assignment against unchanged recorded paths."""
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from review_network_duty_visits import check_paths,scalar_allocation
from settlement_locations_earth import sha,write

OUT=ROOT/'output/continuous_food_visit_calendars_20261112'
PARENT=ROOT/'output/settlement_continuous_destination_20261112'


def main():
    r=json.loads((OUT/'funded_results.json').read_text());a=dict(np.load(OUT/'funded_fields.npz'))
    assert r['fields_sha256']==sha(OUT/'funded_fields.npz') and len(r['rows'])==8
    for name,digest in {**r['sources'],**r['producers'],**r['unchanged_map_sha256']}.items():assert sha(ROOT/name)==digest,name
    reviewed=[]
    for mode in ('raw','corrected'):
        x,p=check_paths(mode);demand=p['target_reference_masks']>0;np.testing.assert_array_equal(a[mode+'__demand'],demand)
        for row in [v for v in r['rows'] if v['climate']==mode]:
            key=row['key'];f=dict(np.load(PARENT/row['parent_key']/'fields.npz'));certificate=json.loads((PARENT/row['parent_key']/'review.json').read_text())
            assert certificate['status']=='passed' and certificate['all_positive_collection_work_supported']
            assert certificate['reviewer_sha256']==sha(ROOT/'scripts/review_continuous_destination.py')
            for month in range(12):
                groups=np.flatnonzero(p['keys'][:,0]==month);ids=np.concatenate([np.arange(p['offsets'][i],p['offsets'][i+1]) for i in groups]);providers=np.repeat(p['keys'][groups,1],np.diff(p['offsets'])[groups])
                budget=f['work_secondary_hours'][0,month];expected=scalar_allocation(providers,p['target_index'][ids],7*(p['outward_days'][ids]+p['inward_days'][ids])+1,x,f,budget,demand,row['crew'])
                for name,value in expected.items():np.testing.assert_array_equal(a[key+'__'+name][month],value)
                np.testing.assert_array_equal(a[key+'__reserved_hours'][month],budget)
                np.testing.assert_array_equal(a[key+'__zero_budget_work_unavailable'][month],demand & ~expected['route_unreachable'])
                nonpatrol=f['work_fundable_collection_hours'][month]+f['work_secondary_hours'][1:,month].sum(axis=0);unused=f['work_gross_hours'][month]-nonpatrol-expected['used_hours']
                assert (unused>=-1e-8).all();np.testing.assert_allclose(a[key+'__whole_provider_unused_hours'][month],unused,atol=1e-7)
            for field,name in [('served','completed_visits'),('route_unreachable','route_unreachable'),('provider_work_unavailable','provider_work_unavailable'),('capacity_unmet','capacity_unmet')]:assert row[name]==int(a[key+'__'+field].sum())
            for actor in row['actors']:
                i=actor['actor_index'];assert actor['requested_visits']==int(demand[i].sum()*12)
                assert actor['completed_visits']==int(a[key+'__served'][:,i].sum())
                for name in ('route_unreachable','provider_work_unavailable','capacity_unmet'):assert actor[name]==int(a[key+'__'+name][:,i].sum())
            reviewed.append(key);print('NEW point jobs scalar allocation/ledger',key,flush=True)
    write(OUT/'funded_review.json',dict(status='passed',results_sha256=sha(OUT/'funded_results.json'),fields_sha256=sha(OUT/'funded_fields.npz'),reviewer_sha256=sha(Path(__file__)),
        path_and_scalar_reviewer_sha256=sha(ROOT/'scripts/review_network_duty_visits.py'),cases=reviewed,recorded_graph_edges_and_targets_checked=True,
        exact_new_parent_reserved_slice=True,unchanged_funded_nonpatrol_commitments=True,no_collection_omissions_reused_as_patrol=True,all_actor_request_partitions=True,
        scope='Hour-funded point jobs only;physical calendars and own destination food remain required before maps.'))


if __name__=='__main__':main()
