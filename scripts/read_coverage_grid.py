"""Read one cell from a downloaded coverage.json and its coverage.bin.gz.

NumPy is needed only for this scientific reader; the atlas server remains
standard-library only. Preserve the packet's raw/corrected folder structure.
"""
from pathlib import Path
import argparse
import gzip
import hashlib
import json


def main():
    import numpy as np
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('metadata',type=Path);parser.add_argument('--climate',choices=['raw','corrected'],required=True)
    parser.add_argument('--row',type=int,required=True);parser.add_argument('--column',type=int,required=True)
    parser.add_argument('--budget',type=int,choices=[1,2,4],default=2);args=parser.parse_args()
    p=json.loads(args.metadata.read_text())['packets'][args.climate]
    compressed=(args.metadata.parent/p['binary']).read_bytes()
    if hashlib.sha256(compressed).hexdigest()!=p['binary_sha256']:raise ValueError('Coverage checksum changed')
    raw=gzip.decompress(compressed)
    if len(raw)!=p['raw_bytes']:raise ValueError('Invalid coverage length')
    h,w=p['shape'];n=p['land_cells'];k=len(p['actors'])
    if not 0<=args.row<h or not 0<=args.column<w:raise ValueError('Point outside grid')
    lookup=np.frombuffer(raw,'<u4',count=h*w).reshape(h,w);index=int(lookup[args.row,args.column])-1
    if index<0:raise ValueError('Selected cell is outside the travel land grid')
    words=np.frombuffer(raw,'<u4',count=3*k*2*n,offset=p['offsets']['words']).reshape(3,k,2,n)
    b=p['budgets_days'].index(args.budget)
    def bins(word):return sum(((int(word)>>(2*m))&3)>=3-b for m in range(12))
    rows=[]
    for s,scenario in enumerate(p['scenarios']):
        for a,actor in enumerate(p['actors']):
            count=actor['source_counts'][s]
            rows.append(dict(scenario=scenario,actor=actor['name'],sources=count,
                status='conditional_site_access' if count else 'missing_source_inventory',
                outward_bins=bins(words[s,a,0,index]) if count else None,
                same_site_two_way_bins=bins(words[s,a,1,index]) if count else None))
    print(json.dumps(dict(climate=args.climate,row=args.row,column=args.column,per_leg_days=args.budget,records=rows),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
