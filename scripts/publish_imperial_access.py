"""Render isolated imperial-access diagnostics into portable atlas extensions."""
from pathlib import Path
import csv
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


def main():
    import numpy as np
    from PIL import Image
    from matplotlib.colors import to_rgb
    from local_benchmark_protocol import file_hash,write_json
    origin=ROOT/'output/imperial_access_20261104'
    inventory_path=ROOT/'output/administrative_inventory_20261104/review.json'
    inventory=json.loads(inventory_path.read_text())
    labels=['Recorded commandery centres','Other marked places included','Proposed towns as sources',
        'Proposed tracks included','Roads also act as sources','Imperial forts and legion markers']
    cases=['recorded_centres','marked_places','proposed_towns','proposed_tracks','road_sources','forts_legions']
    palette=['#eee9df','#d8c8b2','#c6b593','#a1b8a3','#69998a','#286f70']
    summaries=[]
    for name in ['free_fit','earth_fit','whittaker_fit']:
        data=ROOT/'atlases'/name/'data';base=json.loads((data/'atlas.json').read_text());packets={}
        shutil.copyfile(inventory_path,data/'administrative_inventory.json')
        with (data/'imperial_centres.csv').open('w',newline='',encoding='utf-8') as stream:
            writer=csv.DictWriter(stream,fieldnames=['id','source_id','name','seat_name','status','map_name','marker_id','x','y','kind','source_hex','province','provincial_seat','discrepancies'])
            writer.writeheader()
            for record in inventory['commanderies']:writer.writerow({k:record.get(k) for k in writer.fieldnames})
        for mode in ['raw']+(['corrected'] if base.get('corrected_climate') else []):
            folder=origin/(name+'_'+mode);review=json.loads((folder/'review.json').read_text())
            for path,digest in {**review['sources_sha256'],**review['inputs_sha256']}.items():
                if file_hash(ROOT/path)!=digest:raise ValueError('Access audit source/input changed: '+path)
            if file_hash(folder/'fields.npz')!=review['arrays_sha256']:raise ValueError('Access arrays changed')
            with np.load(folder/'fields.npz') as saved:fields={key:saved[key] for key in saved.files}
            prefix='' if mode=='raw' else 'corrected/';destination=data/prefix
            land=fields['land'];images={}
            common=(f'Access scenario, not de facto ownership or allegiance. {review["matched_commanderies"]} of '
                f'{review["listed_commanderies"]} commandery centres have confirmed marker positions; other centres remain unresolved or inexact. '
                'Two-day person-travel threshold; twelve equal climatological model-month bins. Current central-density scenario and ports/river landings are fixed within each comparison. '
                'Displayed access can extend beyond painted imperial claims; summary percentages refer to land inside those claims. No force strength or food provisioning is inferred.')
            def render(key,values,bounds,legends,colors):
                values=np.asarray(values);code=np.searchsorted(bounds,values,side='right')
                rgb=np.asarray([to_rgb(c) for c in colors])[code]
                rgb[~land]=[.84,.89,.94]
                image='administration_'+key+'.webp';path=destination/image
                Image.fromarray(np.rint(rgb*255).astype('u1')).resize((base['width'],base['height']),Image.Resampling.NEAREST).save(path,lossless=True)
                images[prefix+image]=file_hash(path)
                return dict(value=key,file=prefix+image,items=[dict(color=c,label=l) for c,l in zip(colors,legends)])
            options=[]
            for i,(case,label) in enumerate(zip(cases,labels)):
                v=render(case,fields['accessible_months'][i],[.5,3.5,6.5,9.5,11.5],
                    ['0 accessible bins','1–3','4–6','7–9','10–11','All 12 bins'],palette)
                caption=(label+f' · {review["source_counts"][case]} source nodes. ')
                if i<3:caption+='Generated tracks omitted; other transport, including proposed-town port locations, held fixed.'
                elif i==3:caption+='Same sources as the previous case; only generated tracks added.'
                elif i==4:caption+='Same transport as the previous case; painted imperial road cells also become authority sources.'
                else:caption+='Travel access from 25 marked imperial forts and 14 legion locations; no troop numbers, campaign success or year-round presence established.'
                v.update(label=label,caption=caption,note=caption+' '+common);options.append(v)
            layers=[dict(id='admin_imperial_access',label='Imperial access',group='Administration',kind='categories',
                file=options[0]['file'],items=options[0]['items'],note=options[0]['note'],controls=[],
                variants=dict(label='Source scenario',default=cases[0],options=options))]
            diagnostics=[]
            v=render('isolation',fields['longest_isolation'][0],[.5,2.5,5.5,8.5,11.5],
                ['No isolated bins','1–2 consecutive bins','3–5','6–8','9–11','All 12 bins'],palette[::-1])
            v.update(label='Longest isolation · recorded centres',caption='Longest cyclic run outside two-day access to located commandery centres, including across the year boundary.',note='Longest isolation from recorded centres. '+common);diagnostics.append(v)
            count=fields['accessible_months'][0];annual=fields['annual_threshold'][0]
            category=np.where(count==0,0,np.where(count==12,1,np.where(annual,2,3)))
            v=render('annual_reliability',category,[.5,1.5,2.5],
                ['Never within two days','Within two days in all bins','Annual mean within cutoff, but seasonally isolated','Seasonal access; annual mean outside cutoff'],
                ['#ddd6ca','#286f70','#ca9251','#9d7b98'])
            v.update(label='Annual mean versus reliable access',caption='A favourable annual mean does not guarantee access throughout the seasonal year.',note='Annual exponential-mean access versus actual within-threshold bins. '+common);diagnostics.append(v)
            for key,label,earlier,later in [('town_gain','Gain from proposed town sources',1,2),('track_gain','Gain from proposed tracks',2,3),('road_gain','Gain from treating roads as sources',3,4)]:
                delta=fields['accessible_months'][later].astype(int)-fields['accessible_months'][earlier].astype(int)
                if np.any(delta<0):raise ValueError('Source/track scenario decreased threshold access')
                v=render(key,delta,[.5,2.5,5.5,8.5,11.5],['No added access','1–2 added bins','3–5','6–8','9–11','12 added bins'],
                    ['#eee9df','#dfd39f','#c2bd70','#93ad78','#60968a','#286f70'])
                v.update(label=label,caption=label+'; other inputs held fixed in this paired step.',note=label+'. '+common);diagnostics.append(v)
            layers.append(dict(id='admin_source_diagnostics',label='Source assumptions',group='Administration',kind='categories',
                file=diagnostics[0]['file'],items=diagnostics[0]['items'],note=diagnostics[0]['note'],controls=[],
                variants=dict(label='Diagnostic',default='isolation',options=diagnostics)))
            v=render('proposals',fields['proposal_recurrence'],[.5,1.5,2.5],
                ['No proposed town within 10 km in these runs','Town nearby in 1 of 3 runs','Town nearby in 2 of 3 runs','Town nearby in all 3 runs'],
                ['#eee9df','#c8d8c9','#7eaf9c','#286f70'])
            layers.append(dict(id='admin_settlement_alternatives',label='Settlement alternatives',group='Administration',kind='categories',
                file=v['file'],items=v['items'],controls=[],note='Recurrence within 10 km across declared placement seeds 1, 2 and 3, with climate, density, site rules and painted-claim eligibility fixed. '
                'These are administrative/market-town proposals under the existing seat-count model, not predictions of every village or city population. Frequency across three scenarios is not a calibrated probability.'))
            binary=bytearray(fields['access_masks'].astype('<u2').tobytes())
            annual_flags=np.zeros(land.shape,np.uint8)
            for i,a in enumerate(fields['annual_threshold']):annual_flags|=a.astype(np.uint8)<<i
            descriptors={};offset=len(binary)
            for key,array in [('annual_flags',annual_flags),('proposal_recurrence',fields['proposal_recurrence']),('land',land.astype(np.uint8))]:
                descriptors[key]=dict(offset=offset,dtype='uint8');binary.extend(array.astype('u1').tobytes());offset=len(binary)
            packet_file=destination/'administration.bin';packet_file.write_bytes(binary)
            grid=destination/'administration_grid.npz';shutil.copyfile(folder/'fields.npz',grid)
            packets[mode]=dict(layers=layers,cases=cases,case_labels=labels,source_counts=review['source_counts'],
                shape=review['shape'],cell_px=review['cell_px'],binary=prefix+packet_file.name,binary_sha256=file_hash(packet_file),
                access_masks=dict(offset=0,dtype='uint16',shape=[6]+review['shape']),fields=descriptors,
                expected_harvest_fingerprint=review['harvest_fingerprint'],
                expected_harvest_binary_sha256=review['inputs_sha256'][str((data/prefix/'harvest.bin').relative_to(ROOT))],
                grid=prefix+grid.name,grid_sha256=file_hash(grid),image_sha256=images,
                audit_review_sha256=file_hash(folder/'review.json'),summaries=review['summaries'],ensemble=review['ensemble'])
        manifest=dict(version=1,status='isolated_administrative_access_scenarios',packets=packets,
            matched_centres=inventory['matched_commanderies'],listed_centres=len(inventory['commanderies']),
            unresolved_centres=inventory['unresolved_commanderies'],inventory='administrative_inventory.json',
            inventory_sha256=file_hash(data/'administrative_inventory.json'),centres_csv='imperial_centres.csv',
            centres_csv_sha256=file_hash(data/'imperial_centres.csv'),publisher_sha256=file_hash(Path(__file__)),
            adopted_de_facto_ownership_changed=False,threshold_days=2.,seasonal_bins=12)
        write_json(data/'administrative_access.json',manifest)
        summaries.append(dict(atlas=name,manifest_sha256=file_hash(data/'administrative_access.json')))
    write_json(origin/'presentation.json',dict(status='rendered',atlases=summaries,publisher_sha256=file_hash(Path(__file__))))
    print('Rendered all four matching climate packets; legacy de facto ownership unchanged')


if __name__=='__main__':main()
