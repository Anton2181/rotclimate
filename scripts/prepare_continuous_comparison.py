"""Retain every parent/new provider and actor in the declared comparison."""
import argparse
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
PARENT=ROOT/'output/settlement_dispatch_seeded_20261112'
FOOD=['initial_stock','final_stock','peak_stock','harvested','needed','consumed','unmet','spoiled','overflow','shortfall_days','ledger_residual','periodic_residual']


def main(out=OUT):
    summary=json.loads((OUT/'summary.json').read_text());rows=[];providers=[];sources={}
    for case in summary['rows']:
        key=case['key'];x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{case["climate"]}_inputs.npz'))
        sources[str((ROOT/f'output/settlement_feedback_20261112/{case["climate"]}_inputs.npz').relative_to(ROOT))]=sha(ROOT/f'output/settlement_feedback_20261112/{case["climate"]}_inputs.npz')
        for account,folder in [('parent',PARENT/key),('continuous',OUT/key)]:
            result=json.loads((folder/'results.json').read_text());review=json.loads((folder/'review.json').read_text());f=dict(np.load(folder/'fields.npz'))
            assert review['status']=='passed' and review['results_sha256']==sha(folder/'results.json') and result['fields_sha256']==sha(folder/'fields.npz')
            reviewer=ROOT/('scripts/review_continuous_destination.py' if account=='continuous' else 'scripts/review_seeded_dispatch.py')
            assert review['reviewer_sha256']==sha(reviewer)
            for name,digest in {**result['sources'],**result['producers']}.items():assert sha(ROOT/name)==digest,name
            for p in [folder/'results.json',folder/'review.json',folder/'fields.npz',reviewer]:sources[str(p.relative_to(ROOT))]=sha(p)
            def statistics(mask):
                return dict(providers=int(mask.sum()),positive_sites=int((mask & (f['total']>0)).sum()),active_sources=int((mask & f['active']).sum()),
                    town_people=float(f['total'][mask].sum()),civilian_people=float(f['civilian'][mask].sum()),staff_people=float(f['staff'][mask].sum()),
                    collection_hours=float(f['work_required_collection_hours'][:,mask].sum()),gross_staff_hours=float(f['work_gross_hours'][:,mask].sum()),
                    **{'town_'+name:float(f['town_'+name][mask].sum()) for name in FOOD if 'town_'+name in f})
            rows.append(dict(key=key,climate=case['climate'],hours_worker_year=case['hours_worker_year'],accounting=account,
                **statistics(np.ones(len(f['total']),bool)),actors=[dict(actor_index=a,**statistics(x['actor']==a)) for a in range(18)]))
            for site in range(len(f['total'])):
                providers.append(dict(case=key,accounting=account,provider=site,actor=int(x['actor'][site]),total=float(f['total'][site]),civilian=float(f['civilian'][site]),staff=float(f['staff'][site]),
                    active=bool(f['active'][site]),source_supported=bool(f['source_supported'][site]),
                    collection_hours=float(f['work_required_collection_hours'][:,site].sum()),gross_staff_hours=float(f['work_gross_hours'][:,site].sum()),
                    **{'town_'+name:float(f['town_'+name][site]) if 'town_'+name in f else None for name in FOOD}))
    out.mkdir(parents=True,exist_ok=True);buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(providers[0]));writer.writeheader();writer.writerows(providers)
    (out/'providers.csv.gz').write_bytes(gzip.compress(buffer.getvalue().encode(),mtime=0))
    write(out/'comparison.json',dict(status='all_four_parents_and_four_continuous_replans',adopt=False,rows=rows,sources=sources,
        producers={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},providers_sha256=sha(out/'providers.csv.gz'),
        scope='Destination bin-start continuous food inside the finite source/work ledger. Collector-return food remains unqualified;no maps/defaults changed. Old unrecorded peak/duration/periodic fields stay null.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
