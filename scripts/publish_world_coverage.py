"""Publish the worldwide source audit as one dynamic atlas layer."""
from pathlib import Path
import csv
import gzip
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]

VIEWS=[('coverage','Seasonal access','Bins with outward and return access to the same site, within the selected per-leg budget.'),
       ('isolation','Longest access gap','Longest cyclic run without that same-site two-way access, including across the year boundary.'),
       ('overlap','Overlapping reach','Bins when at least two actors have same-site two-way reach here; this does not establish conflict.'),
       ('source_gain','Dependence on extra sources','Bins covered only after adding claim-assigned and generated sources. A missing actor baseline remains unscored.'),
       ('direction_gap','Outward access without same-site return','Bins with outward access but no return to that same site within the per-leg budget.'),
       ('unknown','Unaffiliated marked sites','Two-way access from marked sites with unresolved affiliation; this does not infer local sovereignty or a new polity.')]


def load_fields(folder,review):
    import numpy as np
    raw=gzip.decompress((folder/'coverage.bin.gz').read_bytes())
    if len(raw)!=review['raw_bytes']:raise ValueError('Invalid coverage byte length')
    h,w=review['shape'];n=review['land_cells']
    lookup=np.frombuffer(raw,dtype='<u4',count=h*w).reshape(h,w)
    words=np.frombuffer(raw,dtype='<u4',count=int(np.prod(review['words_shape'])),offset=review['offsets']['words']).reshape(review['words_shape'])
    unknown=np.frombuffer(raw,dtype='<u4',count=2*n,offset=review['offsets']['unknown']).reshape(2,n)
    return lookup,words,unknown


def main():
    import numpy as np
    from PIL import Image
    from matplotlib.colors import to_rgb
    from polity.coverage_audit import aggregate_words,seasonal_mask
    from polity.fields import polity_fills
    from local_benchmark_protocol import file_hash,write_json
    origin=ROOT/'output/world_coverage_20261104';published=[]
    labels=['Evidence-linked marked sites','Add claim-assigned marked sites','Add generated sites']
    items=[dict(color=c,label=l) for c,l in zip(['#eee9df','#d8c8b2','#c6b593','#a1b8a3','#69998a','#286f70'],
        ['No modelled access bins','1–3 bins','4–6','7–9','10–11','All 12 bins'])]
    pop=np.array([i.bit_count() for i in range(4096)],np.uint8)
    for name in ['free_fit','earth_fit','whittaker_fit']:
        data=ROOT/'atlases'/name/'data';meta=json.loads((data/'atlas.json').read_text());packets={}
        for mode in ['raw']+(['corrected'] if meta.get('corrected_climate') else []):
            folder=origin/(name+'_'+mode);review=json.loads((folder/'review.json').read_text())
            for p,h in {**review['inputs_sha256'],**review['sources_sha256']}.items():
                if file_hash(ROOT/p)!=h:raise ValueError('Coverage source/input changed: '+p)
            if file_hash(folder/'coverage.bin.gz')!=review['binary_sha256']:raise ValueError('Coverage grid changed')
            lookup,words,unknown=load_fields(folder,review);prefix='' if mode=='raw' else 'corrected/';destination=data/prefix
            shutil.copyfile(folder/'coverage.bin.gz',destination/'coverage.bin.gz')
            mask=seasonal_mask(aggregate_words(words[0,:,1]),1);count=pop[mask]
            rgb=np.empty((*lookup.shape,3));rgb[:]=[.84,.89,.94]
            rgb[lookup>0]=np.array([to_rgb(i['color']) for i in items])[np.searchsorted([.5,3.5,6.5,9.5,11.5],count)]
            image=destination/'coverage_preview.webp';Image.fromarray(np.rint(rgb*255).astype('u1')).resize((meta['width'],meta['height']),Image.Resampling.NEAREST).save(image,lossless=True)
            ids,info=polity_fills(lookup.shape);records=[]
            for original in review['records']:
                record=dict(original)
                if 'node' in record:
                    d=info.get(int(ids.ravel()[record['node']]),{});record['painted_claim_actor']=d.get('name')
                records.append(record)
            registry=destination/'coverage_sources.json';write_json(registry,dict(actors=review['actors'],records=records,
                unknown_marked_sites=review['unknown_marked_sites'],aliases=json.loads((ROOT/'data/polity_affiliation_aliases.json').read_text())))
            csvfile=destination/'coverage_sources.csv'
            with csvfile.open('w',newline='',encoding='utf-8') as stream:
                writer=csv.DictWriter(stream,fieldnames=['id','name','kind','status','actor','painted_claim_actor','scenario_actor','scenario_basis','x','y','node','signals'])
                writer.writeheader()
                for r in records:writer.writerow({k:json.dumps(r.get(k),ensure_ascii=False) if k=='signals' else r.get(k) for k in writer.fieldnames})
            common=('Access from provisional source inventories, not sovereignty or absence of local communities. '
                'Each outward and return journey must use the same site within the selected per-leg budget. '
                'Overlap means simultaneous travel reach, not observed conflict. All scenarios share modelled transport, including proposed tracks and landings. '
                'Actors with no source inventory remain unscored. Roads are transport, never authority sources in this audit.')
            options=[dict(value=k,label=l,file=prefix+image.name,items=items,note=common,caption=caption) for k,l,caption in VIEWS]
            layer=dict(id='reach_coverage_audit',label='Coverage audit',group='Political reach',kind='categories',controls=[],
                file=prefix+image.name,items=items,note=common,coverage_dynamic=True,
                variants=dict(label='Audit view',default='coverage',options=options))
            packets[mode]=dict(layers=[layer],actors=review['actors'],shape=review['shape'],cell_px=review['cell_px'],land_cells=review['land_cells'],
                words_shape=review['words_shape'],offsets=review['offsets'],raw_bytes=review['raw_bytes'],budgets_days=review['budgets_days'],
                scenarios=review['scenarios'],scenario_labels=labels,unknown_marked_sites=review['unknown_marked_sites'],
                binary=prefix+'coverage.bin.gz',binary_sha256=file_hash(destination/'coverage.bin.gz'),compression='gzip',
                preview_sha256=file_hash(image),registry=prefix+registry.name,registry_sha256=file_hash(registry),
                sources_csv=prefix+csvfile.name,sources_csv_sha256=file_hash(csvfile),
                expected_harvest_fingerprint=review['expected_harvest_fingerprint'],
                expected_harvest_binary_sha256=review['inputs_sha256'][str((data/prefix/'harvest.bin').relative_to(ROOT))],
                summaries=review['summaries'],audit_review_sha256=file_hash(folder/'review.json'))
        manifest=dict(version=1,status='isolated_worldwide_source_and_seasonal_audit',packets=packets,publisher_sha256=file_hash(Path(__file__)),
            no_new_ownership_or_strength_model=True,scope='Evidence-linked sites, claim-only affiliation additions and generated-source sensitivity. Sources are provisional map/game evidence; no evidence-based probability or sovereignty assignment.')
        write_json(data/'coverage.json',manifest);published.append(dict(atlas=name,manifest_sha256=file_hash(data/'coverage.json')))
    write_json(origin/'presentation.json',dict(status='rendered',atlases=published,publisher_sha256=file_hash(Path(__file__))))
    print('Published four matching compressed coverage packets; one button/six dynamic views')


if __name__=='__main__':main()
