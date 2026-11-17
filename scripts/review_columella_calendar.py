"""Independent tag-stripping,paragraph/digest and literal task/calendar claim checks."""
import csv
import hashlib
from html import unescape
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import sha,read,write

OUT=ROOT/'output/urban_columella_calendar_20261117'


def main():
    assert not (OUT/'review.json').exists(),'Preserve completed independent calendar review'
    r=read(OUT/'results.json');assert r['status']=='completed_one_Latin_primary_calendar_witness_with_edition_and_model_transfer_limits'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for key in ['files_sha256','local_source_sha256']:
        for name,digest in r[key].items():assert sha(OUT/name)==digest,name
    html=(OUT/'source/book11_latin.html').read_text()
    start=html.index('<b>II.</b>')+len('<b>II.</b>');end=html.index('<b>III. DE CULTU HORTORUM</b>')
    plain=' '.join(unescape(re.sub(r'<[^>]+>',' ',html[start:end])).split())
    boundaries=list(re.finditer(r'\[(\d+)\]',plain));assert [int(m[1]) for m in boundaries]==list(range(2,102))
    p={1:plain[:boundaries[0].start()].strip()}
    for i,m in enumerate(boundaries):p[int(m[1])]=plain[m.end():boundaries[i+1].start() if i+1<len(boundaries) else len(plain)].strip()
    coverage=list(csv.DictReader((OUT/'coverage.csv').open()));assert [int(c['paragraph']) for c in coverage]==list(range(1,102))
    for row in coverage:
        text=p[int(row['paragraph'])]
        assert hashlib.sha256(text.encode()).hexdigest()==row['normalized_text_sha256']
        assert int(row['word_count'])==len(text.split())
    claims=list(csv.DictReader((OUT/'claims.csv').open()));assert len(claims)==len({c['id'] for c in claims})==39
    checks=0
    for c in claims:
        paragraphs=list(map(int,c['paragraphs'].split('|')));context=list(map(int,c['calendar_context_paragraphs'].split('|')))
        text=' '.join(p[i] for i in paragraphs);ctx=' '.join(p[i] for i in context)
        assert c['short_latin_anchor'] in text,c['id'];checks+=1
        for token in filter(None,c['source_numeric_tokens'].split('|')):assert token in text,(c['id'],token);checks+=1
        for marker in filter(None,c['source_markers'].split('|')):assert marker in ctx,(c['id'],marker);checks+=1
        assert c['model_parameter_adopted']=='False' and c['measured_rate']=='False' and c['modern_date_or_model_bin']==''
    for row in coverage:
        n=int(row['paragraph']);expected=[c['id'] for c in claims if n in map(int,c['paragraphs'].split('|'))]
        assert row['claim_ids']=='|'.join(expected)
    # Explicit safeguards on the most easily overinterpreted statements.
    assert all(token in p[94] for token in ['XVI Kal. Ian.','VIIII Kal. Ian.','ut Hipparcho placet','sic Chaldaei observant'])
    assert 'intra dies triginta' in p[54] and 'stramenta' in p[54]
    assert 'modios tres una opera' in p[26] and 'quod an recte fieri possit, adfirmare non ausim' in p[82]
    assert 'lirantur autem iugera duo bis opera una' in p[46]
    identity=read(OUT/'source_identity.json');limits=read(OUT/'limits.json')
    assert (identity['book'],identity['chapter'],identity['paragraphs'],identity['language'])==(11,2,101,'Latin')
    assert not identity['exact_critical_edition_independently_verified'] and identity['translator'] is None
    index=(OUT/'source/publisher_index.html').read_text()
    assert 'https://www.thelatinlibrary.com/columella.html' in index and 'not_online' in index
    assert read(OUT/'retrieval_failure.json')['http_status']==404
    assert '<td><a href="columella/columella.rr11.shtml">Liber XI</A>' in (OUT/'source/latin_catalogue.html').read_text()
    assert limits['paragraph94_solstice_markers']==['XVI Kal. Ian.','VIIII Kal. Ian.']
    assert limits['paragraph54_thirty_days_applies_to_straw'] and not limits['source_rate_adoption']
    assert not limits['complete_measured_monthly_occupation'] and limits['modern_dates_or_model_bins_assigned']==0
    write(OUT/'review.json',dict(status='passed_independent_calendar_witness_paragraph_and_literal_claim_checks_with_limits',
        reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),paragraphs_independently_extracted=101,
        located_claims=39,literal_anchor_marker_numeric_checks=checks,unavailable_English_retained=True,
        exact_critical_edition_verified=False,dual_solstice_markers_preserved=True,straw_interval_not_storage_duration=True,
        seed_volume_not_area=True,competing_work_norms_not_reconciled=True,modern_date_or_model_bin_conversions=0,
        new_numeric_model_inputs=0,solver_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,
        new_fit=False,new_validation_claim=False,adopt=False))
    print('Independent calendar review passed:101paragraphs,39claims,',checks,'literal checks;edition/transfer limits retained',flush=True)


if __name__=='__main__':main()
