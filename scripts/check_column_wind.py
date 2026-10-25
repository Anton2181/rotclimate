"""Separate the existing column-wind hypothesis from the terrain replacement."""
from dataclasses import asdict
from pathlib import Path
from multiprocessing import Pool
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from check_terrain_quadrature import run_one
from earth_benchmark import load_params
from local_benchmark_protocol import file_hash,freeze,write_json
from experiments.terrain_quadrature import reference_terrain
from benchmark_local import DEV12_SPECS
from rotclimate import earth


def compare(ref,candidate):
    if any(r['status']!='passed' for r in candidate):return dict(passed=False,failures=['Numerical failure'])
    rr={r['region']:r for r in ref};cc={r['region']:r for r in candidate}
    if set(rr)!=set(cc) or any(rr[n]['case_identity']!=cc[n]['case_identity'] for n in rr):raise ValueError('Unpaired cases')
    avg=lambda rows,part,key:float(np.mean([r[part][key] for r in rows]))
    t=avg(candidate,'temperature','monthly_mae_C')/avg(ref,'temperature','monthly_mae_C')
    p=avg(candidate,'rain','loss')/avg(ref,'rain','loss')
    regional={n:.5*cc[n]['temperature']['monthly_mae_C']/rr[n]['temperature']['monthly_mae_C']+
                .5*cc[n]['rain']['loss']/rr[n]['rain']['loss'] for n in rr}
    failures=[];s=.5*(t+p)
    if s>.995:failures.append('S exceeds 0.995')
    if t>1.01:failures.append('Temperature ratio exceeds 1.01')
    failures.extend(n+': regional S exceeds 1.05' for n,value in regional.items() if value>1.05)
    a,b=cc['north_india']['diagnosis'],rr['north_india']['diagnosis']
    if a['july_lowland_mae_mm']>=b['july_lowland_mae_mm']:failures.append('Foothill July MAE did not decrease')
    if a['annual_plateau_mae_mm']>b['annual_plateau_mae_mm']:failures.append('Plateau annual MAE increased')
    return dict(passed=not failures,failures=failures,S=s,T_ratio=t,P_ratio=p,regions=regional)


def main():
    plan_path=ROOT/'calibration/column_wind_20261025/plan.json';plan=json.loads(plan_path.read_text())
    out=ROOT/'output/column_wind_20261025';out.mkdir(exist_ok=True)
    parent=ROOT/'output/terrain_quadrature_20261025';protocol=json.loads((parent/'protocol.json').read_text())
    base=load_params(ROOT/plan['reference']);normalized=json.loads(json.dumps(asdict(base)))
    if normalized!=protocol['params']:raise ValueError('Different reference parameters')
    for name,expected in protocol['sources'].items():
        if file_hash(ROOT/name)!=expected:raise ValueError('Reference source has changed: '+name)
    refs=[];evidence=[parent/'protocol.json']
    for km in [56,28]:
        for name in plan['regions']:
            record=parent/'cases'/f'{name}_{km:g}km/reference.json';row=json.loads(record.read_text())
            cells=record.with_suffix('.npz')
            if row['status']!='passed' or file_hash(cells)!=row['cells_sha256']:raise ValueError('Invalid reference')
            refs.append(row);evidence.extend([record,cells])
    identity=freeze(out/'protocol.json',dict(plan=plan,parent_protocol=protocol,
        evidence_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in evidence},
        sources_sha256={str(p.relative_to(ROOT)):file_hash(p) for p in [plan_path,Path(__file__)]}))
    earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    for name in plan['regions']:reference_terrain(name)
    records=[];reviews={};selected=None;fine=None
    with Pool(2) as pool:
        for factor in plan['factors']:
            label=f'wind_{factor:g}';jobs=[(n,56,label,dict(moisture_wind_factor=factor),asdict(base),identity,str(out)) for n in plan['regions']]
            results=[]
            for row in pool.imap_unordered(run_one,jobs):
                results.append(row);records.append(row)
                write_json(out/'progress.json',dict(complete=False,records=records))
            reviews[label]=compare([r for r in refs if r['cell_km']==56],results)
        eligible=[label for label,row in reviews.items() if row['passed']]
        if eligible:
            selected=min(eligible,key=lambda label:reviews[label]['S']);factor=float(selected.removeprefix('wind_'))
            jobs=[(n,28,selected,dict(moisture_wind_factor=factor),asdict(base),identity,str(out)) for n in plan['regions']]
            results=list(pool.imap_unordered(run_one,jobs));records+=results
            fine=compare([r for r in refs if r['cell_km']==28],results)
            fine['passed']=not any(r['status']!='passed' for r in results) and fine.get('S',float('inf'))<=1.01
            fine['note']='Fine screen uses S <= 1.01 and observed convergence; coarse diagnostics are reported only.'
    review=dict(complete=True,identity=identity,coarse=reviews,selected_for_fine=selected,fine=fine,
        passes_pilot=bool(selected and fine['passed']),records=records,reference_records=refs,
        decision='Prepare full fresh gate; no adoption yet.' if selected and fine['passed'] else 'Retain r38; no pilot candidate qualifies.')
    write_json(out/'review.json',review);write_json(out/'progress.json',dict(complete=True,records=records))
    print(json.dumps({k:v for k,v in review.items() if k not in ['records','reference_records']},indent=2),flush=True)


if __name__=='__main__':main()
