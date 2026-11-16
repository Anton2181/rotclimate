"""Exact parameter-table, local-viewer links and plot source identity checks."""
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/northern_steppe_only_20261116';VIEW=OUT/'presentation'


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for name,value in attrs:
            if name in ['src','href']:self.links.append(value)


def main():
    manifest=json.loads((VIEW/'manifest.json').read_text());review=json.loads((OUT/'review.json').read_text())
    assert review['status']=='passed' and review['results_sha256']==sha(OUT/'results.json')
    assert manifest['renderer_sha256']==sha(ROOT/'scripts/render_northern_steppe_only.py')
    for name in ['preview','comparison','review']:assert manifest[name+'_sha256']==sha(OUT/(name+('.npz' if name=='preview' else '.json')))
    for name,digest in manifest['files_sha256'].items():
        assert sha(VIEW/name)==digest,name
        if name.endswith('.png'):
            image=Image.open(VIEW/name);image.verify()
    protocol=json.loads((ROOT/'calibration/northern_steppe_only_20261116/protocol.json').read_text())
    best=json.loads((OUT/'best_params.json').read_text())
    with (VIEW/'parameters.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==len(protocol['space'])==19
    for row,(name,lo,hi) in zip(rows,protocol['space']):
        assert row['parameter']==name and row['baseline']==str(protocol['base'][name]) and row['candidate']==str(best[name])
        assert float(row['lower_bound'])==lo and float(row['upper_bound'])==hi
        near=False if isinstance(best[name],bool) else min((best[name]-lo)/(hi-lo),(hi-best[name])/(hi-lo))<=.01
        assert row['within_one_percent_of_bound']==str(near)
    parser=Links();parser.feed((VIEW/'index.html').read_text())
    assert len(parser.links)==6
    for value in parser.links:
        assert '://' not in value and (VIEW/value).is_file(),value
    comparison=json.loads((OUT/'comparison.json').read_text())['ensemble'];page=(VIEW/'index.html').read_text()
    for name in ['baseline','candidate']:
        assert f"{comparison[name]['score']:.4f}" in page
        for key in ['BSk_share','BWk_share']:assert f'{comparison[name][key]:.1%}' in page
    receipt=dict(status='passed',reviewer_sha256=sha(Path(__file__)),manifest_sha256=sha(VIEW/'manifest.json'),
        exact_parameter_rows=19,local_links_checked=6,plot_source_identities_passed=True,adopt=False)
    (VIEW/'review.json').write_text(json.dumps(receipt,indent=2)+'\n');print(receipt)


if __name__=='__main__':main()
