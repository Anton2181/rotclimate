"""Check the retained witness's cereal seed/area crosswalk; no coefficient fit."""
import argparse
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import read, write, sha, table, verify_parent
from qualify_plough_resource_contract import Text

OUT = ROOT / 'output/cereal_seed_area_link_20261117'
PLAN = ROOT / 'calibration/roman_benchmark_20261117/cereal_seed_area_link.json'
SOURCE = ROOT / 'output/plough_resource_contract_20261117/source/columella_book2.html'
SELECTED = {9: [1, 2, 3, 4, 5, 6, 14, 15, 16], 12: [1, 2]}


def extract(html):
    result = {}
    for chapter, wanted in SELECTED.items():
        anchors = list(re.finditer(r'<A CLASS="sec" NAME="' + str(chapter) + r'\.(\d+)">\d+</A>', html))
        end = html.index('<A CLASS="chapter" NAME="' + str(chapter + 1) + '">', anchors[-1].end())
        for i, a in enumerate(anchors):
            if int(a[1]) not in wanted: continue
            p = Text(); p.feed(html[a.end():anchors[i+1].start() if i+1 < len(anchors) else end])
            result[f'2.{chapter}.{a[1]}'] = ' '.join(''.join(p.parts).split())
    return result


def verify_sources():
    verify_parent()
    parent = ROOT / 'output/plough_completion_adapter_20261117'; q = read(parent / 'qualification.json')
    for n, h in q['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in q['files_sha256'].items(): assert sha(parent / n) == h, n
    original = read(ROOT / 'research_notes/farm_labour_20261103.json')
    assert sha(SOURCE) == original['cached_sources_sha256']['data/cache/farm_labour/columella_2.html']


def main(out):
    assert not (out / 'results.json').exists()
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    verify_sources(); paragraphs = extract(SOURCE.read_text()); assert len(paragraphs) == 11
    rows = [
        dict(crop_case='common_wheat', seed_modii_per_iugerum='4 or5', sowing_sections='2.9.1;2.9.5',
             task_sections='2.12.1', task_seed_modii='4 or5', link='matched_conditional_prescription',
             listed_days_per_seed_quantity=10.5, prior_scenario_hours_per_ha=336.,
             qualifiers='Soil, sowing season, weather and tree planting alter seed rate; no universal density.'),
        dict(crop_case='hexastichum_barley', seed_modii_per_iugerum='5', sowing_sections='2.9.14;2.9.15',
             task_sections='2.12.2', task_seed_modii='5', link='matched_conditional_prescription',
             listed_days_per_seed_quantity=6.5, prior_scenario_hours_per_ha=208.,
             qualifiers='Named barley case in dry loose soil; rate is conditional, not all barley varieties.'),
        dict(crop_case='distichum_or_Galatian_barley', seed_modii_per_iugerum='6', sowing_sections='2.9.16',
             task_sections='2.12.2', task_seed_modii='5', link='no_direct_same_quantity_match',
             listed_days_per_seed_quantity='', prior_scenario_hours_per_ha='',
             qualifiers='Do not multiply the five-modii task count by6/5 or silently assign the same rate.')]
    note = read(ROOT / 'research_notes/farm_labour_20261103.json')
    assert sum(note['workdays_per_iugerum']['wheat'].values()) == 10.5
    assert sum(note['workdays_per_iugerum']['barley'].values()) == 6.5
    assert note['scenario']['hours_per_workday'] == 8 and note['scenario']['iugerum_hectares'] == .25
    out.mkdir(parents=True, exist_ok=True)
    table(out / 'crosswalk.csv', rows)
    write(out / 'paragraphs.json', {n: dict(sha256=hashlib.sha256(t.encode()).hexdigest(), characters=len(t)) for n, t in paragraphs.items()})
    sources = [PLAN, SOURCE, ROOT / 'research_notes/farm_labour_20261103.json',
        ROOT / 'output/plough_completion_adapter_20261117/qualification.json', Path(__file__),
        ROOT / 'scripts/qualify_plough_resource_contract.py']
    write(out / 'results.json', dict(status='conditional_cereal_seed_area_crosswalk_pending_parse_review',
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
        files_sha256={n: sha(out / n) for n in ['crosswalk.csv', 'paragraphs.json']},
        matched_cases=2, unmatched_variety_cases=1, paragraphs=11, original_source_byte_exact=True,
        eight_hour_day_source_qualified=False, universal_barley_rate_qualified=False,
        model_solver_calls=0, coefficients_changed=False, new_fit=False, main_atlas_changed=False, adopt=False))
    print('Two conditional seed/area matches; one barley variety remains unmatched; coefficients unchanged')


class Stream(HTMLParser):
    """A second, event-based extraction checks the slice-based paragraph export."""
    def __init__(self):
        super().__init__(); self.current = None; self.pending = None; self.skip = False; self.parts = {}
    def handle_starttag(self, tag, attrs):
        if tag != 'a': return
        a = dict(attrs); cls = a.get('class'); name = a.get('name', '')
        if cls in ['chapter', 'sec']:
            self.current = None; self.pending = None
            if cls == 'sec' and re.fullmatch(r'(9|12)\.\d+', name):
                chapter, paragraph = map(int, name.split('.'))
                if paragraph in SELECTED[chapter]: self.pending = '2.' + name
        elif cls == 'ref': self.skip = True
    def handle_endtag(self, tag):
        if tag == 'a':
            self.skip = False
            if self.pending:
                self.current = self.pending; self.parts[self.current] = []; self.pending = None
    def handle_data(self, text):
        if self.current and not self.skip: self.parts[self.current].append(text)


def review():
    assert not (OUT / 'qualification.json').exists()
    verify_sources(); result = read(OUT / 'results.json')
    for n, h in result['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in result['files_sha256'].items(): assert sha(OUT / n) == h, n
    for n in ['results.json', *result['files_sha256']]: assert (OUT / n).read_bytes() == (OUT / 'fresh' / n).read_bytes(), n
    parser = Stream(); parser.feed(SOURCE.read_text())
    paragraphs = {n: ' '.join(''.join(t).split()) for n, t in parser.parts.items()}
    digests = read(OUT / 'paragraphs.json'); assert set(paragraphs) == set(digests)
    for n, text in paragraphs.items():
        assert digests[n] == dict(sha256=hashlib.sha256(text.encode()).hexdigest(), characters=len(text))
    anchors = {'2.9.1': ['iugerum', 'four modii of wheat', 'five'],
        '2.9.2': ['place or season or weather'], '2.9.5': ['only four'],
        '2.9.6': ['one fifth more seed'], '2.9.14': ['hexastichum'],
        '2.9.15': ['One iugerum will take five modii'],
        '2.9.16': ['distichum', 'Galatian', 'six modii'],
        '2.12.1': ['four or five modii', 'ten and one-half'],
        '2.12.2': ['Five modii of barley', 'six and a half']}
    for n, tokens in anchors.items():
        for token in tokens: assert token in paragraphs[n], (n, token)
    import csv
    with (OUT / 'crosswalk.csv').open() as f: rows = list(csv.DictReader(f))
    assert len(rows) == 3 and [r['link'] for r in rows].count('matched_conditional_prescription') == 2
    assert float(rows[0]['prior_scenario_hours_per_ha']) == 10.5 * 8 / .25 == 336.
    assert float(rows[1]['prior_scenario_hours_per_ha']) == 6.5 * 8 / .25 == 208.
    assert rows[2]['prior_scenario_hours_per_ha'] == rows[2]['listed_days_per_seed_quantity'] == ''
    report = 'reports/CEREAL_SEED_AREA_LINK_20261117.md'
    sources = dict(result['sources_sha256']); sources[report] = sha(ROOT / report)
    write(OUT / 'qualification.json', dict(status='passed_conditional_cereal_seed_area_link_not_empirical_work_calibration',
        sources_sha256=sources, files_sha256={n: sha(OUT / n) for n in ['results.json', *result['files_sha256']]},
        independent_paragraph_parse_checks=11, literal_link_checks=sum(map(len, anchors.values())),
        matched_prescribed_cases=2, unmatched_variety_cases=1, fresh_exports_byte_exact=True,
        eight_hour_day_source_qualified=False, universal_barley_rate_qualified=False,
        model_solver_calls=0, coefficients_changed=False, new_fit=False, main_atlas_changed=False, adopt=False))
    print('Passed11 paragraph identities and conditional unit crosswalk; no numerical adoption')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, default=OUT); parser.add_argument('--review', action='store_true')
    args = parser.parse_args(); review() if args.review else main(args.out)
