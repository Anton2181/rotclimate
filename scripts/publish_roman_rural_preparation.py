"""Publish aggregate S2 preparation and a transparent CSV-reader correction."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_locations_earth import sha,write


def role_section(data):
    out=ROOT/'output/roman_rural_roles_20261110';config=ROOT/'calibration/roman_rural_roles_20261110'
    if not (out/'audit.json').exists():return ''
    audit=json.loads((out/'audit.json').read_text())
    checks={'source_snapshot_sha256':ROOT/'output/roman_rural_preparation_20261110/source_snapshot.json',
        'crosswalk_sha256':config/'crosswalk.json','semantic_sources_sha256':config/'semantic_sources.json',
        'producer_sha256':ROOT/'scripts/prepare_roman_rural_roles.py',
        'role_module_sha256':ROOT/'polity/role_evidence.py',
        'parser_sha256':ROOT/'scripts/audit_vidarbha_preparation.py',
        'table_reader_sha256':ROOT/'scripts/audit_roman_rural_preparation.py'}
    for key,path in checks.items():
        if audit[key]!=sha(path):raise ValueError('Stale role-evidence lineage: '+key)
    if any(audit[k] for k in ['adopt','population_allocated','institution_staff_or_actor_assigned',
                              'model_scores_computed','target_maps_generated']):
        raise ValueError('Role preparation unexpectedly changed into adoption/evaluation')
    for src,name in [(out/'audit.json','roman_rural_roles.json'),(config/'crosswalk.json','roman_rural_role_crosswalk.json'),
                     (config/'semantic_sources.json','roman_rural_role_semantics.json')]:
        shutil.copyfile(src,data/name)
    labels={'agricultural_context':'Agricultural context','domestic_observation':'Domestic occupation recorded',
        'enclosure_context':'Enclosure/morphology','military_context':'Military context',
        'nucleated_context':'Nucleated settlement context','production_context':'Production context',
        'residential_context':'Residential context','ritual_funerary_context':'Ritual/funerary context',
        'settlement_context':'Broad rural-settlement category','site_context':'Other site context',
        'transport_context':'Transport context'}
    rows=''.join(f'<tr><th>{labels[key]}</th><td>{value:,}</td><td>{audit["span_compatible_records_per_channel"].get(key,0):,}</td></tr>'
        for key,value in audit['records_per_channel'].items())
    return '''<details id="rural-role-evidence"><summary>Role-aware evidence · overlapping observations, no population or authority estimate</summary>
<p>The new compiler counts each evidence channel once per source record and retains multiple labels, which can describe contemporary or successive roles. The source search confirms roadside settlement and jetty labels omitted by the CSV lookup; all observed labels now have an explicit context mapping. A roadside settlement does not establish a market, a villa an administrator, or a hillfort a staffed garrison.</p>
<div class="table"><table id="rural-role-results"><thead><tr><th>Evidence channel</th><th>Records, all dates</th><th>AD200 span compatible</th></tr></thead><tbody>'''+rows+'''</tbody></table></div>
<p>Columns overlap and must not be summed as settlements or residents. AD200 compatibility concerns the site span; it does not date individual roles. The official guide uses −100 for Middle Iron Age or earlier starts (628 records) and 400 for continuation to the end of the Roman period (1,295 records). Two zero endpoints remain ambiguous; the initial role audit left extra phase fields uninterpreted; the follow-up methodology audit clarifies their general purpose, without assigning function dates.</p>
<p>Exact association identifiers connect153 records into65 nontrivial blocking groups. These prevent related observations crossing future validation folds; they are not physical-place merges or proof of spatial independence. No folds or scores have been assigned. The official map client uses EPSG:3857, but that alone does not identify the CSV MAP coordinate system or precision.</p>
<p><a href="../../reports/ROMAN_RURAL_ROLES_20261110.md">Role compiler and calibration gates</a> · <a href="data/roman_rural_roles.json" download>Aggregate role audit</a> · <a href="data/roman_rural_role_crosswalk.json" download>Explicit context crosswalk</a> · <a href="data/roman_rural_role_semantics.json" download>Source semantics and identities</a></p></details>'''


def coordinate_section(data):
    out=ROOT/'output/roman_rural_coordinates_20261110';config=ROOT/'calibration/roman_rural_coordinates_20261110'
    if not (out/'audit.json').exists():return ''
    audit=json.loads((out/'audit.json').read_text())
    checks={'plan_sha256':config/'plan.json','producer_sha256':ROOT/'scripts/audit_roman_rural_coordinates.py',
        'parser_sha256':ROOT/'scripts/audit_vidarbha_preparation.py',
        'table_reader_sha256':ROOT/'scripts/audit_roman_rural_preparation.py',
        'original_source_snapshot_sha256':ROOT/'output/roman_rural_preparation_20261110/source_snapshot.json',
        'anchor_source_snapshot_sha256':out/'source_snapshot.json'}
    for key,path in checks.items():
        if audit[key]!=sha(path):raise ValueError('Stale coordinate interpretation: '+key)
    if any(audit[k] for k in ['settlement_climate_model_scored','source_target_map_generated','production_adopted']):
        raise ValueError('Coordinate investigation unexpectedly became model evaluation/adoption')
    for src,name in [(out/'audit.json','roman_rural_coordinates.json'),(config/'plan.json','roman_rural_coordinate_plan.json'),
                     (out/'source_snapshot.json','roman_rural_coordinate_sources.json')]:
        shutil.copyfile(src,data/name)
    return '''<details id="rural-coordinate-evidence"><summary>Coordinate interpretation · named-site schema check, not model accuracy</summary>
<p>Six declared named sites were checked against official Historic England grid references. All eight listed points were retained, including all three references for the multipoint Chysauster entry. X=easting/Y=northing in British-grid metres matches every point within 188 m (median 54 m); reversing axes misses every point by at least 29 km. Treating the CSV values as Web Mercator places all records outside the source latitude envelope.</p>
<p><strong>Working interpretation:</strong> OSGB-compatible X easting and Y northing, in metres. This is an exposed schema investigation, not a blind calibration or official export-CRS certification. It does not establish metre survey accuracy, verify all 3,652 coordinates or resolve physical settlements and role dates.</p>
<img id="rural-coordinate-figure" src="../../reports/figures/roman_rural_coordinates_20261110.png" style="max-width:100%;height:auto" width="1600" height="768" alt="Coordinate check: easting/northing residuals range 11 to 188 metres; reversed-axis residuals range 29 to 549 kilometres. Named-site schema check only.">
<p>The protocol records prior exposure and a before-calculation amendment to retain every point in the multipoint entry. A thesis reusing these fields labels their axes oppositely; direct official-anchor comparisons support the working interpretation above. Precision, actual places, extra phases and excavation coverage remain calibration gates.</p>
<p><a href="../../reports/ROMAN_RURAL_COORDINATES_20261110.md">Coordinate method, source citations and limits</a> · <a href="data/roman_rural_coordinates.json" download>Aggregate coordinate check</a> · <a href="data/roman_rural_coordinate_plan.json" download>Declared protocol and amendment</a> · <a href="data/roman_rural_coordinate_sources.json" download>Official anchor source identities</a></p></details>'''


def main():
    out=ROOT/'output/roman_rural_preparation_20261110';audit=json.loads((out/'audit.json').read_text())
    plan=ROOT/'calibration/roman_rural_preparation_20261110/plan.json'
    if audit['plan_sha256']!=sha(plan) or audit['producer_sha256']!=sha(ROOT/'scripts/audit_roman_rural_preparation.py'):
        raise ValueError('Changed rural preparation protocol/producer')
    if audit['parser_source_sha256']!=sha(ROOT/'scripts/audit_vidarbha_preparation.py'):
        raise ValueError('Changed source parser')
    if audit['source_snapshot_sha256']!=sha(out/'source_snapshot.json'):
        raise ValueError('Changed cached-source identities')
    if audit['model_scores_computed'] or audit['model_predictions_loaded'] or audit['target_maps_generated']:
        raise ValueError('Preparation unexpectedly became evaluation')
    correction=ROOT/'output/vidarbha_preparation_20261110/parser_correction.json'
    c=json.loads(correction.read_text())
    if c['new_source_sha256']!=sha(ROOT/'scripts/audit_vidarbha_preparation.py') or c['new_audit_sha256']!=sha(ROOT/'output/vidarbha_preparation_20261110/audit.json'):
        raise ValueError('Stale CSV correction receipt')
    page=ROOT/'atlases/earth_evidence/index.html';data=page.parent/'data'
    for src,name in [(out/'audit.json','roman_rural_preparation.json'),(plan,'roman_rural_preparation_plan.json'),
                     (out/'source_snapshot.json','roman_rural_sources.json'),(correction,'source_csv_correction.json')]:
        shutil.copyfile(src,data/name)
    major=audit['major_roles'];minor=audit['minor_roles'];joins=audit['record_joins'];dates=audit['occupation_intervals']
    rows=[('Joined core/site record IDs',joins['common_ids']),('Records with multiple major roles',major['multi_role_records']),
          ('Records with multiple minor roles',minor['multi_role_records']),('Intervals compatible with AD200',dates['apparent_AD200_compatible']),
          ('Records with unknown/non-numeric dates',dates['missing_or_nonnumeric_endpoint'])]
    table=''.join(f'<tr><th>{label}</th><td>{number:,}</td></tr>' for label,number in rows)
    section='''<!--rural-preparation-start--><section aria-labelledby="rural-preparation-h"><h2 id="rural-preparation-h">Next settlement stage: records, roles and dates</h2><details class="panel" id="rural-preparation"><summary>Rural Britain preparation · source audit, no model evaluation</summary>
<p>The new S2 source has joined record-level data and multiple functions per record. These are excavation observations, not a census of unique settlements or independently staffed institutions. Raw tables remain locally cached and are not redistributed.</p>
<div class="table"><table id="rural-preparation-results"><thead><tr><th>Preparation check</th><th>Records</th></tr></thead><tbody>'''+table+'''</tbody></table></div>
<p>All declared table primary keys are unique and role/association references have no missing parent records. The original minor CSV lookup omits356 observations; the role compiler below resolves their labels against the official source search. Site occupation intervals do not date every function or prove uninterrupted AD200 occupation.</p>
<p><strong>Size and coordinates:</strong> AREA means investigated hectares, not complete settlement extent. The separate size wordlist includes1,466 uncertain records. Exported X_REF_MAP/Y_REF_MAP fields differ from the documented OSGB fields; the initial audit left their units unresolved. The follow-up coordinate check below supports a working interpretation while retaining unknown survey precision. Record IDs have not been merged into unique physical settlements.</p>
<p><strong>Reader correction:</strong> automatic CSV sniffing misread escaped quotes. Standard comma/Excel parsing preserves the fields; all five British tables now have zero nonconforming rows. The earlier Vidarbha audit was rechecked: its zero joins and axis conflict remain, while a parser-induced unnamed-cell warning is removed. Climate and settlement predictions are unchanged.</p>
<p>Next: resolve physical places and MAP/phase semantics before role-specific calibration, then connect residents and institutions through the same food/population/control ledger. The full S1–S5 programme remains open; no production adoption or new independent validation is claimed.</p>
<p><a href="../../reports/ROMAN_RURAL_PREPARATION_20261110.md">Methods and source scope</a> · <a href="../../reports/SETTLEMENT_ROLE_CONTRACT_20261110.md">Settlement/control role contract</a> · <a href="../../reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md">Full roadmap</a> · <a href="data/roman_rural_preparation.json" download>Aggregate preparation audit</a> · <a href="data/roman_rural_preparation_plan.json" download>Frozen protocol</a> · <a href="data/roman_rural_sources.json" download>Source identities</a> · <a href="data/source_csv_correction.json" download>CSV correction and preserved before/after hashes</a></p></details></section><!--rural-preparation-end-->'''
    section=section.replace('</details></section><!--rural-preparation-end-->',role_section(data)+coordinate_section(data)+'</details></section><!--rural-preparation-end-->')
    html=page.read_text();pattern=r'<!--rural-preparation-start-->[\s\S]*?<!--rural-preparation-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-intensity-start-->'
        if marker not in html:raise ValueError('Publish adaptive evidence first')
        html=html.replace(marker,section+'\n'+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';exposure=json.loads(path.read_text())
    entry=dict(id='rural_roman_britain',status='prepared_unscored_roles_and_chronology',evidence='reports/ROMAN_RURAL_PREPARATION_20261110.md',
        note='Five tables prepared without scoring; role-context compiler, date conventions and association blocks implemented. Six-site/eight-point official-anchor check supports operational OSGB-compatible X-easting/Y-northing metres; not whole-source positional accuracy or export-CRS certification. Physical places, precision, phases and coverage unresolved. Britain overlaps Roman development; no sealed status or raw redistribution.')
    exposure['datasets']=[e for e in exposure['datasets'] if e['id']!=entry['id']]+[entry]
    write(path,exposure);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published aggregate rural-role preparation and source-reader correction; no model evaluation.')


if __name__=='__main__':main()
