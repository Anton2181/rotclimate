"""Check a contract's line-scoped quantities; do not turn allotments into rates."""
import hashlib
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import read, write, sha, verify_parent
OUT = ROOT / 'output/reaping_contract_target_20261117'
PLAN = ROOT / 'calibration/roman_benchmark_20261117/documented_task_target.json'
NS = {'t': 'http://www.tei-c.org/ns/1.0'}


def main():
    assert not (OUT / 'qualification.json').exists()
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    verify_parent()
    parent_dir = ROOT / 'output/companion_account_target_20261117'; q = read(parent_dir / 'qualification.json')
    for n, h in q['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in q['files_sha256'].items(): assert sha(parent_dir / n) == h, n
    receipt = read(OUT / 'source_receipt.json'); assert receipt['source_bodies'] == 2 and len(receipt['queries']) == 3
    for n, h in receipt['cache_sha256'].items(): assert sha(OUT / n) == h, n
    payload = read(OUT / 'source/github_payloads.json')
    for name, d in payload.items():
        data = (OUT / f'source/{name}.xml').read_bytes()
        assert data == d['content'].encode()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == d['sha']
    edition = ET.parse(OUT / 'source/edition.xml').getroot(); meta = ET.parse(OUT / 'source/metadata.xml').getroot()
    for root in [edition, meta]:
        assert root.find(".//t:idno[@type='TM']", NS).text == '17068'
        assert root.find(".//t:idno[@type='ddb-hybrid']", NS).text == 'p.sarap;;51'
    assert meta.find('.//t:origDate', NS).attrib['when'] == '0125-04-12'
    body = edition.find(".//t:div[@type='edition']", NS); quantities = {}; line = None
    for node in body.iter():
        if node.tag.endswith('}lb'): line = node.attrib['n']
        if node.tag.endswith('}num'): quantities.setdefault(line, []).append(node.attrib['value'])
    for n, expected in {'6':['130'], '8':['1/2','1/12'], '13':['10','3'], '14':['13'],
                        '18':['1'], '26':['9'], '27':['17'], '29':['26']}.items():
        assert quantities[n] == expected, (n, quantities.get(n))
    assert 10 + 3 == 13 and 130 / 13 == 10
    text = ''.join(body.itertext())
    assert 'τριακάδος' in text and 'ἡμέραν μίαν' in text and 'ἀμισ' in text
    discussion = ' '.join((OUT / 'source/discussion.txt').read_text().split())
    assert '54 arourai, 6 arourai to each' in discussion
    assert 'P.Sarap 51' in discussion and '5/6' in discussion
    findings = dict(status='candidate_closed_contract_allotment_qualified_rate_not_qualified',
        primary_record='P.Sarap.51 / TM17068', catalogue_date='0125-04-12', operation='wheat reaping contract',
        quantities_by_edition_line=quantities, contracted_area_arourai=130,
        reapers_supplied_by_contractors=10, reapers_supplied_by_other_party=3, contractual_reaper_complement=13,
        contracted_area_per_required_reaper_arourai=10,
        completed_job_worker_days=None, realized_area_per_worker_day=None, time_bound_qualified=False,
        one_day_clause='Separate unpaid service, not the duration of the entire area job.',
        quotation_citation_match=False,
        discrepancy='Discussion quotes54 arourai,6 per worker,5/6 artaba but cites primary130 arourai,10+3 reapers,encoded1/2 and1/12 fractions.',
        eligible_area_work_time_pairs=0, numerical_rate_adopted=False, fit_started=False,
        retrospective_fulfillment_observed=False, model_solver_calls=0, main_atlas_changed=False, adopt=False)
    write(OUT / 'findings.json', findings)
    sources = [PLAN, Path(__file__), OUT / 'source_receipt.json', parent_dir / 'qualification.json',
               ROOT / 'reports/REAPING_CONTRACT_TARGET_20261117.md']
    write(OUT / 'qualification.json', dict(status='passed_reaping_record_identity_and_quantity_scope_no_rate_fit',
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources}, files_sha256={'findings.json': sha(OUT / 'findings.json')},
        searches=3, source_bodies=2, primary_Git_blobs_verified=2,
        line_scoped_quantity_groups_checked=8, quotation_mismatch_preserved=True,
        paired_area_crew_contract=1, paired_area_work_time_targets=0,
        independent_scan_or_critical_Greek_collation=False, fit_started=False, model_solver_calls=0,
        new_rate_adopted=False, main_atlas_changed=False, adopt=False))
    print('Area130 and contractual crew13 qualified; duration missing and quotation mismatched: no rate fit')


if __name__ == '__main__': main()
