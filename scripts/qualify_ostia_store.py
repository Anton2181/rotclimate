"""One primary warehouse source:typed claims,coverage and unresolved arithmetic.

Publisher chapter DOI10.4000/books.efr.32815 is authoritative. Local raw
HTML/author-PDF caches are not redistributed. No source value is a model input.
"""
import csv
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from polity.storage_capacity import PhysicalStore,Quantity,convert

OUT=ROOT/'output/urban_ostia_storage_20261117'
PARENT=ROOT/'output/urban_storage_contract_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/ostia_store_source_qualification.json'
URL='https://books.openedition.org/efr/32815?lang=fr'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


class Chapter(HTMLParser):
    def __init__(self):
        super().__init__();self.active=False;self.parts=[];self.para=None;self.rows=[];self.skip=0
        self.table=False;self.cell=False;self.cell_parts=[];self.table_row=[];self.table_rows=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='table':self.table=True
        if self.table and tag in ['td','th']:self.cell=True;self.cell_parts=[]
        if tag=='p' and 'texte' in a.get('class','').split():self.active=True;self.parts=[];self.para=None
        if self.active:
            if self.skip:self.skip+=1
            elif a.get('class')=='paranumber':self.para=int(a['id'].split('-')[1]);self.skip=1
            elif 'footnotecall' in a.get('class',''):self.skip=1
    def handle_endtag(self,tag):
        if self.skip:self.skip-=1
        elif tag=='p' and self.active:
            if self.para:self.rows.append(dict(paragraph=self.para,text=' '.join(''.join(self.parts).split())))
            self.active=False
        if tag in ['td','th'] and self.cell:self.table_row.append(' '.join(''.join(self.cell_parts).split()));self.cell=False
        elif tag=='tr' and self.table:self.table_rows.append(self.table_row);self.table_row=[]
        elif tag=='table':self.table=False
    def handle_data(self,text):
        if self.active and not self.skip:self.parts.append(text)
        if self.cell:self.cell_parts.append(text)


