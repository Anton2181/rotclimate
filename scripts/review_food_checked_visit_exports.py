"""Independent NEW parent, chosen calendar food, point mask/pixel and CSV review."""
import csv,gzip,io,json
from math import exp,expm1,log1p
from pathlib import Path
import sys
import numpy as np
from PIL import Image,ImageColor
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from settlement_locations_earth import sha,write
OUT=ROOT/'output/continuous_food_visit_calendars_20261112';DATA=ROOT/'atlases/earth_fit/data'


def trace(times,cargo,rate,cap,stock):
    # Scalar display-bin replay, with no production inventory/trace import.
    h=-log1p(-.05)/365;clock=0.;index=0;stocks=[stock]
    names=('arrivals','consumed','unmet','spoiled','overflow','shortfall_days');a={name:np.zeros(12) for name in names}
    for month in range(12):
        right=(month+1)*365/12
        while True:
            event=index<len(times) and times[index]<right;t=float(times[index]) if event else right;dt=t-clock
            empty=log1p(stock*h/rate)/h if rate else float('inf');duration=min(dt,empty)
            after=max(0.,stock*exp(-h*duration)+rate*expm1(-h*duration)/h)
            if empty<=dt:after=0.
            a['consumed'][month]+=rate*duration;a['unmet'][month]+=rate*(dt-duration);a['spoiled'][month]+=max(0.,stock-after-rate*duration);a['shortfall_days'][month]+=dt-duration if rate else 0.
            stock=after;clock=t
            if not event:break
            q=float(cargo[index]);a['arrivals'][month]+=q;a['overflow'][month]+=max(0.,stock+q-cap);stock=min(cap,stock+q);index+=1
        stocks.append(stock)
    assert index==len(times);a['stock_path']=np.array(stocks);return a


