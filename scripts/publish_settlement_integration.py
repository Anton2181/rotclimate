"""Publish joint settlement/food/source scenarios inside the existing two modes."""
from pathlib import Path
import argparse
import gzip
import json
import shutil
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]


EARTH_CONTROL=ROOT/'output/earth_control_20261106/results.json'


def earth_test(case):
    """One sentence with the end-to-end Earth control result of a food case, if that test has run."""
    if not EARTH_CONTROL.exists():return ''
    r=json.loads(EARTH_CONTROL.read_text())['regions']
    if case not in r['rome']['cases']:return ''
    a,b=r['rome']['cases'],r['han']['cases']
    return (f" Earth control test (reports/EARTH_CONTROL_20261106.md): staffs {a[case]['staffed_share']:.0%} of Rome's towns and {b[case]['staffed_share']:.0%} of Han's county seats;"
            f" extent balanced accuracy {a[case]['all']['ba']:.2f} (Rome) and {b[case]['all']['ba']:.2f} (Han) against {a['legacy_0']['all']['ba']:.2f} and {b['legacy_0']['all']['ba']:.2f} for the transport-only map.")


def main():
    import numpy as np
    from PIL import Image,ImageDraw
    from matplotlib.colors import to_rgb
    from local_benchmark_protocol import file_hash,write_json
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--origin',type=Path,default=ROOT/'output/settlement_integration_20261104');args=parser.parse_args()
    origin=args.origin.resolve();published=[]
    note=('Scenario: finite local cereal supports requested civilians and a resident institutional cohort in ONE repeating food budget. '
        'Only feasible affiliated cohorts emit two-way seasonal reach. Same candidates and transport in every case; no population-to-power multiplier. '
        'Proposed sites inherit painted-claim hypotheses; marked evidence takes precedence. Missing sources or local grain support do not prove empty land or lost sovereignty. '
        'Other staples, livestock food, maritime grain imports, water volumes and complete household/draft labour are not yet integrated. See the selected-site ledger and methods.')
    for name in ['free_fit','earth_fit','whittaker_fit']:
        data=ROOT/'atlases'/name/'data';meta=json.loads((data/'atlas.json').read_text());packets={}
        for mode in ['raw']+(['corrected'] if meta.get('corrected_climate') else []):
            out=origin/(name+'_'+mode);review=json.loads((out/'review.json').read_text())
            for p,h in {**review['sources_sha256'],**review['inputs_sha256']}.items():
                if file_hash(ROOT/p)!=h:raise ValueError('Changed settlement source: '+p)
            for p,h in review['artifacts_sha256'].items():
                if file_hash(out/p)!=h:raise ValueError('Changed settlement artifact: '+p)
            prefix='corrected/' if mode=='corrected' else '';folder=data/prefix
            model=json.loads(gzip.decompress((out/'settled_reach.json.gz').read_bytes()))
            raw=gzip.decompress((out/'settled_reach.bin.gz').read_bytes());h,w=review['shape'];size=h*w
            lookup=np.frombuffer(raw,'<u4',count=size);assignment=np.frombuffer(raw,'<u2',count=size,offset=review['offsets']['catchments'])
            masks=np.frombuffer(raw,'<u2',offset=review['offsets']['masks']).reshape(review['masks_shape']);land=lookup>0
            if len(raw)!=review['raw_bytes']:raise ValueError('Invalid settlement grid layout')
            pop=np.array([i.bit_count() for i in range(4096)],np.uint8);colors=np.array([to_rgb(a['color']) for a in model['actors']]);options={'reach_towns':[],'reach_defacto':[]}
            for k,c in enumerate(model['cases']):
                c=dict(c,label=c['label'].replace('; default',''))   # the default is chosen in the viewer (Earth control test)
                case_note=note
                if c.get('labour_constrained'):case_note+=' Listed cereal field work also limits complete cropped hectares. Rural food claims remain fixed when production falls; see the field-work summary and cell audit.'
                if c.get('fertility_constrained'):
                    fs=c['fertility_summary'];case_note+=(f" Soil fertility: equilibrium wheat/barley grain from the Earth-tested soil-fertility state at the AD 200 non-fertilizer N input ({c['input_n_kg_ha_yr']} kg N/ha/yr), "
                        f"{fs['production_ratio']*100:.1f}% of the previous chain's cereal (cell factor median {fs['factor_median']:.2f}, 10-90% {fs['factor_p10']:.2f}-{fs['factor_p90']:.2f})."
                        +(f" Three-field rotation with {c['transfer_t_ha']:.1f} t/ha FYM-equivalent carried to each crop." if c['regime']=='transfer' else
                          ' Three-field rotation with bare fallow and no nutrient transfer; it keeps the Han AD 2 census fit and improves the 11-region Earth census check.' if c['regime']=='bare' else ' Three-field rotation with a clover third, no manure (sensitivity).')

                        +' Rothamsted soil assumed everywhere; rural food claims remain fixed. See reports/FERTILITY_INTEGRATION_20261106.md.')
                case_note+=earth_test(c['id'])
                residents=np.array(c['civilian_people'])+np.array(c['institutional_people']);request=np.array([s['civilian_request_people'] for s in model['sites']]);retained=np.minimum(1,np.array(c['civilian_people'])/request)
                rgb=np.zeros((size,3));rgb[:]=[.84,.89,.94];rgb[land]=[.84,.83,.78]
                assigned=assignment>0;ratio=retained[assignment[assigned]-1]
                rgb[assigned]=np.array([.89,.85,.76])*(1-ratio[:,None])+np.array([.47,.66,.58])*ratio[:,None]
                im=Image.fromarray(np.rint(rgb.reshape(h,w,3)*255).astype('u1')).resize((meta['width'],meta['height']),Image.Resampling.NEAREST);draw=ImageDraw.Draw(im)
                for j,s in enumerate(model['sites']):
                    x=(s['column']+.5)*review['cell_px'];y=(s['row']+.5)*review['cell_px'];radius=max(1.5,min(8,1.2+np.sqrt(residents[j])/22))
                    fill=model['actors'][s['actor_index']]['color'] if s['actor_index']>=0 else '#59636b'
                    if not c['community_viable'][j]:
                        if s['marked']:draw.rectangle((x-2,y-2,x+2,y+2),outline='#222222',width=1)
                        continue
                    draw.ellipse((x-radius,y-radius,x+radius,y+radius),fill=fill,outline='white',width=1)
                    if c['institutional_active'][j]:draw.point((x,y),fill='#111111')
                filename='settled_towns_'+c['id']+'.webp';im.save(folder/filename,lossless=True)
                townitems=[dict(color='#78a895',label='Catchment tint: fraction of civilian request supported'),dict(color='#59636b',label='Circles: allocated resident scenario; dark centre: feasible cohort'),dict(color='#d6d4c7',label='Unassigned/scenario unsupported; actual inhabitants unknown')]
                options['reach_towns'].append(dict(value=c['id'],label=c['label'],file=prefix+filename,file_sha256=file_hash(folder/filename),items=townitems,note=case_note,integrated_support=True,caption='Local cereal-dependent allocation; reference requests are assumptions, not measured city sizes.'))
                counts=pop[masks[k]];winner=counts.argmax(0);best=counts.max(0);allbins=pop[np.bitwise_or.reduce(masks[k],axis=0)];overlap=np.sum(counts>0,axis=0)>1
                rgb[:]=[.84,.89,.94];base=np.tile([.89,.87,.81],(len(best),1));alpha=best/12*.8
                rgb[land]=base*(1-alpha[:,None])+colors[winner]*alpha[:,None]
                # A pale check marks areas reached by multiple actors at some
                # time; bins need not coincide. Exact masks remain downloadable.
                indices=np.flatnonzero(land);pattern=((indices//w+indices%w)%5==0)&overlap
                rgb[indices[pattern]]=rgb[indices[pattern]]*.65+.35
                im=Image.fromarray(np.rint(rgb.reshape(h,w,3)*255).astype('u1')).resize((meta['width'],meta['height']),Image.Resampling.NEAREST)
                filename='settled_control_'+c['id']+'.webp';im.save(folder/filename,lossless=True)
                reachitems=[dict(color=a['color'],label=a['name']) for a in model['actors']]+[dict(color='#e3decf',label='No modelled reach; local organization unscored')]
                options['reach_defacto'].append(dict(value=c['id'],label=c['label'],file=prefix+filename,file_sha256=file_hash(folder/filename),items=reachitems,note=case_note,integrated_support=True,caption='Hue: actor with most access bins (ties use fixed registry order). Tint: its 0–12 bins. Pale checks: multiple actors reach here at some time; this is not proof of conflict or sovereignty.'))
            v2=folder/'settled_control_v2_joint365.webp'; v2s=ROOT/'output/control_v2_20261107'/f'{name}_{mode}'/'summary.json'
            if v2.exists() and v2s.exists():
                # control map v2 (scripts/build_control_v2.py): passed the frozen blind test plan_blind2.json
                vs=json.loads(v2s.read_text())
                options['reach_defacto'].insert(0,dict(value='v2_joint365',label='Food-supported reach v2 · joint budget + the roads staffed towns keep',file=prefix+v2.name,file_sha256=file_hash(v2),
                    items=[dict(color=a['color'],label=a['name']) for a in model['actors']]+[dict(color='#e3decf',label='Not held: no staffed town or kept road within 2 year-round days')],
                    note=(f"Held where the nearest polity's staffed towns (joint food budget: {vs['staffed']} of {vs['sites']} sites) or the painted roads within 2 year-round days of them are within 2 days over the year. "
                          f"{vs['held_land_share']*100:.0f} % of land held. Earth tests: Rome AD 150 (development) 0.835 against 0.820 for transport only; blind on Chinese county seats, Western Jin AD 280 0.707 against 0.710 and Ming AD 1580 0.787 against 0.789, with 98-99 % of seats fed. See reports/EARTH_CONTROL_20261106.md."),
                    integrated_support=False,caption='Hue: the polity whose staffed towns and kept roads are nearest (year-round days <= 2). Food decides which towns are staffed; extent rule from the Earth tests.'))
            v21=folder/'settled_control_v21_joint365.webp'; v21s=ROOT/'output/control_v21_20261107'/f'{name}_{mode}'/'summary.json'
            if v21.exists() and v21s.exists():
                # control map v2.1 (scripts/build_control_v21.py): v2 + enclosed pockets, adopted by the blind test of
                # calibration/geography_control_20261107/plan_A.json
                vs=json.loads(v21s.read_text())
                options['reach_defacto'].insert(0,dict(value='v21_joint365',label='Food-supported reach v2.1 · v2 with enclosed land as territory',file=prefix+v21.name,file_sha256=file_hash(v21),
                    items=[dict(color=a['color'],label=a['name']) for a in model['actors']]+[dict(color='#c9b9c9',label='Hatched: unadministered upland / forest inside a polity (scenario)'),dict(color='#d9d2c6',label='Light tint and fine line: painted claim, not held'),dict(color='#e3decf',label='Not held, unclaimed')],
                    note=(f"Control v2, with every pocket wholly enclosed by one polity's held land as its territory: {vs['held_land_share']*100:.0f} % of land held, "
                          f"{vs['unadministered_share']*100:.1f} % unadministered upland or forest (pockets steeper, more forested or emptier than the polity's held land); "
                          f"desert or empty pockets ({vs.get('desert_hole_share', 0)*100:.1f} % of land; median P/PET < 0.2 or < 0.5 people/km2) stay holes. "
                          "Earth tests (calibration/geography_control_20261107/plan_A.json): development Rome AD 150 + Han AD 2; blind Song China AD 1080 0.737 and the late-antique Mediterranean AD 550 0.774, against 0.697 and 0.766 for v2. "
                          "Borders are drawn as lines over the relief; patches under 3 cells are merged. See reports/GEOGRAPHY_CONTROL_PLAN_20261107.md."),
                    integrated_support=False,caption='Fill: the polity whose staffed towns and kept roads are nearest (year-round days <= 2), plus the land it wholly encloses. Hatching: enclosed but ungoverned. Light tint: your painted claim where it is not held. Dark lines: borders of held territory.'))
            for filename in ['settled_reach.json.gz','settled_reach.bin.gz']:shutil.copyfile(out/filename,folder/filename)
            packets[mode]=dict(shape=review['shape'],cell_px=review['cell_px'],land_cells=review['land_cells'],masks_shape=review['masks_shape'],offsets=review['offsets'],raw_bytes=review['raw_bytes'],options=options,
                payload=prefix+'settled_reach.json.gz',payload_sha256=file_hash(folder/'settled_reach.json.gz'),binary=prefix+'settled_reach.bin.gz',binary_sha256=file_hash(folder/'settled_reach.bin.gz'),
                expected_harvest_fingerprint=review['expected_harvest_fingerprint'],expected_harvest_binary_sha256=review['inputs_sha256'][str((folder/'harvest.bin').relative_to(ROOT))],summary=review['summary'],review_sha256=file_hash(out/'review.json'))
            if (out/'field_support.npz').exists():packets[mode]['field_support']='../../'+str((out/'field_support.npz').relative_to(ROOT));packets[mode]['field_support_sha256']=file_hash(out/'field_support.npz')
        write_json(data/'settled_reach.json',dict(version=1,packets=packets,publisher_sha256=file_hash(Path(__file__)),status='conditional_food_settlement_source_integration'))
        published.append(dict(atlas=name,manifest_sha256=file_hash(data/'settled_reach.json')))
    write_json(origin/'presentation.json',dict(status='published',atlases=published))
    print('Updated existing settlements and de facto modes; all four climate packets')


if __name__=='__main__':main()
