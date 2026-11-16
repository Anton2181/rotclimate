"""Reviewed seasonal civilian/staff budgets as isolated downstream source packets."""
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_candidate_seasonal_20261116'
BASE=ROOT/'output/urban_hierarchy_candidate_20261116';RELEASE=ROOT/'output/settlement_release4_20261116'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    dest=OUT/'downstream';dest.mkdir(exist_ok=True);summary={};templates={};parents={}
    for mode in ['raw','corrected']:
        parent=RELEASE/f'reach/settlement_supplyfed/earth_fit_{mode}/settled_reach.json.gz'
        templates[mode]=json.loads(gzip.decompress(parent.read_bytes()));parents[mode]=sha(parent)
    with np.load(OUT/'town_model.npz') as a:
        for c in r['cases']:
            key=c['key'];mode=c['mode'];template=templates[mode]
            sites=json.loads((BASE/f'{c["model"]}/placed_{mode}_sites.json').read_text())['sites']
            assert [s['node'] for s in sites]==[s['node'] for s in template['sites']]
            affiliation=np.array([s['actor_index']>=0 for s in template['sites']])
            np.testing.assert_array_equal(affiliation,[bool(s.get('actor')) for s in sites])
            active=a[key+'__active'];staff=a[key+'__staff'];civil=a[key+'__civilian'];total=a[key+'__target']
            np.testing.assert_allclose(total,staff+civil,atol=1e-6,rtol=1e-10)
            assert (staff==100*active).all() and not (active&~affiliation).any()
            before=np.array(next(x for x in template['cases'] if x['id']=='joint365')['institutional_active'],bool)
            changes=[dict(id=s['id'],name=s['name'],node=s['node'],actor_index=template['sites'][i]['actor_index'],
                annual_active=bool(before[i]),seasonal_active=bool(active[i])) for i,s in enumerate(sites) if before[i]!=active[i]]
            status='ready_for_isolated_reach_rebuild' if c['qualified'] else 'blocked_unqualified_seasonal_case'
            packet=dict(status=status,adopt=False,gate=dict(passed=False,reason='Conditional cereal/accounting scenario; empirical transfer and complete resources/work/roles unresolved.'),integrated_support=False,source_case=key,
                source_results_sha256=sha(OUT/f'cases/{key}/results.json'),physical_certificate=c['physical_certificate'],
                actors=template['actors'],sites=[dict(id=s['id'],name=s['name'],node=s['node'],actor_index=template['sites'][i]['actor_index']) for i,s in enumerate(sites)],
                cases=[dict(id='seasonal_actual',civilian_people=civil.tolist(),institutional_people=staff.tolist(),
                    total_people=total.tolist(),institutional_active=active.tolist(),community_viable=(civil>=50).tolist())],
                limits='Only reviewed cereal/cohort scenario. Parent affiliation retained;recruitment rights,roles,complete diet/work and political reach are not qualified by this export.')
            target=dest/(key+'.json.gz');target.write_bytes(gzip.compress(json.dumps(packet,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode(),mtime=0))
            summary[key]=dict(status=status,funded_cohorts=int(active.sum()),staff_people=float(staff.sum()),
                source_set_equals_published_annual=bool(np.array_equal(active,before)),changed_sources=changes,
                packet_sha256=sha(target),reach_rebuilt=False)
    (dest/'staffing.json').write_text(json.dumps(dict(status='reviewed_seasonal_staffing_inputs_not_reach_publication',
        producer_sha256=sha(Path(__file__)),seasonal_results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),
        parent_packets_sha256=parents,cases=summary,adopt=False,main_atlas_published=False),indent=2)+'\n')
    print('Exported16 actual civilian/cohort source packets; reach remains explicitly pending')


if __name__=='__main__':main()
