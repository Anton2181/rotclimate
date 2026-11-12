"""Bound civilian meal demand with fixed staff, shipments and physical storage."""
import argparse
import csv
from dataclasses import asdict
import gzip
import io
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.meal_headroom import civilian_meal_headroom
from settlement_locations_earth import sha,write

OUT=ROOT/'output/network_visit_meal_headroom_20261112'
PLAN=ROOT/'calibration/network_visit_meal_headroom_20261112/plan.json'
TIMING=ROOT/'output/network_visit_delivery_timing_20261112'


def main(out=OUT):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes(),'Commit headroom declaration first'
    controls=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q','tests/test_meal_headroom.py','tests/test_event_food_stocks.py'],cwd=ROOT,capture_output=True,text=True)
    assert controls.returncode==0,controls.stdout+controls.stderr
    parent=json.loads((TIMING/'results.json').read_text());review=json.loads((TIMING/'review.json').read_text());a=dict(np.load(TIMING/'fields.npz'))
    assert review['status']=='passed' and review['results_sha256']==sha(TIMING/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_delivery_timing.py')
    sources={**parent['sources'],**parent['producers']}
    for p in [TIMING/'results.json',TIMING/'review.json',*(TIMING/name for name in parent['files_sha256'])]:sources[str(p.relative_to(ROOT))]=sha(p)
    for path,digest in {**sources,**parent['unchanged_atlas_sha256']}.items():assert sha(ROOT/path)==digest,path
    arrays={};rows=[];provider_rows=[]
    keys=list(dict.fromkeys(row['key'] for row in parent['rows']))
    for key in keys:
        old=next(v for v in parent['rows'] if v['key']==key);mode=old['climate'];hours=old['hours_worker_year']
        f=dict(np.load(ROOT/f'output/settlement_dispatch_seeded_20261112/{mode}_h{hours}_load120000_all_open/fields.npz'))
        n=len(f['total']);scored=a[key+'__scored'];staff=f['total']-f['civilian'];np.testing.assert_allclose(staff[scored],100.,atol=1e-12)
        cap=a[key+'__capacity'];np.testing.assert_allclose(cap,f['total']*2500*90,rtol=0,atol=0)
        np.testing.assert_array_equal(a[key+'__residents'],f['total']);events=dict(np.load(TIMING/f'{key}_events.npz'));offsets=np.searchsorted(events['site'],np.arange(n+1))
        for name,value in [('scored',scored),('fixed_staff',staff),('parent_civilian',f['civilian']),('physical_capacity',cap),('actor',a[key+'__actor'])]:arrays[f'{key}__{name}']=value
        for account in 'BC':
            prefix=f'{key}__{account}__';v={name:np.zeros(n,bool) for name in ['staff_feasible','full_demand_passes','passing_valid','failing_valid']}
            v.update({name:np.full(n,np.nan) for name in ['passing_alpha','failing_alpha']})
            for site in np.flatnonzero(scored):
                if account=='B':times=np.arange(12)*365/12;cargo=f['arrivals'][:,site]
                else:sl=slice(offsets[site],offsets[site+1]);times=events['time'][sl];cargo=events['cargo'][sl]
                result=civilian_meal_headroom(times,cargo,staff_residents=staff[site],civilian_residents=f['civilian'][site],capacity=cap[site])
                for name in ['staff_feasible','full_demand_passes','passing_alpha','failing_alpha']:
                    value=getattr(result,name)
                    if value is not None:v[name][site]=value
                csv_row=dict(case=key,accounting=account,provider=int(site),actor=int(a[key+'__actor'][site]),fixed_staff=float(staff[site]),parent_civilian=float(f['civilian'][site]),physical_capacity=float(cap[site]),
                    staff_feasible=result.staff_feasible,full_demand_passes=result.full_demand_passes,passing_alpha=result.passing_alpha,failing_alpha=result.failing_alpha,
                    staff_unmet=result.staff_only.unmet,full_demand_unmet=result.full_demand.unmet)
                for label,inventory in [('staff',result.staff_only),('full',result.full_demand),('passing',result.passing_inventory),('failing',result.failing_inventory)]:
                    if label in ('passing','failing'):v[label+'_valid'][site]=inventory is not None
                    for name,value in asdict(inventory or result.staff_only).items():
                        field=label+'__'+name
                        if field not in v:v[field]=np.zeros(n)
                        if inventory is not None:v[field][site]=value
                        if label=='passing':csv_row[name]=value if inventory is not None else None
                provider_rows.append(csv_row)
            for name,value in v.items():arrays[prefix+name]=value
            def summary(mask):
                feasible=mask & v['staff_feasible'];bounded=feasible & ~v['full_demand_passes'];alpha=v['passing_alpha'][feasible]
                return dict(scored_providers=int(mask.sum()),staff_infeasible=int((mask & ~v['staff_feasible']).sum()),full_demand_passes=int((mask & v['full_demand_passes']).sum()),
                    fixed_staff=float(staff[mask].sum()),parent_civilian=float(f['civilian'][mask].sum()),
                    conditional_civilian_meal_equivalent=float((f['civilian'][feasible]*alpha).sum()),
                    civilian_meal_equivalent_reduction=float((f['civilian'][feasible]*(1-alpha)).sum()),
                    min_passing_alpha=float(alpha.min()) if len(alpha) else None,max_passing_alpha=float(alpha.max()) if len(alpha) else None,
                    max_bracket_width=float((v['failing_alpha'][bounded]-v['passing_alpha'][bounded]).max(initial=0)),
                    passing_unmet=float(v['passing__unmet'][feasible].sum()),full_demand_unmet=float(v['full__unmet'][mask].sum()),
                    max_abs_periodic_residual=float(np.abs(v['passing__periodic_residual'][feasible]).max(initial=0)),
                    max_abs_ledger_residual=float(np.abs(v['passing__ledger_residual'][feasible]).max(initial=0)))
            rows.append(dict(key=key,climate=mode,hours_worker_year=hours,crew=old['crew'],accounting=account,**summary(scored),
                unscored_providers=int((~scored).sum()),actors=[dict(actor_index=actor,**summary(scored & (a[key+'__actor']==actor))) for actor in range(18)]))
            print(key,account,'staff infeasible',rows[-1]['staff_infeasible'],'civilian meal equivalent reduction',rows[-1]['civilian_meal_equivalent_reduction'],flush=True)
    out.mkdir(parents=True,exist_ok=True);np.savez_compressed(out/'fields.npz',**arrays)
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=list(provider_rows[0]));writer.writeheader();writer.writerows(provider_rows)
    (out/'providers.csv.gz').write_bytes(gzip.compress(buffer.getvalue().encode(),mtime=0))
    producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'harvest/meal_headroom.py',ROOT/'tests/test_meal_headroom.py',PLAN]}
    for path,digest in {**sources,**parent['unchanged_atlas_sha256']}.items():assert sha(ROOT/path)==digest,path
    write(out/'controls.json',dict(status='passed_before_production',output=controls.stdout,producers=producers))
    write(out/'results.json',dict(status='fixed_shipment_conditional_civilian_meal_headroom',adopt=False,rows=rows,sources=sources,producers=producers,
        files_sha256={name:sha(out/name) for name in ['fields.npz','providers.csv.gz']},unchanged_atlas_sha256=parent['unchanged_atlas_sha256'],
        fixed_staff_and_original_physical_capacity=True,bracket_iterations=48,
        scope='Conditional destination meal bound only,not resident replanning. Source production/work/exports and worker jobs stay frozen. No maps/defaults,empirical population,famine or authority adoption.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);main(p.parse_args().out)
