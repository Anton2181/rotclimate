"""Rebuild the unchanged release on fixed sites before a candidate is interpreted."""
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
import settlement_fantasy_inputs as I
import settlement_hierarchy_map as M
from polity import settlement_sizes as Z
from polity.settlement_locations import prior_tiling_sites

BASE=ROOT/'output/urban_hierarchy_refresh_20261116'
RELEASE=ROOT/'output/settlement_release4_20261116'
OUT=ROOT/'output/urban_hierarchy_candidate_20261116'
PLAN=ROOT/'calibration/urban_diagnosis_20261116/hierarchy_candidate_build.json'
AMENDMENT=PLAN.parent/'hierarchy_candidate_metadata_a1.json'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert subprocess.check_output(['git','show','HEAD:'+str(AMENDMENT.relative_to(ROOT))],cwd=ROOT)==AMENDMENT.read_bytes()
    previous=json.loads((BASE/'results.json').read_text());review=json.loads((BASE/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(BASE/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_hierarchy_refresh.py')
    for name,digest in {**previous['producers'],**previous['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in previous['files_sha256'].items():assert sha(BASE/name)==digest,name
    original=json.loads((RELEASE/'release3/fantasy.json').read_text());earth=json.loads((RELEASE/'earth_results.json').read_text())
    protected=dict(previous['protected_sha256']);protected.update(previous['producers'])
    for name in ['results.json','review.json',*previous['files_sha256']]:protected[str((BASE/name).relative_to(ROOT))]=sha(BASE/name)
    for p in (ROOT/'atlases/earth_fit').rglob('*'):
        if p.is_file():protected[str(p.relative_to(ROOT))]=sha(p)
    historical=OUT/'failed_metadata_control/archived_atlas.json';current=ROOT/'atlases/earth_fit/data/atlas.json'
    oldmeta=json.loads(historical.read_text());newmeta=json.loads(current.read_text())
    for meta in [oldmeta,newmeta]:
        meta['layers']=[v for v in meta['layers'] if v.get('id')!='land_forest']
        meta['corrected_climate']['layers']=[v for v in meta['corrected_climate']['layers'] if v.get('id')!='land_forest']
    assert oldmeta==newmeta,'Metadata changes exceed declared forest display descriptors'
    assert sha(historical)==original['climates']['raw']['inputs']['atlases/earth_fit/data/atlas.json']
    metadata_delta=dict(historical_atlas_sha256=sha(historical),current_atlas_sha256=sha(current),only_removed_layer_id='land_forest',exact_after_scoped_removal=True,amendment_sha256=sha(AMENDMENT))
    inputs=[Path(__file__),PLAN,AMENDMENT,historical,ROOT/'scripts/settlement_fantasy_inputs.py',ROOT/'scripts/settlement_hierarchy_map.py',ROOT/'scripts/build_settlement_release2.py',
            ROOT/'scripts/build_settlement_release3.py',ROOT/'polity/settlement_locations.py',RELEASE/'release3/fantasy.json',RELEASE/'earth_results.json']
    (OUT/'control').mkdir(parents=True,exist_ok=True);(OUT/'prepared').mkdir(parents=True,exist_ok=True)
    module=M.patched_build();Z.MODELS['M1C']=('lnH','capital');controls={};identities={};geometry={}
    try:
        for mode in ['raw','corrected']:
            print(mode,':reading fixed published geometry',flush=True)
            w=I.world(mode);source=RELEASE/f'release3/placed_{mode}_sites.json';packet=json.loads(source.read_text());sites=packet['sites']
            assert len(sites)==original['climates'][mode]['sites']
            spec=json.loads(gzip.decompress((w['folder']/'settled_reach.json.gz').read_bytes()))['specification']
            owner=I.collection_owner(w,[s['node'] for s in sites],spec['collection_base_bin'],spec['collection_maximum_days_each_way']);local=np.flatnonzero(owner>=0)
            # Recover only the original track-input order,at the archived seat
            # parameter. It is a fixed-placement replay,not a new placement fit.
            kwargs=dict(allowed=w['claimed'],aridity=w['aridity'],marked=w['marked'],dry_water_km=w['dry_water_km'],prior=w['prior'],seat_people=original['climates'][mode]['placement']['seat_people'])
            oldenv=os.environ.get('ROTCLIMATE_CONFLUENCE_K');os.environ['ROTCLIMATE_CONFLUENCE_K']='1.0'
            try:towns=prior_tiling_sites(w['density'],w['land'],w['water_km'],w['road'],w['elev'],w['cell'],**kwargs)
            finally:
                if oldenv is None:os.environ.pop('ROTCLIMATE_CONFLUENCE_K',None)
                else:os.environ['ROTCLIMATE_CONFLUENCE_K']=oldenv
            assert set(map(tuple,towns))=={(s['row'],s['column']) for s in sites if not s['marked']},'Fixed-placement replay differs'
            print(mode,':reconstructing identical tracks and collection inputs',flush=True)
            tracks=I.tracks(w,towns);assert int(tracks.sum())==original['climates'][mode]['placement']['track_cells']
            prepared=OUT/f'prepared/{mode}.npz'
            np.savez_compressed(prepared,local=local,catchment=owner[local],tracks=tracks,prior=w['prior'],claimed=w['claimed'],density=w['density'],marked_cells=np.array(w['marked']))
            (OUT/f'control/placed_{mode}_sites.json').write_bytes(source.read_bytes())
            custom=dict(sites=sites,local=local,catchment=owner[local],prefix='placed',extra=dict(tracks=tracks,prior=w['prior'],claimed=w['claimed'],density=w['density'],marked_cells=np.array(w['marked'])))
            print(mode,':replaying published hierarchy and annual ledgers',flush=True)
            result=module.build(mode,copy.deepcopy(earth),OUT/'control',custom=custom)
            result['outputs'][source.name]=sha(source)
            expected=original['climates'][mode]
            for key,value in result.items():
                if key!='inputs':assert value==expected[key],f'{mode}:{key} differs from released summary'
            actual_inputs=dict(result['inputs']);expected_inputs=dict(expected['inputs'])
            assert actual_inputs.pop('atlases/earth_fit/data/atlas.json')==sha(current)
            assert expected_inputs.pop('atlases/earth_fit/data/atlas.json')==sha(historical)
            assert actual_inputs==expected_inputs,'Computational input receipt differs'
            for name,digest in expected['outputs'].items():
                assert sha(OUT/'control'/name)==digest,f'{mode}:{name} differs from released bytes'
                identities[str((OUT/'control'/name).relative_to(ROOT))]=digest
            controls[mode]=result;geometry[mode]=dict(collection_origins=len(local),track_cells=int(tracks.sum()),fixed_sites=len(sites),archived_seat_people=kwargs['seat_people'],track_order_replayed_only=True)
            identities[str(prepared.relative_to(ROOT))]=sha(prepared)
            inputs += [source,w['folder']/'harvest.json',w['folder']/'harvest.bin',w['folder']/'administration_grid.npz',ROOT/f'output/settlement_feedback_20261112/{mode}_inputs.npz']
            print(mode,':CSV,site JSON,fields NPZ and unrounded summaries EXACT',flush=True)
        for name,digest in protected.items():assert sha(ROOT/name)==digest,name
        receipt=dict(status='passed_exact_released_controls',controls=controls,geometry=geometry,metadata_delta=metadata_delta,sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},protected_sha256=protected,files_sha256=identities,
                     placement_changed=False,climate_rerun=False,adopt=False,scope='Published crop/geometry/transport reconstruction reused. Exact six released CSV/site/fields identities and unrounded numeric summaries. A1 records later forest-display metadata receipt difference;all other computational inputs exact. No candidate interpreted before this control passes.')
        (OUT/'control.json').write_text(json.dumps(receipt,indent=2)+'\n');print('Both unchanged release controls PASS exact bytes',flush=True)
    except Exception as error:
        failure=dict(status='failed_preserved_control',error=f'{type(error).__name__}: {error}',completed_modes=list(controls),sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in inputs},adopt=False)
        (OUT/'control_failure.json').write_text(json.dumps(failure,indent=2)+'\n');raise


if __name__=='__main__':main()
