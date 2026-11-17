"""Independent literal/section and missing-denominator review of one FAO chapter."""
import csv
import hashlib
import html
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_handling_rate_screen_20261117'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return json.loads(p.read_text())


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed source screen'
    r=read(OUT/'results.json')
    assert r['status']=='completed_single_direct_FAO_chapter_handling_rate_suitability_screen'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in {**r['files_sha256'],**r['local_source_sha256']}.items():assert sha(OUT/name)==digest,name
    body=(OUT/'source/fao_bag_storage.html').read_bytes().decode('latin-1')
    normalized=' '.join(html.unescape(re.sub(r'<[^>]*>',' ',body)).split())
    with (OUT/'claims.csv').open() as f:claims=list(csv.DictReader(f))
    assert len(claims)==10 and len({c['id'] for c in claims})==10
    for claim in claims:
        position=normalized.index(claim['exact_quote'])
        assert normalized.rfind(claim['section'],0,position)>=0,claim['id']
        assert claim['empirical_handling_rate']==claim['coefficient_adopted']=='False'
    identity=read(OUT/'source_identity.json');search=read(OUT/'search.json');suitability=read(OUT/'suitability.json')
    assert identity['url']=='https://www.fao.org/4/T0522E/T0522E0c.htm'
    assert identity['edition_date'] is identity['author_on_opened_chapter'] is None
    assert len(search['queries'])==3 and len(search['candidate_records_screened'])==6
    assert search['candidate_records_screened'][0]['url']==identity['url']
    assert search['selected_body_count']==1 and search['next_lead_fulltext_opened'] is False
    assert suitability['status']=='refuse_empirical_handling_rate_from_this_chapter'
    assert all(v is None for v in suitability['empirical_rate_fields'].values())
    assert suitability['hours_per_net_edible_kcal'] is None
    assert suitability['prescriptive_guidance_qualified'] and not suitability['observed_timing_dataset_qualified']
    assert suitability['capacity_or_inspection_numbers_are_not_handling_productivity']
    assert not suitability['modern_context_transferred'] and not suitability['source_document_instructions_treated_as_task_instructions']
    assert r['primary_bodies_opened']==1 and r['initial_search_queries']==3
    for field in ['empirical_rates_qualified','coefficient_changes','solver_calls','new_staff_allocations','new_Earth_food_scenarios']:assert r[field]==0
    for field in ['main_atlas_changed','new_fit','new_validation_claim','adopt']:assert r[field] is False
    review=dict(status='passed_independent_ten_literal_sections_and_rate_refusal',results_sha256=sha(OUT/'results.json'),
        reviewer_sha256=sha(Path(__file__)),literal_claims=10,independent_parser='Regex tag removal + HTML entity normalization, separate from producer HTMLParser.',
        section_order_checked=True,primary_body_visually_read=True,prescription_not_empirical_timing=True,
        no_numeric_coefficient_qualified=True,current_publication_unchanged=True,new_fit=False,new_validation_claim=False,adopt=False)
    (OUT/'review.json').write_text(json.dumps(review,indent=2)+'\n')
    nextplan=ROOT/'calibration/urban_diagnosis_20261117/handling_observation_primary.json'
    sources=dict(r['sources_sha256'])
    for p in [Path(__file__),ROOT/'reports/HANDLING_RATE_SCREEN_20261117.md',nextplan]:sources[str(p.relative_to(ROOT))]=sha(p)
    result=dict(status='passed_single_direct_FAO_handling_source_screen_no_empirical_rate',sources_sha256=sources,
        protected_sha256=r['protected_sha256'],local_source_sha256=r['local_source_sha256'],
        files_sha256={n:sha(OUT/n) for n in ['results.json','review.json',*r['files_sha256']]},
        primary_bodies_opened=1,located_claims=10,empirical_rates_qualified=0,handling_rates_unknown=True,
        solver_calls=0,new_staff_allocations=0,new_Earth_food_scenarios=0,main_atlas_changed=False,
        new_fit=False,new_validation_claim=False,adopt=False,next_plan=str(nextplan.relative_to(ROOT)))
    (OUT/'qualification.json').write_text(json.dumps(result,indent=2)+'\n')
    print('Qualified one direct FAO prescription chapter; 10 independent literal/section checks; no rate adoption',flush=True)


if __name__=='__main__':main()
