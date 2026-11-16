"""Fresh parent/final/initial physical trials and exact compact exports, not solver-history replay."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
from scipy.sparse import load_npz

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from polity.seasonal_settlement_network import Inputs,CoupledNetwork,audit_network,KCAL
from build_urban_seasonal import table

OUT=ROOT/'output/urban_candidate_seasonal_20261116';BASE=ROOT/'output/urban_hierarchy_candidate_20261116'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    r=json.loads((OUT/'results.json').read_text());compact={};rows=[];points=0
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for c in r['cases']:
        key=c['key'];mode=c['mode'];label=c['model'];reading=c['reading']
        with np.load(OUT/f'cases/{key}/fields.npz') as z:a={k:z[k] for k in z.files}
        with np.load(BASE/f'{label}/placed_{mode}_fields.npz') as z:f={k:z[k] for k in z.files}
        with np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz') as z:x={k:z[k] for k in z.files}
        with np.load(OUT/f'prepared/network_{mode}.npz') as z:n={k:z[k] for k in z.files}
        source=np.flatnonzero(f['land']);sites=json.loads((BASE/f'{label}/placed_{mode}_sites.json').read_text())['sites']
        inputs=Inputs(f['people'].ravel()[source],load_npz(OUT/f'prepared/people_{mode}_{label}_{reading}.npz'),x['potential_kcal'][source],x['boundaries'][source],
            x['listed_hours'][source],x['reaping_hours'][source],n['owner'][:,source],n['share'][:,source],n['between'],f['residents_'+reading],np.array([bool(s.get('actor')) for s in sites]))
        m=CoupledNetwork(inputs,hours=c['hours_worker_year'],marketed_share=c['marketed_share'])
        initial=m.evaluate(inputs.request);initial_arrays=dict(initial_supported=initial['allocation'].settlement.total_people.copy(),
            initial_food_ceiling=initial['allocation'].settlement.food_ceiling_people.copy(),initial_town_unmet=initial['town_food'].unmet.copy());del initial
        parent=m.evaluate(a['certificate_from_target']);fresh=m.evaluate(a['target']);points+=3
        if c['physical_certificate']:
            np.testing.assert_array_equal(parent['allocation'].settlement.total_people,a['target'])
            frozen=parent['allocation'];fresh['allocation']=replace(frozen,settlement=replace(frozen.settlement,food_year=fresh['town_food']),arrivals=fresh['arrivals'].copy())
            fresh['physical_certificate']=True
        audit=audit_network(m,fresh,require_qualified=c['qualified'])
        for field in ['rural','moved','marketed','departures','direct','inter_received','inter_exported','shipments','arrivals']:
            np.testing.assert_array_equal(fresh[field],a[field],err_msg=key+' '+field)
        np.testing.assert_array_equal(fresh['work'].produced_kcal,a['produced'])
        data=dict(request=inputs.request,target=fresh['target'],civilian=fresh['allocation'].settlement.civilian_people,
            staff=fresh['allocation'].settlement.institutional_people,active=fresh['allocation'].settlement.institutional_active,
            allocator_total=fresh['allocation'].settlement.total_people,food_ceiling=fresh['allocation'].settlement.food_ceiling_people,
            arrivals=fresh['arrivals'],**initial_arrays,town_unmet=fresh['town_food'].unmet,town_stock=fresh['town_food'].stock_path)
        compact.update({key+'__'+k:v for k,v in data.items()})
        for i,s in enumerate(sites):
            rows.append(dict(case=key,id=s['id'],name=s['name'],row=s['row'],column=s['column'],requested=float(inputs.request[i]),
                supported=float(fresh['target'][i]),support_fraction=float(fresh['target'][i]/inputs.request[i]) if inputs.request[i]>0 else 0.,
                civilian=float(data['civilian'][i]),staff=float(data['staff'][i]),active=bool(data['active'][i]),
                conditional_initial_supported=float(data['initial_supported'][i]),seasonal_unmet_person_years=float(data['town_unmet'][i]/KCAL),qualified=c['qualified']))
        print('Fresh three-point replay',key,flush=True)
        del a,parent,fresh
    dest=OUT/'fresh';dest.mkdir(exist_ok=True);np.savez_compressed(dest/'town_model.npz',**compact);table(dest/'towns.csv',rows)
    for name in ['town_model.npz','towns.csv']:assert (dest/name).read_bytes()==(OUT/name).read_bytes(),name
    receipt=dict(status='passed',replayer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
        physical_trials=points,cases=16,compact_files_byte_exact=['town_model.npz','towns.csv'],
        scope='Fresh initial,parent-allocator and final physical-source trials at stored vectors;all final routes/source people/production exact and compact export bytes exact. Full solver iteration histories are preserved,not independently rerun.',adopt=False)
    (OUT/'replay.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt)


if __name__=='__main__':main()
