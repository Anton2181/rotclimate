"""Located one-chapter evidence screen; a prescription does not supply a rate."""
import csv
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/urban_handling_rate_screen_20261117'
PARENT=ROOT/'output/urban_handling_exposure_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/handling_rate_evidence_screen.json'
URL='https://www.fao.org/4/T0522E/T0522E0c.htm'


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(p):return json.loads(p.read_text())
def write(p,value):p.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,data):self.parts.append(data)


CLAIMS=[
 ('manual','Equipment for handling','Bags of grain are generally handled manually and hand-carried.','Operation description, not timed observation.'),
 ('trolley','Equipment for handling','two-wheeled trolleys are used for unit transport of bags.','Equipment differs from unaided hand carrying.'),
 ('conveyor','Equipment for handling','bags are stacked with the help of a bag-conveyor belt','Mechanically assisted stacking; no human labour rate supplied.'),
 ('hooks','Equipment for handling','Remember not to use hooks','Bag damage warning, not productivity.'),
 ('volume_unit','Specific volume','Its unit of measurement is the cubic metre per tonne of product','Storage volume unit, not a time denominator.'),
 ('stack_height','Height of the stacks','maximum heights can be 5-6 metres','Prescribed stack height conditioned on bag material; not measured lift geometry.'),
 ('reconditioning','Equipment for reconditioning products','quality seems doubtful on arrival','Additional conditional work; not covered by a generic unloading operation.'),
 ('maintenance','Building upkeep','permanently monitored','Ongoing work beyond grain movements.'),
 ('inspection','Inspections','more thorough inspections must be made every week or two','Prescribed inspection frequency; duration and crew unknown.'),
 ('capacity','Bag-storage management','avoid taking in more grain than the storehouse can hold','Physical storage constraint, not handling-hour capacity.')]


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert not (OUT/'results.json').exists(),'Preserve completed screen'
    q=read(PARENT/'qualification.json');assert q['status']=='passed_all_original_town_rate_free_handling_exposure'
    for key,prefix in [('sources_sha256',ROOT),('protected_sha256',ROOT),('files_sha256',PARENT)]:
        for name,digest in q[key].items():assert sha(prefix/name)==digest,name
    raw=OUT/'source/fao_bag_storage.html';receipt=read(OUT/'source/receipt.json');assert sha(raw)==receipt['sha256']
    assert receipt['url']==URL and receipt['resolved_url']==URL
    parser=Text();parser.feed(raw.read_bytes().decode('latin-1'));text=' '.join(' '.join(parser.parts).split())
    rows=[]
    for name,heading,quote,meaning in CLAIMS:
        assert quote in text,(name,quote)
        assert heading in text,heading
        rows.append(dict(id=name,source_url=URL,section=heading,exact_quote=quote,interpretation=meaning,empirical_handling_rate=False,coefficient_adopted=False))
    with (OUT/'claims.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    candidates=[
        dict(order=1,url=URL,title='Agricultural engineering in development — Storage in bags',decision='selected_first_matching_direct_institutional_manual'),
        dict(order=2,url='https://ageconsearch.umn.edu/record/310428/files/mrr145.pdf',title='Materials handling in public refrigerated warehouses',decision='not_opened; later record'),
        dict(order=3,url='https://journals.tubitak.gov.tr/agriculture/vol23/iss8/25/',title='Loading, unloading and stacking in forest transportation',decision='not_opened; timber operation'),
        dict(order=4,url='https://documents1.worldbank.org/curated/en/590801468068329068/pdf/multi-page.pdf',title='Grain storage projects',decision='not_opened; later record'),
        dict(order=5,url='https://www.scitepress.org/publishedPapers/2022/119727/pdf/index.html',title='Inserting ergonomic grain into sacks — a case study',decision='not_opened; later record'),
        dict(order=6,url='https://ageconsearch.umn.edu/record/312121/files/mrr1113.pdf',title='Reducing costs of less-than-trailer-load purchases',decision='not_opened; later record')]
    write(OUT/'search.json',dict(queries=['site.logcluster.org warehouse manual bagged grain loading unloading labour productivity',
        'site.fao.org grain storage manual bag handling labour loading unloading tonnes man day',
        'manual grain bag stacking loading unloading time study worker productivity'],candidate_records_screened=candidates,
        result_order='First six records in the combined returned search output; later returned leads were not full-text screened.',
        selected_body_count=1,selection_before_body_read=True,
        next_observational_lead='https://www.jstage.jst.go.jp/article/indhealth/45/1/45_1_165/_pdf',next_lead_fulltext_opened=False))
    write(OUT/'source_identity.json',dict(url=URL,publisher='Food and Agriculture Organization of the United Nations (FAO)',
        chapter='Storage in bags',series_from_search_title='Agricultural engineering in development',
        source_kind='Direct institutional technical guidance chapter',edition_date=None,author_on_opened_chapter=None,
        identity_limit='Chapter is directly hosted by FAO; author, publication year and edition are not established from this one opened body.',
        original_body_sha256=sha(raw),retrieval=receipt,scope='This single chapter only; no inference about unexamined chapters.'))
    write(OUT/'suitability.json',dict(status='refuse_empirical_handling_rate_from_this_chapter',
        supported=['Manual bag carrying is described','Trolleys, conveyors and bag lifts are separate equipment contexts',
                   'Reconditioning, checks, maintenance and inspections are additional duties','Stack geometry and access depend on material and layout'],
        empirical_rate_fields=dict(task_elapsed_time=None,person_hours=None,crew_size=None,bag_mass=None,
                                   timed_distance_or_lift=None,sample_and_measurement_protocol=None,rate_uncertainty=None,
                                   edible_energy_per_mass=None),
        observed_timing_dataset_qualified=False,prescriptive_guidance_qualified=True,
        complete_operation_schedule_qualified=False,hours_per_net_edible_kcal=None,
        capacity_or_inspection_numbers_are_not_handling_productivity=True,modern_context_transferred=False,
        source_document_instructions_treated_as_task_instructions=False,coefficient_adopted=False))
    sources=dict(q['sources_sha256'])
    for p in [Path(__file__),PLAN,PARENT/'qualification.json']:sources[str(p.relative_to(ROOT))]=sha(p)
    for name,digest in q['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    files=['claims.csv','search.json','source_identity.json','suitability.json']
    write(OUT/'results.json',dict(status='completed_single_direct_FAO_chapter_handling_rate_suitability_screen',sources_sha256=sources,
        protected_sha256=q['protected_sha256'],files_sha256={n:sha(OUT/n) for n in files},
        local_source_sha256={'source/fao_bag_storage.html':sha(raw),'source/receipt.json':sha(OUT/'source/receipt.json')},
        initial_search_queries=3,candidate_records=6,primary_bodies_opened=1,located_claims=len(rows),empirical_rates_qualified=0,
        coefficient_changes=0,solver_calls=0,new_staff_allocations=0,new_Earth_food_scenarios=0,
        main_atlas_changed=False,new_fit=False,new_validation_claim=False,adopt=False))
    print('Screened one direct FAO chapter:10 located claims; no empirical handling rate qualified',flush=True)


if __name__=='__main__':main()
