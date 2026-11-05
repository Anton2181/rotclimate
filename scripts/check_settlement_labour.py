"""Independent cell audit and exact preservation of the six earlier cases."""
from pathlib import Path
import argparse
import gzip
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();reviews=[]
    origin=ROOT/'output/settlement_labour_20261105';baseline=ROOT/'output/settlement_integration_20261104'
    for new in sorted(origin.glob('*/review.json')):
        folder=new.parent;review=json.loads(new.read_text());old=baseline/folder.name;prior=json.loads((old/'review.json').read_text())
        m=json.loads(gzip.decompress((folder/'settled_reach.json.gz').read_bytes()));b=json.loads(gzip.decompress((old/'settled_reach.json.gz').read_bytes()));ls=m['labour_specification'];spec=m['specification']
        assert m['cases'][:len(b['cases'])]==b['cases'] and m['summaries'][:len(b['summaries'])]==b['summaries']
        raw=gzip.decompress((folder/'settled_reach.bin.gz').read_bytes());before=gzip.decompress((old/'settled_reach.bin.gz').read_bytes());offset=prior['offsets']['masks']
        assert raw[:len(before)]==before
        masks=np.frombuffer(raw,'<u2',offset=offset).reshape(review['masks_shape']);cells=0
        with np.load(folder/'field_support.npz') as f:
            annual=f['reference_production_kcal'];need=f['fixed_rural_need_kcal'];hours=f['listed_hours_per_million'];reap=f['reaping_hours_per_million'];workers=need/(spec['ration_kcal_person_day']*spec['year_days'])*ls['worker_fraction_of_reference_rural_people']
            np.testing.assert_allclose(need,annual*spec['rural_demand_fraction_of_cereal_production'])
            for c in m['cases'][len(b['cases']):]:
                key=c['id']+'_';fraction=f[key+'retained'];produced=f[key+'produced_kcal'];year_available=workers*c['hours_worker_year'];peak_available=np.minimum(year_available,workers*ls['hours_worker_day']*c['harvest_days'])
                # Direct algebraic upper bounds, rather than calling the field
                # allocation or seasonal-food solver again.
                np.testing.assert_allclose(produced,annual*fraction)
                np.testing.assert_allclose(f[key+'annual_hours_used'],produced*hours/1e6)
                np.testing.assert_allclose(f[key+'reaping_hours_used'],produced*reap/1e6)
                assert np.all(f[key+'annual_hours_used']<=year_available+1e-7)
                assert np.all(f[key+'reaping_hours_used']<=peak_available+1e-7)
                assert np.all(produced<=annual+1e-7) and np.all(fraction>=0)
                assert np.all(f[key+'exportable_kcal'][f[key+'rural_unmet_kcal']>1e-8*np.maximum(need,1)]==0)
                r=c['rural_ledger'];w=c['work_summary']
                assert np.isclose(r['fixed_need_kcal'],need.sum()) and np.isclose(r['harvested_kcal'],produced.sum())
                assert np.isclose(w['production_retained'],produced.sum()/annual.sum())
                i=next(i for i,v in enumerate(m['cases']) if v['id']==c['id']);assert not np.any(masks[i]&~masks[1])
                cells+=len(annual)
            generous=f['work600_30_retained']
            for k in ['work600_10','work300_30']:assert np.all(f[k+'_retained']<=generous+1e-12)
        reviews.append(dict(packet=folder.name,cells_by_cases=cells,old_cases_and_masks_identical=True,work_bounds_hold=True,rural_claim_fixed=True,no_export_from_deficit=True))
    assert len(reviews)==4
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(dict(status='passed',reviews=reviews),indent=2)+'\n');print(json.dumps(reviews,indent=2))


if __name__=='__main__':main()
