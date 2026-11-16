"""Check every viewer datum against independently reviewed candidate outputs."""
import csv
import base64
import hashlib
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_hierarchy_candidate_20261116'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    presentation=json.loads((OUT/'presentation.json').read_text());result=json.loads((OUT/'results.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json') and review['reviewer_sha256']==sha(ROOT/'scripts/review_urban_hierarchy_candidate.py')
    assert presentation['result_sha256']==sha(OUT/'results.json') and presentation['review_sha256']==sha(OUT/'review.json') and presentation['renderer_sha256']==sha(ROOT/'scripts/render_urban_hierarchy_candidate.py')
    for name,digest in presentation['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert presentation['background_source_sha256']==sha(ROOT/'atlases/earth_fit/data/administration_grid.npz')
    assert presentation['painted_roads_source_sha256']==sha(ROOT/'data/source/ravages_v8/roads.png')
    data=json.loads((OUT/'viewer_data.json').read_text());html=(OUT/'index.html').read_text();embedded=json.loads(re.search(r'<script id="payload" type="application/json">(.*?)</script>',html,re.S)[1]);assert data==embedded
    assert data['result_sha256']==sha(OUT/'results.json') and 'Development preview' in html and 'Seasonal source food, labour and imported supply remain to be qualified' in html
    assert base64.b64decode(data['background'].split(',',1)[1])==(OUT/'terrain.png').read_bytes()
    with (OUT/'town_changes.csv').open() as f:rows=list(csv.DictReader(f))
    with np.load(OUT/'town_model.npz') as z:arrays={k:z[k] for k in z.files}
    cells=0
    for mode,n in [('raw',1034),('corrected',1053)]:
        source=[r for r in rows if r['mode']==mode];target=data['modes'][mode]['towns'];assert len(source)==len(target)==n
        for i,(s,t) in enumerate(zip(source,target)):
            expected=dict(id=s['id'],name=s['name'],actor=s['actor'],x=int(s['column']),y=int(s['row']),marked=s['marked']=='True',symbol=s['campaign_symbol'],old_area=float(s['legacy_area_ha']),new_area=float(s['candidate_area_ha']),ratio=float(s['area_ratio']))
            for reading in ['central','low']:
                expected['old_res_'+reading]=float(s['legacy_residents_'+reading]);expected['new_res_'+reading]=float(s['candidate_residents_'+reading]);expected['old_food_'+reading]=float(arrays[f'{mode}__legacy__local_support_share_{reading}'][i]);expected['new_food_'+reading]=float(s['candidate_local_support_'+reading])
            assert t==expected;assert 0<=t['x']<1000 and 0<=t['y']<463;cells+=len(t)
        for reading in ['central','low']:
            c=next(c for c in result['comparison'] if c['mode']==mode and c['reading']==reading)
            assert data['modes'][mode]['summary'][reading]==dict(old_res=c['legacy_residents'],new_res=c['candidate_allocated_residents'],old_area=c['legacy_area_ha'],new_area=c['candidate_area_ha'])
    with Image.open(OUT/'terrain.png') as im:assert im.size==(1000,463)
    report=dict(status='passed',reviewer_sha256=sha(Path(__file__)),presentation_sha256=sha(OUT/'presentation.json'),scientific_review_sha256=sha(OUT/'review.json'),viewer_towns=2087,viewer_town_values=cells,embedded_payload_exact=True,relative_links='Candidate/control CSV filenames match both retained mode directories.',adopt=False)
    (OUT/'presentation_review.json').write_text(json.dumps(report,indent=2)+'\n');print(f'Reviewed all2087viewer towns/{cells}values and exact embedded payload')


if __name__=='__main__':main()
