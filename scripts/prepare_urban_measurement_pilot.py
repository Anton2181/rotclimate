"""Freeze source-basis pilot eligibility and anonymous design BEFORE fitting."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_hierarchy as SH

OUT=ROOT/'output/urban_measurement_pilot_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/measurement_basis_pilot.json'
AUDIT=ROOT/'output/urban_development_evidence_20261116'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    plan=json.loads(PLAN.read_text());prior=json.loads((AUDIT/'results.json').read_text());review=json.loads((AUDIT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(AUDIT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_development_evidence.py')
    for name,digest in {**prior['sources_sha256'],**prior['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in prior['files_sha256'].items():assert sha(AUDIT/name)==digest,name
    rows,_,_,capital=SH.cohort()
    basis={a['Primary Key']:a['Estimate Basis'] for a in csv.DictReader(io.StringIO((SH.R.CACHE/'areas.csv').read_bytes().decode('utf-8-sig')))}
    strict=np.array([basis[r['key']]=='Inhabited area' for r in rows]);fold=np.array([SH.Z.province_fold(r['province']) for r in rows])
    provinces=sorted({r['province'] for r in rows});province=np.array([provinces.index(r['province']) for r in rows])
    assert len(rows)==664 and [int((fold==f).sum()) for f in range(4)]==[208,182,144,130]
    arrays=dict(area=np.array([r['area'] for r in rows]),lnH=np.array([r['lnH'] for r in rows]),capital=capital,strict=strict,fold=fold,province=province)
    X=np.column_stack([np.ones(len(rows)),arrays['lnH'],capital.astype(float)])
    support=[];failures=[]
    for outer in range(4):
        test=strict & (fold==outer)
        if test.sum()<10:failures.append(f'outer{outer}:strict test fewer than10')
        for name,eligible in [('mixed',np.ones(len(rows),bool)),('strict',strict)]:
            for inner in [None]+[f for f in range(4) if f!=outer]:
                training=eligible & (fold!=outer)
                if inner is not None:training &= fold!=inner
                ranks={model:int(np.linalg.matrix_rank(X[training,:len(terms)])) for model,terms in plan['models'].items()}
                record=dict(outer=outer,training_cohort=name,inner_heldout=inner,training_rows=int(training.sum()),training_provinces=len(np.unique(province[training])),training_capitals=int(capital[training].sum()),strict_outer_test_rows=int(test.sum()),ranks=ranks)
                support.append(record)
                if training.sum()<10:failures.append(f'{outer}/{name}/{inner}:training fewer than10')
                for model,terms in plan['models'].items():
                    if ranks[model]!=len(terms):failures.append(f'{outer}/{name}/{inner}:{model} rank deficient')
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'design.npz',**arrays)
    paths=[Path(__file__),PLAN,ROOT/'scripts/settlement_hierarchy.py',ROOT/'scripts/settlement_release2_earth.py',
           ROOT/'polity/settlement_sizes.py',ROOT/'rotclimate/earth.py',SH.CAP,SH.R.POOLS/'rome_inputs.npz',SH.R.CORE/'rome_history.npz']
    protected=dict(prior['protected_sha256']);protected.update(prior['sources_sha256'])
    for name in ['results.json','aggregates.csv','review.json']:protected[str((AUDIT/name).relative_to(ROOT))]=sha(AUDIT/name)
    result=dict(status='support_prepared_before_fit',support_gate_passed=not failures,failures=failures,
                mixed_rows=len(rows),strict_rows=int(strict.sum()),strict_fold_rows=[int((strict & (fold==f)).sum()) for f in range(4)],
                strict_provinces=len(np.unique(province[strict])),strict_capitals=int(capital[strict].sum()),support=support,
                sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=protected,
                files_sha256={'design.npz':sha(out/'design.npz')},fit_performed=False,new_scores=False,adopt=False,
                scope='Anonymous derived design only; no source identities or coordinates. Geometry and corrected areas replay existing source-defined cohort. No mean coefficients or predictive sigma estimated.')
    (out/'eligibility.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:result[k] for k in ['support_gate_passed','failures','mixed_rows','strict_rows','strict_fold_rows','strict_provinces','strict_capitals']},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
