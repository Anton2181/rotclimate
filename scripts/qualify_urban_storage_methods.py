"""One-source archaeological methods ledger; no site data or food model runs.

Source: Salido Domínguez (2018), Gerión 36(1),79–94,CC BY4.0.
The ledger distinguishes the author's review/interpretation from verified
primary measurements and from our explicit model-interface requirements.
"""
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_storage_methods_20261117'
PARENT=ROOT/'output/urban_storage_source_scope_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/storage_capacity_method_qualification.json'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def normalized(text):
    text=unicodedata.normalize('NFC',text)
    text=re.sub(r'-\s*\n\s*','',text)
    return ' '.join(text.split())


# These are methods locators,not extracted site measurements. Spanish anchors
# locate the argument; English interpretations are our labelled paraphrases.
CLAIMS=[
    ('commodity_identity',88,'§7,item1','el tipo de cereal',
     'reviewed_unknown','Cereal identity is frequently unknown;mass conversion depends on what was stored.',
     'Require material-specific density provenance;the cited Gentry table is not our measured density.'),
    ('mixed_commodities',88,'§7,item2;§4pp85–86','no sólo se conservó grano',
     'review_of_cited_archaeobotanical_findings','Horrea can contain products other than grain.',
     'Do not allocate the whole building to one modeled edible-cereal pool.'),
    ('storage_arrangement',88,'§7,item3;§5pp86–87','a granel, en sacos',
     'reviewed_unknown','Bulk,sack and container arrangements are not generally determined.',
     'Require a compatible usable-volume definition;bulk filling is not a universal geometry.'),
    ('grain_state',88,'§7,item4;§3pp84–85','en espigas o limpio',
     'reviewed_unknown','Ear/husk/clean-grain state is often unresolved.',
     'Match bulk density and edible conversion to stored state;avoid repeated net-harvest deductions.'),
    ('turnover_and_ownership',88,'§7,item5','continuamente vaciados en cada cosecha',
     'author_interpretation','Author argues harvest turnover and owner needs decouple stocks from annual production.',
     'This motivates separate throughput/stock/rights,not a measured dispatch schedule or universal immediacy.'),
    ('working_space',88,'§7,item6,continuedp89','espacios de circulación',
     'author_inference_from_archaeobotany','Circulation,ventilation and possible compartmentation reduce grain-usable space.',
     'Use explicitly allocated usable area/volume rather than gross footprint.'),
    ('structural_support',89,'§7,item7','resistencia de los tabulata',
     'physical_constraint_with_unknown_material','Raised-floor support depends on construction material and is hard to estimate.',
     'A geometric volume is not an operational capacity without structural support evidence.'),
    ('fill_geometry',89,'§7,item8,continuedp90','No existe acuerdo',
     'reported_disagreement_between_prior_estimates','Prior proposals disagree about safe pile height and preservation.',
     'Do not pick one cited height or the density table as a new calibrated ancient coefficient.'),
    ('duration',90,'§7,item9','no necesariamente debe mantener el grano durante',
     'author_interpretation_with_unknown_duration','Store duration is unknown;one year is not required for every rural horreum.',
     'Capacity-day equivalents need a separately justified flow denominator and seasonal use.'),
    ('chronology_and_function',81,'§2,Veranes discussion,continuedp84','cuando el edificio cambió de función',
     'review_of_dated_site_interpretation','A cited building changes function over time.',
     'Do not transfer storage function/capacity between building phases or automatically to the model epoch.'),
    ('preservation_and_losses',87,'§6,continuedp88','La germinación puede',
     'author_interpretation_and_review_of_cited_findings','Germination can be intentional or accidental;preservation depends on conditions.',
     'Do not infer an annual stored-energy loss fraction from germination presence or a threshold.'),
    ('coverage_and_observation',84,'§2,regional evidence limitations','las conclusiones a las que podemos llegar',
     'author_evidence_coverage_assessment','Evidence coverage and excavation reporting are incomplete.',
     'This one review is methods evidence,not a representative ancient store census or independent transfer test.')]


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    parent=read(PARENT/'qualification.json');assert parent['status'].startswith('passed_existing_storage_contract')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():assert sha(prefix/name)==digest,name
    OUT.mkdir(exist_ok=True);assert not (OUT/'results.json').exists(),'Preserve completed qualification'
    source=OUT/'source';pdf=source/'salido2018.pdf';access=read(source/'access.json')
    assert sha(pdf)==access['sha256']=='a4374b2b23e7cbfea88b3abe2ebb26fd71515a6ea2adb82bedf09c31d4608424'
    extracted={}
    for mode in ['layout','raw']:
        path=source/f'salido2018.{mode}.txt'
        # Fresh extraction checks the recorded PDF;no network/source substitution.
        subprocess.run(['pdftotext','-'+mode,str(pdf),str(path)],check=True)
        pages=[text for text in path.read_text().split('\f') if text.strip()]
        assert len(pages)==16
        first=normalized(pages[0]);assert '10.5209/GERI.60294' in first
        assert 'Javier Salido Domínguez' in first and 'Gerión 36(1) 2018: 79-94' in first
        extracted[mode]=pages
    rows=[]
    for field,page,locator,anchor,kind,meaning,limit in CLAIMS:
        for pages in extracted.values():assert anchor in normalized(pages[page-79]),(field,page)
        rows.append(dict(field=field,printed_page=page,pdf_page=page-78,section=locator,span_anchor=anchor,
            source_statement_kind=kind,interpretation=meaning,our_interface_requirement=limit,
            primary_site_measurement_verified=False,numeric_parameter_adopted=False))
    with (OUT/'methods.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write(OUT/'exposure.json',dict(status='full_source_development_methods_read_not_evaluation',date='2026-11-17',
        article_doi='10.5209/GERI.60294',article_sha256=sha(pdf),article_pages=16,
        figures_and_numerical_examples_incidentally_visible=True,
        numerical_site_or_density_or_height_observations_extracted=0,site_measurement_table_created=False,
        secondary_cited_sources_opened=0,primary_site_observations_verified=0,
        reviewed_pdf_pages=[88,89,90],visual_checks='Enumerated factors7–9 and qualitative claims checked against publisher PDF images.',
        van_oyen_chapter_body_read=False,rickman_monograph_body_read=False,
        record_limits='Do not call this source,its illustrations or already-visible examples an unseen validation pool.'))
    paths=[Path(__file__),PLAN,PARENT/'qualification.json',pdf,source/'access.json']
    result=dict(status='completed_one_source_storage_capacity_methods_qualification',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=parent['protected_sha256'],
        files_sha256={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()},
        source_doi='10.5209/GERI.60294',method_fields=len(rows),pages=16,extraction_paths=2,
        all_anchors_match_both_extractions=True,primary_site_measurements_verified=0,
        new_qualified_historical_numeric_parameters=0,new_site_measurement_rows=0,food_kernel_calls=0,new_food_scenarios=0,
        decision='Retain current store budgets as explicit scenarios. Future physical stores need function/location/material/chronology and usable-volume evidence before conversion or attachment to modeled origins.',
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False)
    for name,digest in parent['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',result);print(result['status'],len(rows),'fields;two extraction paths',flush=True)


if __name__=='__main__':main()
