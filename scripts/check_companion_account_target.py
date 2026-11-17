"""Close the single primary companion target by identity and quantity scope."""
import hashlib
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import read, write, sha, verify_parent
from check_agricultural_calibration_entry import canonical

OUT = ROOT / 'output/companion_account_target_20261117'
PLAN = ROOT / 'calibration/roman_benchmark_20261117/companion_account_target.json'
NS = {'t': 'http://www.tei-c.org/ns/1.0'}


def main():
    assert not (OUT / 'qualification.json').exists()
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    verify_parent()
    parent_dir = ROOT / 'output/agricultural_calibration_entry_20261117'; q = read(parent_dir / 'qualification.json')
    for n, h in q['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in q['files_sha256'].items(): assert sha(parent_dir / n) == h, n
    receipt = read(OUT / 'source_receipt.json'); assert receipt['bodies_read'] == 1 and receipt['additional_web_searches'] == 0
    for name, info in receipt['source_files'].items():
        data = (OUT / 'source' / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == info['sha256']
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == info['git_blob']
    current = ET.parse(OUT / 'source/edition.xml').getroot(); old = ET.parse(OUT / 'source/historical.xml').getroot()
    meta = ET.parse(OUT / 'source/metadata.xml').getroot()
    for root in [current, old, meta]:
        assert root.find(".//t:idno[@type='TM']", NS).text == '32187'
        assert root.find(".//t:idno[@type='ddb-hybrid']", NS).text == 'sb;20;14452'
    edition = current.find(".//t:div[@type='edition']", NS)
    assert canonical(edition) == canonical(old.find(".//t:div[@type='edition']", NS))
    assert [n.attrib['n'] for n in edition.findall('.//t:lb', NS)] == ['1', '2']
    assert edition.findall('.//t:num', NS) == []
    assert all(g.attrib['unit'] == 'character' for g in edition.findall('.//t:gap', NS))
    date = meta.find('.//t:origDate', NS)
    assert date.attrib == dict(notBefore='0226', notAfter='0275', precision='low')
    assert 'Personenliste' in meta.find('.//t:title', NS).text
    commentary = ''.join(meta.find(".//t:div[@type='commentary']", NS).itertext()); assert '14453' in commentary
    decision = dict(status='candidate_closed_no_matched_work_area_observation',
        target='SBXX14452 / TM32187', catalogue_date_range=dict(date.attrib),
        surviving_edition_lines=2, qualified_workforce_count=None, matched_area_work_pairs=0,
        empirical_fit_ready=False, fit_started=False, unit_stage='complete',
        baseline_and_evidence_stage='baseline_recorded_eligible_observation_missing',
        fit_evaluation_stage='not_started', remaining_planned_stages=2,
        next_priority='Acquire a matched operation/area/crew-duration or separately defined draft-exposure target, not another generic accounting adapter.',
        source_search_budget_closed=True, previous_primitive_and_atlas_outputs_changed=False)
    write(OUT / 'candidate_closure.json', decision)
    sources = [PLAN, Path(__file__), OUT / 'source_receipt.json',
        parent_dir / 'qualification.json', ROOT / 'scripts/check_agricultural_calibration_entry.py',
        ROOT / 'reports/COMPANION_ACCOUNT_TARGET_20261117.md']
    write(OUT / 'qualification.json', dict(status='passed_companion_identity_scope_and_explicit_no_fit_closure',
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
        files_sha256={'candidate_closure.json': sha(OUT / 'candidate_closure.json')},
        new_primary_bodies=1, new_web_searches=0, target_Git_blobs_checked=3,
        record_identity='sb;20;14452 / TM32187', current_historical_edition_bodies_match=True,
        matched_target_observations=0, independent_scan_or_Greek_edition_collation=False,
        fit_started=False, model_solver_calls=0, main_atlas_changed=False, adopt=False))
    print('Companion is a two-line person-list fragment: candidate closed, no eligible calibration pair')


if __name__ == '__main__': main()
