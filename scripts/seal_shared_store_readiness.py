"""Independent schema/quote/read-only boundary checks for route readiness."""
import ast
import csv
from fractions import Fraction
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_shared_store_readiness import OUT,PARENT,MONTHLY,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed readiness qualification'
    r=read(OUT/'results.json');assert r['status']=='completed_read_only_shared_store_coupling_readiness'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    rows=list(csv.DictReader((OUT/'contracts.csv').open()));assert len(rows)==15
    for row in rows:assert row['exact_quote'] in ' '.join((ROOT/row['source']).read_text().split()),row['interface']
    schemas=read(OUT/'schemas.json');assert len(schemas)==6
    for name,fields in schemas.items():
        with np.load(ROOT/name) as archive:
            assert set(fields)==set(archive.files)
            # Representative actual arrays independently check the header path.
            for key in set(fields)&{'owner','dist','between','road','land','cell_km','source_indices'}:
                assert fields[key]['shape']==list(archive[key].shape) and fields[key]['dtype']==str(archive[key].dtype)
    ready=read(OUT/'readiness.json');assert not ready['archived_chosen_paths_saved'] and not ready['new_shared_Earth_food_trial_ready']
    for row in ready['source_statistics']:
        with np.load(MONTHLY/'cases'/row['reading']/'fields.npz') as c:
            owner=c['owner'];exporting=c['departures'].sum(0)>0
            # Pairwise set membership gives a separate check of quarter changes.
            changing=np.array([len(set(values))>1 for values in owner.T])
            assert row['sources_with_quarterly_recipient_change']==int(changing.sum())==4050
            assert row['exporting_sources_with_recipient_change']==int((changing&exporting).sum())
    # Exact manufactured algebra check;this is no transport or food scenario.
    a,b,L=Fraction(1,4),Fraction(1,5),Fraction(1)
    assert (1-a/L)*(1-b/L)-(1-(a+b)/L)==a*b/L**2>0
    tree=ast.parse((ROOT/'scripts/audit_shared_store_readiness.py').read_text())
    allowed={'csv','hashlib','json','pathlib','subprocess','zipfile','numpy'}
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):assert all(alias.name in allowed for alias in node.names)
        if isinstance(node,ast.ImportFrom):assert node.module in allowed
    parent=read(PARENT/'qualification.json')
    for key,prefix in [('sources_sha256',ROOT),('files_sha256',PARENT),('protected_sha256',ROOT)]:
        for name,digest in parent[key].items():assert sha(prefix/name)==digest,name
    for key in ['food_kernel_calls','dijkstra_calls','graph_rebuilds','new_Earth_food_scenarios','real_origin_to_port_mappings']:
        assert r[key]==0
    paths=[Path(__file__),ROOT/'reports/SHARED_STORE_READINESS_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/warehouse_route_provenance_controls.json']
    q=dict(status='passed_read_only_shared_store_coupling_contract_and_schema_audit',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in paths}},
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},protected_sha256=r['protected_sha256'],
        contract_rows=15,archive_schemas=6,source_statistics_independently_checked=True,
        split_leg_retention_algebra_checked=True,archived_chosen_paths_saved=False,new_shared_Earth_food_trial_ready=False,
        food_kernel_calls=0,dijkstra_calls=0,graph_rebuilds=0,new_Earth_food_scenarios=0,real_origin_to_port_mappings=0,
        actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/warehouse_route_provenance_controls.json')
    write(OUT/'qualification.json',q);print(q['status'],flush=True)


if __name__=='__main__':main()
