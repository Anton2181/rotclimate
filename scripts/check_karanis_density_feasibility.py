"""Check the finite source screen's provenance/scope, without deriving density."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/karanis_density_feasibility_20261117'
PARENT = ROOT / 'output/annual_assumption_impact_20261117'
PLAN = ROOT / 'calibration/roman_benchmark_20261117/karanis_density_feasibility.json'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_text())


def main():
    assert not (OUT / 'qualification.json').exists(), 'Preserve completed screen'
    assert subprocess.check_output(['git', 'show', 'HEAD:' + str(PLAN.relative_to(ROOT))], cwd=ROOT) == PLAN.read_bytes()
    receipt = read(OUT / 'source_receipt.json')
    assert len(receipt['search_queries']) == 3 and len(receipt['bodies']) == 3
    for n, h in receipt['cache_sha256'].items():
        assert sha(OUT / n) == h, n
    assert receipt['bodies']['yiftach']['evidence_route'] == 'web_extracted_printed_chapter_text_not_direct_HTML_preview'
    web = read(OUT / 'source/yiftach_web_extract.json')
    text = '\n'.join(c['text'] for c in web['content'] if c['type'] == 'text')
    assert 'tax list does not indicate where each unit was located' in text
    assert '11 census returns, while 10 clearly omit' in text
    assert '97.2' in text and 'II 577.7-8 (201/2 CE)' in text
    assert text.count('201/2 CE') >= 2
    chronology = (OUT / 'source/chronology.txt').read_text()
    assert '13 archaeobotanical specimens' in chronology
    assert 'level system cannot even provide broader relative phases' in chronology
    museum = (OUT / 'source/museum.txt').read_text()
    assert 'dug to bedrock' in museum and 'not, however, always clear-cut' in museum
    q = read(PARENT / 'qualification.json')
    assert q['status'] == 'passed_existing_annual_matched_sensitivity_not_empirical_uncertainty'
    checked = 0
    for n, h in {**q['sources_sha256'], **q['protected_sha256']}.items():
        assert sha(ROOT / n) == h, n
        checked += 1
    for n, h in q['files_sha256'].items():
        assert sha(PARENT / n) == h, n
        checked += 1
    files = [PLAN, Path(__file__), OUT / 'source_receipt.json',
             ROOT / 'reports/KARANIS_DENSITY_FEASIBILITY_20261117.md',
             ROOT / 'calibration/roman_benchmark_20261117/annual_agricultural_budget.json']
    result = dict(status='passed_bounded_source_provenance_and_scope_no_matched_density_observation',
        sources_sha256={str(p.relative_to(ROOT)): sha(p) for p in files},
        parent_qualification=str((PARENT / 'qualification.json').relative_to(ROOT)),
        parent_qualification_sha256=sha(PARENT / 'qualification.json'), parent_identities_verified=checked,
        searches=3, source_bodies=3, scholarly_chapter_facsimile_verified=False,
        independently_reinterpreted_papyri=False, new_papyrus_records_opened=0,
        complete_AD200_population_count_qualified=False, contemporaneous_occupied_area_qualified=False,
        matched_density_observations=0, model_solver_calls=0, new_fit=False,
        main_atlas_changed=False, adopt=False,
        next_plan='calibration/roman_benchmark_20261117/annual_agricultural_budget.json')
    (OUT / 'qualification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(result['status'])


if __name__ == '__main__':
    main()
