"""Check every origin/provider CSV value against independently reviewed fields."""
import csv,gzip,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_food_events_20261113'

def main():
    e=json.loads((OUT/'exports.json').read_text());r=json.loads((OUT/'results.json').read_text());assert e['results_sha256']==sha(OUT/'results.json') and e['producer_sha256']==sha(ROOT/'scripts/export_source_pickup_calendars.py');counts={}
    for n,d in e['files_sha256'].items():assert sha(OUT/n)==d
    for kind in ('origins','providers'):
        previous=None;count=0;seen={}
        with gzip.open(OUT/(kind+'.csv.gz'),'rt',newline='') as stream:
            for v in csv.DictReader(stream):
                case=v['case'];j=int(v['index'])
                if case!=previous:
                    assert case not in seen and case in {v['case'] for v in r['rows']};seen[case]=0;previous=case
                    z=np.load(OUT/(case+'_fields.npz'));fields={n:z[n] for n in v if n not in ('case','index')};z.close()
                assert j==seen[case];seen[case]+=1
                for name,array in fields.items():
                    value=array[j].item()
                    if isinstance(value,bool):assert v[name]==str(value)
                    else:assert float(v[name])==value,(case,j,name)
                count+=1
        assert len(seen)==24 and count==e['rows'][kind];counts[kind]=count
        for case,n in seen.items():
            with np.load(OUT/(case+'_fields.npz')) as z:assert n==len(z['people' if kind=='origins' else 'provider_active'])
    write(OUT/'export_review.json',dict(status='passed',exports_sha256=sha(OUT/'exports.json'),results_sha256=sha(OUT/'results.json'),reviewer_sha256=sha(Path(__file__)),all_csv_fields_and_rows_checked=counts,all24plans_retained=True,full_pickup_fields_independently_reviewed=True));print('Independent source CSVreview passed',counts)
if __name__=='__main__':main()
