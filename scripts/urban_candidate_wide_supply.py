"""Exact release-4 supply controls, then the unadopted fixed-site seed-1 candidate."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'scripts')]
import build_wide_supply_release3 as B
from polity import release3_placement as P
from harvest.field_support import field_support

OUT = ROOT/'output/urban_candidate_supply_20261116'
BASE = ROOT/'output/urban_hierarchy_candidate_20261116'
RELEASE = ROOT/'output/settlement_release4_20261116'
PLAN = ROOT/'calibration/urban_diagnosis_20261116/candidate_supply_robustness.json'


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f,'sha256').hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def verify_previous():
    r=json.loads((BASE/'results.json').read_text()); review=json.loads((BASE/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(BASE/'results.json')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():
        assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():
        assert sha(BASE/name)==digest,name
    assert not r['adopt'] and not r['seasonal_origin_food_work_validated']
    return r


def main(out):
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert os.environ.get('ROTCLIMATE_FOREST_TRAVEL','0') in ('','0')
    previous=verify_previous(); archived=json.loads((RELEASE/'supply/results.json').read_text())
    B.EXTRACTION=(archived['marketed_share'],.10,archived['climates']['raw']['scenarios']['low_x14']['extraction'])
    B.HEADLINE=archived['headline']; B.EARTH=ROOT/'output/greek_walls_20261114/results.json'
    assert sha(B.EARTH)==archived['earth_calibration_sha256']
    assert sha(B.__file__)==archived['producer_sha256']
    assert sha(ROOT/'polity/wide_supply.py')==archived['model_sha256']
    out.mkdir(parents=True,exist_ok=True); cache=OUT/'network'; cache.mkdir(parents=True,exist_ok=True)
    inputs=[PLAN,Path(__file__),BASE/'results.json',BASE/'review.json',RELEASE/'supply/results.json',
            RELEASE/'release3/fantasy.json',ROOT/'scripts/build_wide_supply_release3.py',B.EARTH,
            ROOT/'harvest/field_support.py',ROOT/'output/supply_low_reading_20261114/results.json']
    inputs+=sorted((ROOT/'polity').glob('*.py'))
    sources={str(p.relative_to(ROOT)):sha(p) for p in inputs}
    protected=previous['protected_sha256']; packets={}; original=json.loads((RELEASE/'release3/fantasy.json').read_text())
    for label,folder in [('control','control'),('candidate','candidate')]:
        packet=out/'packets'/label;packet.mkdir(parents=True,exist_ok=True);packets[label]=packet
        for mode in ['raw','corrected']:
            for suffix in ['fields.npz','sites.json','towns.csv']:
                name=f'placed_{mode}_{suffix}';shutil.copyfile(BASE/folder/name,packet/name)
                sources[str((BASE/folder/name).relative_to(ROOT))]=sha(BASE/folder/name)
        if label=='control':
            (packet/'fantasy.json').write_bytes((RELEASE/'release3/fantasy.json').read_bytes())
        else:
            write(packet/'fantasy.json',dict(status='unadopted_fixed_site_seed1_downstream_input',
                adopt=False,gate=dict(passed=False),climates=previous['cases'],
                candidate_results_sha256=sha(BASE/'results.json'),
                scope='Downstream packet adapter only; no placement, climate, fit or adoption.'))
    # Rebuild the canonical freight world once per map. Cache float64 shares:
    # canonical supply NPZ stores only float32, insufficient for exact replay.
    canonical_network=B.network; network_receipts={}
    def network(mode):
        key={k:v for k,v in sources.items() if k not in [str(Path(__file__).relative_to(ROOT))]}
        stamp=cache/f'{mode}.json'; target=cache/f'{mode}.npz'
        if stamp.exists() and target.exists():
            receipt=json.loads(stamp.read_text())
            assert receipt['sources_sha256']==key and receipt['cache_sha256']==sha(target)
            with np.load(target) as z:
                a={k:z[k] for k in z.files}
            sites=json.loads((B.R3/f'placed_{mode}_sites.json').read_text())['sites']
            assert np.array_equal(a['nodes'],[s['node'] for s in sites])
            network_receipts[mode]=receipt
            return dict(land=a['land']),sites,a['nodes'],a['owner'],a['share'],a['between']
        assert B.R3==packets['control'],'Control freight world must be built first'
        print(mode,': rebuilding canonical fixed-node freight network',flush=True)
        r,sites,nodes,owner,share,between=canonical_network(mode)
        with np.load(B.R3/f'placed_{mode}_fields.npz') as z:
            assert np.array_equal(nodes,[s['node'] for s in sites])
            track_equal=bool(np.array_equal(r['world']['tracks'],z['tracks']))
        np.savez_compressed(target,land=r['land'],nodes=nodes,owner=owner,share=share,between=between,tracks=r['world']['tracks'])
        receipt=dict(sources_sha256=key,cache_sha256=sha(target),nodes=len(nodes),
            track_equals_placement_fields=track_equal,
            note='Canonical supply world replays release3 placement routing and track ordering; exact released supply outputs are the acceptance control. Float64 network reused only on identical fixed nodes and protected travel inputs.')
        write(stamp,receipt);network_receipts[mode]=receipt
        return r,sites,nodes,owner,share,between
    B.network=network; variants={}; control_exact=False
    try:
        for label in ['control','candidate']:
            if label=='candidate':assert control_exact
            B.R3=packets[label];P.OUT=B.R3;destination=out/label
            print(label,': running unchanged annual supply builder',flush=True)
            result=B.run(destination)
            if label=='control':
                assert result==archived,'Supply control differs from released receipt'
                for mode in ['raw','corrected']:
                    for name,digest in archived['climates'][mode]['outputs'].items():
                        assert sha(destination/name)==digest,(mode,name)
                control_exact=True
                print('All four released supply files and complete unrounded receipt EXACT',flush=True)
            variants[label]=result
        # Source/work diagnostics augment (never modify) canonical supply results.
        diagnostics={}; townarrays={}; differences=[]
        for label in variants:
            diagnostics[label]={}
            for mode in ['raw','corrected']:
                with np.load(packets[label]/f'placed_{mode}_fields.npz') as z:f={k:z[k] for k in z.files}
                with np.load(ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz') as z:x={k:z[k] for k in z.files}
                with np.load(out/label/f'supply_{mode}.npz') as z:
                    for k in z.files:
                        if k not in ['owner','share','between','nodes']:townarrays[f'{label}__{mode}__{k}']=z[k]
                land=f['land'].ravel(); potential=np.where(land,x['potential_kcal'],0.)
                diagnostics[label][mode]={}
                for key,s in variants[label]['climates'][mode]['scenarios'].items():
                    reading=s['density'];rural=f['rural_'+reading].ravel();need=rural*B.KCAL
                    w=field_support(potential,x['listed_hours'],x['reaping_hours'],rural_need_kcal=need,hours_worker_year=s['hours_worker_year'])
                    deficit=np.maximum(need-w.produced_kcal,0.);surplus=np.where(land,np.maximum(w.produced_kcal-need,0.),0.)
                    d=dict(rural_people=float(rural.sum()),rural_workers=float(w.workers.sum()),
                        rural_food_shortfall_person_years=float(deficit[land].sum()/B.KCAL),
                        cells_below_rural_need=int((land & (deficit>1e-6)).sum()),
                        production_forgone_person_years=float((potential-w.produced_kcal)[land].sum()/B.KCAL),
                        annual_hours_available=float(w.annual_hours_available[land].sum()),
                        annual_hours_used=float(w.annual_hours_used[land].sum()),
                        reaping_hours_available=float(w.reaping_hours_available[land].sum()),
                        reaping_hours_used=float(w.reaping_hours_used[land].sum()),
                        rural_need_person_years=float(need[land].sum()/B.KCAL),
                        source_surplus_person_years=float(surplus.sum()/B.KCAL),
                        marketed_person_years=float(surplus.sum()*s['extraction']/B.KCAL),
                        town_unfed_person_years=float(s['residents']-s['residents_fed']))
                    diagnostics[label][mode][key]=d
                    if label=='candidate':
                        old=variants['control']['climates'][mode]['scenarios'][key]
                        differences.append(dict(mode=mode,scenario=key,old_residents=old['residents'],new_residents=s['residents'],
                            old_fed_share=old['fed_share_of_residents'],new_fed_share=s['fed_share_of_residents'],
                            old_short_towns=old['short_towns'],new_short_towns=s['short_towns'],
                            old_fed=old['residents_fed'],new_fed=s['residents_fed'],
                            old_rural_food_shortfall=diagnostics['control'][mode][key]['rural_food_shortfall_person_years'],
                            new_rural_food_shortfall=d['rural_food_shortfall_person_years']))
        from urban_candidate_seed_sensitivity import table
        table(out/'comparison.csv',differences);np.savez_compressed(out/'town_model.npz',**townarrays)
        files=['comparison.csv','town_model.npz']
        for label in variants:
            files += [f'{label}/results.json',f'packets/{label}/fantasy.json']
            files += [f'{label}/supply_{mode}_towns.csv' for mode in ['raw','corrected']]
        for name,digest in protected.items():assert sha(ROOT/name)==digest,name
        write(out/'results.json',dict(status='reviewable_annual_wide_supply_candidate_not_seasonal_qualification',
            sources_sha256=sources,protected_sha256=protected,files_sha256={n:sha(out/n) for n in files},
            released_control_exact=True,variants=variants,diagnostics=diagnostics,comparison=differences,
            network=network_receipts,network_reused_between_models=True,
            scope='Canonical annual work-limited grain recipe at unchanged shares;new rural source needs/work in every variant. Seasonal travel cost sampling does not qualify seasonal continuous food/work feasibility.',
            adopt=False,main_atlas_published=False,seasonal_origin_food_work_validated=False))
    except Exception as error:
        write(out/'failure.json',dict(status='failed_preserved',error=f'{type(error).__name__}: {error}',
            completed=list(variants),released_control_exact=control_exact,sources_sha256=sources,adopt=False))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--out',type=Path,default=OUT)
    main(parser.parse_args().out)
