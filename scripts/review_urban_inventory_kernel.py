"""Same-input canonical inventory controls for every declared initial seasonal case."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from scipy.sparse import load_npz

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.seasonal_settlement_network import Inputs,CoupledNetwork,food_year,KCAL
from harvest.field_support import fixed_rural_food
from harvest.food_stocks import periodic_food_year

OUT=ROOT/'output/urban_candidate_seasonal_20261116';BASE=ROOT/'output/urban_hierarchy_candidate_20261116'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def compare(a,b):
    scale=np.maximum(1,np.maximum(a.harvested,a.needed));tolerance=1e-10*scale
    maxratio=0.
    for key in ['initial_stock','final_stock','peak_stock','consumed','unmet','spoiled','overflow','stock_path','unmet_path']:
        error=np.abs(getattr(a,key)-getattr(b,key));allowance=tolerance+50*np.finfo(float).eps*scale
        if np.any(error>allowance):raise AssertionError((key,float((error/allowance).max())))
        maxratio=max(maxratio,float((error/allowance).max()))
    assert a.periodic_converged.all() and b.periodic_converged.all()
    return maxratio


def main():
    amendment=ROOT/'calibration/urban_diagnosis_20261116/seasonal_inventory_kernel_a1.json'
    assert subprocess.check_output(['git','show','HEAD:'+str(amendment.relative_to(ROOT))],cwd=ROOT)==amendment.read_bytes()
    maximum=0.;cases=0;inventories=0
    rng=np.random.default_rng(20261116)
    for pattern in range(5):
        h=rng.uniform(0,100,(12,80));n=rng.uniform(0,100,(12,80));cap=rng.uniform(0,1000,80)
        if pattern==1:h[:]=0
        if pattern==2:n[:]=0
        if pattern==3:cap[:]=0
        if pattern==4:h[1:]=0;h[0]*=24
        maximum=max(maximum,compare(food_year(h,n,cap),periodic_food_year(h,n,cap,loss_fraction_year=.05,step_days=365/12,record=True)))
    for mode in ['raw','corrected']:
        with np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz') as z:x={k:z[k] for k in z.files}
        with np.load(OUT/f'prepared/network_{mode}.npz') as z:net={k:z[k] for k in z.files}
        for model in ['control','candidate']:
            sites=json.loads((BASE/f'{model}/placed_{mode}_sites.json').read_text())['sites']
            with np.load(BASE/f'{model}/placed_{mode}_fields.npz') as z:f={k:z[k] for k in z.files}
            source=np.flatnonzero(f['land'])
            for reading in ['central','low']:
                M=load_npz(OUT/f'prepared/people_{mode}_{model}_{reading}.npz')
                inputs=Inputs(f['people'].ravel()[source],M,x['potential_kcal'][source],x['boundaries'][source],
                    x['listed_hours'][source],x['reaping_hours'][source],net['owner'][:,source],net['share'][:,source],net['between'],
                    f['residents_'+reading],np.array([bool(s.get('actor')) for s in sites]))
                for hours in [600,300]:
                    engine=CoupledNetwork(inputs,hours=hours,marketed_share=.3371937035110408 if reading=='central' else .14049021985082757)
                    c=engine.evaluate(inputs.request);rural=fixed_rural_food(c['work'].produced_kcal,inputs.boundaries,c['rural']*KCAL)
                    np.testing.assert_array_equal(c['rural_food'].harvest,rural.harvest)
                    maximum=max(maximum,compare(c['rural_food'].year,rural.year))
                    assert np.array_equal(c['rural_food'].year.unmet<=1e-8*np.maximum(1,c['rural_food'].year.needed),rural.year.unmet<=1e-8*np.maximum(1,rural.year.needed))
                    dispatch=np.broadcast_to(c['marketed'].sum(0)/12,c['marketed'].shape).copy()
                    for month in range(12):dispatch[month]*=(inputs.owner[month//3]>=0)&(inputs.retention[month//3]>0)
                    triples=[(c['export_food'],c['marketed'],dispatch,c['marketed'].sum(0)),
                        (c['direct_food'],c['direct'],np.broadcast_to(inputs.request*KCAL/12,c['direct'].shape),inputs.request*2500*90),
                        (c['town_food'],c['arrivals'],np.broadcast_to(inputs.request*KCAL/12,c['arrivals'].shape),inputs.request*2500*90)]
                    for a,h,n,cap in triples:
                        maximum=max(maximum,compare(a,periodic_food_year(h,n,cap,loss_fraction_year=.05,step_days=365/12,record=True)))
                    cases+=1;inventories+=4;print('Kernel controls',mode,model,reading,hours,flush=True)
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),module_sha256=sha(ROOT/'polity/seasonal_settlement_network.py'),
        amendment_sha256=sha(amendment),initial_cases=cases,physical_and_town_inventories=inventories,
        manufactured_patterns=5,max_fraction_of_original_inventory_tolerance=maximum,
        canonical_files_unchanged=True,scope='Same-input closed affine fixed state versus canonical bisection at its original inventory tolerance; every source stock/path and town/export stock checked,source support flags unchanged.',adopt=False)
    (OUT/'kernel_review.json').write_text(json.dumps(report,indent=2)+'\n');print(report)


if __name__=='__main__':main()
