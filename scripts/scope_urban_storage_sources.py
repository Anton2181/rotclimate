"""Existing-source/interface inventory and bibliographic leads; no model calls."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_storage_source_scope_20261117'
PARENT=ROOT/'output/urban_fixed_dispatch_20261117'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/storage_dispatch_source_scope.json'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


CONTRACTS=[
    ('reports/CALENDAR_STORAGE_20261103.md','mathematical_inventory_scenario',
     'The reserve calculation here is **our explicit inventory scenario and algebra**',
     'Minimum repeating stock given specified harvest and demand',
     'Does not identify ancient capacity,loss,institution or reserve policy'),
    ('reports/FOOD_STOCKS_20261103.md','numerical_inventory_definition',
     'periodicity and food sufficiency are different checks.',
     'Conserved supplied inventory and explicit initial stocks',
     'Does not reconstruct historical stock accumulation or granary construction'),
    ('reports/PRESENCE_MOBILITY_20261104.md','declared_export_store_scenario',
     'This is an assumed physical storage capacity, not observed granaries.',
     'Distinct on-farm commercial stock with finite capacity',
     'One year of modeled export flow is not observed archaeological capacity'),
    ('research_notes/presence_mobility_scale_20261104.json','modern_manual_existing_consultation_log',
     'Separate short harvest receipt periods, dispatch schedules and finite buffer capacity.',
     'Existing FAO storage-sizing mechanism reference;not reread as new measurements',
     'Neither ancient90/365days nor5%loss is measured by the logged use'),
    ('research_notes/settlement_integration_20261104.json','historical_market_existing_excerpt_log',
     'Distinguish production, supply security and entitlement.',
     'Erdkamp2005 publisher introduction already exposed:physical supply and rights differ',
     'Complete monograph not consulted;no storage coefficient or entitlement rule transferred'),
    ('reports/SEASONAL_FOOD_SYSTEM_20261103.md','network_interface_limit',
     'Its costs are **road-km equivalents**, not travel days, cargo capacities or tonnes;',
     'Keep freight cost distinct from travel duration and physical throughput',
     'Existing route losses do not measure fleet size or seasonal cargo capacity'),
    ('reports/URBAN_EVIDENCE_BUFFERS_20261116.md','existing_evidence_boundary',
     'Universal historical granary capacity, spoilage rate or food-risk probability',
     'Source contract explicitly records missing historical inventory parameters',
     'Buffer peaks and model conservation are not storage observations'),
    ('reports/URBAN_STORAGE_THROUGHPUT_20261117.md','conditional_model_throughput_identity',
     'This identity is conditional on those requirements;',
     'Single-pulse,all-open,zero-loss commercial throughput explains saved paths',
     'Not an ancient dispatch law;not applicable to blocked,multipulse or decaying stores'),
    ('reports/URBAN_FIXED_DISPATCH_20261117.md','controlled_model_rule_diagnosis',
     'No other city materially loses meals against the five-percent control',
     'Fixed baseline quota removes19observed local declines in two declared cases',
     'Does not choose a better default or identify historical storage/dispatch')]

BIBLIOGRAPHY=[
    dict(id='salido2018',author='Javier Salido Domínguez',year=2018,
         title='Sobre la capacidad de almacenaje de los "horrea" rurales romanos: teoría del Escepticismo Cuantitativo',
         url='https://revistas.ucm.es/index.php/GERI/en/article/view/60294',doi='10.5209/GERI.60294',
         source_kind='journal_publisher_metadata_and_abstract',region_period='Roman rural storage;individual dating requires full source',
         access='Publisher title,author,date,DOI and qualitative abstract verified;article body not read',
         interface='Archaeological capacity conversion and admissible assumptions',
         lead_summary='Abstract questions storage-capacity proposals through construction and grain-organization factors.',
         next_access='Open journal full text for method/source qualification under a later declaration',
         cannot_infer='No site capacity,packing density,usable height,stock loss or days of modeled flow extracted'),
    dict(id='vanoyen2020flow',author='Astrid Van Oyen',year=2020,
         title='Control (Flow): Warehouses in the Ports of Ostia and Portus',
         url='https://www.cambridge.org/core/books/abs/socioeconomics-of-roman-storage/control-flow-warehouses-in-the-ports-of-ostia-and-portus/CD3841AF3DA4A937E875B6197014450B',
         doi='10.1017/9781108850216.006',source_kind='publisher_chapter_metadata_and_summary',
         region_period='Ostia/Portus,Roman supply;chronology of particular claims unqualified',
         access='Cambridge author,year,DOI and summary verified;chapter behind access interface,body not read',
         interface='Warehouse use,commodity turnover and institutional/time distinctions',
         lead_summary='Summary distinguishes varied products and turnover,with different temporal registers of agency.',
         next_access='Locate lawful accessible full chapter or primary studies it cites;do not assume access',
         cannot_infer='No general state/private binary,uniform turnover schedule or numerical buffer transferred'),
    dict(id='rickman1971',author='Geoffrey Rickman',year=1971,title='Roman Granaries and Store Buildings',
         url='https://agris.fao.org/search/en/providers/122535/records/65de068d0f3e94b9e5c9760f',doi='',
         source_kind='FAO_AGRIS_National_Agricultural_Library_bibliographic_record',
         region_period='Roman granary/store-building reference;site periods not qualified',
         access='Catalogue author,title,year and Cambridge publisher verified;monograph not read',
         interface='Source trail for granary classification and documented physical structures',
         lead_summary='Bibliographic record identifies a monograph on granaries and warehouses.',
         next_access='Use as a source trail;authenticate cited primary excavation evidence before measurements',
         cannot_infer='Catalogue is not evidence of usable cereal volume,grain stocks,ownership or dispatch')]


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    q=read(PARENT/'qualification.json');assert q['status']=='passed_two_fixed_baseline_dispatch_cases_and_four_exact_controls'
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in q[key].items():assert sha(prefix/name)==digest,name
    OUT.mkdir(exist_ok=True);assert not (OUT/'results.json').exists(),'Preserve completed scope'
    rows=[];sources={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),PLAN,PARENT/'qualification.json']}
    for name,kind,quote,supported,missing in CONTRACTS:
        path=ROOT/name;text=' '.join(path.read_text().split());assert quote in text,(name,quote)
        sources[name]=sha(path)
        rows.append(dict(source=name,source_kind=kind,exact_existing_quote=quote,supported_interface=supported,
                         cannot_infer=missing,new_historical_numeric_parameter_qualified=False))
    with (OUT/'existing_contracts.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    write(OUT/'bibliographic_leads.json',BIBLIOGRAPHY)
    exposure=dict(date='2026-11-17',status='development_bibliographic_exposure_not_blind_evaluation',
        queries=['Geoffrey Rickman Roman Granaries and Store Buildings 1971 Cambridge publisher',
                 'Roman grain storage granaries capacity interpretation ownership OpenEdition Portus'],
        tool='search_service_web_run',retained_leads=[entry['id'] for entry in BIBLIOGRAPHY],
        access_scope='Search snippets,publisher/catalogue metadata and abstracts/summaries only;no article/chapter/monograph full text read.',
        incidental_search_snippets_may_contain_quantities=True,quantitative_observations_transcribed_or_used=0,
        excluded_quantitative_snippet=dict(title='Granaries and Garrisons in Roman Forts',
            url='https://onlinelibrary.wiley.com/doi/full/10.1111/j.1468-0092.2004.00220.x',
            status='Search snippet visible;not opened,extracted,adopted or treated as held-out evidence'),
        source_claims_not_parameter_evidence=True,fit_or_validation_pool_created=False)
    write(OUT/'exposure.json',exposure)
    for name,digest in q['protected_sha256'].items():assert sha(ROOT/name)==digest,name
    result=dict(status='completed_existing_contract_inventory_and_bibliographic_scope',sources_sha256=sources,
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=q['protected_sha256'],
        contracts=len(rows),bibliographic_leads=len(BIBLIOGRAPHY),new_qualified_historical_numeric_parameters=0,
        quantitative_observations_extracted=0,food_kernel_calls=0,new_food_scenarios=0,phenology_rescores=0,
        recommendation='Qualify archaeological conversion and institutional/source categories first;Salido2018 open methods paper is next bounded source. Do not fit a universal ancient capacity/loss or select a quota from these model outcomes.',
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False)
    write(OUT/'results.json',result);print(result['status'],len(rows),'contracts',len(BIBLIOGRAPHY),'leads',flush=True)


if __name__=='__main__':main()
