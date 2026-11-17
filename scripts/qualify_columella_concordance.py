"""Six same-chapter expressions:separate digital agreement from printed evidence."""
import csv
from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import sha,read,write
from qualify_columella_calendar import paragraphs

OUT=ROOT/'output/urban_columella_concordance_20261117'
PARENT=ROOT/'output/urban_columella_calendar_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/columella_calendar_concordance.json'


class WikiText(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if 'pagenum' in a.get('class','').split():
            m=re.search(r'/([0-9]+)$',a.get('title',''))
            if m:self.parts.append(' @@PAGE'+m[1]+'@@ ')
    def handle_data(self,text):self.parts.append(text)


def selected_wiki(html):
    fragment=html[html.index('<h3 id="II.">'):html.index('<h3 id="III.">')];fragment=fragment[fragment.index('<p>'):]
    parser=WikiText();parser.feed(fragment);text=' '.join(' '.join(parser.parts).split());parts=re.split(r'\[(\d+)\]',text)
    raw=[(1,parts[0])]+[(int(parts[i]),parts[i+1]) for i in range(1,len(parts),2)]
    assert [n for n,_ in raw]==list(range(1,102))
    page=428;selected={}
    for n,text in raw:
        pages=[page]+[int(x) for x in re.findall(r'@@PAGE(\d+)@@',text)];page=pages[-1]
        if n in [3,6,9,26,46,94]:selected[n]=dict(text=re.sub(r'\s*@@PAGE\d+@@\s*',' ',text).strip(),scan_pages=list(dict.fromkeys(pages)))
    return selected


# Printed readings were inspected visually in the retained six page images.
# Long-s and line breaks are normalized only in these short transcriptions.
TARGETS=[
 (3,428,422,'per dimidios menses','per dimidios menses','same_target_wording',
  ['per dimidios menfes','ante quindecim dies'],'Half-month/fifteen-day wording agrees;no modern date or complete schedule follows.'),
 (6,429,423,'Hoc igitur semestrium','Hoc igitur semestrium','same_target_wording',
  ['femeftrium'],'The unusual interval term is also printed;duration meaning remains unassigned.'),
 (9,430,424,'quattuor fibrarum','quatuor fibrarum','orthographic_variant_same_target',
  ['quatuor fibrarum'],'One/two t orthography retained;no modern botanical stage inferred.'),
 (26,434,428,'modios tres una opera recte sarit','modios tres una opera recte sarrit','orthographic_variant_same_quantity',
  ['modios tres una opera'],'Sarit/sarrit differs;modii/opera quantity is retained without an area conversion.'),
 (46,439,433,'lirantur autem iugera duo bis opera una','lirantur autem jugera duo opera una','digital_print_substantive_variant',
  ['lirantur autem jugera duo opera una'],'Digital texts include bis;the linked printed line lacks it. Do not repair or select a model rate.'),
 (94,451,445,'XVI Kal. Ian.|VIIII Kal. Ian.','Sextodecimo Kalend. Januarii|Nono Kalend. Januarias','source_numeral_spelling_equivalence',
  ['ut Hipparcho placet','Nono Kalend. Januarias'],'Both differently attributed solstice markers survive;source identifier concordance is not modern-date conversion.')]


def table(path,rows):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def main():
    assert not (OUT/'results.json').exists(),'Preserve completed six-target concordance'
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert read(OUT/'exposure.json')['plan_sha256']==sha(PLAN)
    parent=read(PARENT/'qualification.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('local_source_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():assert sha(prefix/name)==digest,name
    source=OUT/'source';wiki_html=(source/'wikisource_book11.html').read_text()
    assert 'De Re Rustica (Gesner)/Liber XI' in wiki_html and '134877' in wiki_html
    index=(source/'scan_index.html').read_text();commons=(source/'scan_commons.html').read_text()
    assert 'Pseudo-Gesner' in index and 'Pseudo-1787' in index
    assert 'Bipontium, Typ. Soc.' in commons and '1787' in commons and 'PD-old-100-expired' in commons
    # Titlepage image5 was inspected:Gesner recension,volume2,Columella,Biponti,1787.
    ll={r['paragraph']:r['text'] for r in paragraphs((PARENT/'source/book11_latin.html').read_text())}
    wiki=selected_wiki(wiki_html);rows=[];visual=[]
    for paragraph,page,printed,original,scan,kind,ocr_anchors,limit in TARGETS:
        assert wiki[paragraph]['text']==ll[paragraph],paragraph
        if paragraph==94:
            for token in original.split('|'):assert token in ll[paragraph]
        else:assert original in ll[paragraph]
        image=source/f'scan_page{page}.jpg';assert image.exists()
        ocr=source/f'ocr_page{page}.txt';text=' '.join(ocr.read_text().split())
        for token in ocr_anchors:assert token in text,(paragraph,token)
        rows.append(dict(paragraph=paragraph,first_witness='LatinLibrary bookXI',digital_comparator='Wikisource revision134877',
            whole_selected_digital_paragraphs_exact=True,digital_target=original,printed_target_normalized=scan,
            scan_page=page,printed_page=printed,comparison=kind,limits=limit,
            scan_supports_digital_target_without_substantive_variant=paragraph!=46,
            independent_textual_descent_established=False,model_adoption=False))
        visual.append(dict(paragraph=paragraph,scan_page=page,printed_page=printed,image_sha256=sha(image),
            OCR_sha256=sha(ocr),visual_reading_normalized=scan,long_s_normalized_for_short_reading=True,
            visual_inspected=True,OCR_only_not_sufficient=True))
    table(OUT/'concordance.csv',rows);write(OUT/'visual_checks.json',visual)
    write(OUT/'identity.json',dict(status='printed_title_identified_online_transcription_edition_equivalence_not_established',
        work='Columella,De re rustica11.2',digital_revision=134877,
        digital_url='https://la.wikisource.org/w/index.php?title=De_Re_Rustica_(Gesner)/Liber_XI&oldid=134877',
        scan_url='https://commons.wikimedia.org/wiki/File:Columellae_opera.djvu',
        titlepage_scan_page=5,titlepage_visual_inspected=True,title='Scriptores rei rusticae veteres Latini',
        printed_recension='E recensione Jo.Matth.Gesneri',volume=2,contents='Columellam',imprint='Biponti,Ex Typographia Societatis',
        printed_title_year=1787,source_index_labels=['Pseudo-Gesner','Pseudo-1787'],metadata_pseudo_labels_explained=False,
        exact_LatinLibrary_critical_edition_still_unverified=True,digital_and_scan_whole_edition_equivalence_established=False,
        six_selected_digital_paragraphs_identical=True,digital_textual_independence_established=False,
        public_domain_scan_status='Commons PD-old-100-expired;printed1787title inspected',
        adjacent_scan_page_context_incidental=True,new_historical_validation=False))
    write(OUT/'limits.json',dict(selected_locations=6,substantive_target_variants=1,variant_paragraph=46,
        digital_has_bis=True,linked_printed_line_has_bis=False,variant_not_reconciled=True,
        old_source_packet_not_edited=True,no_model_reading_selected=True,dual_solstice_markers_retained=True,
        semestrium_duration_still_unassigned=True,fibrae_modern_stage_still_unassigned=True,
        modii_not_converted_to_area=True,modern_date_or_bin_conversions=0,new_rate_coefficients=0,
        full_Earth_occupation_or_staffing_qualified=False))
    paths=[Path(__file__),PLAN,PARENT/'qualification.json',ROOT/'scripts/qualify_columella_calendar.py']
    sources={str(p.relative_to(ROOT)):sha(p) for p in paths}
    local={str(p.relative_to(OUT)):sha(p) for p in source.iterdir() if p.is_file()}
    for name,digest in parent['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',dict(status='completed_six_target_concordance_with_one_unreconciled_digital_print_variant',sources_sha256=sources,
        local_source_sha256=local,protected_sha256=parent['protected_sha256'],files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},
        target_locations=6,selected_digital_paragraphs_exact=6,selected_printed_pages_inspected=6,titlepage_inspected=True,
        substantive_target_variants=1,whole_edition_equivalence_established=False,old_packet_changed=False,
        solver_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,new_numeric_model_inputs=0,
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False))
    print('Six-target concordance:6identical digital paragraphs,1printed-target variant;no model adoption',flush=True)


if __name__=='__main__':main()
