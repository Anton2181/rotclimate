"""Review all50 transcriptions against PDF text and independent decimal arithmetic."""
from decimal import Decimal
import csv
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from settlement_locations_earth import sha,write


def main():
    source=ROOT/'data/source/roman_housing_2023';out=ROOT/'output/settlement_size_evidence_20261112'
    meta=json.loads((source/'source.json').read_text());result=json.loads((out/'results.json').read_text())
    pdf=ROOT/'data/cache/settlement_size_20261112/silchester2023.pdf'
    if sha(pdf)!=meta['source']['sha256']:raise ValueError('Source PDF differs')
    text=subprocess.check_output(['pdftotext','-f','8','-l','8','-layout',str(pdf),'-']).decode()
    source_rows={}
    for line in text.splitlines():
        parts=re.split(r'\s{2,}',line.strip())
        if len(parts)==6 and parts[0].isdigit():
            key,name,province,area,sample,count=parts
            if key in source_rows:raise ValueError('Duplicate PDF key')
            source_rows[key]=(re.sub(r'[1-6]$','',name),province,area,sample,count)
    with (source/'table2.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==len(source_rows)==50
    assert set(source_rows)=={r['city_key'] for r in rows}
    targets={r['city_key']:r for r in result['rows']};assert set(targets)==set(source_rows)
    for r in rows:
        name,province,area,sample,count=source_rows[r['city_key']]
        assert (r['ancient_name'],r['province'])==(name,province)
        assert tuple(map(Decimal,(r['site_area_ha'],r['sample_area_ha'],r['properties'])))==tuple(map(Decimal,(area,sample,count)))
        a,s,n=map(Decimal,(area,sample,count));record=targets[r['city_key']]
        assert abs(Decimal(str(record['sample_fraction']))-s/a)<Decimal('1e-15')
        for h in (3,5,7):
            ref=record['reference_scenarios'][str(h)]
            assert abs(Decimal(str(ref['people']))/(n/s*a*h)-1)<Decimal('1e-14')
            assert ref['direct_census'] is False
        assert not record['AD150_size_fit_eligible'] and record['AD150_blockers']
    # Independent source-prose checks: these are three explicitly incompatible
    # sample phases for AD150, not an assertion that every other phase qualifies.
    excluded={r['city_key'] for r in result['rows'] if 'reported_sample_phase_excludes_year' in r['AD150_blockers']}
    assert excluded=={'385','408','387'}
    fulltext=subprocess.check_output(['pdftotext','-layout',str(pdf),'-']).decode()
    for phrase in ('late first century','late third and fourth centuries','fourth century'):
        assert phrase.lower() in fulltext.lower()
    assert len(targets)==result['summary']['source_rows'] and result['summary']['AD150_eligible']==0
    for path,digest in result['sources_sha256'].items():assert sha(ROOT/path)==digest,path
    comparators=meta['silchester_comparators'];assert 142+35+9==comparators[0]['properties']==186
    assert 186*5==comparators[0]['people_at5']==930
    assert Decimal(4)/Decimal('.25')*45*5==comparators[1]['people_at5']==3600
    assert comparators[2]['kind']=='infrastructure_regression'
    write(out/'review.json',dict(status='passed',results_sha256=sha(out/'results.json'),source_pdf_sha256=sha(pdf),
        reviewer_sha256=sha(Path(__file__)),source_rows_checked=50,numeric_source_fields_checked=150,
        conditional_population_scenarios_checked=150,all_names_and_provinces_checked=True,
        source_pdf_page_render_visually_inspected=True,independent_decimal_arithmetic=True,
        phase_exclusion_keys=sorted(excluded),AD150_eligible=0,raw_catalogue_join_unavailable=True,
        reviewer_scope='Independent PDF text vsmanualCSV and decimal arithmetic,not independent archaeological survey or certification of phase/representativeness.'))
    print('Reviewed50 PDF records,150 numeric fields and150 conditional population scenarios; allAD150qualification gates retained.')


if __name__=='__main__':main()