# Numeric entries retain source strings,including approximate/bounded values.
# They are source claims,not observations silently promoted to model parameters.
NUMBERS=[
 ('gross_length',2,'180','100','m','reported_architectural_dimension','gross envelope,not usable grain area'),
 ('gross_width',2,'180','72','m','reported_architectural_dimension','gross envelope,not usable grain area'),
 ('gross_area_lower_bound',12,'189','7000','m2','reported_architectural_extent','source says greater than;not net area'),
 ('surviving_wall_height',12,'189','3','m','reported_preserved_extent','up to;not grain fill height'),
 ('distance_to_ancient_river',9,'185','150','m','source_spatial_estimate','connection and river position uncertain'),
 ('early_building_height',18,'192','9','m','author_reconstruction','approximate architectural height,not pile height'),
 ('phase5_cella_threshold',22,'193','0,50','m','reported_architectural_dimension','greater than circulation level'),
 ('phase6_external_openings',23,'196','1,50','m','reported_architectural_dimension','above paved street,not pile height'),
 ('raised_floor_room_count',56,'212','53','rooms','source_archaeological_inventory','preservation systems,not measured load'),
 ('support_wall_width',57,'212–213','0,30|0,45','m','reported_architectural_range','raised-floor support geometry'),
 ('support_wall_height',57,'212–213','0,55|0,60','m','reported_architectural_range','underfloor void,not grain depth'),
 ('grain_height_proposals',58,'213','2,20|1,60','m','author_estimates','first upper proposal,second more probable;not observed bounds'),
 ('vault_height_reconstruction',58,'213','5','m','author_reconstruction','slightly less than;architectural height'),
 ('air_layer_interpretation',58,'213','3','m','author_derivation','approximate;not calibrated thermal buffering'),
 ('modern_repose_range',61,'215','24|26','degrees','modern_FAO_analogy','modern wheat,not measured ancient grain'),
 ('chosen_repose_angle',64,'217','26','degrees','author_convention','theoretical/maximalist pile geometry'),
 ('chosen_pile_width_fraction',64,'217','2/3','cella_width_fraction','author_convention','grain footprint explicitly unknown'),
 ('raised_floor_bulk_volume_prose',64,'217','990','m3','author_capacity_estimate','approximately;not stored grain observation'),
 ('raised_floor_bulk_modii_prose',64,'217','103 500','modii','author_capacity_estimate','approximately;unit consistency unresolved'),
 ('upper_storey_multiplier',64,'217','2','dimensionless','author_extrapolation','probable doubling,not an observed filled storey'),
 ('central_bulk_volume_prose',65,'217–218','204','m3','author_capacity_estimate','alternative bulk case'),
 ('central_bulk_modii_prose',65,'218','23 300','modii','author_capacity_estimate','approximate'),
 ('modern_sack_stack_height',65,'218','5|6','m','modern_FAO_analogy','not adopted as ancient geometry'),
 ('small_door_leaf_mean',65,'218,n117','0,45','m','reported_measurement_summary','mean of listed in-situ door-leaf widths'),
 ('chosen_sack_wall_clearance',65,'218','0,45','m','author_inference_from_door_width','storage clearance is inferred,not separately measured'),
 ('chosen_sack_pyramid_height',65,'218','4,50','m','author_convention','approximately15Romanfeet;actual stack unknown'),
 ('chosen_sack_pyramid_angle',65,'218','75','degrees_to_floor','author_convention','actual angle unknown'),
 ('modern_bulk_specific_volume',65,'218,n118','1,3','m3/tonne','modern_FAO_analogy','not ancient observation'),
 ('modern_sack_specific_volume',65,'218,n118','1,6','m3/tonne','modern_FAO_analogy','package volume differs from grain volume'),
 ('central_sack_grain_volume_prose',65,'218','753','m3','author_capacity_estimate','grain rather than outer package envelope'),
 ('central_sack_modii_prose',65,'218–219','84 000','modii','author_capacity_estimate','approximate'),
 ('modern_density_range_rejected',66,'219','750|840','kg/m3','modern_FAO_analogy','authors explicitly reject direct ancient transfer'),
 ('ancient_text_density_comparison',66,'219','740|804','kg/m3','interpretation_of_cited_Pliny','lower end less than740;not source-site bulk sample'),
 ('adopted_density_in_source',66,'219,n121','740','kg/m3','author_convention_from_ancient_text','not adopted here or used for edible energy'),
 ('source_modius_volume',66,'219,n121','8,76','litres/modius','author_unit_convention','used only for internal source-column check'),
 ('source_modius_mass',66,'219,n121','6,48','kg/modius','author_unit_convention','rounded convention,not independent measured density'),
 ('source_mass_range',66,'219–220','1645|2430','tonnes','author_capacity_estimate','approximately;not independent historical stock'),
 ('inbound_ship_size_comparison',40,'202–203','150|200','tonnes','secondary_literature_estimates','competing estimates for3000amphora carrier'),
 ('inbound_ship_amphora_class',40,'202–203','3000','amphorae','secondary_literature_claim','not a measured local fleet'),
 ('inbound_ship_volume_example',40,'203','20 000','modii','secondary_literature_estimate','associated with150tonne example'),
 ('unloading_time_example',45,'205','1','week','source_scenario_estimate','for150tonne carrier,not directly measured warehouse rate'),
 ('bag_mass_example',45,'205','35','kg/bag','author_assumption','approximately;transport handling example'),
 ('bag_modii_example',45,'205','5','modii/bag','author_assumption','approximately;different rounded handling convention'),
 ('saccarii_trip_count',45,'205','4200','trips','author_derivation','more than;not worker census or measured workforce'),
 ('inbound_ships_for_ground_floor',46,'205','6|9','ships','author_derivation','150tonne illustrative carriers'),
 ('modern_moisture_threshold',51,'209','15','percent','modern_analogy_hypothesis','conditional on ancient properties resembling modern'),
 ('modern_temperature_range',51,'209','15|30','degrees_C','modern_analogy_hypothesis','not measured ancient Tiber microclimate'),
 ('conditional_safe_storage',51,'209','1|6','months','modern_analogy_hypothesis','best-condition range,not historical residence time'),
 ('outbound_boat_capacity_mass',70,'220','70','tonnes','secondary_scenario_estimate','medium caudicaria example,not measured fleet'),
 ('outbound_boat_capacity_volume',70,'220','10 000','modii','secondary_scenario_estimate','approximate handling convention'),
 ('outbound_cycle',70,'220','10','days','secondary_scenario_estimate','approximately;not existing network travel-bin calibration'),
 ('outbound_cycle_parts',70,'220','3|3|3|0,5','days','secondary_scenario_estimates','loading,upstream,unloading,downstream respectively'),
 ('navigable_days',70,'220','300','days/year','secondary_scenario_assumption','at least;not modeled year-round availability evidence'),
 ('outbound_annual_rotations',70,'220','30','rotations/year','author_derivation','conditional on boat and navigable-day assumptions'),
 ('warehouse_outbound_rotations',71,'222','25|37','rotations','author_derivation','conditional on authors reconstructed capacities'),
 ('one_boat_warehouse_clearance',71,'222','8 mois|1 an','as_printed_mixed_time','author_derivation','not grain residence observation;no silent time-unit normalization'),
 ('one_month_fleet_example',71,'222','20|30','boats','author_derivation','illustrative simultaneous fleet,not observed fleet size'),
 ('Rome_demand_denominator',75,'223','50 000 000','modii/year','secondary_city_demand_estimate','recorded only as source denominator,no city/model crossing'),
 ('Rome_demand_mass_equivalent',75,'223','350 000','tonnes/year','secondary_city_demand_estimate','not a population observation or calibrated model input'),
 ('source_share_of_Rome_demand',75,'223','0,50|0,75','percent','author_derivation','warehouse reconstruction divided by secondary city demand'),
 ('source_Rome_meal_day_equivalent',75,'223','1,8|2,7','days','author_derivation','stock/demand equivalent,not residence time or new store setting')]

