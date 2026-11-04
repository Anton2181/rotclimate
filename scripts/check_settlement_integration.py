"""Independently audit published food ledgers and subset/sensitivity invariants."""
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);args=ap.parse_args();reviews=[]
    for name in ['free_fit','earth_fit','whittaker_fit']:
        data=ROOT/'atlases'/name/'data';manifest=json.loads((data/'settled_reach.json').read_text())
        for mode,p in manifest['packets'].items():
            for options in p['options'].values():
                for option in options:assert hashlib.sha256((data/option['file']).read_bytes()).hexdigest()==option['file_sha256']
            a=(data/p['payload']).read_bytes();b=(data/p['binary']).read_bytes()
            assert hashlib.sha256(a).hexdigest()==p['payload_sha256'];assert hashlib.sha256(b).hexdigest()==p['binary_sha256']
            m=json.loads(gzip.decompress(a));raw=gzip.decompress(b);size=np.prod(p['shape']);n=len(m['sites']);spec=m['specification']
            assert len(raw)==p['raw_bytes'] and m['climate']==mode
            lookup=np.frombuffer(raw,'<u4',count=size);ids=np.frombuffer(raw,'<u2',count=size,offset=p['offsets']['catchments'])
            masks=np.frombuffer(raw,'<u2',offset=p['offsets']['masks']).reshape(p['masks_shape'])
            assert (ids<=n).all() and np.sum(lookup>0)==p['land_cells'] and (masks<=4095).all()
            nodes=[s['node'] for s in m['sites']];assert len(nodes)==len(set(nodes)) and all(ids[node]==i+1 for i,node in enumerate(nodes))
            assert sum(len(s['evidence_ids']) for s in m['sites'])==151
            request=np.array([s['civilian_request_people'] for s in m['sites']]);affiliated=np.array([s['actor_index']>=0 for s in m['sites']]);cases={c['id']:c for c in m['cases']}
            residual_max=0.;ledgers=0
            for k,c in enumerate(m['cases']):
                civ=np.array(c['civilian_people']);staff=np.array(c['institutional_people']);active=np.array(c['institutional_active']);total=civ+staff
                assert np.all(civ<=request+1e-7) and not np.any(active&~affiliated)
                assert not np.any(masks[k]&~masks[0])
                for ai in range(len(m['actors'])):
                    if not any(active[j] and s['actor_index']==ai for j,s in enumerate(m['sites'])):assert not masks[k,ai].any()
                if not c['food_constrained']:continue
                assert np.all(total<=np.array(c['food_ceiling_people'])+1e-6)
                assert np.all(civ[active]>=spec['minimum_community_people']-1e-7)
                arrivals=np.array(c['monthly_arrivals_kcal']);need=np.array(c['monthly_need_kcal']);stocks=np.array(c['stock_path_kcal'])
                np.testing.assert_allclose(need,np.broadcast_to(total[:,None]*spec['ration_kcal_person_day']*spec['year_days']/12,need.shape))
                cap=total*spec['ration_kcal_person_day']*spec['destination_store_demand_days'];retention=(1-spec['annual_stored_energy_loss_fraction'])**(1/12)
                # Replay each stored month directly from the public starting
                # inventory, independently of the solver and its bisection.
                available=stocks[:,:-1]+arrivals;eaten=np.minimum(available,need);remaining=np.maximum(0,available-eaten);overflow=np.maximum(0,remaining-cap[:,None]);kept=np.minimum(remaining,cap[:,None]);loss=kept*(1-retention)
                np.testing.assert_allclose(stocks[:,1:],kept*retention,rtol=1e-9,atol=1e-4)
                assert np.max(np.abs(stocks[:,0]-stocks[:,-1]))<1e-6*max(1,arrivals.sum())
                assert np.max(need-eaten)<1e-6*max(1,need.max())
                for key,value in [('resident_consumed_kcal',eaten.sum()),('destination_loss_kcal',loss.sum()),('destination_unused_kcal',overflow.sum())]:
                    assert np.isclose(c['ledger'][key],value,rtol=1e-9,atol=1e-3),(key,c['ledger'][key],value)
                r=m['rural_ledger'];l=c['ledger'];independent=r['harvested_kcal']-sum([r['consumed_kcal'],r['storage_loss_kcal'],l['uncollected_kcal'],l['origin_loss_kcal'],l['transport_loss_kcal'],eaten.sum(),loss.sum(),overflow.sum()])
                assert abs(independent)<1e-7*max(1,r['harvested_kcal'])
                residual_max=max(residual_max,abs(independent));ledgers+=n*12
            a=cases['joint365'];assert np.all(np.array(cases['joint1']['food_ceiling_people'])<=np.array(a['food_ceiling_people'])+1e-6)
            assert np.all(np.array(cases['joint90']['food_ceiling_people'])<=np.array(a['food_ceiling_people'])+1e-6)
            assert not any(cases['joint0']['institutional_active'])
            assert sum(a['institutional_active'])<sum(cases['reference']['institutional_active'])
            assert masks[1].tobytes()!=masks[0].tobytes()
            reviews.append(dict(atlas=name,climate=mode,sites=n,site_bin_ledgers=ledgers,max_joint_residual_kcal=residual_max,changed_settlements=True,changed_reach_sources=True))
    args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(json.dumps(dict(status='passed',reviews=reviews),indent=2)+'\n');print(json.dumps(reviews,indent=2))


if __name__=='__main__':main()
