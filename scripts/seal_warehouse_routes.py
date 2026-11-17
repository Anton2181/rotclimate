"""Seal the bounded original-route provenance packet after independent review."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts')]
from select_warehouse_routes import OUT,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve qualified original-route packet'
    r=read(OUT/'results.json');review=read(OUT/'review.json');plot=read(OUT/'map_receipt.json')
    assert r['status']=='recovered_bounded_original_routes_pending_independent_review'
    assert review['status']=='passed_independent_original_route_selection_direction_edge_and_cost_checks'
    assert review['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_warehouse_routes.py')
    for name,digest in {**r['sources_sha256'],**r['protected_sha256'],**plot['sources_sha256']}.items():
        assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    assert plot['figure_sha256']==sha(OUT/'original_routes.png')
    assert r['graph_rebuilds']==4 and r['dijkstra_calls']==8 and r['route_count']==review['route_certificates_checked']==16
    assert review['canonical_graph_rebuilds']==review['dijkstra_calls']==review['food_kernel_calls']==0
    assert r['food_kernel_calls']==r['new_Earth_food_scenarios']==r['actual_warehouse_mappings']==r['new_all_pairs_tables']==0
    assert review['source_owners_and_archived_dtype_distances_exact_readings_times_quarters']==8
    assert review['selected_forward_costs_exact']==8 and review['selection_rankings_checked']==16
    assert not (OUT/'failure.json').exists()
    extra=[Path(__file__),ROOT/'scripts/review_warehouse_routes.py',ROOT/'scripts/plot_warehouse_routes.py',
        ROOT/'reports/WAREHOUSE_ROUTE_PROVENANCE_20261117.md',
        ROOT/'calibration/urban_diagnosis_20261117/warehouse_no_hold_contract.json']
    q=dict(status='passed_sixteen_original_route_certificates_with_exact_archived_costs_and_owners',
        sources_sha256={**r['sources_sha256'],**{str(p.relative_to(ROOT)):sha(p) for p in extra}},
        files_sha256={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file()},
        protected_sha256=r['protected_sha256'],route_records=16,distinct_node_chains=6,
        source_owners_distances_exact_both_readings_four_snapshots=True,selected_intertown_costs_exact=8,
        producer_canonical_graph_rebuilds=4,producer_dijkstra_calls=8,reviewer_canonical_graph_rebuilds=0,
        reviewer_independent_CSR_assemblies=4,reviewer_dijkstra_calls=0,food_kernel_calls=0,
        new_Earth_food_scenarios=0,actual_warehouse_mappings=0,new_all_pairs_tables=0,
        unique_historical_paths_proven=False,physical_days_inferred=False,actual_population_changed=False,
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False,
        next_plan='calibration/urban_diagnosis_20261117/warehouse_no_hold_contract.json')
    write(OUT/'qualification.json',q);print(q['status'],flush=True)


if __name__=='__main__':main()
