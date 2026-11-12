"""Replan four finite source/work cases with continuous destination-bin meals."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import itertools
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import build_settlement_dispatch as BASE
from polity.continuous_destination import ContinuousDestinationFeedback
from settlement_locations_earth import sha,write

OUT=ROOT/'output/settlement_continuous_destination_20261112'
PLAN=ROOT/'calibration/settlement_continuous_destination_20261112/plan.json'
PARENT=ROOT/'output/settlement_dispatch_seeded_20261112'


def run(mode,hours,out=OUT):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes(),'Commit continuous destination declaration first'
    key=BASE.case_key(mode,hours,120000,'all_open');parent=PARENT/key
    old=json.loads((parent/'results.json').read_text());review=json.loads((parent/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(parent/'results.json') and old['fields_sha256']==sha(parent/'fields.npz')
    produced=[]
    def factory(*args,**kwargs):
        model=ContinuousDestinationFeedback(*args,**kwargs);produced.append(model);return model
    previous=BASE.DispatchFeedback
    try:
        BASE.DispatchFeedback=factory
        result=BASE.run(mode,hours,120000,'all_open',out)
    finally:BASE.DispatchFeedback=previous
    assert len(produced)==1
    model=produced[0];folder=out/key;f=dict(np.load(folder/'fields.npz'));old_fields=dict(np.load(parent/'fields.npz'))
    final=model.evaluate(f['total']);model._set_dispatch(final,f['dispatch_scale'],final=True)
    np.testing.assert_allclose(final['town_food'].unmet,f['town_unmet'],rtol=0,atol=0)
    f.update(seeded_parent_total=old_fields['total'],seeded_parent_active=old_fields['active'],threshold_seeded=model.threshold_seeded,
        threshold_feasible=model.threshold_feasible,preseed_total=model.preseed_total,preseed_active=model.preseed_active,
        town_peak_stock=final['town_food'].peak_stock,town_shortfall_days=final['town_food'].shortfall_days,
        town_periodic_residual=final['town_food'].periodic_residual,town_periodic_converged=final['town_food'].periodic_converged,
        continuous_food_ceiling=final['total']*0.)
    # The displayed ceiling is recalculated by the versioned class;retain it
    # explicitly alongside the writer's source/food/work fields.
    from polity.continuous_destination import continuous_food_ceiling
    f['continuous_food_ceiling']=continuous_food_ceiling(f['arrivals'],kcal_day=model.kcal_day,store_days=model.destination_store_days,
        loss_fraction_year=model.loss_fraction_year,year_days=model.year_days)
    np.savez_compressed(folder/'fields.npz',**f)
    result.update(status='continuous_destination_joint_dispatch_resident_scenario',parent_plan_sha256=result['plan_sha256'],plan_sha256=sha(PLAN),
        effective_model='ContinuousDestinationFeedback',fields_sha256=sha(folder/'fields.npz'),
        inventory_convention='Destination bin-start supply,immediate capacity clip,continuous meals/decay;source food stays monthly',
        parent_key=key,parent_seeded_town_people=float(old_fields['total'].sum()),parent_seeded_active_sources=int(old_fields['active'].sum()),
        paired_town_people_delta=float(f['total'].sum()-old_fields['total'].sum()),paired_active_sources_delta=int(f['active'].sum()-old_fields['active'].sum()),
        continuous_destination_only=True,collector_return_food_qualified=False,
        source_factory_scope='One worker call;original factory restored even on failure')
    for p in [PLAN,parent/'results.json',parent/'review.json',parent/'fields.npz']:result['sources'][str(p.relative_to(ROOT))]=sha(p)
    for p in [Path(__file__),ROOT/'polity/continuous_destination.py',ROOT/'polity/settlement_seeded_dispatch.py',ROOT/'harvest/continuous_food_stocks.py']:
        result['producers'][str(p.relative_to(ROOT))]=sha(p)
    write(folder/'results.json',result)
    print(key,'continuous destination',result['town_people'],'people;delta',result['paired_town_people_delta'],flush=True)
    return result


def task(args):return run(*args)


def main(out=OUT,jobs=4):
    controls=subprocess.run([str(ROOT/'.venv/bin/python'),'-m','pytest','-q','tests/test_continuous_food_stocks.py','tests/test_continuous_destination.py'],cwd=ROOT,capture_output=True,text=True)
    assert controls.returncode==0,controls.stdout+controls.stderr
    preserved={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'atlases/earth_fit').rglob('*') if p.is_file()}
    out.mkdir(parents=True,exist_ok=True)
    with ProcessPoolExecutor(max_workers=jobs) as workers:rows=list(workers.map(task,[(mode,hours,out) for mode,hours in itertools.product(('raw','corrected'),(600,300))]))
    for name,digest in preserved.items():assert sha(ROOT/name)==digest,name
    write(out/'controls.json',dict(status='passed_before_production',output=controls.stdout))
    write(out/'summary.json',dict(status='four_continuous_destination_resident_replans',adopt=False,rows=rows,unchanged_atlas_sha256=preserved,
        scope='Source/food/work resident feedback with continuous destination-bin meals;not collector-return food,source intrabin/ration/location validation or calibrated population.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,default=OUT);p.add_argument('--jobs',type=int,default=4);args=p.parse_args();main(args.out,args.jobs)
