"""Exact plotted values, case qualifications, viewer assets and staffing-packet audit."""
import gzip
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_candidate_seasonal_20261116';VIEW=OUT/'presentation';BASE=ROOT/'output/urban_hierarchy_candidate_20261116'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for name,value in attrs:
            if name in ['href','src']:self.links.append(value)


def main():
    m=json.loads((VIEW/'manifest.json').read_text());r=json.loads((OUT/'results.json').read_text())
    q=json.loads((OUT/'review.json').read_text());replay=json.loads((OUT/'replay.json').read_text())
    assert q['status']=='passed' and q['results_sha256']==sha(OUT/'results.json')
    assert replay['status']=='passed' and replay['results_sha256']==sha(OUT/'results.json')
    for name in ['results','review','replay']:assert m[name+'_sha256']==sha(OUT/(name+'.json'))
    assert m['renderer_sha256']==sha(ROOT/'scripts/render_urban_seasonal.py')
    assert m['terrain_sha256']==sha(BASE/'terrain.png')
    images=0
    for name,digest in m['files_sha256'].items():
        assert sha(VIEW/name)==digest,name
        if name.endswith('.png'):images+=1;assert Image.open(VIEW/name).size==(2700,750)
    payload=json.loads((VIEW/'plot_data.json').read_text());pairs=0;cases={c['key']:c for c in r['cases']}
    with np.load(OUT/'town_model.npz') as a:
        for k,data in payload.items():
            mode,reading,hour=k.split('_');sites=json.loads((BASE/f'control/placed_{mode}_sites.json').read_text())['sites']
            assert data['ids']==[s['id'] for s in sites]
            np.testing.assert_array_equal(data['xy'],[(s['column']+.5,s['row']+.5) for s in sites])
            for label in ['control','candidate']:
                key=f'{mode}_{label}_{reading}_{hour}'
                np.testing.assert_array_equal(data[label+'_people'],a[key+'__target'])
                ratio=np.divide(a[key+'__target'],a[key+'__request'],out=np.zeros(len(sites)),where=a[key+'__request']>0)
                np.testing.assert_array_equal(data[label+'_fraction'],ratio)
            pairs+=len(sites)
        staff=json.loads((OUT/'downstream/staffing.json').read_text())
        assert staff['seasonal_results_sha256']==sha(OUT/'results.json') and not staff['adopt']
        for key,c in cases.items():
            p=OUT/'downstream'/(key+'.json.gz');assert sha(p)==staff['cases'][key]['packet_sha256']
            packet=json.loads(gzip.decompress(p.read_bytes()));case=packet['cases'][0]
            assert not packet['adopt'] and not packet['gate']['passed']
            assert packet['status']==('ready_for_isolated_reach_rebuild' if c['qualified'] else 'blocked_unqualified_seasonal_case')
            for field,suffix in [('total_people','target'),('civilian_people','civilian'),('institutional_people','staff'),('institutional_active','active')]:
                np.testing.assert_array_equal(case[field],a[key+'__'+suffix])
    assert images==8 and pairs==8348
    parser=Links();parser.feed((VIEW/'index.html').read_text())
    assert len(parser.links)==12
    for value in parser.links:assert '://' not in value and (VIEW/value).is_file(),value
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),manifest_sha256=sha(VIEW/'manifest.json'),
        plotted_town_scenario_pairs=pairs,plotted_support_people_values=pairs*4,images=8,
        staffing_packets=16,source_values_exact=True,local_links=12,adopt=False)
    (VIEW/'review.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt)


if __name__=='__main__':main()
