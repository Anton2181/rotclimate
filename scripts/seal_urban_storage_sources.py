"""Check the scope's exact local contracts, access labels and protected identities."""
import ast
import csv
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from scope_urban_storage_sources import OUT,PARENT,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed scope qualification'
    r=read(OUT/'results.json');assert r['status']=='completed_existing_contract_inventory_and_bibliographic_scope'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    rows=list(csv.DictReader((OUT/'existing_contracts.csv').open()));assert len(rows)==r['contracts']==9
    for row in rows:
        assert row['exact_existing_quote'] in ' '.join((ROOT/row['source']).read_text().split())
        assert row['new_historical_numeric_parameter_qualified']=='False'
        assert row['supported_interface'] and row['cannot_infer']
    bibliography=read(OUT/'bibliographic_leads.json');assert len(bibliography)==3
    expected={'salido2018':('Javier Salido Domínguez',2018,'10.5209/GERI.60294'),
              'vanoyen2020flow':('Astrid Van Oyen',2020,'10.1017/9781108850216.006'),
              'rickman1971':('Geoffrey Rickman',1971,'')}
    for row in bibliography:
        assert (row['author'],row['year'],row['doi'])==expected[row['id']]
        assert row['url'].startswith('https://') and row['access'] and row['cannot_infer']
        assert 'not read' in row['access']
    exposure=read(OUT/'exposure.json');assert len(exposure['queries'])==2
    assert exposure['quantitative_observations_transcribed_or_used']==0
    assert not exposure['fit_or_validation_pool_created']
    # Source inspection independently limits the producer to stdlib local I/O
    # and its committed-plan check: no scientific imports or network execution.
    tree=ast.parse((ROOT/'scripts/scope_urban_storage_sources.py').read_text())
    allowed={'csv','hashlib','json','pathlib','subprocess'}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):assert all(alias.name in allowed for alias in node.names)
        if isinstance(node,ast.ImportFrom):assert node.module in allowed
    parent=read(PARENT/'qualification.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():assert sha(prefix/name)==digest,name
    for key in ['new_qualified_historical_numeric_parameters','quantitative_observations_extracted','food_kernel_calls','new_food_scenarios','phenology_rescores']:
        assert r[key]==0
    paths=[Path(__file__),ROOT/'reports/URBAN_STORAGE_SOURCES_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/storage_capacity_method_qualification.json']
    q=dict(status='passed_existing_storage_contract_inventory_and_bibliographic_access_scope',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        existing_contracts=9,bibliographic_leads=3,unread_source_bodies_kept_unqualified=True,
        metadata_access_scope_checked=True,live_web_metadata_independently_revalidated=False,
        new_qualified_historical_numeric_parameters=0,quantitative_observations_extracted=0,food_kernel_calls=0,
        new_food_scenarios=0,phenology_rescores=0,actual_population_changed=False,new_fit=False,new_validation_claim=False,
        adopt=False,main_atlas_changed=False,next_plan='calibration/urban_diagnosis_20261117/storage_capacity_method_qualification.json')
    write(OUT/'qualification.json',q);print(q['status'],flush=True)


if __name__=='__main__':main()
