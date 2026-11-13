"""Check every archived byte,provider CSV field and typed comparison row."""
import csv,gzip,io,json,sys,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/continuous_food_visit_calendars_20261112'

def main():
    r=json.loads((OUT/'results.json').read_text());e=json.loads((OUT/'exports.json').read_text());assert e['results_sha256']==sha(OUT/'results.json') and e['producer_sha256']==sha(ROOT/'scripts/export_food_visit_calendars.py')
    for name,digest in e['files_sha256'].items():assert sha(OUT/name)==digest
    records=list(csv.DictReader(io.StringIO(gzip.decompress((OUT/'providers.csv.gz').read_bytes()).decode())));index={(v['case'],v['policy'],v['accounting'],int(v['provider'])):v for v in records};assert len(index)==len(records)==e['provider_rows'];entries=checked=0;S=dict(np.load(OUT/'selected_fields.npz'))
    for case in r['cases']:
        key=case['key'];expected={**case['files_sha256'],key+'/case.json':sha(OUT/key/'case.json')}
        with zipfile.ZipFile(OUT/(key+'.zip')) as z:
            assert set(z.namelist())==set(expected)
            for name in expected:assert z.read(name)==(OUT/name).read_bytes();entries+=1
        mode=key.split('_')[0];hours=int(key.split('_h')[1].split('_')[0]);f=dict(np.load(ROOT/f'output/settlement_continuous_destination_20261112/{mode}_h{hours}_load120000_all_open/fields.npz'));x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'))
        for policy in ('baseline','joint','selected'):
            a=dict(np.load(OUT/key/policy/'fields.npz')) if policy!='selected' else {n.removeprefix(key+'__'):v for n,v in S.items() if n.startswith(key+'__')}
            for account in ('ABC' if policy!='selected' else 'C'):
                for site in range(len(f['total'])):
                    v=index.pop((key,policy,account,site));mandatory=bool(a['selected_mandatory_complete' if policy=='selected' else 'mandatory_complete'][site]);food={n.removeprefix('food_' if policy=='selected' else account+'__'):q[site] for n,q in a.items() if n.startswith('food_' if policy=='selected' else account+'__')}
                    expected_fields=dict(actor=int(x['actor'][site]),scored=bool(f['active'][site]),residents=float(f['total'][site]),staff=float(f['staff'][site]),capacity=float(f['total'][site]*2500*90),mandatory_complete=mandatory,food_no_shortage=bool(food['no_shortage']),mandatory_and_food=bool(mandatory and food['no_shortage']),selected_policy=int(S[key+'__policy'][site]) if policy=='selected' else int(policy=='joint'))
                    expected_fields.update({n:float(q) for n,q in food.items() if n!='no_shortage'})
                    for n,q in expected_fields.items():assert (v[n]==str(q) if isinstance(q,bool) else float(v[n])==q),(key,n)
                    assert set(v)==set(expected_fields)|{'case','policy','accounting','provider'};checked+=1
    assert not index
    for kind in ('visit','food'):
        rows=list(csv.DictReader((OUT/(kind+'_comparisons.csv')).open()));assert len(rows)==len(r[kind+'_rows'])
        for v,q in zip(rows,r[kind+'_rows']):
            for n in v:assert v[n]==('' if q.get(n) is None else str(q[n]))
    write(OUT/'download_review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),exports_sha256=sha(OUT/'exports.json'),reviewer_sha256=sha(Path(__file__)),archive_entries_checked=entries,provider_rows_checked=checked,comparison_rows_checked=80,all_inactive_rows_explicit=True))
    print('Download review passed',entries,'archived packets,',checked,'provider outcomes,80 comparison rows.')
if __name__=='__main__':main()
