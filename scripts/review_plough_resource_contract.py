"""Stream the two text sections independently and check the resource-scope packet."""
import csv
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import read, write, sha, verify_parent
OUT = ROOT / 'output/plough_resource_contract_20261117'


class Stream(HTMLParser):
    def __init__(self):
        super().__init__(); self.current = None; self.pending = None; self.skip = False; self.parts = {}
    def handle_starttag(self, tag, attrs):
        if tag != 'a': return
        a = dict(attrs); cls = a.get('class'); name = a.get('name', '')
        if cls in ['chapter', 'sec']:
            self.current = None
            if cls == 'sec' and re.fullmatch(r'(4|12)\.\d+', name): self.pending = '2.' + name
            else: self.pending = None
        elif cls == 'ref': self.skip = True
    def handle_endtag(self, tag):
        if tag != 'a': return
        self.skip = False
        if self.pending is not None:
            self.current = self.pending; self.parts[self.current] = []; self.pending = None
    def handle_data(self, text):
        if self.current is not None and not self.skip: self.parts[self.current].append(text)


def main():
    assert not (OUT / 'qualification.json').exists()
    verify_parent(); r = read(OUT / 'results.json')
    for n, h in r['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in r['files_sha256'].items(): assert sha(OUT / n) == h, n
    for n in ['results.json', *r['files_sha256']]: assert (OUT / n).read_bytes() == (OUT / 'fresh' / n).read_bytes(), n
    stream = Stream(); stream.feed((OUT / 'source/columella_book2.html').read_text())
    paragraphs = {n: ' '.join(''.join(parts).split()) for n, parts in stream.parts.items()}
    assert set(paragraphs) == {'2.4.' + str(i) for i in range(1, 12)} | {'2.12.' + str(i) for i in range(1, 10)}
    for n, d in read(OUT / 'paragraphs.json').items():
        assert d == dict(sha256=hashlib.sha256(paragraphs[n].encode()).hexdigest(), characters=len(paragraphs[n]))
    anchors = {'2.12.1': ['ploughmen', 'ten and one-half'], '2.12.2': ['ploughman', 'six and a half'],
        '2.12.7': ['two hundred iugera', 'two yoke of oxen', 'six common labourers'],
        '2.4.8': ['three-fourths', 'one-fourth', 'ridges and sown'],
        '2.4.5': ['muddy', 'half soaked'], '2.4.6': ['oxen'], '2.4.11': ['three days'],
        '2.12.8': ['fifty days', 'twenty-five', 'forty days'], '2.12.9': ['Forty-five days', 'thirty days']}
    count = 0
    for n, tokens in anchors.items():
        for token in tokens: assert token in paragraphs[n], (n, token); count += 1
    assert 2 + 1 + .75 + .25 == 4 and 50 + 25 + 40 == 115
    with (OUT / 'claims.csv').open() as f: claims = list(csv.DictReader(f))
    assert len(claims) == len({c['claim'] for c in claims}) == 10
    for c in claims:
        assert set(c['sections'].split(';')) <= set(paragraphs)
        assert c['evidence_class'] == 'prescriptive_translated_Roman_text'
    contract = read(OUT / 'resource_contract.json')
    assert not contract['numeric_defaults_adopted'] and not contract['canonical_task_counts_changed']
    assert not contract['complete_resource_budget'] and r['original_farm_source_byte_exact']
    next_plan = 'calibration/roman_benchmark_20261117/plough_completion_adapter.json'
    sources = dict(r['sources_sha256'])
    for n in ['scripts/review_plough_resource_contract.py', 'reports/PLOUGH_RESOURCE_CONTRACT_20261117.md', next_plan]: sources[n] = sha(ROOT / n)
    write(OUT / 'qualification.json', dict(status='passed_one_witness_plough_resource_scope_no_capacity_adoption',
        sources_sha256=sources, files_sha256={n: sha(OUT / n) for n in ['results.json', *r['files_sha256']]},
        source_bodies=1, paragraphs_reviewed=20, claims_reviewed=10, literal_scope_anchors=count,
        original_farm_source_byte_exact=True, fresh_exports_byte_exact=True, independent_scan_or_Latin_collation=False,
        resource_coefficients_adopted=0, model_solver_calls=0, new_fit=False, main_atlas_changed=False, adopt=False,
        next_plan=next_plan))
    print('Passed20 independent paragraph identities,10 claims and resource-scope checks')


if __name__ == '__main__': main()
