"""Check new pilot selection/design atop the pinned, unchanged Roman geometry."""
import csv
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from scipy.linalg import qr

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_release2_earth as R

OUT=ROOT/'output/urban_measurement_pilot_20261116'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    rep=json.loads((OUT/'eligibility.json').read_text())
    for name,digest in {**rep['sources_sha256'],**rep['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    assert sha(OUT/'design.npz')==rep['files_sha256']['design.npz']
    # Reuse the previously reviewed unchanged geometry only. New selection,
    # wall corrections, capitals and province encoding are independently built.
    old,_,_=R.cohort();old=[r for r in old if r['area']!=20 and r['area']!=30]
    with (R.CACHE/'areas.csv').open(encoding='utf-8-sig') as f:raw={row[0]:(float(row[1]),row[2]) for row in list(csv.reader(f))[1:]}
    with (R.CACHE/'cities.csv').open(encoding='cp1252') as f:cities={r['Primary Key']:r for r in csv.DictReader(f)}
    cap_source=json.loads((ROOT/'output/capital_effect_20261115/results.json').read_text())
    capitals={(r['town'],r['province']) for r in cap_source['matched']}
    province_names=sorted({r['province'] for r in old})
    expected={k:[] for k in ['area','lnH','capital','strict','fold','province']}
    for r in old:
        a,basis=raw[r['key']];assert a==r['area']
        if r['province'] in ['Achaea','Macedonia','Epirus'] and basis.startswith('Walls'):a=a/3 if a>=100 else a/2
        expected['area'].append(a);expected['lnH'].append(r['lnH']);expected['strict'].append(basis=='Inhabited area')
        expected['capital'].append((cities[r['key']]['Ancient Toponym'],r['province']) in capitals)
        expected['fold'].append(int(hashlib.sha256(r['province'].encode()).hexdigest()[:2],16)%4)
        expected['province'].append(province_names.index(r['province']))
    with np.load(OUT/'design.npz') as z:actual={k:z[k] for k in z.files}
    assert set(expected)==set(actual)
    for key,values in expected.items():np.testing.assert_allclose(actual[key],values,rtol=1e-14,atol=1e-12)
    fold=actual['fold'];strict=actual['strict'];capital=actual['capital'];province=actual['province']
    assert rep['mixed_rows']==len(old)==664 and rep['strict_rows']==int(sum(strict))==153
    assert rep['strict_fold_rows']==[int(sum(strict & (fold==f))) for f in range(4)]==[43,43,31,36]
    assert rep['strict_provinces']==len(set(province[strict]))==40 and rep['strict_capitals']==int(sum(capital[strict]))==4
    seen=set()
    for row in rep['support']:
        outer,cohort,inner=row['outer'],row['training_cohort'],row['inner_heldout'];key=outer,cohort,inner
        assert key not in seen;seen.add(key)
        tr=(fold!=outer) & (strict if cohort=='strict' else True)
        if inner is not None:assert inner!=outer;tr &= fold!=inner
        assert row['training_rows']==int(sum(tr))>=10
        assert row['training_provinces']==len(set(province[tr]))
        assert row['training_capitals']==int(sum(capital[tr]))
        assert row['strict_outer_test_rows']==int(sum(strict & (fold==outer)))>=10
        X=np.column_stack([np.ones(sum(tr)),actual['lnH'][tr],capital[tr]])
        for model,p in [('M0',1),('M1',2),('M1C',3)]:
            _,upper,_=qr(X[:,:p],pivoting=True,mode='economic')
            rank=sum(abs(np.diag(upper))>1e-9)
            assert row['ranks'][model]==rank==p
    expected_keys={(f,c,i) for f in range(4) for c in ['mixed','strict'] for i in [None]+[g for g in range(4) if g!=f]}
    assert seen==expected_keys and len(seen)==32
    assert rep['support_gate_passed'] and rep['failures']==[] and not rep['fit_performed'] and not rep['new_scores'] and not rep['adopt']
    fresh={}
    for name in ['eligibility.json','design.npz']:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes();fresh[name]=sha(OUT/name)
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),eligibility_sha256=sha(OUT/'eligibility.json'),
                method='Pinned unchanged previously reviewed release2 geometry reused,not a new independent geometry check. Separate raw-source joins,exact basis filter,scalar wall corrections/capital matches/hexadecimal folds/design checks; QR ranks independent of producer rank routine.',
                rows=664,strict_rows=153,support_splits=32,support_gate_passed=True,fresh_byte_exact=fresh,fit_performed=False)
    (OUT/'support_review.json').write_text(json.dumps(report,indent=2)+'\n');print('Reviewed 664 anonymous design rows;153 strict,32 support splits;eligible before fitting')


if __name__=='__main__':main()
