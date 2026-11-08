"""Publish recorded hierarchical communication scenarios to normal atlases."""
from pathlib import Path
import csv
import io
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from atlas_set import active as active_atlases  # noqa: E402  (free and Whittaker fits retired, 8 Nov 2026)

VIEWS=[('local_marked','Provincial reply · marked interchanges',0,'local'),
       ('local_proposed','Provincial reply · proposed transport',1,'local'),
       ('chain_marked','Imperial reply via province · marked',0,'chain'),
       ('chain_proposed','Imperial reply via province · proposed',1,'chain'),
       ('seasonality_marked','Seasonal range of imperial reply · marked',0,'seasonality'),
       ('proposed_gain','Imperial reply time saved by proposed transport',1,'gain')]


def main():
    import numpy as np
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from PIL import Image
    from polity.administrative_hierarchy import reply_times,LEGS
    from local_benchmark_protocol import file_hash,write_json
    origin=ROOT/'output/administrative_hierarchy_20261104';published=[]
    common=('Schematic links, not travel routes. Colours describe seats, not surrounding territory. '
        'Reply time holds one seasonal snapshot fixed, without processing delays or courier relays. '
        'Marked interchange locations are inferred, not proven harbours; the alternative adds proposed tracks and landings. '
        'Budgets update seat readouts, not political control. Uses a separate travel calculation from Imperial access. '
        'Two unresolved seats have no assigned times; see the methods for assumptions.')
    registry=None
    for name in active_atlases(['free_fit','earth_fit','whittaker_fit']):
        data=ROOT/'atlases'/name/'data';meta=json.loads((data/'atlas.json').read_text());packets={}
        for mode in ['raw']+(['corrected'] if meta.get('corrected_climate') else []):
            folder=origin/(name+'_'+mode);review=json.loads((folder/'review.json').read_text())
            for path,digest in {**review['sources_sha256'],**review['inputs_sha256']}.items():
                if file_hash(ROOT/path)!=digest:raise ValueError('Hierarchy audit source/input changed: '+path)
            if file_hash(folder/'links.npz')!=review['arrays_sha256']:raise ValueError('Hierarchy arrays changed')
            registry=review['registry'];links=registry['links'];by_id={c['commandery_id']:c for c in links}
            with np.load(folder/'links.npz') as saved:days=saved['days']
            local,chain=reply_times(days);prefix='' if mode=='raw' else 'corrected/';destination=data/prefix
            # Existing matching atlas mask supplies only the diagram background.
            from harvest.export import geometry
            shape=meta['arrays']['elev']['shape']
            geo,_=geometry(meta,shape);land=geo['land_fraction']>.5
            colours=['#276d69','#68a59a','#b6b568','#d2a560','#b67453','#8b4f52']
            options=[];images={}
            for key,label,scenario,quantity in VIEWS:
                view_colours=colours
                boundaries=[7,14,30,60,120]
                legends=['≤7 days','7–14','14–30','30–60','60–120','>120 days']
                if quantity in ['local','chain']:
                    field=np.max(local[scenario] if quantity=='local' else chain[scenario],axis=0)
                    detail='Longest reply time among the twelve model-month snapshots. '
                    if quantity=='local':detail+='A provincial capital has a zero local self-link; this does not measure service to its hinterland. '
                elif quantity=='seasonality':
                    field=np.max(chain[0],axis=0)-np.min(chain[0],axis=0)
                    boundaries=[1,3,7,14,30];legends=['≤1 day range','1–3','3–7','7–14','14–30','>30 days'];detail='Longest minus shortest frozen-month imperial reply time. '
                else:
                    field=np.max(chain[0],axis=0)-np.max(chain[1],axis=0)
                    boundaries=[.01,1,3,7,14];legends=['No material saving','0.01–1 day','1–3','3–7','7–14','>14 days'];detail='Reduction in the worst snapshot reply time after adding proposed transport; the worst months can differ between cases. '
                    view_colours=['#cac7bc','#bad4ca','#8fbeb0','#65a795','#3c8c80','#276d69']
                fig,ax=plt.subplots(figsize=(10,4.63),dpi=200)
                rgb=np.empty((*land.shape,3));rgb[:]=[.84,.89,.94];rgb[land]=[.94,.93,.89]
                ax.imshow(rgb,extent=(0,meta['width'],meta['height'],0))
                capital=by_id[registry['capital_id']]
                for c in links:
                    if c['status']!='located':continue
                    p=by_id[c['province_id']]
                    ax.plot([p['x'],c['x']],[p['y'],c['y']],c='white',lw=2.5,zorder=2)
                    ax.plot([p['x'],c['x']],[p['y'],c['y']],c='#63717a',lw=.65,ls='--',zorder=3)
                if quantity!='local':
                    for pid in registry['provinces'].values():
                        p=by_id[pid]
                        if p['status']!='located':continue
                        ax.plot([capital['x'],p['x']],[capital['y'],p['y']],c='white',lw=3,zorder=2)
                        ax.plot([capital['x'],p['x']],[capital['y'],p['y']],c='#76537b',lw=1,ls=':',zorder=3)
                for i,c in enumerate(links):
                    if c['status']!='located':continue
                    colour=view_colours[int(np.searchsorted(boundaries,field[i],side='left'))] if np.isfinite(field[i]) else '#33333d'
                    ax.scatter([c['x']],[c['y']],s=23,c=colour,edgecolors='white',linewidths=.7,zorder=5)
                    if c['local_self_link']:ax.scatter([c['x']],[c['y']],s=40,facecolors='none',edgecolors='#28343b',linewidths=.7,zorder=6)
                ax.annotate('Imperial capital',(capital['x'],capital['y']),xytext=(8,-15),textcoords='offset points',fontsize=7,
                    bbox=dict(boxstyle='round,pad=.2',fc='white',ec='#76537b',alpha=.9),zorder=7)
                ax.set_xlim(0,meta['width']);ax.set_ylim(meta['height'],0);ax.axis('off');fig.subplots_adjust(0,0,1,1)
                buf=io.BytesIO();fig.savefig(buf,format='png',dpi=200);plt.close(fig);buf.seek(0)
                filename='hierarchy_'+key+'.webp'
                Image.open(buf).convert('RGB').resize((meta['width'],meta['height'])).save(destination/filename,lossless=True)
                images[prefix+filename]=file_hash(destination/filename)
                options.append(dict(value=key,label=label,file=prefix+filename,scenario=scenario,quantity=quantity,
                    items=[dict(color=c,label=l) for c,l in zip(view_colours,legends)]+[dict(color='#33333d',label='No finite reply in a snapshot')],
                    note=detail+common,caption=detail))
            def clean(a):
                if isinstance(a,list):return [clean(v) for v in a]
                return a if np.isfinite(a) else None
            point_file=destination/'hierarchy_links.json';write_json(point_file,dict(days=clean(days.tolist()),leg_order=LEGS))
            grid=destination/'hierarchy_links.npz';shutil.copyfile(folder/'links.npz',grid)
            csvfile=destination/'hierarchy_links.csv'
            with csvfile.open('w',newline='',encoding='utf-8') as stream:
                keys=['climate','scenario','model_month','commandery_id','name','seat','province','province_seat','status',*LEGS,'provincial_reply_days','imperial_reply_days']
                writer=csv.DictWriter(stream,fieldnames=keys);writer.writeheader()
                for s,scenario in enumerate(review['scenarios']):
                    for m in range(12):
                        for i,c in enumerate(links):
                            row=dict(climate=mode,scenario=scenario,model_month=m+1,commandery_id=c['commandery_id'],name=c['name'],seat=c['seat_name'],
                                province=c['province'],province_seat=c['province_seat'],status=c['status'])
                            row.update({leg:float(v) if np.isfinite(v) else None for leg,v in zip(LEGS,days[s,m,i])})
                            row.update(provincial_reply_days=float(local[s,m,i]) if np.isfinite(local[s,m,i]) else None,
                                imperial_reply_days=float(chain[s,m,i]) if np.isfinite(chain[s,m,i]) else None)
                            writer.writerow(row)
            packets[mode]=dict(layers=[dict(id='hierarchy_links',label='Administrative links',group='Administration',kind='categories',controls=[],
                file=options[2]['file'],items=options[2]['items'],note=options[2]['note'],
                variants=dict(label='Communication view',default='chain_marked',options=options))],
                days_file=prefix+point_file.name,days_sha256=file_hash(point_file),grid=prefix+grid.name,grid_sha256=file_hash(grid),
                csv=prefix+csvfile.name,csv_sha256=file_hash(csvfile),image_sha256=images,
                expected_harvest_fingerprint=review['harvest_fingerprint'],
                expected_harvest_binary_sha256=review['inputs_sha256'][str((data/prefix/'harvest.bin').relative_to(ROOT))],
                scenarios=review['scenarios'],summaries=review['summaries'],audit_sha256=file_hash(folder/'review.json'))
        manifest=dict(version=1,status='isolated_recorded_hierarchy',registry=registry,packets=packets,budgets_days=[7,14,30,60],
            inventory_sha256=file_hash(data/'administrative_inventory.json'),publisher_sha256=file_hash(Path(__file__)))
        write_json(data/'administrative_hierarchy.json',manifest)
        published.append(dict(atlas=name,manifest_sha256=file_hash(data/'administrative_hierarchy.json')))
    write_json(origin/'presentation.json',dict(status='rendered',atlases=published,publisher_sha256=file_hash(Path(__file__))))
    print('Published six hierarchy views on each of four matching climate packets')


if __name__=='__main__':main()
