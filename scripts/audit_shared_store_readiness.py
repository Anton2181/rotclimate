"""Read-only cached-schema and source contracts for a warehouse network attachment."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

import numpy as np

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/urban_shared_store_readiness_20261117'
PARENT=ROOT/'output/urban_shared_warehouse_20261117'
MONTHLY=ROOT/'output/urban_earth_monthly_20261116'
ANNUAL=ROOT/'output/urban_seasonal_transfer_20261116/wind_1981'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/shared_store_coupling_readiness.json'


def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def read(path):return json.loads(path.read_text())
def write(path,value):path.write_text(json.dumps(value,indent=2)+'\n')


CONTRACTS=[
 ('protected_deposit','harvest/field_support.py','protected=self.year.unmet<=1e-8*np.maximum(self.year.needed,1)',
  'available_for_existing_scenario','Upstream protection is explicit;shared primitive alone does not certify rural food/work.'),
 ('unique_store_capacity','polity/shared_warehouse.py','Unique nonempty physical store IDs required',
  'primitive_available_mapping_missing','Unique capacity supported;Earth cache has no authenticated warehouse ID/mapping.'),
 ('pooling_permission','polity/shared_warehouse.py','Sharing a physical store requires explicit scenario pooling permission',
  'scenario_contract_only','No empirical collective ownership/access inferred.'),
 ('source_path_discarded','scripts/settlement_supply_calibration.py','d, _, src = dijkstra(net.base.T.tocsr(), directed=True, indices=nodes, min_only=True, return_predecessors=True, limit=limit)',
  'not_saved','Directed source→town costs use reverse graph;computed predecessor vector is discarded.'),
 ('town_path_capture','scripts/urban_seasonal_transfer_controls.py','assert not predecessors',
  'not_saved','Exact capture retains city-cost columns;no intertown predecessor chains.'),
 ('predecessor_API','polity/trade.py','return_predecessors=predecessors',
  'API_available_not_replayed','Original cost API supports predecessor output;no call in this audit.'),
 ('whole_leg_retention','scripts/urban_earth_monthly.py',"retention=np.maximum(1-a['dist'][:,source].astype(float)/270,0)",
  'nonmultiplicative_rule','Splitting one charged leg changes paid grain unless the loss accounting is explicitly preserved.'),
 ('one_bin_leg','polity/seasonal_settlement_network.py','direct[(month+1)%12]+=np.bincount',
  'declared_lag_not_path_duration','Adding a store must not silently add another one-bin transport delay.'),
 ('same_path_cost_days_API','polity/freight_corridors.py','Keep cost, duration and mode on the SAME directed transport leg/path.',
  'isolated_API_not_legacy_equivalence','Existing connector preserves metadata but its graph construction differs from legacy.'),
 ('legacy_parallel_edges','polity/control.py','self.base = coo_matrix((d, (r, c)), shape=(self.n, self.n)).tocsr()',
  'legacy_semantics_must_remain','CSR sums parallel records;do not silently replace graph while reconstructing old paths.'),
 ('isolated_parallel_edges','polity/freight_corridors.py','Sorting before CSR construction prevents its duplicate-entry sum.',
  'different_semantics','Connector selects an alternative;not presumed identical to legacy Earth freight graph.'),
 ('graph_road_provenance','scripts/settlement_supply_calibration.py',"world = P.world_of(g, x['road']); st = N.statics(world); cl = N.climate(world, st)",
  'reconstruction_input_required','Prepared transport snapshot alone omits road and other world fields;preserve exact old recipe.'),
 ('one_workforce','polity/earth_component_work.py','workers=rural*.4',
  'partial_work_only','Cereal field/reaping work is budgeted;warehouse handling,transport and complete work are not.'),
 ('no_duplicate_people_or_land','polity/seasonal_settlement_network.py','Each demographic shard owns only population, never another copy of',
  'upstream_rule_preserved','Pooling food must not duplicate physical land,grain,workers or recruitment.'),
 ('physical_store_evidence','reports/URBAN_STORAGE_CONTRACT_20261117.md','The model\'s grid coordinates are known;',
  'physical_facility_evidence_missing','Grid cell is not an authenticated building,capacity or historical permission.')]


def schema(path):
    result={}
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.endswith('.npy'):continue
            with archive.open(name) as f:
                version=np.lib.format.read_magic(f)
                reader=np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
                shape,fortran,dtype=reader(f)
            result[name[:-4]]=dict(shape=list(shape),dtype=str(dtype),fortran=bool(fortran))
    return result


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    sources={};protected={}
    for folder in [PARENT,MONTHLY]:
        q=read(folder/'qualification.json');assert q['status'].startswith('passed_')
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in q[key].items():assert sha(prefix/name)==digest,name
        sources[str((folder/'qualification.json').relative_to(ROOT))]=sha(folder/'qualification.json');protected.update(q['protected_sha256'])
    annual=read(ANNUAL/'readiness.json');assert annual['annual_archived_result_bytes_exact'] and annual['annual_cases']==6
    for key in ['inputs_sha256','protected_sha256']:
        for name,digest in annual[key].items():assert sha(ROOT/name)==digest,name
    sources[str((ANNUAL/'readiness.json').relative_to(ROOT))]=sha(ANNUAL/'readiness.json')
    OUT.mkdir(exist_ok=True);assert not (OUT/'results.json').exists(),'Preserve completed readiness audit'
    contracts=[]
    for field,name,quote,status,meaning in CONTRACTS:
        text=' '.join((ROOT/name).read_text().split());assert quote in text,(field,name)
        sources[name]=sha(ROOT/name);contracts.append(dict(interface=field,source=name,exact_quote=quote,status=status,interpretation=meaning))
    with (OUT/'contracts.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(contracts[0]));writer.writeheader();writer.writerows(contracts)
    files=[ANNUAL/'prepared'/f'low_{r}.npz' for r in ['central','low']]
    files += [MONTHLY/'cases'/r/'fields.npz' for r in ['central','low']]
    files += [ANNUAL/'prepared/low_transport_world.npz',ROOT/'output/settlement_locations_20261110/rome_inputs.npz']
    schemas={str(path.relative_to(ROOT)):schema(path) for path in files}
    for path in files:sources[str(path.relative_to(ROOT))]=sha(path)
    write(OUT/'schemas.json',schemas)
    statistics=[]
    for reading in ['central','low']:
        akey=str((ANNUAL/'prepared'/f'low_{reading}.npz').relative_to(ROOT));mkey=str((MONTHLY/'cases'/reading/'fields.npz').relative_to(ROOT))
        available=set(schemas[akey])|set(schemas[mkey])
        route_fields=[key for key in available if any(token in key.lower() for token in ['predecess','path_node','path_edge','warehouse','port_id'])]
        assert not route_fields
        with np.load(ROOT/mkey) as monthly:
            owner=monthly['owner'];exporting=monthly['departures'].sum(0)>0
            changing=np.any(owner!=owner[:1],axis=0)
            statistics.append(dict(reading=reading,physical_source_rows=owner.shape[1],quarterly_owner_rows=owner.shape[0],
                sources_with_quarterly_recipient_change=int(changing.sum()),exporting_sources_with_recipient_change=int((changing&exporting).sum()),
                saved_path_or_warehouse_fields=route_fields))
    worldkey=str((ANNUAL/'prepared/low_transport_world.npz').relative_to(ROOT));worldfields=set(schemas[worldkey])
    roadskey='output/settlement_locations_20261110/rome_inputs.npz'
    assert 'road' in schemas[roadskey]
    write(OUT/'readiness.json',dict(status='path_reconstruction_and_explicit_attachment_contracts_required',
        archived_endpoints_costs_retention_present=True,archived_chosen_paths_saved=False,source_predecessors_computed_then_discarded=True,
        quarter_owner_is_not_store_identity=True,source_statistics=statistics,
        transport_snapshot_missing_world_fields=[key for key in ['road','biome','cell_km'] if key not in worldfields],
        archived_road_field_available=True,physical_warehouse_mapping_present=False,empirical_capacity_or_rights_qualified=False,
        warehouse_handling_work_budget_present=False,shared_commercial_town_physical_capacity_deduplication_defined=False,
        connector_parallel_semantics_equivalent_to_legacy=False,
        split_leg_loss_identity='For positive unclipped a,b with a+b<L:(1-a/L)*(1-b/L)=(1-(a+b)/L)+a*b/L^2.',
        split_leg_interpretation='Multiplying subleg retentions exceeds the original one-leg retention;requires an explicit no-invented-grain reduction contract.',
        zero_hold_pass_through_requires_original_arrival_lag=True,
        new_shared_Earth_food_trial_ready=False,real_origin_store_mapping_attempted=False))
    paths=[Path(__file__),PLAN];sources.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',dict(status='completed_read_only_shared_store_coupling_readiness',sources_sha256=sources,protected_sha256=protected,
        files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},contract_rows=len(contracts),archive_schemas=len(schemas),
        food_kernel_calls=0,dijkstra_calls=0,graph_rebuilds=0,new_Earth_food_scenarios=0,real_origin_to_port_mappings=0,
        new_historical_measurements=0,actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False))
    print(statistics,flush=True)


if __name__=='__main__':main()
