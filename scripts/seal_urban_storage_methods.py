"""Verify source identity, page anchors and the methods-only qualification boundary."""
import csv
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from qualify_urban_storage_methods import OUT,PARENT,sha,read,write,normalized


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed qualification'
    r=read(OUT/'results.json');assert r['status']=='completed_one_source_storage_capacity_methods_qualification'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    pdf=OUT/'source/salido2018.pdf';info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
    assert 'Pages:           16' in info and 'Javier Salido' in info
    rows=list(csv.DictReader((OUT/'methods.csv').open()));assert len(rows)==12
    for mode in ['raw','layout']:
        # A second process extracts the retained bytes again,not a cached ledger.
        text=subprocess.check_output(['pdftotext','-'+mode,str(pdf),'-'],text=True)
        pages=[page for page in text.split('\f') if page.strip()];assert len(pages)==16
        for row in rows:
            p=int(row['printed_page']);assert int(row['pdf_page'])==p-78
            assert row['span_anchor'] in normalized(pages[p-79])
            assert row['primary_site_measurement_verified']==row['numeric_parameter_adopted']=='False'
    assert len({row['field'] for row in rows})==12
    exposure=read(OUT/'exposure.json');assert exposure['secondary_cited_sources_opened']==0
    assert exposure['numerical_site_or_density_or_height_observations_extracted']==0
    assert not exposure['site_measurement_table_created']
    assert not exposure['van_oyen_chapter_body_read'] and not exposure['rickman_monograph_body_read']
    parent=read(PARENT/'qualification.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():assert sha(prefix/name)==digest,name
    paths=[Path(__file__),ROOT/'reports/URBAN_STORAGE_METHODS_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/storage_capacity_contract.json']
    q=dict(status='passed_one_source_storage_methods_identity_and_dual_extraction_locators',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()},protected_sha256=r['protected_sha256'],
        source_pages=16,method_fields=12,dual_extraction_anchor_checks=24,pdf_visual_pages_checked=[88,89,90],
        primary_site_measurements_independently_verified=0,new_qualified_historical_numeric_parameters=0,
        new_site_measurement_rows=0,food_kernel_calls=0,new_food_scenarios=0,actual_population_changed=False,
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/storage_capacity_contract.json')
    write(OUT/'qualification.json',q);print(q['status'],flush=True)


if __name__=='__main__':main()
