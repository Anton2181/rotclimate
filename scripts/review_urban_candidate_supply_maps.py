"""Check every plotted town value/coordinate against reviewed numerical arrays."""
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_candidate_supply_20261116'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=json.loads((OUT/'presentation.json').read_text());d=json.loads((OUT/'plot_data.json').read_text())
    review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    assert p['results_sha256']==sha(OUT/'results.json') and p['review_sha256']==sha(OUT/'review.json')
    assert p['renderer_sha256']==sha(ROOT/'scripts/render_urban_candidate_supply.py')
    assert p['terrain_sha256']==sha(ROOT/'output/urban_hierarchy_candidate_20261116/terrain.png')
    for name,digest in p['files_sha256'].items():
        assert sha(OUT/name)==digest,name
        if name.endswith('.png'):assert Image.open(OUT/name).size==(2700,765)
    checked=0
    with np.load(OUT/'town_model.npz') as a:
        for key,t in d.items():
            mode,scenario=key.split('__');sites=json.loads((OUT/f'packets/control/placed_{mode}_sites.json').read_text())['sites']
            assert t['ids']==[s['id'] for s in sites]
            np.testing.assert_array_equal(t['xy'],[(s['column']+.5,s['row']+.5) for s in sites])
            for side,label in [('old','control'),('new','candidate')]:
                np.testing.assert_array_equal(t[side],a[f'{label}__{mode}__{scenario}_fed_share'])
            checked+=len(sites)
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),presentation_sha256=sha(OUT/'presentation.json'),
        plotted_town_scenario_pairs=checked,values_and_coordinates_exact=True,images=4,adopt=False)
    (OUT/'presentation_review.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('Reviewed',checked,'plotted town/scenario pairs and four image identities')


if __name__=='__main__':main()
