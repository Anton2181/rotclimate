"""Run the frozen common-terrain closure pilot with paired verified controls."""
from dataclasses import asdict
from pathlib import Path
from multiprocessing import Pool
import importlib.metadata
import json
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
import numpy as np
from benchmark_local import DEV12_SPECS,temperature_metrics
from earth_benchmark import load_params
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json
from rainfall_metrics import local_metrics
from experiments.terrain_quadrature import prepare_case,reference_terrain
from rotclimate import earth
from rotclimate.config import Params
from rotclimate.koppen import monthly_stats


def run_one(job):
    name,km,scheme,changes,base,identity,out=job;started=time.monotonic();out=Path(out)
    folder=out/'cases'/f'{name}_{km:g}km';folder.mkdir(parents=True,exist_ok=True)
    record=folder/(scheme+'.json');cells=folder/(scheme+'.npz')
    case=prepare_case(earth.region_case(name,km));g=case.grid;case_id=case_hash(case)
    if record.exists():
        previous=json.loads(record.read_text())
        if previous['identity']!=identity or previous['case_identity']!=case_id:raise ValueError('Changed saved inputs')
        if previous['status']!='passed':raise ValueError('Saved failure needs diagnosis, not an unchanged rerun')
        if file_hash(cells)!=previous['cells_sha256']:raise ValueError('Changed saved cell fields')
        return previous
    row=dict(region=name,cell_km=km,scheme=scheme,identity=identity,case_identity=case_id)
    try:
        p=Params(**base).replace(**changes)
        result=earth.run_case(p,case,steps=p.steps_per_year)
        if result.numerics.get('all_checks_passed') is not True:raise ValueError('Observed numerical checks failed')
        st=monthly_stats(result.T,result.P,result.days,result.params.year_days,
            summer_solstice=result.params.winter_solstice_day+result.params.year_days/2)
        mask=g.inmap&g.land&np.isfinite(case.obs_T).all(0)&np.isfinite(case.obs_P).all(0)
        arrays=dict(Ts=st['Tm'][:,mask].astype(np.float32),Ps=st['Pm'][:,mask].astype(np.float32),
                    To=case.obs_T[:,mask].astype(np.float32),Po=case.obs_P[:,mask].astype(np.float32),
                    elev=g.elev[mask],i=np.where(mask)[0],j=np.where(mask)[1])
        if scheme=='reference' and km==56:
            with np.load(ROOT/f'output/rain_structure_20261025/reference_recovery/cells/{name}.npz') as old:
                for key in ['Ts','Ps','To','Po']:
                    if not np.array_equal(arrays[key],old[key]):raise ValueError('Legacy control changed: '+key)
            row['cached_r38_float32_exact']=True
        row.update(status='passed',cells=int(mask.sum()),numerics=result.numerics,
            temperature=temperature_metrics(st['Tm'][:,mask],case.obs_T[:,mask]),
            rain=local_metrics(np.maximum(st['Pm'],0.),np.nan_to_num(case.obs_P),mask))
        if name=='north_india':
            low=arrays['elev']<1500;high=arrays['elev']>4500
            row['diagnosis']=dict(july_lowland_mae_mm=float(np.abs(st['Pm'][6,mask][low]-case.obs_P[6,mask][low]).mean()),
                annual_plateau_mae_mm=float(np.abs(st['Pm'][:,mask][:,high].sum(0)-case.obs_P[:,mask][:,high].sum(0)).mean()))
        np.savez_compressed(cells,**arrays);row['cells_sha256']=file_hash(cells)
    except Exception as error:
        row.update(status='failed',error=repr(error))
    row['seconds']=time.monotonic()-started;write_json(record,row)
    print(f'{name} {km:g} km {scheme}: '+row['status']+
          (f' · P loss {row["rain"]["loss"]:.4f}' if row['status']=='passed' else ' '+row['error']),flush=True)
    return row


