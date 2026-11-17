"""Pin the calibration-entry decision and distinguish dates from work exposure."""
import csv
import hashlib
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT / 'scripts'))
from cereal_activity_packet import read, write, sha, verify_parent
OUT = ROOT / 'output/agricultural_calibration_entry_20261117'
NS = {'t': 'http://www.tei-c.org/ns/1.0'}


def canonical(node):
    return (node.tag, sorted(node.attrib.items()), (node.text or '').strip(),
            [canonical(c) for c in node], (node.tail or '').strip())


def main():
    assert not (OUT / 'qualification.json').exists()
    verify_parent()
    unit = ROOT / 'output/cereal_seed_area_link_20261117'; q = read(unit / 'qualification.json')
    for n, h in q['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in q['files_sha256'].items(): assert sha(unit / n) == h, n
    assert q['matched_prescribed_cases'] == 2 and q['unmatched_variety_cases'] == 1
    receipt = read(OUT / 'source_receipt.json')
    assert len(receipt['search_queries']) == 3 and receipt['bodies_read'] == 2
    for n, h in receipt['cache_sha256'].items(): assert sha(OUT / n) == h, n
    payloads = read(OUT / 'source/github_payloads.json')
    for name, d in payloads.items():
        data = (OUT / 'source' / name).read_bytes()
        assert data == d['content'].encode()
        assert hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() == d['sha']
    for page in range(261, 270): assert (OUT / f'source/rathbone_page{page}.txt').is_file()
    current = ET.parse(OUT / 'source/sb_20_14453_current.xml').getroot()
    old = ET.parse(OUT / 'source/sb_20_14453_historical.xml').getroot()
    meta = ET.parse(OUT / 'source/sb_20_14453_metadata.xml').getroot()
    for tree in [current, old, meta]:
        assert tree.find(".//t:idno[@type='TM']", NS).text == '14883'
        assert tree.find(".//t:idno[@type='ddb-hybrid']", NS).text == 'sb;20;14453'
    edition = current.find(".//t:div[@type='edition']", NS)
    assert canonical(edition) == canonical(old.find(".//t:div[@type='edition']", NS))
    date = meta.find('.//t:origDate', NS)
    assert date.attrib['when'] == '0259-06-20'
    nums = [n.attrib['value'] for n in edition.findall('.//t:num', NS)]
    assert nums == ['6', '26']
    text = ''.join(edition.itertext())
    assert 'ἔτους' in text and 'Παῦνι' in text and 'τριακάδος' in text
    assert 'ἄροτρον' in text and 'μισθοῦ' in text and 'ἀρούρ' not in text
    commentary = ''.join(meta.find(".//t:div[@type='commentary']", NS).itertext())
    assert '14452' in commentary
    modern_dates = [n.text for n in current.findall('./t:text/t:body/t:head/t:ref/t:date', NS)]
    assert modern_dates == ['1907', '1997']
    baseline_dir = ROOT / 'output/cereal_activity_packet_20261117'
    bq = read(baseline_dir / 'qualification.json')
    for n, h in bq['sources_sha256'].items(): assert sha(ROOT / n) == h, n
    for n, h in bq['files_sha256'].items(): assert sha(baseline_dir / n) == h, n
    with (baseline_dir / 'cases.csv').open() as f:
        row = next(r for r in csv.DictReader(f) if r['physical_case'] == 'candidate__corrected__central__h600')
    baseline = dict(physical_case=row['physical_case'], packet=str((baseline_dir / 'activities_corrected.npz').relative_to(ROOT)),
        packet_sha256=sha(baseline_dir / 'activities_corrected.npz'), case_summary=row,
        fixed='Existing climate/crop/yield/land use/population/density/worker allowance; no new scenario or input field.',
        proposed_parameter='plough_operator_workdays_per_worked_area_for_a_defined_package',
        reference_days_per_iugerum=3., assumed_hectares_per_iugerum=.25,
        reference_days_per_hectare=12., assumed_hours_per_workday=8.,
        operator_or_draft_capacity_fit=False, current_coefficients_changed=False)
    write(OUT / 'baseline.json', baseline)
    gate = dict(status='not_ready_for_empirical_agricultural_fit_missing_matched_observation',
        milestones=dict(unit_link='complete', baseline_and_target='baseline_and_estimand_proposed_target_unqualified', fit_and_comparison='blocked_on_target'),
        entry_requirements=dict(traceable_baseline=True, named_estimand=True, qualified_matched_target=False,
                                disjoint_training_evaluation=False, frozen_fit_metric_bounds_partition=False),
        evidence=dict(candidate_family='Heroninos/Appianus estate', contextual_period='AD249-268',
            primary_record='SBXX14453 / TM14883', catalogue_date=date.attrib['when'],
            eligible_area_operator_day_pairs=0, calendar_numerals_are_work_exposure=False,
            observed_AD200_operator_or_team_capacity_qualified=False),
        empirical_fit_started=False, invented_target=False, new_model_scenarios=0,
        next_record='SBXX14452: companion explicitly cited by same HGV metadata, unopened',
        count='Two planned work packages remain after unit check; evidence acquisition has no guaranteed source/turn/time count.')
    write(OUT / 'readiness.json', gate)
    sources = [ROOT / 'calibration/roman_benchmark_20261117/calibration_entry.json',
        ROOT / 'calibration/roman_benchmark_20261117/companion_account_target.json', Path(__file__),
        ROOT / 'reports/AGRICULTURAL_CALIBRATION_ENTRY_20261117.md', OUT / 'source_receipt.json',
        unit / 'qualification.json', baseline_dir / 'qualification.json']
    write(OUT / 'qualification.json', dict(status='passed_calibration_entry_provenance_no_eligible_fit_target',
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in sources},
        files_sha256={n: sha(OUT / n) for n in ['baseline.json', 'readiness.json']},
        searches=3, source_bodies_read=2, unavailable_method_body=1, article_pages_read=9,
        primary_edition_bodies_match=True, official_Git_blob_identities_checked=4,
        primary_record_date=date.attrib['when'], numeric_target_pairs_qualified=0,
        calibration_ready=False, fit_started=False, model_solver_calls=0, main_atlas_changed=False, adopt=False,
        next_plan='calibration/roman_benchmark_20261117/companion_account_target.json'))
    print('Baseline/estimand recorded; zero matched area/operator-day observations: empirical fit remains blocked')


if __name__ == '__main__': main()
