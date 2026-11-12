"""Independently check all eight comparison rows and every actor/provider export."""
import csv
import gzip
import io
import json
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/settlement_continuous_destination_20261112'


def main():
    r=json.loads((OUT/'comparison.json').read_text());assert sha(OUT/'providers.csv.gz')==r['providers_sha256']
    for name,digest in {**r['sources'],**r['producers']}.items():assert sha(ROOT/name)==digest,name
    providers=list(csv.DictReader(io.StringIO(gzip.decompress((OUT/'providers.csv.gz').read_bytes()).decode())));index={(v['case'],v['accounting'],int(v['provider'])):v for v in providers};assert len(index)==len(providers)
    actors=0
    for row in r['rows']:
        key=row['key'];folder=(OUT if row['accounting']=='continuous' else ROOT/'output/settlement_dispatch_seeded_20261112')/key
        f=dict(np.load(folder/'fields.npz'));x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{row["climate"]}_inputs.npz'));n=len(f['total'])
        for actor in [None,*range(18)]:
            mask=np.ones(n,bool) if actor is None else x['actor']==actor;s=row if actor is None else row['actors'][actor]
            assert s['providers']==int(mask.sum()) and s['active_sources']==int((mask & f['active']).sum()) and s['positive_sites']==int((mask & (f['total']>0)).sum())
            for name,field in [('town_people','total'),('civilian_people','civilian'),('staff_people','staff')]:assert s[name]==float(f[field][mask].sum())
            for name,field in [('collection_hours','work_required_collection_hours'),('gross_staff_hours','work_gross_hours')]:assert s[name]==float(f[field][:,mask].sum())
            for name in s:
                if name.startswith('town_') and name!='town_people':assert s[name]==float(f[name][mask].sum())
            if actor is not None:actors+=1
        for site in range(n):
            v=index.pop((key,row['accounting'],site));assert int(v['actor'])==x['actor'][site]
            for field in ('total','civilian','staff'):assert float(v[field])==f[field][site]
            for field in ('active','source_supported'):assert v[field]==str(bool(f[field][site]))
            for name,field in [('collection_hours','work_required_collection_hours'),('gross_staff_hours','work_gross_hours')]:assert float(v[name])==f[field][:,site].sum()
            for name,value in v.items():
                if name.startswith('town_'):
                    if name in f:assert float(value)==f[name][site]
                    else:assert value==''
    assert not index and len(r['rows'])==8
    write(OUT/'comparison_review.json',dict(status='passed',comparison_sha256=sha(OUT/'comparison.json'),providers_sha256=sha(OUT/'providers.csv.gz'),reviewer_sha256=sha(Path(__file__)),
        rows_checked=8,actor_summaries_checked=actors,provider_records_checked=len(providers),all_original_fields_and_nulls_exact=True))
    print('Eightcomparison rows,all144actor summaries and',len(providers),'provider records passed.')


if __name__=='__main__':main()