CONTEXT=[
 ('location_and_access',8,'184–185','architectural_interpretation','Port warehouse with restricted access;connection to river not securely established.'),
 ('public_land_not_grain_rights',11,'186–188','epigraphic_context_and_interpretation','Public-land context does not identify grain ownership or allocation rights.'),
 ('phase_identity',39,'202','author_scope','Functional reconstruction selects first Severan phase,not all phases combined.'),
 ('phase_uncertainty',36,'201','source_chronological_limit','Brick stamps do not resolve construction/rebuilding chronology precisely.'),
 ('commodity_identity',38,'202','explicit_author_convention','No positive determination of contents;wheat chosen by convention.'),
 ('stored_grain_state',38,'202','unknown','Species and cleaned/husked state not authenticated;no net-edible yield supplied.'),
 ('layout_and_doubling',60,'214–215','author_reconstruction','Earlier geometry incomplete;central rooms and upper storey condition capacity estimates.'),
 ('bulk_or_sacks',59,'213–214','author_hypotheses','Bulk favored argumentatively;sack/intermediate relay interpretation not excluded.'),
 ('cleaning_and_handling',48,'208','interpretative_operating_sequence','Sorting,drying,cleaning and moisture checks require work;no usable labor rate given.'),
 ('repairs_and_aeration',50,'208','interpretative_operating_sequence','Regular turning,aeration and store maintenance;not a quantified annual loss law.'),
 ('microclimate',52,'209','explicit_unknown','Ancient internal temperature/humidity not known;modern storage bounds remain conditional.'),
 ('structural_load',57,'212–213','unknown_numeric_limit','Raised masonry supports described;no admissible kg/m2 load bound supplied.'),
 ('door_geometry',54,'210','architectural_observation_and_functional_interpretation','Door-adjacent pillars preserve access;not an observed grain footprint.'),
 ('residence_time',68,'220','unknown','Unspecified stock interval;conditional preservation months do not measure actual residence.'),
 ('redistribution_destination',77,'223–224','explicit_unresolved_question','Rome versus priority use within Ostia remains unresolved.'),
 ('source_equation',64,'217,n114','printed_expression_not_adopted','As printed,formula adds a cubic prism term and an area term;do not silently repair.'),
 ('water_volume_excluded',28,'197–198','non_cereal_inventory','Cistern capacity concerns water;must not be counted as cereal storage.'),
 ('later_work',78,'224–225','publication_addendum','Base text completed2008,published2016;later-complex examples are outside this cohort.')]


