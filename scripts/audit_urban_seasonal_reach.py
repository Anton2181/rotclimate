"""Source-set dependency audit; identical inputs can retain existing political maps."""
import ast
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_candidate_seasonal_20261116'
RELEASE=ROOT/'output/settlement_release4_20261116'
REFERENCE='d05e7092b139919eed6d5af1f4275274110cae7d'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    r=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    staffing=json.loads((OUT/'downstream/staffing.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    assert staffing['seasonal_results_sha256']==sha(OUT/'results.json')
    assert os.environ.get('ROTCLIMATE_FOREST_TRAVEL','0') in ('','0')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    code={};case_reads={}
    for name in ['scripts/build_control_v2.py','scripts/build_control_v21.py']:
        p=ROOT/name;old=subprocess.check_output(['git','show',REFERENCE+':'+name],cwd=ROOT)
        code[name]=dict(current_sha256=sha(p),reference_sha256=hashlib.sha256(old).hexdigest(),exact_source=old==p.read_bytes())
        tree=ast.parse(p.read_text());keys=set()
        for node in ast.walk(tree):
            if isinstance(node,ast.Subscript) and isinstance(node.value,ast.Name) and node.value.id=='case' and isinstance(node.slice,ast.Constant):keys.add(node.slice.value)
        assert keys=={'institutional_active'},(name,keys)
        case_reads[name]=sorted(keys)
    cases={};all_primary=True
    for mode in ['raw','corrected']:
        parent=RELEASE/f'reach/settlement_supplyfed/earth_fit_{mode}/settled_reach.json.gz'
        old=json.loads(gzip.decompress(parent.read_bytes()));oldcase=next(c for c in old['cases'] if c['id']=='joint365')
        for label in ['control','candidate']:
            key=f'{mode}_{label}_central_h600';meta=staffing['cases'][key]
            packet=OUT/'downstream'/(key+'.json.gz');assert sha(packet)==meta['packet_sha256']
            new=json.loads(gzip.decompress(packet.read_bytes()))
            oldnodes=[(s['node'],s['actor_index']) for s in old['sites']];newnodes=[(s['node'],s['actor_index']) for s in new['sites']]
            node_actor_same=oldnodes==newnodes;actors_same=old['actors']==new['actors']
            flags_same=np.array_equal(oldcase['institutional_active'],new['cases'][0]['institutional_active'])
            qualified=next(c['qualified'] for c in r['cases'] if c['key']==key)
            identical=bool(node_actor_same and actors_same and flags_same and qualified and all(v['exact_source'] for v in code.values()))
            all_primary &= identical;maps={}
            for rule in ['v2','v21']:
                folder=ROOT/'atlases/earth_fit/data/release3/reach_fed'/('corrected' if mode=='corrected' else '')
                image=folder/f'settled_control_{rule}_joint365.webp'
                assert sha(image)==r['protected_sha256'][str(image.relative_to(ROOT))]
                maps[str(image.relative_to(ROOT))]=sha(image)
            cases[key]=dict(node_actor_order_identical=node_actor_same,actors_identical=actors_same,active_source_vector_identical=flags_same,
                seasonal_case_qualified=qualified,political_map_identity_proved=identical,
                status='retain_existing_map_under_identical_fixed_travel_inputs' if identical else 'isolated_reach_rebuild_required',
                changed_sources=meta['changed_sources'],retained_published_map_sha256=maps if identical else {},packet_sha256=sha(packet))
    receipt=dict(status='primary_reach_identity_proved' if all_primary else 'some_primary_reach_rebuilds_required',
        auditor_sha256=sha(Path(__file__)),seasonal_results_sha256=sha(OUT/'results.json'),staffing_sha256=sha(OUT/'downstream/staffing.json'),
        canonical_sources=code,case_field_reads=case_reads,reference_commit=REFERENCE,cases=cases,
        scope='Dependency identity under the existing fixed travel/occupation/cost recipe: P2/v2.1 consume funded active sources,not civilian counts. Source/world assets are protected and exact; the inherited forest display metadata A1 changes no opt-in-disabled travel. This is not an independent reach-physics validation or a newly rendered map.',
        stress_scenarios='600h central is the published political-map headline. Flat-density/300h alternatives remain explicit staffing packets;changed source sets require their own reach rebuild before any such option is published.',
        adopt=False,main_atlas_published=False)
    (OUT/'downstream/reach_identity.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt['status'])


if __name__=='__main__':main()
