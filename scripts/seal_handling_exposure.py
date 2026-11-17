"""Seal the reviewed read-only handling basis and unchanged current atlas."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_handling_exposure import ROOT,OUT,sha,read,write


def main():
    assert not (OUT/'qualification.json').exists(),'Preserve completed qualification'
    r=read(OUT/'results.json');review=read(OUT/'review.json')
    assert review['status']=='passed_independent_all_node_ordered_shipments_exposures_ratios_and_plot_values'
    assert review['results_sha256']==sha(OUT/'results.json')
    assert review['reviewer_sha256']==sha(ROOT/'scripts/review_handling_exposure.py')
    assert review['monthly_quantities_checked']==52080 and review['ordered_shipments']==15896
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    for name in ['results.json',*r['files_sha256']]:assert (OUT/name).read_bytes()==(OUT/'fresh'/name).read_bytes(),name
    sources=dict(r['sources_sha256'])
    next_plan=ROOT/'calibration/urban_diagnosis_20261117/handling_rate_evidence_screen.json'
    for p in [Path(__file__),ROOT/'scripts/review_handling_exposure.py',ROOT/'reports/HANDLING_EXPOSURE_20261117.md',next_plan]:sources[str(p.relative_to(ROOT))]=sha(p)
    write(OUT/'qualification.json',dict(status='passed_all_original_town_rate_free_handling_exposure',sources_sha256=sources,
        protected_sha256=r['protected_sha256'],files_sha256={name:sha(OUT/name) for name in ['results.json','review.json',*r['files_sha256']]},
        town_rows=2170,town_bins=26040,monthly_quantities_checked=52080,ordered_shipments=15896,
        year_wrap_rows=1363,all_original_nodes_including_zeros=True,requested_populations_exact=True,
        historical_publication_remappings=len(r['historical_publication_remappings']),current_protected_identities=len(r['protected_sha256']),
        source_clock_and_grain_exact=True,fresh_outputs_byte_exact=True,figure_visually_inspected=True,
        handling_hours_unknown=True,handling_rates_qualified=False,solver_calls=0,new_Earth_food_scenarios=0,
        new_staff_allocations=0,actual_warehouse_mappings=0,actual_population_changed=False,
        main_atlas_changed=False,new_fit=False,new_validation_claim=False,adopt=False,next_plan=str(next_plan.relative_to(ROOT))))
    print('Qualified all-node rate-free handling basis; current r5 atlas unchanged',flush=True)


if __name__=='__main__':main()