def summarize(records,plan):
    failures=[];scores={}
    for km in plan['cell_km']:
        ref=[r for r in records if r['cell_km']==km and r['scheme']=='reference']
        cand=[r for r in records if r['cell_km']==km and r['scheme']=='terrain_quadrature']
        if len(ref)!=len(plan['regions']) or len(cand)!=len(ref) or any(r['status']!='passed' for r in ref+cand):
            failures.append(f'{km} km: incomplete or failed numerical result');continue
        rr={r['region']:r for r in ref};cc={r['region']:r for r in cand}
        if any(rr[n]['case_identity']!=cc[n]['case_identity'] for n in rr):raise ValueError('Unpaired case inputs')
        avg=lambda rows,part,key:float(np.mean([r[part][key] for r in rows]))
        tr=avg(ref,'temperature','monthly_mae_C');tc=avg(cand,'temperature','monthly_mae_C')
        pr=avg(ref,'rain','loss');pc=avg(cand,'rain','loss')
        regional={n:.5*cc[n]['temperature']['monthly_mae_C']/rr[n]['temperature']['monthly_mae_C']+
                    .5*cc[n]['rain']['loss']/rr[n]['rain']['loss'] for n in rr}
        s=.5*tc/tr+.5*pc/pr;scores[str(km)]=dict(S=s,T_ratio=tc/tr,P_ratio=pc/pr,regions=regional)
        if km==56:
            if pc/pr>.99:failures.append('56 km rain improvement below 1%')
            if tc/tr>1.01:failures.append('56 km temperature worsened by more than 1%')
            failures.extend(n+': regional S exceeds 1.05' for n,s in regional.items() if s>1.05)
            for key,strict in [('july_lowland_mae_mm',True),('annual_plateau_mae_mm',False)]:
                a,b=cc['north_india']['diagnosis'][key],rr['north_india']['diagnosis'][key]
                if a>=b if strict else a>b:failures.append('North India '+key+' did not meet the declared limit')
        elif s>1.01:failures.append('28 km S exceeds 1.01')
    return dict(complete=True,passes_pilot=not failures,failures=failures,scores=scores,
        decision='Prepare full fresh development gate; no adoption yet.' if not failures else 'Retain r38; this replacement is not qualified.',
        note='Four-region development pilot, not an independent validation or atlas adoption gate.')


def main():
    plan_path=ROOT/'calibration/terrain_quadrature_20261025/plan.json';plan=json.loads(plan_path.read_text())
    out=ROOT/'output/terrain_quadrature_20261025';out.mkdir(exist_ok=True)
    base=load_params(ROOT/plan['reference']);earth.REGIONS.update(json.loads(DEV12_SPECS.read_text()))
    sources=list((ROOT/'rotclimate').glob('*.py'))+[Path(__file__),plan_path,ROOT/plan['reference'],DEV12_SPECS,
        ROOT/'experiments/terrain_quadrature.py',ROOT/'scripts/benchmark_local.py',ROOT/'scripts/earth_benchmark.py',
        ROOT/'scripts/local_benchmark_protocol.py',ROOT/'scripts/rainfall_metrics.py']
    sources += [earth.WORLDCLIM/f'wc2.1_5m_{v}.zip' for v in ['elev','prec','tavg','vapr']]
    sources += [ROOT/f'output/rain_structure_20261025/reference_recovery/cells/{n}.npz' for n in plan['regions']]
    identity=freeze(out/'protocol.json',dict(plan=plan,params=asdict(base),
        sources={str(p.relative_to(ROOT)):file_hash(p) for p in sources},
        packages={p:importlib.metadata.version(p) for p in ['numpy','scipy','Pillow']}))
    for name in plan['regions']:
        reference_terrain(name,plan['terrain_reference_km']);print(name+': common fine DEM prepared',flush=True)
    records=[]
    with Pool(2) as pool:
        for scheme,changes in plan['schemes'].items():
            jobs=[(n,km,scheme,changes,asdict(base),identity,str(out)) for km in plan['cell_km'] for n in plan['regions']]
            for row in pool.imap_unordered(run_one,jobs):
                records.append(row);write_json(out/'progress.json',dict(complete=False,identity=identity,records=records))
            if scheme=='reference' and any(r['status']!='passed' for r in records):
                raise RuntimeError('Reference control failed; candidates are not run')
    review=summarize(records,plan);review.update(identity=identity,records=records)
    write_json(out/'review.json',review);write_json(out/'progress.json',dict(complete=True,identity=identity,records=records))
    print(json.dumps({k:v for k,v in review.items() if k!='records'},indent=2),flush=True)


if __name__=='__main__':main()