def table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    assert not (OUT/'results.json').exists(),'Preserve completed source qualification'
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    registered=read(OUT/'exposure.json');assert registered['status']=='registered_development_before_target_search_or_body_read'
    assert registered['plan_sha256']==sha(PLAN)
    parent=read(PARENT/'qualification.json');assert parent['status'].startswith('passed_explicit_storage_capacity_contract')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():assert sha(prefix/name)==digest,name
    source=OUT/'source';html=(source/'chapter.html').read_text();parser=Chapter();parser.feed(html)
    assert [row['paragraph'] for row in parser.rows]==list(range(1,82))
    assert len(parser.table_rows)==8
    for literal in ['Les Grandi Horrea d’Ostie','Giulia Boetto','Évelyne Bukowiecki','Nicolas Monteix','Corinne Rousse',
                    '177-226','2016/01','10.4000/books.efr.32815','Licence OpenEdition Books']:
        assert literal in html,literal
    pdf=source/'halshs-01441802-mirror.pdf';access=read(source/'mirror_access.json');assert sha(pdf)==access['sha256']
    raw=subprocess.check_output(['pdftotext','-raw',str(pdf),'-'],text=True)
    layout=subprocess.check_output(['pdftotext','-layout',str(pdf),'-'],text=True)
    pages=layout.split('\f');chapter_pages=pages[6:56];assert len(chapter_pages)==50
    assert '522' in pages[1] and '2016' in pages[1] and 'halshs-01441802' in pages[0]
    assert 'LES GRANDI HORREA' in chapter_pages[4] and '226' in chapter_pages[-1][:100]
    # Pin only this chapter's semantic source text;the mirror additionally has
    # covers,bibliography and indexes,which are not a second empirical cohort.
    semantic='\n'.join(row['text'] for row in parser.rows)
    write(OUT/'source_identity.json',dict(chapter_doi='10.4000/books.efr.32815',publisher_url=URL,
        title='Les Grandi Horrea d’Ostie',authors=['Giulia Boetto','Évelyne Bukowiecki','Nicolas Monteix','Corinne Rousse'],
        print_year=2016,publisher_online_date='2022/03/01',printed_pages=[177,226],collection=522,
        publisher_html_sha256=sha(source/'chapter.html'),publisher_paragraphs_sha256=hashlib.sha256(semantic.encode()).hexdigest(),
        mirror_pdf_sha256=sha(pdf),hal_id='halshs-01441802',mirror_pdf_chapter_pages=[7,56],
        publisher_meta_citation_doi_is_book_level='10.4000/books.efr.32730',
        publisher_citation_modal_chapter_doi_verified=True,
        license='Publisher text:Licence OpenEdition Books;illustrations/annexes all rights reserved unless otherwise stated. Raw caches not redistributed.',
        metadata_discrepancies='Secondary catalogue snippets contain552/322and178page variants;retained book title page522and publisher177–226 are authoritative.',
        source_access_receipts=[read(source/'access.json'),access]))
    nrows=[]
    for field,para,page,value,unit,kind,limit in NUMBERS:
        assert 1<=para<=81 and value
        nrows.append(dict(field=field,paragraph=para,printed_page=page,source_value=value,unit=unit,
            statement_kind=kind,limit=limit,source_url=URL.split('?')[0]+'#para-'+str(para),
            source_claim_only=True,model_parameter_adopted=False))
    crows=[dict(field=field,paragraph=para,printed_page=page,statement_kind=kind,assessment=assessment,
                source_url=URL.split('?')[0]+'#para-'+str(para)) for field,para,page,kind,assessment in CONTEXT]
    table(OUT/'numeric_claims.csv',nrows);table(OUT/'context.csv',crows)
    table(OUT/'capacity_estimates.csv',[dict(group=row[0],volume_m3=row[1],modii=row[2],estimated_tonnes=row[3],
        statement_kind='author_reconstruction_estimate_not_measured_stock',printed_page=217,source_locator='Table1',adopt=False)
        for row in parser.table_rows[1:]])
    relevant={x[1] for x in NUMBERS}|{x[1] for x in CONTEXT}
    coverage=[]
    for row in parser.rows:
        num=row['paragraph']
        status='claims_or_context_recorded' if num in relevant else 'context_read_no_distinct_capacity_measurement'
        if num in [27,37,47,67]:status='author_signature'
        if num in [55,79,80,81]:status='external_comparison_or_reference_not_extracted'
        coverage.append(dict(paragraph=num,status=status,source_url=URL.split('?')[0]+'#para-'+str(num)))
    table(OUT/'coverage.csv',coverage)
    # Unit check of published columns only;no corrected capacities are adopted.
    checks=[];modius=Decimal('0.00876');rho=Decimal('740')
    for row in parser.table_rows[1:]:
        def endpoints(s):return [Decimal(v.strip().replace('ca.','').replace(',','.')) for v in s.split(' - ')]
        volumes=endpoints(row[1]);mods=endpoints(row[2]);masses=endpoints(row[3])
        for index,(v,m,t) in enumerate(zip(volumes,mods,masses)):
            implied=m*modius;checks.append(dict(group=row[0],endpoint=index,reported_volume_m3=str(v),reported_modii=str(m),
                implied_volume_from_source_modius_m3=str(implied),reported_minus_implied_volume_m3=str(v-implied),
                reported_mass_tonnes=str(t),mass_from_reported_volume_and_source_density_tonnes=str(v*rho/1000),
                assessment='source_column_diagnostic_only_no_correction_or_model_adoption'))
    table(OUT/'source_column_checks.csv',checks)
    write(OUT/'source_issues.json',dict(north_row_volume_and_modii_unaligned_under_source_unit=True,
        central_sack_endpoint_volume_and_modii_unaligned_under_source_unit=True,
        printed_formula='V=(L*l*h/2)+(pi*l^2/3)/4;h=l*tan(26)',
        printed_formula_term_length_exponents=[3,2],dimensional_issue_visible_in_HTML_note114_and_PDF_page217=True,
        source_formula_not_implemented_or_corrected=True,source_table_not_reconciled=True,
        illustration_digitization=False,archaeological_measurements_reconstructed_from_plans=False))
    unknown=lambda unit:Quantity(None,unit,'unknown',URL,'No compatible operational input established')
    record=PhysicalStore('GrandiHorreaOstia:firstSeveran','port_warehouse','Ostia:complex_II_9',
        'firstSeveran_phase_author_scope',None,None,None,'net edible cereal','stored_material','single_commodity_allocated_usable',
        unknown('m2'),unknown('m'),Quantity(740.,'kg_stored/m3','author_estimate',URL,'p219,n121,not adopted'),
        'wheat_by_author_convention',None,unknown('kg_edible/kg_stored'),unknown('kcal/kg_edible'),unknown('kg_stored/m2'),None,None)
    result=convert(record);assert result['geometric_net_energy_kcal'] is None and not result['empirically_qualified']
    write(OUT/'interface.json',dict(source_capacity_estimates_are_not_converter_inputs=True,
        commodity_not_empirically_identified=True,stored_state_unqualified=True,source_record_status='incomplete_source_context_not_attached_to_network',
        conversion_result=result,model_origin_or_city_crossing_performed=False))
    paths=[Path(__file__),PLAN,PARENT/'qualification.json',ROOT/'polity/storage_capacity.py']
    # Raw caches are local/protected by digests;public outputs retain facts,
    # provenance and negative findings rather than republishing the chapter.
    r=dict(status='completed_one_complex_Ostia_source_qualification_with_unresolved_numeric_issues',
        sources_sha256={str(p.relative_to(ROOT)):sha(p) for p in paths},protected_sha256=parent['protected_sha256'],
        local_source_sha256={str(p.relative_to(OUT)):sha(p) for p in source.iterdir() if p.is_file()},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},
        publisher_paragraphs=81,printed_chapter_pages=50,numeric_source_claims=len(nrows),context_rows=len(crows),
        capacity_estimate_rows=7,source_column_checks=len(checks),historical_operational_capacities_qualified=0,
        geometric_net_energy_computed=False,source_issues_preserved=True,network_attachments=0,
        food_kernel_calls=0,new_food_scenarios=0,new_fit=False,new_validation_claim=False,actual_population_changed=False,adopt=False)
    for name,digest in parent['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',r);print(r['status'],r['numeric_source_claims'],'numeric source statements',flush=True)


if __name__=='__main__':main()
