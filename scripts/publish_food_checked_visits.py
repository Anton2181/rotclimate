"""Export NEW-parent point maps with one OWN-food-checked full provider year."""
import argparse
import copy
import csv
import gzip
import io
import json
from pathlib import Path
import shutil
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from harvest.event_food_trace import trace_event_food_year
from publish_network_duty_visits import point_image
from settlement_locations_earth import sha,write

OUT=ROOT/'output/continuous_food_visit_calendars_20261112'
PARENT=ROOT/'output/settlement_continuous_destination_20261112'
INPUTS=ROOT/'output/settlement_feedback_20261112'
PATHS=ROOT/'output/network_duty_visits_20261112'
DATA=ROOT/'atlases/earth_fit/data'


def main(export=DATA,activate=False):
    result=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text());replay=json.loads((OUT/'replay.json').read_text());funded=json.loads((OUT/'funded_results.json').read_text())
    summary_review=json.loads((OUT/'summary_review.json').read_text())
    assert summary_review['status']=='passed' and summary_review['results_sha256']==sha(OUT/'results.json') and summary_review['reviewer_sha256']==sha(ROOT/'scripts/review_food_visit_summaries.py')
    assert review['status']==replay['status']=='passed' and review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_continuous_food_visits.py')
    for name,digest in {**result['sources'],**result['producers'],**result['unchanged_map_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in replay['byte_exact_files'].items():assert sha(OUT/name)==digest,name
    parent=json.loads((DATA/'settled_reach.json').read_text());old=json.loads((DATA/'network_duty_visits.json').read_text());meta=json.loads((DATA/'atlas.json').read_text())
    selected=dict(np.load(OUT/'selected_fields.npz'));full_fields=dict(selected);packets={};bits=(1<<np.arange(12,dtype='u2'))[:,None,None]
    for mode in ('raw','corrected'):
        p=parent['packets'][mode];original=json.loads(gzip.decompress((DATA/old['packets'][mode]['payload']).read_bytes()));x=dict(np.load(INPUTS/f'{mode}_inputs.npz'));paths=dict(np.load(PATHS/f'{mode}_paths.npz'))
        np.testing.assert_array_equal([s['node'] for s in original['sites']],x['nodes']);np.testing.assert_allclose([s['civilian_request_people'] for s in original['sites']],x['civilian_request'],rtol=1e-12)
        model={name:copy.deepcopy(original[name]) for name in ('version','atlas','climate','shape','sites','actors','specification','labour_specification')}
        model.update(cases=[copy.deepcopy(original['cases'][0])],summaries=[copy.deepcopy(original['summaries'][0])],point_target_nodes=paths['target_nodes'].tolist(),
            point_requested_targets=[paths['target_nodes'][v>0].tolist() for v in paths['target_reference_masks']],
            scope='Point jobs require one whole provider-year and its OWN destination cereal inventory. Uniform destination meals,monthly source availability and supplied work remain assumptions;crew-carried food/location,complete diets,observed roles and territory unqualified.')
        with gzip.open(DATA/p['binary'],'rb') as stream:prefix=stream.read(p['offsets']['masks'])
        reference=np.load(INPUTS/f'{mode}_footprints.npz')['reference'];masks=[reference];positions=np.searchsorted(np.flatnonzero(x['land']),paths['target_nodes']);options=[];grids={};point_csv={}
        target=export/'food_checked_visits'/mode;target.mkdir(parents=True,exist_ok=True)
        for row in [v for v in result['visit_rows'] if v['stage']=='selected' and v['climate']==mode]:
            key=row['key'];ident=f'foodvisits{row["hours_worker_year"]}_crew{row["crew"]}';source=PARENT/f'{mode}_h{row["hours_worker_year"]}_load120000_all_open'
            f=dict(np.load(source/'fields.npz'));r=json.loads((source/'results.json').read_text());n=len(f['total'])
            S={name.removeprefix(key+'__'):value for name,value in selected.items() if name.startswith(key+'__')}
            with np.load(OUT/'funded_fields.npz') as z:F={name.removeprefix(key+'__'):z[name] for name in z.files if name.startswith(key+'__')}
            policies={policy:dict(np.load(OUT/key/policy/'fields.npz')) for policy in ('baseline','joint')};events={policy:dict(np.load(OUT/key/policy/'events.npz')) for policy in policies}
            event_offsets={policy:np.searchsorted(e['site'],np.arange(n+1)) for policy,e in events.items()};use_joint=S['policy']==1
            actual_arrivals=np.where(use_joint[None,:],policies['joint']['packed_arrivals'],policies['baseline']['packed_arrivals'])
            need=np.broadcast_to(f['total']*2500*365/12,(12,n));traces={name:[] for name in ('stock_path','arrivals','needed','consumed','unmet','spoiled','overflow','shortfall_days','peak_stock')}
            for site in range(n):
                policy='joint' if use_joint[site] else 'baseline';e=events[policy];o=event_offsets[policy];sl=slice(o[site],o[site+1])
                trace=trace_event_food_year(e['time'][sl],e['cargo'][sl],demand_rate=f['total'][site]*2500,capacity=f['total'][site]*2500*90,initial_stock=S['food_initial_stock'][site])
                for name in traces:traces[name].append(trace[name])
                np.testing.assert_allclose(trace['stock_path'][-1],S['food_final_stock'][site],rtol=1e-10,atol=1e-4)
                for name in ('consumed','unmet','spoiled','overflow','shortfall_days'):np.testing.assert_allclose(trace[name].sum(),S['food_'+name][site],rtol=1e-9,atol=1e-4)
            traces={name:np.asarray(value) for name,value in traces.items()};np.testing.assert_allclose(traces['arrivals'].T,actual_arrivals,rtol=1e-12,atol=1e-6)
            provider=F['provider_for_target'];assigned_policy=S['policy'][np.maximum(provider,0)]
            physical=F['served']&np.where(assigned_policy==1,policies['joint']['scheduled'],policies['baseline']['scheduled'])
            assert np.all(~S['served']|physical) and int(physical.sum())==int(S['provider_physical_visits'].sum())
            full_fields[key+'__provider_for_target']=provider;full_fields[key+'__chosen_cost_hours']=F['chosen_cost_hours'];full_fields[key+'__physical_served']=physical
            full_fields[key+'__stock_path_kcal']=traces['stock_path'];full_fields[key+'__monthly_actual_arrivals_kcal']=actual_arrivals;full_fields[key+'__monthly_need_kcal']=need
            for name in ('consumed','unmet','spoiled','overflow','shortfall_days'):full_fields[key+'__monthly_'+name]=traces[name].T
            food={name.removeprefix('food_'):value.tolist() for name,value in S.items() if name.startswith('food_')}
            food.update(active=f['active'].tolist(),qualified=S['qualified'].tolist(),monthly_unmet_kcal=traces['unmet'].tolist(),monthly_consumed_kcal=traces['consumed'].tolist(),
                monthly_spoiled_kcal=traces['spoiled'].tolist(),monthly_overflow_kcal=traces['overflow'].tolist(),monthly_shortfall_days=traces['shortfall_days'].tolist(),
                convention='Selected calendar return phases with original one-bin lag;minimum repeating destination cereal stock. Crew-carried food/location and source within-bin availability untracked.')
            c=dict(id=ident,label=f'Provider calendar + destination cereal · {row["hours_worker_year"]}h / crew {row["crew"]}',feedback_coupled=True,food_constrained=True,labour_constrained=True,
                hours_worker_year=row['hours_worker_year'],harvest_days=30,transfer_fraction=.075,food_ceiling_people=f['continuous_food_ceiling'].tolist(),food_ceiling_scope='Parent planning ceiling under continuous bin-start supply;not a new return-phase resident ceiling',
                civilian_people=f['civilian'].tolist(),institutional_people=f['staff'].tolist(),institutional_active=S['qualified'].tolist(),community_viable=(f['civilian']>=50).tolist(),
                resident_budget_people=f['budget'].tolist(),source_supported=f['source_supported'].tolist(),monthly_arrivals_kcal=actual_arrivals.T.tolist(),monthly_need_kcal=need.T.tolist(),stock_path_kcal=traces['stock_path'].tolist(),
                work_summary=dict(production_retained=r['local_production_retained'],scenario_workers=float(f['rural'].sum()*.4)),rural_ledger=dict(unmet_kcal=r['local_rural_unmet_kcal'],deficit_origins=r['local_rural_deficit_origins'],outside_unmet_kcal=r['outside_rural_unmet_kcal']),
                source_gate=r['source_gate'],source_gate_scope='Parent finite source-food gate before explicit job omissions and return phases',empirical_resident_size_fit=False,whole_world_food_supported=False,
                dispatch_work=dict(threshold_seeded=True,load_kcal=120000.,availability='all_open',dispatch_scale=f['dispatch_scale'].tolist(),dispatch_scale_scope='Parent planned dispatch before unpacked trips',
                    collection_hours=S['provider_collection_hours'].T.tolist(),gross_hours=f['work_gross_hours'].T.tolist(),unused_hours=S['provider_unused_staff_hours'].T.tolist(),modeled_worker_calendars_checked=True,actual_geographic_patrol_hours_qualified=False),
                point_visits=dict(crew=row['crew'],requested=next(v['requested_visits'] for v in funded['rows'] if v['key']==key),completed=row['qualified_visits'],schedule_unqualified=int(S['schedule_unqualified'].sum()),
                    route_unreachable=int(S['route_unreachable'].sum()),provider_work_unavailable=int(S['provider_work_unavailable'].sum()),capacity_unmet=int(S['capacity_unmet'].sum()),
                    reserved_hours=S['provider_reserved_patrol_hours'].T.tolist(),used_hours=S['provider_visit_hours'].T.tolist(),unused_hours=S['provider_unused_patrol_hours'].T.tolist(),completed_by_provider=S['provider_completed_visits'].T.tolist(),
                    physically_scheduled_by_provider=S['provider_physical_visits'].T.tolist(),actual_block_edge_km=funded['target_metadata'][mode]['actual_block_edge_km']),
                year_schedule=dict(policy=S['policy'].tolist(),mandatory_complete=S['selected_mandatory_complete'].tolist(),qualified=S['qualified'].tolist(),work_hours=S['provider_work_hours'].T.tolist(),max_worker_hours=S['provider_max_worker_hours'].T.tolist(),max_calendar_end=S['provider_max_calendar_end'].T.tolist()),
                destination_food=food)
            summary=dict(id=ident,key=key,town_people=float(f['total'].sum()),civilian_people=float(f['civilian'].sum()),institutional_people=float(f['staff'].sum()),active_sources=int(S['qualified'].sum()),viable_communities=int((f['civilian']>=50).sum()),
                area_weighted_access_bins=None,all_bin_area_km2=None,any_bin_area_km2=None,area_weighted_access_scope='Unscored:point tasks do not establish a visited-area or territory estimate',actors=[])
            for actor,ref in enumerate(original['summaries'][0]['actors']):
                owned=x['actor']==actor;summary['actors'].append(dict(actor=model['actors'][actor]['name'],candidate_sources=int(owned.sum()),active_sources=int((owned&S['qualified']).sum()),inventory_scored=ref['inventory_scored'],
                    civilian_people=float(f['civilian'][owned].sum()),institutional_people=float(f['staff'][owned].sum()),all_bin_area_km2=None,qualified_visits=int(S['served'][:,actor].sum())))
            model['cases'].append(c);model['summaries'].append(summary)
            grid=np.zeros_like(reference);grid[:,positions]=np.sum(S['served'].astype('u2')*bits,axis=0).astype('u2');masks.append(grid)
            path=target/(ident+'.webp');point_image(x,paths,S['served'],model['actors'],meta).save(path,lossless=True)
            status={name:np.sum(value.astype('u2')*bits,axis=0).astype('u2') for name,value in dict(qualified=S['served'],physical=physical,schedule_unqualified=S['schedule_unqualified'],
                route_unreachable=S['route_unreachable'],provider_work_unavailable=S['provider_work_unavailable'],capacity_unmet=S['capacity_unmet'],original_funded=S['original_funded'],baseline_both=S['baseline_served'],
                not_physically_scheduled=S['original_funded']&~physical,scheduled_but_provider_unqualified=physical&~S['served']).items()}
            buffer=io.StringIO(newline='');writer=csv.writer(buffer);mask_names=list(status)
            writer.writerow(['climate','scenario','actor','target_grid_node','target_row','target_column','requested_bins','qualified_bins',*[name+'_bin_mask' for name in mask_names],
                'original_funded_provider_by_bin','provider_year_policy_by_bin','provider_mandatory_year_by_bin','provider_destination_food_by_bin','provider_qualified_year_by_bin','scope'])
            for actor,j in zip(*np.where(selected[mode+'__demand'])):
                node=int(paths['target_nodes'][j]);yy,xx=divmod(node,x['land'].shape[1]);owners=np.where(S['original_funded'][:,actor,j],provider[:,actor,j],-1)
                flags=[[int(values[s]) if s>=0 else fallback for s in owners] for values,fallback in [(S['policy'],-1),(S['selected_mandatory_complete'],0),(S['selected_food_no_shortage'],0),(S['qualified'],0)]]
                writer.writerow([mode,ident,model['actors'][actor]['name'],node,yy,xx,12,int(S['served'][:,actor,j].sum()),*[int(status[name][actor,j]) for name in mask_names],
                    '|'.join(map(str,owners.tolist())),*['|'.join(map(str,values)) for values in flags],
                    'ONE provider-year and OWN destination cereal;source bin availability and crew food location remain assumptions;not observed visits or territory'])
            csv_path=target/(ident+'_points.csv.gz');csv_path.write_bytes(gzip.compress(buffer.getvalue().encode(),mtime=0));point_csv[ident]=str(csv_path.relative_to(export));grids[ident]='food_checked_visits/fields.npz'
            options.append(dict(value=ident,label=c['label'],integrated_support=True,food_checked_visit_support=True,file=str(path.relative_to(export)),file_sha256=sha(path),
                note='Point jobs require one whole provider-year and its OWN destination cereal inventory. Staff availability,monthly source food and uniform destination meals remain assumptions;crew food location,complete diets,observed roles and territory unqualified.',
                caption='Qualified target-point tasks. Size reflects bins;white centres indicate overlapping actors. Background and intervening land are unscored.',
                items=[dict(color=a['color'],label=a['name']) for a in model['actors']]+[dict(color='#e3decf',label='Unscored background;no territory claim')]))
        model['specification']['cases']=[dict(id=c['id'],label=c['label']) for c in model['cases']]
        model['destination_food_specification']=dict(convention='OWN selected calendar return phases,minimum repeating stock',year_days=365.,kcal_person_day=2500.,stored_loss_fraction=.05,imposed_delivery_delay_bins=1,transport_retention=.95,crew_food_location_tracked=False,source_within_bin_availability_validated=False)
        payload=target/'settled_reach.json.gz';binary=target/'settled_reach.bin.gz';combined=np.stack(masks)
        payload.write_bytes(gzip.compress(json.dumps(model,ensure_ascii=False,allow_nan=False,separators=(',',':')).encode(),mtime=0));binary.write_bytes(gzip.compress(prefix+combined.astype('<u2').tobytes(),mtime=0))
        packets[mode]=dict(shape=list(x['land'].shape),cell_px=meta['width']/x['land'].shape[1],land_cells=int(x['land'].sum()),masks_shape=list(combined.shape),offsets=p['offsets'],raw_bytes=len(prefix)+combined.nbytes,
            payload=str(payload.relative_to(export)),payload_sha256=sha(payload),binary=str(binary.relative_to(export)),binary_sha256=sha(binary),parent_payload_sha256=p['payload_sha256'],
            expected_harvest_fingerprint=p['expected_harvest_fingerprint'],expected_harvest_binary_sha256=p['expected_harvest_binary_sha256'],options={'reach_towns':[],'reach_defacto':options},fields=grids,point_csv=point_csv)
    np.savez_compressed(export/'food_checked_visits/fields.npz',**full_fields)
    manifest=export/'food_checked_visits.json';write(manifest,dict(version=1,status='optional_own_destination_cereal_and_full_provider_year_points',default_adoption=False,complete_provisioning_validated=False,packets=packets))
    if export.resolve()!=DATA.resolve():print('Fresh food-checked point exports generated without UI activation.');return
    files={str(path.relative_to(ROOT)):sha(path) for path in (DATA/'food_checked_visits').rglob('*') if path.is_file()};files[str(manifest.relative_to(ROOT))]=sha(manifest)
    receipt=dict(status='exported_food_checked_visit_maps',manifest_sha256=sha(manifest),results_sha256=sha(OUT/'results.json'),scenarios=8,files_sha256=files,
        producers={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'harvest/event_food_trace.py',ROOT/'scripts/publish_network_duty_visits.py']},
        prior_assets_preserved=len(result['unchanged_map_sha256']),ui_integration_snapshot_before=funded['ui_integration_snapshot_before'],defaults_unchanged=True)
    write(OUT/'map_exports.json',receipt)
    if activate:
        previous_publication=OUT/'atlas_publication.json'
        expected_ui=json.loads(previous_publication.read_text())['ui_integration_after'] if previous_publication.exists() else funded['ui_integration_snapshot_before']
        for name,digest in expected_ui.items():assert sha(ROOT/name)==digest,name
        page=DATA.parent/'index.html';html=page.read_text()
        if 'data-food-checked-visits-enabled' not in html:
            assert 'data-network-visit-year-complete-enabled' in html;html=html.replace('data-network-visit-year-complete-enabled','data-network-visit-year-complete-enabled data-food-checked-visits-enabled',1)
        page.write_text(html)
        for name in ('settled-reach.js','evidence.js'):shutil.copyfile(ROOT/'atlas'/name,DATA.parent/name)
        receipt['status']='activated_optional_food_checked_visit_maps';receipt['ui_integration_after']={name:sha(ROOT/name) for name in funded['ui_integration_snapshot_before']};write(OUT/'atlas_publication.json',receipt)
    print('Exported eight OWN-food-checked provider-year maps'+(';UI activated.' if activate else ';UI not activated yet.'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out-data',type=Path);p.add_argument('--activate',action='store_true');args=p.parse_args();main(args.out_data or DATA,args.activate)
