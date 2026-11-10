"""Publish aggregate S2 preparation and a transparent CSV-reader correction."""
import json
from pathlib import Path
import re
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from settlement_locations_earth import sha,write


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
<p>All declared table primary keys are unique and role/association references have no missing parent records. Minor classification lookups omit356 observed labels, which remain explicit rather than guessed. Site occupation intervals do not date every function or prove uninterrupted AD200 occupation.</p>
<p><strong>Size and coordinates:</strong> AREA means investigated hectares, not complete settlement extent. The separate size wordlist includes1,466 uncertain records. Exported X_REF_MAP/Y_REF_MAP fields differ from the documented OSGB fields; their units remain unresolved and no projection or map was generated. Record IDs have not been merged into unique physical settlements.</p>
<p><strong>Reader correction:</strong> automatic CSV sniffing misread escaped quotes. Standard comma/Excel parsing preserves the fields; all five British tables now have zero nonconforming rows. The earlier Vidarbha audit was rechecked: its zero joins and axis conflict remain, while a parser-induced unnamed-cell warning is removed. Climate and settlement predictions are unchanged.</p>
<p>Next: resolve place grouping, MAP/phase semantics and taxonomy before role-specific calibration, then connect residents and institutions through the same food/population/control ledger. The full S1–S5 programme remains open; no production adoption or new independent validation is claimed.</p>
<p><a href="../../reports/ROMAN_RURAL_PREPARATION_20261110.md">Methods and source scope</a> · <a href="../../reports/SETTLEMENT_ROLE_CONTRACT_20261110.md">Settlement/control role contract</a> · <a href="../../reports/SETTLEMENT_CONTROL_ROADMAP_20261110.md">Full roadmap</a> · <a href="data/roman_rural_preparation.json" download>Aggregate preparation audit</a> · <a href="data/roman_rural_preparation_plan.json" download>Frozen protocol</a> · <a href="data/roman_rural_sources.json" download>Source identities</a> · <a href="data/source_csv_correction.json" download>CSV correction and preserved before/after hashes</a></p></details></section><!--rural-preparation-end-->'''
    html=page.read_text();pattern=r'<!--rural-preparation-start-->[\s\S]*?<!--rural-preparation-end-->'
    if re.search(pattern,html):html=re.sub(pattern,lambda m:section,html)
    else:
        marker='<!--settlement-intensity-start-->'
        if marker not in html:raise ValueError('Publish adaptive evidence first')
        html=html.replace(marker,section+'\n'+marker,1)
    page.write_text(html)
    path=ROOT/'calibration/earth_components_20261105/dataset_usage.json';exposure=json.loads(path.read_text())
    entry=dict(id='rural_roman_britain',status='prepared_unscored_roles_and_chronology',evidence='reports/ROMAN_RURAL_PREPARATION_20261110.md',
        note='Five observation tables read under frozen preparation-only protocol. Record/role joins valid; physical places, MAP coordinates and phase roles unresolved. Excavation-selected Britain overlaps Roman development; no predictions, scores or sealed status. Raw source tables not redistributed.')
    exposure['datasets']=[e for e in exposure['datasets'] if e['id']!=entry['id']]+[entry]
    write(path,exposure);shutil.copyfile(path,data/'dataset_usage.json')
    print('Published aggregate rural-role preparation and source-reader correction; no model evaluation.')


if __name__=='__main__':main()
