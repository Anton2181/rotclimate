"""Independent fixed-site residual/lore and finite annual people replay for five seeds."""
import csv
import hashlib
import inspect
import json
import math
from pathlib import Path
import sys

import numpy as np
from scipy.spatial.distance import cdist

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
import review_urban_hierarchy_candidate as R

OUT = ROOT/'output/urban_candidate_seeds_20261116'
BASE = ROOT/'output/urban_hierarchy_candidate_20261116'
SEEDS = [1, 7, 19, 43, 97]


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def close(a,b,atol=2e-6):
    np.testing.assert_allclose(a,b,atol=atol,rtol=1e-10)


def rows(path):
    with path.open() as f:
        return list(csv.DictReader(f))


def scalar_concentration(v):
    a = sorted(map(float,v)); total = math.fsum(a); n = len(a)
    return dict(total=total,largest=a[-1],top1_share=a[-1]/total,
                top10_share=math.fsum(a[-10:])/total,
                gini=math.fsum((2*i-n-1)*x for i,x in enumerate(a,1))/(n*total))


def main():
    result = json.loads((OUT/'results.json').read_text())
    prior = json.loads((BASE/'results.json').read_text())
    priorreview = json.loads((BASE/'review.json').read_text())
    assert priorreview['status']=='passed' and priorreview['reviewer_sha256']==sha(Path(R.__file__))
    for name,digest in {**result['sources_sha256'],**result['protected_sha256'],
                        **prior['sources_sha256'],**prior['protected_sha256']}.items():
        assert sha(ROOT/name)==digest,name
    for name,digest in result['files_sha256'].items():
        assert sha(OUT/name)==digest,name
    assert result['seeds']==SEEDS and result['size_draws']==20 and result['annual_population_cases']==40
    # Reuse the preceding independent scalar residual/lore reviewer, exposing
    # only its formerly fixed seed. The producer uses the canonical builder.
    source = inspect.getsource(R.application)
    old = 'model,bounds,cell):'; new = 'model,bounds,cell,seed):'
    assert source.count(old)==1 and source.count('np.random.default_rng(1)')==1
    adapted = source.replace(old,new).replace('np.random.default_rng(1)','np.random.default_rng(seed)')
    space = dict(np=np,math=math,cdist=cdist,close=R.close)
    exec(compile(adapted,'independent_seed_application','exec'),space)
    application = space['application']
    (OUT/'reviewer_application_snapshot.txt').write_text(adapted)
    with np.load(OUT/'model.npz') as z:
        compact = {k:z[k] for k in z.files}
    towns = rows(OUT/'seed_towns.csv'); intervals = rows(OUT/'town_intervals.csv'); cases = rows(OUT/'cases.csv')
    assert len(towns)==20870 and len(intervals)==2087 and len(cases)==40
    assert len(towns)==result['per_site_seed_rows']
    townlookup = {(t['mode'],t['model'],int(t['seed']),t['id']):t for t in towns}
    caselookup = {(t['mode'],t['model'],int(t['seed']),t['reading']):t for t in cases}
    assert len(townlookup)==len(towns) and len(caselookup)==len(cases)
    for csvcase,case in zip(cases,result['cases']):
        for key,v in case.items():
            if isinstance(v,(str,bool)) or v is None:
                assert csvcase[key]==('' if v is None else str(v))
            else:
                close(float(csvcase[key]),v)
    earth = dict(published=json.loads((ROOT/'output/settlement_release4_20261116/earth_results.json').read_text()),
                 candidate=json.loads((BASE/'candidate_earth.json').read_text()))
    assert earth['candidate']['adopt'] is False and earth['candidate']['sizes']['primary']['gate']['passed'] is False
    checked = 0; maxarea = 0.; maxrural = 0.; summaries = {}
    for mode in ['raw','corrected']:
        sites = json.loads((BASE/f'control/placed_{mode}_sites.json').read_text())['sites']
        symbols = [t['campaign_symbol'] for t in rows(BASE/f'control/placed_{mode}_towns.csv')]
        folder = ROOT/'atlases/earth_fit/data'/('corrected' if mode=='corrected' else '')
        with np.load(folder/'administration_grid.npz') as z:
            land = z['land']; density = z['density']
        cell = prior['cases'][mode]['cell_km']; people = np.where(land,density,0)*cell**2
        centres = np.array([(s['row'],s['column']) for s in sites])
        links = ROOT/'atlases/earth_fit/data'/('release3/hierarchy/corrected/hierarchy_links.csv' if mode=='corrected' else 'release3/hierarchy/hierarchy_links.csv')
        seats = {a['province_seat'] for a in rows(links)}
        capital = np.array([s['marked'] and s['name'] in seats for s in sites])
        H,loc,dest,weight = R.ownership(land,people,centres,cell)
        with np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz') as z:
            potential = z['potential_kcal']
        with np.load(BASE/f'control/placed_{mode}_fields.npz') as z:
            local,owner = z['collection_local'],z['collection_owner']
        for label in ['published','candidate']:
            primary = earth[label]['sizes']['primary']; model = primary['models']['M1C']
            prefix = f'{mode}__{label}__'
            for j,seed in enumerate(SEEDS):
                area,e = application(H,sites,symbols,capital,model,primary['area_range_ha'],cell,seed)
                close(compact[prefix+'area_ha'][j],area,atol=1e-7)
                close(compact[prefix+'residual'][j],e,atol=0)
                maxarea = max(maxarea,float(np.max(np.abs(compact[prefix+'area_ha'][j]-area))))
                folder = OUT/'cases'/mode/label/str(seed)
                with np.load(folder/f'placed_{mode}_fields.npz') as z:
                    fields = {k:z[k] for k in z.files}
                if seed==1:
                    ref = BASE/('control' if label=='published' else 'candidate')
                    for name in [f'placed_{mode}_fields.npz',f'placed_{mode}_towns.csv']:
                        assert sha(folder/name)==sha(ref/name)
                for key,a in compact.items():
                    if key.startswith(prefix):
                        np.testing.assert_array_equal(a[j],fields[key[len(prefix):]])
                for reading in ['central','low']:
                    expected = R.annual(area,H,people,land,centres,cell,loc,dest,weight,reading,potential,local,owner)
                    for k,field in [('residents','residents'),('rural','rural'),('moved','moved'),
                                    ('own','from_own_hinterland'),('wide','from_wider_region'),
                                    ('radius','wider_radius_km'),('support','local_support_share')]:
                        close(fields[field+'_'+reading],expected[k])
                    maxrural = max(maxrural,float(np.max(np.abs(fields['rural_'+reading]-expected['rural']))))
                    case = caselookup[(mode,label,seed,reading)]
                    for key,value in [('area_ha',math.fsum(area)),('requested',math.fsum(expected['wanted'])),
                        ('allocated',math.fsum(expected['residents'])),('unmet',math.fsum(np.maximum(expected['wanted']-expected['residents'],0))),
                        ('rural',math.fsum(expected['rural'].ravel())),('world_people',math.fsum(people.ravel())),
                        ('own',math.fsum(expected['own'])),('wide',math.fsum(expected['wide']))]:
                        close(float(case[key]),value)
                    for key,value in scalar_concentration(expected['residents']).items():
                        close(float(case['residents_'+key]),value)
                    assert int(case['local_supported'])==int((expected['support']>=1).sum())
                    assert int(case['local_import_dependent'])==int((expected['support']<1).sum())
                    assert case['rural_array_sha256']==hashlib.sha256(fields['rural_'+reading].tobytes()).hexdigest()
                    close(float(case['population_residual']),0,atol=1e-6)
                    assert expected['rural'].min()>=-1e-8
                    close(people.sum(),expected['residents'].sum()+expected['rural'].sum())
                for i,site in enumerate(sites):
                    row = townlookup[(mode,label,seed,site['id'])]
                    assert row['name']==site['name']
                    for key,a in compact.items():
                        if key.startswith(prefix):
                            close(float(row[key[len(prefix):]]),a[j,i],atol=1e-10)
                    checked += 1
                print('independent replay',mode,label,seed,flush=True)
        ratio = compact[f'{mode}__candidate__area_ha']/compact[f'{mode}__published__area_ha']
        ir = [t for t in intervals if t['mode']==mode]; assert len(ir)==len(sites)
        for i,(row,site) in enumerate(zip(ir,sites)):
            assert row['id']==site['id'] and row['name']==site['name'] and row['marked']==str(site['marked'])
            close(float(row['ratio_gt2_fraction']),(ratio[:,i]>2).mean(),atol=1e-12)
            close(float(row['ratio_lt_half_fraction']),(ratio[:,i]<.5).mean(),atol=1e-12)
            # Scalar order statistics with linear interpolation, independent
            # of the producer's np.quantile calls.
            vectors = {'paired_area_ratio':ratio[:,i]}
            for label in ['published','candidate']:
                for field in ['area_ha','residents_central','residents_low']:
                    vectors[label+'_'+field]=compact[f'{mode}__{label}__{field}'][:,i]
            for key,a in vectors.items():
                a = sorted(map(float,a))
                for q,suffix in [(.1,'p10'),(.5,'p50'),(.9,'p90')]:
                    pos = q*4; low = int(pos); t = pos-low
                    expected = a[low]*(1-t)+a[min(low+1,4)]*t
                    close(float(row[key+'_'+suffix]),expected,atol=1e-10)
        summaries[mode] = dict(sites=len(sites),seed1_gt2=int((ratio[0]>2).sum()),
            seed1_lt_half=int((ratio[0]<.5).sum()),
            majority_seeds_gt2=int(((ratio>2).sum(0)>=3).sum()),all_seeds_gt2=int((ratio>2).all(0).sum()),
            majority_seeds_lt_half=int(((ratio<.5).sum(0)>=3).sum()),all_seeds_lt_half=int((ratio<.5).all(0).sum()),
            median_paired_ratio=float(np.median(np.median(ratio,axis=0))))
    assert result['summary']==summaries
    assert not any(result[k] for k in ['wider_supply_rebuilt','seasonal_origin_food_work_validated','adopt','main_atlas_published'])
    for name in ['results.json',*result['files_sha256']]:
        assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name
    report = dict(status='passed',reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),
        method='Canonical producer replay checked with previous independent scalar application/annual reviewer; only expose application seed; full-distance ownership recomputed. Scalar concentration and quantile interpolation; all CSV/compact/cached rural arrays; fresh compact artifacts byte-exact.',
        previous_reviewer_sha256=sha(Path(R.__file__)),application_adapter_sha256=sha(OUT/'reviewer_application_snapshot.txt'),
        size_draws=20,annual_population_cases=40,site_seed_rows=checked,
        max_area_difference_ha=maxarea,max_rural_people_difference=maxrural,
        seed1_published_and_candidate_files_exact=True,
        seasonal_origin_food_work_validated=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
