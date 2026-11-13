"""Export all origin/provider source ledgers;full pickup IDs stay in NPZ fields."""
import argparse,csv,gzip,io,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/source_food_events_20261113'

def main(out=OUT):
    out.mkdir(parents=True,exist_ok=True);r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json');files={};counts={}
    for kind in ('origins','providers'):
        b=io.StringIO(newline='');writer=None;count=0
        for row in r['rows']:
            f=dict(np.load(OUT/(row['case']+'_fields.npz')))
            if kind=='origins':
                columns=['origin_grid_node','owner','actor','people','produced','harvest_bin','rural_capacity','export_capacity','rural_food_pass','export_request_pass','both_pass','uncollected','total_ledger_residual']+[n for n in f if n.startswith(('rural__','export__'))];size=len(f['people'])
            else:columns=['provider_active','provider_actor']+[n for n in f if n.startswith('provider__')];size=len(f['provider_active'])
            if writer is None:writer=csv.writer(b);writer.writerow(['case','index',*columns])
            for j in range(size):writer.writerow([row['case'],j,*[f[n][j].item() for n in columns]]);count+=1
        path=out/(kind+'.csv.gz');path.write_bytes(gzip.compress(b.getvalue().encode(),mtime=0));files[path.name]=sha(path);counts[kind]=count
    write(out/'exports.json',dict(status='exported_all_origin_and_provider_source_ledgers',results_sha256=sha(OUT/'results.json'),producer_sha256=sha(Path(__file__)),files_sha256=files,rows=counts,full_pickup_fields=r['files_sha256'],scope='Raw requested,withdrawn and unfilled source cargo. These fixed diagnostics retain rural food failures;no actual destination replacement or transport retention at source.'))
    print('Exportedsource origin/provider rows',counts)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
