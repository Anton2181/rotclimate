"""Independent six-locus digital comparison and retained scan/visual/OCR safeguards."""
import csv
from html import unescape
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_work_evidence_scope import sha,read,write

OUT=ROOT/'output/urban_columella_concordance_20261117'
PARENT=ROOT/'output/urban_columella_calendar_20261117'


def numbered(text):
    parts=re.split(r'\[(\d+)\]',text)
    rows={1:parts[0].strip()};rows.update({int(parts[i]):parts[i+1].strip() for i in range(1,len(parts),2)})
    assert list(rows)==list(range(1,102))
    return rows


def main():
    assert not (OUT/'review.json').exists(),'Preserve independent concordance review'
    r=read(OUT/'results.json');assert r['status']=='completed_six_target_concordance_with_one_unreconciled_digital_print_variant'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for key in ['files_sha256','local_source_sha256']:
        for name,digest in r[key].items():assert sha(OUT/name)==digest,name
    primary=(PARENT/'source/book11_latin.html').read_text();primary=primary.split('<b>II.</b>',1)[1].split('<b>III. DE CULTU HORTORUM</b>',1)[0]
    wiki=(OUT/'source/wikisource_book11.html').read_text();wiki=wiki.split('<h3 id="II.">',1)[1].split('<h3 id="III.">',1)[0];wiki=wiki[wiki.index('<p>'):]
    strip=lambda text:' '.join(unescape(re.sub(r'<[^>]+>',' ',text)).split())
    ll=numbered(strip(primary));other=numbered(strip(wiki))
    rows=list(csv.DictReader((OUT/'concordance.csv').open()));assert [int(c['paragraph']) for c in rows]==[3,6,9,26,46,94]
    visual=read(OUT/'visual_checks.json');assert len(visual)==6
    for row,v in zip(rows,visual):
        n=int(row['paragraph']);assert ll[n]==other[n]
        assert v['paragraph']==n and sha(OUT/'source'/f'scan_page{row["scan_page"]}.jpg')==v['image_sha256']
        assert sha(OUT/'source'/f'ocr_page{row["scan_page"]}.txt')==v['OCR_sha256']
        assert v['visual_inspected'] and v['OCR_only_not_sufficient']
        assert row['model_adoption']=='False' and row['independent_textual_descent_established']=='False'
        if n!=94:assert row['digital_target'] in ll[n]
        else:
            assert all(x in ll[n] for x in ['XVI Kal. Ian.','VIIII Kal. Ian.','ut Hipparcho placet','sic Chaldaei observant'])
    variant=next(c for c in rows if c['paragraph']=='46')
    assert variant['digital_target']=='lirantur autem iugera duo bis opera una'
    assert variant['printed_target_normalized']=='lirantur autem jugera duo opera una'
    assert variant['comparison']=='digital_print_substantive_variant'
    # OCR supports the visually inspected printed target;never normalize away bis.
    ocr=' '.join((OUT/'source/ocr_page439.txt').read_text().split())
    assert 'lirantur autem jugera duo opera una' in ocr
    assert 'lirantur autem jugera duo bis opera una' not in ocr
    identity=read(OUT/'identity.json');limits=read(OUT/'limits.json')
    assert identity['printed_title_year']==1787 and identity['volume']==2 and identity['titlepage_visual_inspected']
    assert identity['source_index_labels']==['Pseudo-Gesner','Pseudo-1787'] and not identity['metadata_pseudo_labels_explained']
    assert not identity['digital_and_scan_whole_edition_equivalence_established']
    assert limits['substantive_target_variants']==1 and limits['old_source_packet_not_edited'] and limits['variant_not_reconciled']
    parent=read(PARENT/'qualification.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('local_source_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():assert sha(prefix/name)==digest,name
    write(OUT/'review.json',dict(status='passed_faithful_six_locus_concordance_with_unreconciled_scan_variant',reviewer_sha256=sha(Path(__file__)),
        results_sha256=sha(OUT/'results.json'),target_locations=6,exact_selected_digital_paragraphs=6,
        substantive_target_scan_variants=1,scan_variant_paragraph=46,visual_receipts_verified=6,
        printed_edition_and_digital_equivalence_established=False,old_packet_identities_unchanged=True,
        new_numeric_model_inputs=0,modern_date_conversions=0,solver_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,
        new_fit=False,new_validation_claim=False,adopt=False))
    print('Independent six-locus review passed;printed bis absence retained,old witness unchanged',flush=True)


if __name__=='__main__':main()
