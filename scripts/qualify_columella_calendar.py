"""One Latin calendar witness:paragraph-located prescriptions,not model dates/rates."""
import csv
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import sha,read,write

OUT=ROOT/'output/urban_columella_calendar_20261117'
PARENT=ROOT/'output/urban_work_evidence_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/columella_calendar_source.json'
ADAPTER=PLAN.with_name('columella_calendar_latin_adapter.json')


class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,value):self.parts.append(value)
    def text(self):return ' '.join(' '.join(self.parts).split())


def paragraphs(html):
    match=re.search(r'<b>\s*II\.</b>(.*?)<b>\s*III\.',html,re.S|re.I);assert match
    parser=Text();parser.feed(match.group(1));parts=re.split(r'\[(\d+)\]',parser.text())
    rows=[dict(paragraph=1,text=parts[0].strip())]
    rows.extend(dict(paragraph=int(parts[i]),text=parts[i+1].strip()) for i in range(1,len(parts),2))
    assert [r['paragraph'] for r in rows]==list(range(1,102))
    return rows


# All English is our paraphrase. Latin anchors/markers stay source identifiers.
# (id,paragraphs,anchor,kind,task,paraphrase,calendar-context,markers,numeric tokens,limit)
CLAIMS=[
 ('weather', [1], 'ut permiserit status caeli','conditional_prescription','all field tasks','Fit agricultural tasks to what weather permits.',[1],[],[],'No universal fixed dates or weather observations.'),
 ('spring_not_exact_day',[2],'non sic observare rusticus debet','calendar_qualification','start field work','The farmer need not wait for the exact astronomical first day of spring.',[2],[],[],'Not a rule for model-year rotation.'),
 ('half_month',[3],'per dimidios menses','calendar_prescription','planning interval','Advice is organized in half-month intervals,with discussion of fifteen days early or late.',[3],['Idibus Ianuariis'],['quindecim'],'Not a measured task duration or uniform deadline.'),
 ('cold_morning',[6,7],'usque in horam secundam vel tertiam','competing_duty_prescription','clean fields and prepare wood before pruning','Cold morning delays vine cutting;other duties can precede later pruning.',[6,7],['ab Idibus Ianuariis'],['secundam','tertiam'],'Source horae are not converted into modern staff hours.'),
 ('soil_timing',[8],'uliginosi et mediocris habitus','conditional_prescription','first ploughing','Wet/intermediate soils and lean dry soils receive different seasonal timing from dry rich soils.',[6,8],['sub aestatem','post aestatem primo autumno'],[],'Soil/weather conditions required;not one global sowing window.'),
 ('rich_soil_work',[8],'iugerum agri pinguis','prescribed_task_quantity','first ploughing','The text gives two operae for a rich-soil iugerum under this seasonal moisture condition.',[8],[],['duabus operis'],'Prescriptive original units;no hours/hectare conversion or animal-work equivalence.'),
 ('grain_development',[9],'quattuor fibrarum','conditional_prescription','hoeing autumn cereals','Autumn cereals are hoed before the named boundary and at a quattuor-fibrae development marker.',[9],['ante Kalendas Februarias'],['quattuor fibrarum'],'Botanical translation of fibrae not equated to a modern growth-stage code.'),
 ('barley_spare_work',[9],'quibus superest opera','competing_duty_prescription','barley hoeing','Barley hoeing is conditioned on work remaining available.',[9],[],[],'Spare work is contextual,not a measured surplus workforce.'),
 ('short_crop_sowing',[20],'Trimestrium quoque satio','regional_prescription','sowing short-season cereals','The text permits this sowing period but prefers the named earlier month in warm regions.',[15,20],['per mensem Ianuarium'],[],'Crop term and local conditions retained;no modern cultivar or model window inferred.'),
 ('regional_shift',[22],'frigidis locis','regional_qualification','seasonal tasks','Operations described earlier differ in timeliness between colder and warmer places.',[21,22],['VII Kal. Mart.'],[],'Not a quantified temperature threshold or fixed geographic mask.'),
 ('second_hoeing',[26],'Sartura quoque frumentorum iteratur','task_prescription','repeat grain hoeing','The calendar calls for repeated grain hoeing in this period.',[24,26],['a Kalendis Martiis'],[],'Not a full work allocation over the month.'),
 ('hoeing_seed_unit',[26],'modios tres una opera','prescribed_task_quantity','grain hoeing','The task quantity is expressed as three modii per opera in the witness.',[26],[],['modios tres una opera'],'Seed-volume expression is not silently converted to area or edible grain.'),
 ('plough_repeat',[32],'ultima parte Martii sunt iteranda','conditional_prescription','first/repeat ploughing','Soil first worked in the named earlier month is repeated later;wet rich land has another timing.',[32],['mense Ianuario','ultima parte Martii'],[],'Conditional sequence,not a complete schedule.'),
 ('weed_hay_overlap',[40],'runcandae segetes sunt, faenisiciae instituendae','competing_duty_prescription','weeding and haymaking','Cereal weeding and haymaking occur among the tasks of this period.',[39,40],['VI Id. Mai.','III Id. Mai.'],[],'No complete human/animal occupation budget supplied.'),
 ('unfinished_work',[46],'si opere victi sumus','contingency_prescription','carry over unfinished tasks','Tasks from the end of the preceding named month may remain to be done.',[45,46],['extremo mense Maio'],[],'A prescribed calendar does not guarantee task completion.'),
 ('difficult_soil_rates',[46],'si est difficilis','prescribed_task_quantity','successive soil working','Difficult land is assigned three,two and one operae for successive stated passes.',[46],[],['tribus','duabus','una'],'No modern hours,soil-class calibration or observed productivity.'),
 ('easy_soil_rates',[46],'At si facilis est terra','prescribed_task_quantity','successive soil working','Easier land receives different first and repeat working quantities.',[46],[],['duabus operis','iteratur una'],'Normative comparison,not transferable coefficients.'),
 ('lira_clause',[46],'lirantur autem iugera duo bis opera una','textual_unit_limit','ridge/furrow work','Retain the witness clause with iugera,repeat wording and opera.',[46],[],['iugera duo bis opera una'],'The bis/unit construction is not resolved into a new rate.'),
 ('threshing_floor',[47],'area triturae praeparanda est','task_sequence_prescription','prepare threshing floor','Prepare the threshing floor so cut material can be brought to it.',[45,47],[],[],'Floor preparation is not a measured warehouse handling intensity;the paragraph solstice deadline explicitly concerns vine work.'),
 ('barley_postharvest',[50],'hordeum metere','task_sequence_prescription','barley harvest/threshing and straw storage','Harvest barley,thresh it,and preserve straw alongside other farm tasks.',[49,50],['VIII et VII et VI Kal. Iul.','Solstitium'],[],'No hours per delivered kcal or measured residence time.'),
 ('harvest_straw_window',[54],'intra dies triginta','regional_task_sequence','harvest and straw clearing','In temperate/coastal places harvest is completed;cut straw is gathered within the stated interval.',[51,52,53,54],['locis temperatis et maritimis'],['dies triginta'],'Thirty days concerns post-cut straw handling,not a universal harvest or warehouse residence limit.'),
 ('straw_work',[54],'Iugerum stramentorum opera una desecat','prescribed_task_quantity','cut straw','One opera is prescribed for cutting straw over an iugerum.',[54],[],['Iugerum','opera una'],'Not a measured grain unloading or storage rate.'),
 ('avoid_heat',[55],'ne per aestum','time_of_day_prescription','vine/animal-feed competing duties','Foliage gathering and digging are moved to cooler parts of the day.',[55],['mane usque in tertiam','a decima usque in crepusculum'],[],'No modern daily work-hour capacity inferred.'),
 ('regional_crop_example',[56],'in Cilicia et Pamphylia','regional_qualification','competing crop sowing','The text contrasts regional sowing practice with wetter Italian places.',[56],['ultimo mense Iunio'],[],'Context only;no new sesame crop/yield cohort.'),
 ('maturity_warning',[67,68,69],'Quae omnia fallacia sunt','phenological_qualification','competing grape harvest','External signs and taste are questioned;the text describes a maturity assessment.',[67,68,69],[],[],'Contextual competing duty;not a new phenology calibration.'),
 ('estate_preparation',[70,71],'ante quindecim dies','task_sequence_prescription','prepare wine containers/equipment','Prepare containers and processing equipment before harvest while maintaining other agricultural duties.',[70,71],[],['quindecim dies'],'Wine preparation is not cereal warehouse labor or a capacity estimate.'),
 ('delegation',[72],'vilicae delegare','institutional_prescription','estate work supervision','Indoor estate duties may be delegated while the manager oversees field tasks.',[71,72],[],[],'No observed workforce share,gender fraction or access right inferred.'),
 ('cold_shaded_sowing',[74],'Locis etiam opacis triticum','regional_prescription','cereal sowing','Cold-region cereal sowing and shaded-place wheat sowing are specifically discussed.',[73,74],['VI Id. Oct.','III et pridie Id. Oct.'],[],'No universal crop calendar.'),
 ('seed_quantities',[75],'tritici modios quattuor vel quinque','prescribed_seed_quantity','cereal sowing input','The witness states seed quantities per iugerum for wheat,emmer and barley.',[75],[],['quattuor vel quinque','novem vel decem','quinque vel sex'],'Seed quantities are not yields,food rations or adopted unit conversions.'),
 ('cold_before_warm',[80],'is primus conseratur','regional_task_order','sowing','Colder places are prescribed earlier sowing and warmer places later sowing.',[79,80],[],[],'Qualitative order,not dates or temperature cutoffs.'),
 ('lupin_work_gap',[81],'vacuis operariis','competing_duty_prescription','lupin sowing/collection','Lupin tasks are described as fitting before other sowing and after other produce is collected.',[81],[],[],'No empirically free labor or spare-hour total.'),
 ('harrow_contested',[82],'Duo iugera tres operae','contested_prescription','harrowing and tree work after sowing','Three operae for two iugera are contrasted with an earlier one-per-iugerum norm the author hesitates to affirm.',[82],[],['Duo iugera tres operae','singulis operis singula iugera'],'Competing prescriptions retained;do not overwrite old task coefficients.'),
 ('drainage',[82],'fossas rivosque purgare','competing_duty_prescription','drainage maintenance','Ditches,streams and drainage furrows are maintained in this same period.',[82],[],[],'Additional duties without a full quantified labor budget.'),
 ('night_work',[90,91,92],'in lucubratione recte agantur','time_of_day_prescription','tool/wood/basket preparation','Long nights may include equipment and material preparation as well as daytime duties.',[90,91,92],['intra Kalendas Decembres'],[],'No conversion of dark hours into guaranteed available staff hours.'),
 ('winter_hours',[91],'brumales dies horarum novem','source_daylength_statement','regional winter context','The text describes nine daylight and fifteen night horae in specified regions.',[91],[],['novem','quindecim'],'Source horae/daylength are not an eight-hour modern working-day measurement.'),
 ('cold_deadline',[93],'nam frigidis recte fieri iam non possunt','regional_qualification','unfinished operations','Later completion is treated differently in temperate/warm versus cold places.',[93],['Kal. Dec.','III Id. Dec.'],[],'Does not locate model cells or assign deadlines automatically.'),
 ('two_solstices',[94],'ut Hipparcho placet','attributed_calendar_markers','winter solstice','Two source date markers are attributed to Hipparchus and Chaldean practice.',[94],['XVI Kal. Ian.','VIIII Kal. Ian.'],[],'Both retained without choosing one day or converting to a modern/model date.'),
 ('religious_restrictions',[95,96,98],'religiosiores agricolae','institutional_calendar_qualification','winter soil work and alternatives','Some cultivators restrict soil working while allowing alternative tasks and ceremonial beginnings.',[95,96,97,98],['Kalendis Ianuariis','usque in proximas Idus'],[],'Prescription/practice distinction;no universally closed model bins.'),
 ('animal_feeding',[98,99,100,101],'quid uni iugo boum','recurring_competing_duty','feed draft animals','The calendar continues with per-month daily feeding provisions for an ox team.',[98,99,100,101],[],[],'No animal/human feed mass conversion,complete occupation or measured handler hours.')]


