"""Qualify one retained Roman text witness; do not adopt resource rates."""
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import read, write, sha, table, verify_parent

OUT = ROOT / 'output/plough_resource_contract_20261117'
PLAN = ROOT / 'calibration/roman_benchmark_20261117/plough_resource_contract.json'
SOURCE = OUT / 'source/columella_book2.html'
PARENT = ROOT / 'output/cereal_operation_demands_20261117'


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = False
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'a' and a.get('class') == 'ref': self.skip = True
    def handle_endtag(self, tag):
        if tag == 'a': self.skip = False
    def handle_data(self, text):
        if not self.skip: self.parts.append(text)


def paragraphs(html):
    selected = {}
    for chapter, count in [(4, 11), (12, 9)]:
        anchors = list(re.finditer(r'<A CLASS="sec" NAME="' + str(chapter) + r'\.(\d+)">\d+</A>', html))
        assert [int(a[1]) for a in anchors] == list(range(1, count + 1))
        end = html.index('<A CLASS="chapter" NAME="' + str(chapter + 1) + '">', anchors[-1].end())
        for i, anchor in enumerate(anchors):
            parser = Text(); parser.feed(html[anchor.end():anchors[i+1].start() if i+1 < len(anchors) else end])
            selected[f'2.{chapter}.{anchor[1]}'] = ' '.join(''.join(parser.parts).split())
    return selected


CLAIMS = [
    ('operator_days', ['2.12.1', '2.12.2'], 'Human ploughmen are named separately from other field occupations.', 'Operator work is a qualified subset of human time, not an extra workforce.'),
    ('paired_estate_example', ['2.12.7'], 'The tree-free200-iugerum example lists two ox yokes, two ploughmen and six common labourers.', 'One operator/one yoke can be an explicit conditional scenario; no universal observed ratio.'),
    ('trees_change_staffing', ['2.12.7'], 'The tree-planted comparison calls for additional workers.', 'Do not transfer this staffing example into a universal rural worker fraction.'),
    ('bundled_passes_and_sowing', ['2.4.8'], 'Four prescribed days combine first breaking, repeat passes, ridging and sowing.', 'Not four identical passes; avoid charging the same sowing/ridging again.'),
    ('moisture_workability', ['2.4.5', '2.4.6'], 'Both drought and unsuitable wetness impede acceptable tillage.', 'Qualitative condition only; no numeric soil-moisture cutoff.'),
    ('terrain_and_soil', ['2.4.9', '2.4.10', '2.4.11'], 'Topography and soil alter timing, furrow direction and prescribed effort.', 'No universal calendar or soil-invariant task rate.'),
    ('conditional_day_counts', ['2.4.8', '2.4.11', '2.12.8'], 'Explicit schedules differ with land and operation context.', 'Preserve the differing counts; do not replace all tasks with one average.'),
    ('seed_volume_area_link', ['2.12.1', '2.12.2', '2.4.8'], 'The crop list states seed volumes; the method example explicitly states a land area.', 'This screen does not independently certify the seed-volume-to-hectare link for every crop.'),
    ('nonplough_days_and_other_duties', ['2.12.9'], 'The annual example allows nonplough days and other hauling duties.', 'No globally free winter labour or full household/animal budget follows.'),
    ('quality_of_completion', ['2.4.2', '2.4.3'], 'Preparation is judged by pulverization and unworked skips.', 'Completing an hour quota alone does not establish field quality.')]


def main(out):
    assert not (out / 'results.json').exists()
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    verify_parent(); q = read(PARENT / 'qualification.json')
    for n, h in q['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in q['files_sha256'].items(): assert sha(PARENT / n) == h, n
    receipt = read(OUT / 'source_receipt.json')
    assert receipt['access'] == 'success' and receipt['sha256'] == sha(SOURCE)
    original = read(ROOT / 'research_notes/farm_labour_20261103.json')['cached_sources_sha256']['data/cache/farm_labour/columella_2.html']
    assert original == sha(SOURCE), 'Do not silently replace the historical task witness'
    html = SOURCE.read_text(); assert 'Loeb Classical Library' in html and '1941' in html
    parsed = paragraphs(html); rows = []
    for code, locators, claim, consequence in CLAIMS:
        assert all(n in parsed for n in locators)
        rows.append(dict(claim=code, sections=';'.join(locators), evidence_class='prescriptive_translated_Roman_text',
                         finding=claim, model_consequence=consequence))
    contract = dict(status='conditional_resource_definitions_not_observed_capacity',
        human='Ploughing claims human operator time from the same total human budget.',
        operator_subset='Qualified operator availability must be supplied separately and cannot exceed total available human time.',
        animal='A draft-team service is separate and simultaneous; actual team count, endurance, feed and other uses are unknown.',
        one_operator_one_yoke='Supported as the staffing relationship in one conditional estate prescription, not a universal fitted coefficient.',
        other_tasks='Do not infer draft-free harrowing or complete processing/household work from silence.',
        operation_scope='Method example bundles multiple passes plus ridging/sowing. Barley three-day aggregate has no qualified per-pass split here.',
        seed_area='Per-hectare conversion retains the prior seed-area assumption; this two-section screen does not independently establish it.',
        workability='Soil, moisture, terrain, timing and completed quality matter; no numerical workability threshold adopted.',
        implementation='Existing harvest.labour supports simultaneous resources. A plough-only adapter may test supplied human/operator/team capacities, but cannot label completion as grain production or a complete crop activity.',
        numeric_defaults_adopted=False, canonical_task_counts_changed=False, complete_resource_budget=False)
    out.mkdir(parents=True, exist_ok=True)
    table(out / 'claims.csv', rows)
    write(out / 'paragraphs.json', {n: dict(sha256=hashlib.sha256(t.encode()).hexdigest(), characters=len(t)) for n, t in parsed.items()})
    write(out / 'resource_contract.json', contract)
    paths = [PLAN, SOURCE, OUT / 'source_receipt.json', PARENT / 'qualification.json',
             ROOT / 'research_notes/farm_labour_20261103.json', ROOT / 'harvest/labour.py', Path(__file__)]
    write(out / 'results.json', dict(status='qualified_one_translated_witness_plough_resource_scope_pending_review',
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in paths},
        files_sha256={n: sha(out / n) for n in ['claims.csv', 'paragraphs.json', 'resource_contract.json']},
        witness='LacusCurtius English BookII, site identifies Loeb1941; no independent scan/Latin collation.',
        original_farm_source_byte_exact=True, source_bodies=1, focused_chapters=[4, 12], paragraphs=20, claims=10,
        model_solver_calls=0, resource_coefficients_adopted=0, new_fit=False, main_atlas_changed=False, adopt=False))
    print('Qualified20 paragraphs/10 resource-scope findings in the exact original task witness')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--out', type=Path, default=OUT)
    main(parser.parse_args().out)