def main():
    r=json.loads((OUT/'results.json').read_text());e=json.loads((OUT/'map_exports.json').read_text());manifest=json.loads((DATA/'food_checked_visits.json').read_text())
    assert e['results_sha256']==sha(OUT/'results.json') and e['manifest_sha256']==sha(DATA/'food_checked_visits.json')
    for name,digest in {**r['sources'],**r['producers'],**r['unchanged_map_sha256'],**e['files_sha256'],**e['producers']}.items():assert sha(ROOT/name)==digest,name
    S=dict(np.load(OUT/'selected_fields.npz'));F=dict(np.load(OUT/'funded_fields.npz'));E=dict(np.load(DATA/'food_checked_visits/fields.npz'))
    for name in S:np.testing.assert_array_equal(S[name],E[name])
    parent=json.loads((DATA/'settled_reach.json').read_text());old=json.loads((DATA/'network_duty_visits.json').read_text());meta=json.loads((DATA/'atlas.json').read_text());cases=[];pixels=points=stocks=0
    for mode,p in manifest['packets'].items():
        x=dict(np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz'));paths=dict(np.load(ROOT/f'output/network_duty_visits_20261112/{mode}_paths.npz'))
        model=json.loads(gzip.decompress((DATA/p['payload']).read_bytes()));raw=gzip.decompress((DATA/p['binary']).read_bytes());prior=old['packets'][mode];prior_raw=gzip.decompress((DATA/prior['binary']).read_bytes())
        assert len(raw)==p['raw_bytes'];assert raw[:p['offsets']['masks']]==prior_raw[:prior['offsets']['masks']];assert p['parent_payload_sha256']==parent['packets'][mode]['payload_sha256']
        assert p['expected_harvest_fingerprint']==parent['packets'][mode]['expected_harvest_fingerprint'];assert model['shape']==list(x['land'].shape) and model['climate']==mode
        actors=model['actors'];land=int(x['land'].sum());masks=np.frombuffer(raw,'<u2',offset=p['offsets']['masks']).reshape(5,len(actors),land)
        np.testing.assert_array_equal(masks[0],np.frombuffer(prior_raw,'<u2',offset=prior['offsets']['masks'],count=len(actors)*land).reshape(len(actors),land))
        np.testing.assert_array_equal(model['point_target_nodes'],paths['target_nodes']);positions=np.searchsorted(np.flatnonzero(x['land']),paths['target_nodes'])
        names={v['name']:i for i,v in enumerate(actors)};lookup={int(v):j for j,v in enumerate(paths['target_nodes'])}
        for row in (v for v in r['visit_rows'] if v['stage']=='selected' and v['climate']==mode):
            key=row['key'];ident=f'foodvisits{row["hours_worker_year"]}_crew{row["crew"]}';k=next(i for i,c in enumerate(model['cases']) if c['id']==ident);c=model['cases'][k];s={n.removeprefix(key+'__'):v for n,v in S.items() if n.startswith(key+'__')}
            f=dict(np.load(ROOT/f'output/settlement_continuous_destination_20261112/{mode}_h{row["hours_worker_year"]}_load120000_all_open/fields.npz'));pr=json.loads((ROOT/f'output/settlement_continuous_destination_20261112/{mode}_h{row["hours_worker_year"]}_load120000_all_open/results.json').read_text())
            for field,name in [('civilian_people','civilian'),('institutional_people','staff'),('resident_budget_people','budget'),('source_supported','source_supported'),('food_ceiling_people','continuous_food_ceiling')]:np.testing.assert_array_equal(c[field],f[name])
            np.testing.assert_array_equal(c['institutional_active'],s['qualified']);np.testing.assert_array_equal(c['year_schedule']['policy'],s['policy']);np.testing.assert_array_equal(c['year_schedule']['mandatory_complete'],s['selected_mandatory_complete']);np.testing.assert_array_equal(c['year_schedule']['qualified'],s['qualified'])
            assert c['source_gate']==pr['source_gate'] and c['work_summary']['production_retained']==pr['local_production_retained'];assert c['work_summary']['scenario_workers']==float(f['rural'].sum()*.4)
            np.testing.assert_array_equal(c['dispatch_work']['dispatch_scale'],f['dispatch_scale']);np.testing.assert_array_equal(c['dispatch_work']['gross_hours'],f['work_gross_hours'].T)
            for field,name in [('work_hours','work_hours'),('max_worker_hours','max_worker_hours'),('max_calendar_end','max_calendar_end')]:np.testing.assert_array_equal(c['year_schedule'][field],s['provider_'+name].T)
            for field,name in [('reserved_hours','reserved_patrol_hours'),('used_hours','visit_hours'),('unused_hours','unused_patrol_hours'),('completed_by_provider','completed_visits'),('physically_scheduled_by_provider','physical_visits')]:np.testing.assert_array_equal(c['point_visits'][field],s['provider_'+name].T)
            for field,name in [('collection_hours','collection_hours'),('unused_hours','unused_staff_hours')]:np.testing.assert_array_equal(c['dispatch_work'][field],s['provider_'+name].T)
            for name in s:
                if name.startswith('food_'):np.testing.assert_array_equal(c['destination_food'][name[5:]],s[name])
            np.testing.assert_array_equal(c['destination_food']['active'],f['active']);np.testing.assert_array_equal(c['destination_food']['qualified'],s['qualified'])
            events={pol:dict(np.load(OUT/key/pol/'events.npz')) for pol in ('baseline','joint')};policies={pol:dict(np.load(OUT/key/pol/'fields.npz')) for pol in events}
            for site in range(len(f['total'])):
                pol='joint' if s['policy'][site] else 'baseline';ev=events[pol];sl=ev['site']==site;rate=f['total'][site]*2500;t=trace(ev['time'][sl],ev['cargo'][sl],rate,rate*90,s['food_initial_stock'][site]);stocks+=1
                np.testing.assert_allclose(c['stock_path_kcal'][site],t['stock_path'],rtol=1e-10,atol=1e-4)
                np.testing.assert_allclose(c['monthly_arrivals_kcal'][site],t['arrivals'],rtol=1e-12,atol=1e-5);np.testing.assert_allclose(c['monthly_need_kcal'][site],np.full(12,rate*365/12),rtol=1e-12,atol=1e-5)
                for name in ('consumed','unmet','spoiled','overflow','shortfall_days'):np.testing.assert_allclose(c['destination_food']['monthly_'+name+('_kcal' if name!='shortfall_days' else '')][site],t[name],rtol=1e-9,atol=1e-4)
                assert bool(s['qualified'][site])==bool(f['active'][site] and s['selected_mandatory_complete'][site] and s['selected_food_no_shortage'][site])
            served=s['served'];provider=F[key+'__provider_for_target'];physical=F[key+'__served']&np.where(s['policy'][np.maximum(provider,0)]==1,policies['joint']['scheduled'],policies['baseline']['scheduled'])
            np.testing.assert_array_equal(E[key+'__physical_served'],physical);expected=np.zeros((len(actors),land),'u2');expected[:,positions]=sum(served[m].astype('u2')<<m for m in range(12));np.testing.assert_array_equal(masks[k],expected)
            o=next(o for o in p['options']['reach_defacto'] if o['value']==ident);assert o['food_checked_visit_support']
            with Image.open(DATA/o['file']) as im:
                assert im.size==(meta['width'],meta['height']);im=im.convert('RGB');visits=served.sum(axis=0)
                for j in np.flatnonzero(visits.any(axis=0)):
                    a=int(np.argmax(visits[:,j]));color=(255,255,255) if (visits[:,j]>0).sum()>1 else ImageColor.getrgb(actors[a]['color']);yy,xx=divmod(int(paths['target_nodes'][j]),x['land'].shape[1]);assert im.getpixel((int((xx+.5)*p['cell_px']),int((yy+.5)*p['cell_px'])))==color;pixels+=1
            records=list(csv.DictReader(io.StringIO(gzip.decompress((DATA/p['point_csv'][ident]).read_bytes()).decode())));assert len(records)==int(S[mode+'__demand'].sum());seen=set();total=0
            status=dict(qualified=served,physical=physical,schedule_unqualified=s['schedule_unqualified'],route_unreachable=s['route_unreachable'],provider_work_unavailable=s['provider_work_unavailable'],capacity_unmet=s['capacity_unmet'],original_funded=s['original_funded'],baseline_both=s['baseline_served'],not_physically_scheduled=s['original_funded']&~physical,scheduled_but_provider_unqualified=physical&~served)
            for v in records:
                a=names[v['actor']];node=int(v['target_grid_node']);j=lookup[node];assert (a,j) not in seen and S[mode+'__demand'][a,j];seen.add((a,j));yy,xx=divmod(node,x['land'].shape[1]);assert (int(v['target_row']),int(v['target_column']))==(yy,xx) and v['scenario']==ident and v['climate']==mode
                for name,array in status.items():assert int(v[name+'_bin_mask'])==sum(1<<m for m in range(12) if array[m,a,j]),(key,name)
                assert sum(int(v[n+'_bin_mask']) for n in ('qualified','schedule_unqualified','route_unreachable','provider_work_unavailable','capacity_unmet'))==4095
                assert int(v['baseline_both_bin_mask'])&~int(v['qualified_bin_mask'])==0;assert int(v['qualified_bins'])==int(v['qualified_bin_mask']).bit_count();total+=int(v['qualified_bins'])
                owners=[int(provider[m,a,j]) if s['original_funded'][m,a,j] else -1 for m in range(12)];assert list(map(int,v['original_funded_provider_by_bin'].split('|')))==owners
                for col,arr,fallback in [('provider_year_policy_by_bin',s['policy'],-1),('provider_mandatory_year_by_bin',s['selected_mandatory_complete'],0),('provider_destination_food_by_bin',s['selected_food_no_shortage'],0),('provider_qualified_year_by_bin',s['qualified'],0)]:assert list(map(int,v[col].split('|')))==[int(arr[z]) if z>=0 else fallback for z in owners]
            assert total==row['qualified_visits']==c['point_visits']['completed'];points+=len(records);cases.append(key);print('Independent NEW-parent,food trace,masks,pixels,CSV passed',key,flush=True)
    write(OUT/'map_review.json',dict(status='passed',results_sha256=sha(OUT/'results.json'),manifest_sha256=sha(DATA/'food_checked_visits.json'),exports_sha256=sha(OUT/'map_exports.json'),reviewer_sha256=sha(Path(__file__)),cases=cases,checked_point_rows=points,checked_visited_point_pixels=pixels,checked_provider_stock_paths=stocks,new_parent_people_and_planning_ceiling_exact=True,own_food_and_physical_year_flags_separate=True,all_point_masks_and_partitions=True,baseline_both_task_inclusion=True,all_prior_data_preserved=True))

if __name__=='__main__':main()
