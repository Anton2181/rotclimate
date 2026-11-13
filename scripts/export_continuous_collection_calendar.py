"""Export complete calendar packets and all provider food/work comparisons."""
import argparse
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


def main(out=OUT):
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_continuous_collection_calendar.py')
    out.mkdir(parents=True,exist_ok=True);archives={};provider_rows=[]
    for case in r['cases']:
        key=case['key'];a=dict(np.load(OUT/key/'fields.npz'));archive=out/(key+'.zip')
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as z:
            for name,digest in case['files_sha256'].items():
                assert sha(OUT/name)==digest,name
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o644<<16;z.writestr(info,(OUT/name).read_bytes())
        archives[archive.name]=sha(archive)
        for account in 'ABC':
            names=[name.removeprefix(account+'__') for name in a if name.startswith(account+'__') and name!=account+'__no_shortage']
            for site in range(len(a['active'])):
                provider_rows.append(dict(case=key,accounting=account,provider=site,actor=int(a['actor'][site]),scored=bool(a['active'][site]),residents=float(a['residents'][site]),staff=float(a['staff'][site]),capacity=float(a['capacity'][site]),
                    mandatory_complete=bool(a['mandatory_complete'][site]),food_no_shortage=bool(a[account+'__no_shortage'][site]),mandatory_and_food=bool(a['mandatory_complete'][site]&a[account+'__no_shortage'][site]),
                    actual_worker_hours=float(a['worker_work_hours'][:,site].sum()),missing_destination_potential_kcal=float(a['missing_arrivals'][:,site].sum()),
                    **{name:float(a[account+'__'+name][site]) for name in names}))
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(provider_rows[0]));writer.writeheader();writer.writerows(provider_rows)
    (out/'providers.csv.gz').write_bytes(gzip.compress(buffer.getvalue().encode(),mtime=0))
    write(out/'exports.json',dict(status='exported_complete_new_collection_packets',results_sha256=sha(OUT/'results.json'),review_sha256=sha(OUT/'review.json'),
        producer_sha256=sha(Path(__file__)),files_sha256={**archives,'providers.csv.gz':sha(out/'providers.csv.gz')},provider_rows=len(provider_rows),
        note='Missing destination potential kcal is the counterfactual retained supply if unshipped raw cargo had been transported. Missing raw cargo stays separately identified at source;no actual transport loss is charged on it.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
