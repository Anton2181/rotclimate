"""Export complete new calendar archives and every provider/policy food result."""
import argparse,csv,gzip,io,json,sys,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/continuous_food_visit_calendars_20261112'

def main(out=OUT):
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    out.mkdir(parents=True,exist_ok=True);files={};records=[];selected=dict(np.load(OUT/'selected_fields.npz'))
    for case in r['cases']:
        key=case['key'];archive=out/(key+'.zip')
        with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as z:
            for name,digest in sorted(case['files_sha256'].items()):
                assert sha(OUT/name)==digest
                info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o644<<16;z.writestr(info,(OUT/name).read_bytes())
            info=zipfile.ZipInfo(key+'/case.json',date_time=(1980,1,1,0,0,0));info.create_system=3;info.external_attr=0o644<<16;z.writestr(info,(OUT/key/'case.json').read_bytes())
        files[archive.name]=sha(archive)
        mode=key.split('_')[0];hours=int(key.split('_h')[1].split('_')[0]);f=dict(np.load(ROOT/f'output/settlement_continuous_destination_20261112/{mode}_h{hours}_load120000_all_open/fields.npz'));x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'))
        for policy in ('baseline','joint','selected'):
            a=dict(np.load(OUT/key/policy/'fields.npz')) if policy!='selected' else {n.removeprefix(key+'__'):v for n,v in selected.items() if n.startswith(key+'__')}
            for account in ('ABC' if policy!='selected' else 'C'):
                food={n.removeprefix(account+'__'):v for n,v in a.items() if n.startswith(account+'__')} if policy!='selected' else {n.removeprefix('food_'):v for n,v in a.items() if n.startswith('food_')}
                for site in range(len(f['total'])):
                    mandatory=a['mandatory_complete'][site] if policy!='selected' else a['selected_mandatory_complete'][site]
                    record=dict(case=key,policy=policy,accounting=account,provider=site,actor=int(x['actor'][site]),scored=bool(f['active'][site]),residents=float(f['total'][site]),staff=float(f['staff'][site]),capacity=float(f['total'][site]*2500*90),mandatory_complete=bool(mandatory),food_no_shortage=bool(food['no_shortage'][site]),mandatory_and_food=bool(mandatory and food['no_shortage'][site]),selected_policy=int(selected[key+'__policy'][site]) if policy=='selected' else (policy=='joint')*1)
                    record.update({n:float(v[site]) for n,v in food.items() if n!='no_shortage'});records.append(record)
    b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=list(records[0]));w.writeheader();w.writerows(records);path=out/'providers.csv.gz';path.write_bytes(gzip.compress(b.getvalue().encode(),mtime=0));files[path.name]=sha(path)
    for kind in ('visit','food'):
        rows=[{k:v for k,v in row.items() if k!='actors'} for row in r[kind+'_rows']];columns=list(dict.fromkeys(k for row in rows for k in row));b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=columns);w.writeheader();w.writerows(rows);path=out/(kind+'_comparisons.csv');path.write_text(b.getvalue());files[path.name]=sha(path)
    write(out/'exports.json',dict(status='exported_all_calendars_and_provider_outcomes',results_sha256=sha(OUT/'results.json'),producer_sha256=sha(Path(__file__)),files_sha256=files,provider_rows=len(records),archives=8,scope='All active and explicitly unscored providers. Selected C uses one whole physical calendar and its OWN food;unshipped raw cargo stays at source.'))
    print('Exported',len(records),'provider outcomes and 8 complete calendar archives.')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
