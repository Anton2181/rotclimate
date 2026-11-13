"""Check every archive entry and every provider/scored/food/work export."""
import csv
import gzip
import io
import json
from pathlib import Path
import sys
import zipfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/continuous_collection_calendar_20261112'


def main():
    r=json.loads((OUT/'results.json').read_text());export=json.loads((OUT/'exports.json').read_text());assert export['results_sha256']==sha(OUT/'results.json') and export['review_sha256']==sha(OUT/'review.json')
    assert export['producer_sha256']==sha(ROOT/'scripts/export_continuous_collection_calendar.py')
    for name,digest in export['files_sha256'].items():assert sha(OUT/name)==digest,name
    rows=list(csv.DictReader(io.StringIO(gzip.decompress((OUT/'providers.csv.gz').read_bytes()).decode())));index={(v['case'],v['accounting'],int(v['provider'])):v for v in rows};assert len(rows)==len(index)==export['provider_rows'];entries=0
    for case in r['cases']:
        key=case['key'];a=dict(np.load(OUT/key/'fields.npz'))
        with zipfile.ZipFile(OUT/(key+'.zip')) as z:
            assert z.namelist()==list(case['files_sha256'])
            for name in z.namelist():assert z.read(name)==(OUT/name).read_bytes();entries+=1
        for account in 'ABC':
            for site in range(len(a['active'])):
                v=index.pop((key,account,site));assert int(v['actor'])==a['actor'][site]
                for csv_name,field in [('scored','active'),('mandatory_complete','mandatory_complete'),('food_no_shortage',account+'__no_shortage')]:assert v[csv_name]==str(bool(a[field][site]))
                assert v['mandatory_and_food']==str(bool(a['mandatory_complete'][site]&a[account+'__no_shortage'][site]))
                for field in ('residents','staff','capacity'):assert float(v[field])==a[field][site]
                assert float(v['actual_worker_hours'])==a['worker_work_hours'][:,site].sum() and float(v['missing_destination_potential_kcal'])==a['missing_arrivals'][:,site].sum()
                for field in a:
                    if field.startswith(account+'__') and field!=account+'__no_shortage':assert float(v[field.removeprefix(account+'__')])==a[field][site]
    assert not index
    write(OUT/'export_review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),exports_sha256=sha(OUT/'exports.json'),reviewer_sha256=sha(Path(__file__)),
        archive_entries_byte_exact=entries,provider_rows_checked=len(rows),all_scored_and_unscored_flags_preserved=True,all_food_work_fields_exact=True))
    print('All',entries,'archive entries and',len(rows),'provider records checked.')


if __name__=='__main__':main()