def table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    assert not (OUT/'results.json').exists(),'Preserve completed calendar extraction'
    for path in [PLAN,ADAPTER]:assert subprocess.check_output(['git','show','HEAD:'+str(path.relative_to(ROOT))],cwd=ROOT)==path.read_bytes()
    assert read(OUT/'exposure.json')['plan_sha256']==sha(PLAN)
    assert read(OUT/'latin_exposure.json')['adapter_sha256']==sha(ADAPTER)
    prior=read(PARENT/'qualification.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in prior[key].items():assert sha(prefix/name)==digest,name
    source=OUT/'source';html=(source/'book11_latin.html').read_text()
    assert 'Columella: de Re Rustica XI' in html and 'DE RE RUSTICA LIBER UNDECIMUS' in html
    assert '<b>I.</b>' in html and '<b>III. DE CULTU HORTORUM</b>' in html
    rows=paragraphs(html);p={r['paragraph']:r['text'] for r in rows}
    claims=[]
    for name,locations,anchor,kind,task,meaning,context,markers,numbers,limit in CLAIMS:
        text=' '.join(p[i] for i in locations);context_text=' '.join(p[i] for i in context)
        assert anchor in text,(name,anchor)
        for marker in markers:assert marker in context_text,(name,marker)
        for token in numbers:assert token in text,(name,token)
        claims.append(dict(id=name,paragraphs='|'.join(map(str,locations)),short_latin_anchor=anchor,classification=kind,task=task,
            our_English_paraphrase=meaning,calendar_context_paragraphs='|'.join(map(str,context)),source_markers='|'.join(markers),
            source_numeric_tokens='|'.join(numbers),limits=limit,measured_rate=False,model_parameter_adopted=False,modern_date_or_model_bin=None))
    assert len(claims)==39
    table(OUT/'claims.csv',claims)
    import hashlib
    coverage=[dict(paragraph=r['paragraph'],word_count=len(r['text'].split()),normalized_text_sha256=hashlib.sha256(r['text'].encode()).hexdigest(),
        claim_ids='|'.join(c['id'] for c in claims if r['paragraph'] in map(int,c['paragraphs'].split('|'))),analytical_scope='chapterII only') for r in rows]
    table(OUT/'coverage.csv',coverage)
    write(OUT/'source_identity.json',dict(status='identified_Latin_site_witness_not_critically_established_edition',author='L.Iunius Moderatus Columella',
        work='De re rustica',book=11,chapter=2,paragraphs=101,language='Latin',our_English='paraphrases,not an attributed translation',
        primary_url='https://www.thelatinlibrary.com/columella/columella.rr11.shtml',catalogue_url='https://www.thelatinlibrary.com/columella.html',
        publisher_index_url='https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Columella/home.html',
        declared_English_url_http_status=404,publisher_bookXI_English_and_Latin_not_online=True,
        publisher_link_to_complete_Latin_verified=True,publisher_general_edition_assertion='LatinLibrary described as unmodified Lundstrom text',
        direct_bookpage_edition_metadata_present=False,exact_critical_edition_independently_verified=False,translator=None,
        retrieval_scope='wholebookXI raw;chaptersI/III incidentally retrieved/partly visible during identity inspection,not extracted as evidence',
        source_is_development=True,independent_historical_validation=False,raw_fulltext_redistributed=False))
    write(OUT/'limits.json',dict(complete_measured_monthly_occupation=False,global_crop_calendar=False,warehouse_handling_intensity=False,
        physical_staff_affiliation=False,workday_hours_defined_for_model=False,source_hours_not_modern_work_capacity=True,
        paragraph6_interval_term='semestrium',paragraph6_term_not_used_for_numeric_duration=True,
        paragraph9_development_marker='quattuor fibrarum',modern_growth_stage_unqualified=True,
        paragraph26_unit='modios tres una opera',seed_volume_not_area_or_edible_output=True,
        paragraph46_lira_clause='lirantur autem iugera duo bis opera una',clause_not_repaired_or_implemented=True,
        paragraph54_thirty_days_applies_to_straw=True,warehouse_residence_time_not_inferred=True,
        paragraph82_competing_work_norms_retained=True,paragraph94_solstice_markers=['XVI Kal. Ian.','VIIII Kal. Ian.'],
        one_solstice_date_not_selected=True,modern_dates_or_model_bins_assigned=0,source_rate_adoption=False))
    paths=[Path(__file__),PLAN,ADAPTER,PARENT/'qualification.json']
    for name in ['exposure.json','latin_exposure.json','retrieval_failure.json','publisher_index_retrieval.json','latin_retrieval.json']:
        paths.append(OUT/name)
    sources={str(path.relative_to(ROOT)):sha(path) for path in paths}
    local={str(path.relative_to(OUT)):sha(path) for path in source.iterdir() if path.is_file()}
    for name,digest in prior['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',dict(status='completed_one_Latin_primary_calendar_witness_with_edition_and_model_transfer_limits',
        sources_sha256=sources,local_source_sha256=local,protected_sha256=prior['protected_sha256'],
        files_sha256={path.name:sha(path) for path in OUT.iterdir() if path.is_file()},paragraphs=101,located_claims=39,
        primary_analytical_chapters=1,exact_critical_edition_verified=False,new_numeric_model_inputs=0,modern_dates_or_model_bins=0,
        labour_LP_calls=0,component_work_calls=0,food_kernel_calls=0,stock_solves=0,graph_rebuilds=0,dijkstra_calls=0,
        new_Earth_food_scenarios=0,new_staff_allocations=0,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False))
    print('Extracted39located calendar/task claims across101covered paragraphs;zero model inputs',flush=True)


if __name__=='__main__':main()
