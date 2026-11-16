"""Seal reviewed annual controls, the preserved period failure and next input gaps."""
import csv
import json
from pathlib import Path

from urban_seasonal_transfer_controls import ROOT, OUT, sha


def read(path):return json.loads(path.read_text())


def table(path,rows):
    with path.open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main():
    qualified=OUT/'wind_1981';r=read(qualified/'readiness.json');failed=read(OUT/'readiness.json')
    assert r['annual_archived_result_bytes_exact'] and r['annual_cases']==6 and r['independent_flow_settings']==100
    assert not failed['annual_archived_result_bytes_exact'] and failed['independent_flow_settings']==200
    assert not r['seasonal_trial_ready'] and r['missing_calendar_production_share']==1
    for stage in ['greek','low']:
        control=read(qualified/stage/'control.json')
        assert control['status']=='passed_byte_exact_archived_annual_controls'
        assert sha(qualified/stage/'results.json')==control['archived_sha256']
        for path,digest in {**control['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/path)==digest,path
    sources=read(qualified/'wind_restoration.json')
    for value in sources['sources'].values():
        assert '1981/01/01 - 2010/12/31' in value['period']
        assert sha(ROOT/value['path'])==value['sha256']
    first=read(OUT/'greek/results.json');last=read(qualified/'greek/results.json')
    rows=[]
    for c in r['cases']:
        rows.append({k:c[k] for k in ['stage','name','cities','residents','source_cells','positive_production_cells',
            'basin_source_cells','basin_potential_share','potential_person_years','grown_person_years','rural_people',
            'annual_rural_deficit_person_years','calendar_missing_production_share','archived_e95','replay_e95']})
    table(OUT/'cases.csv',rows)
    inventory=[
        dict(dependency='Annual controls',available='Six complete archived results reproduced byte for byte',remaining_gap='Controls are development diagnostics on exposed evidence; no new validation'),
        dict(dependency='Population',available='61.4M empire normalization on capacity×history; finite rural workforce',remaining_gap='Uniform global recruitment differs from fantasy local origin links; future port needs an explicit factorized scenario'),
        dict(dependency='Crop energy and field work',available='Original crop selection, net calories,600h worker-year and shared reaping budget recovered',remaining_gap='Partial cereal tasks only; complete diet,household,draft and transport work absent'),
        dict(dependency='Harvest calendars',available='Original crop_yield can return a best-season mask',remaining_gap='No saved harvest date for any positive production cell; reconstruct original model timing and verify unchanged energies'),
        dict(dependency='Floodplain partition',available='455 active source cells;2.6769667704213053% of potential; separate energy components retained',remaining_gap='Annual boost is winter-cereal maximum blended into both crop options; recover actual maximum crop identity and timing'),
        dict(dependency='Flood timing',available='Restored monthly basin flow,catchment IDs,last flood month and qualification receipt',remaining_gap='Flood timing is not a crop harvest date; compare reconstructed sowing windows with flood recession'),
        dict(dependency='Transport',available='Four actual seasonal source owners/distances and town matrices; original1981–2010 wind product recovered',remaining_gap='Reader fallback serves1991–2020; future port must assert source period and explicitly map monthly bins/leg delay'),
        dict(dependency='City demand',available='1354 AD150 catalogue rows;1115 eligible rows;1085 city cells;central and low densities',remaining_gap='403 eligible areas imputed at15ha; residents are area×assumed density,not observed censuses'),
        dict(dependency='Food closure',available='Source production and rural demand audited separately',remaining_gap='Primary central annual rural calorie deficit207112 person-years; seasonal scarcity/losses and all-world closure unqualified'),
        dict(dependency='Adoption',available='All protected files and main atlas identities verified unchanged',remaining_gap='No new seasonal Earth trial or share fit; independent transfer/resource/role gates remain')
    ]
    table(OUT/'dependencies.csv',inventory)
    paths=[Path(__file__),ROOT/'reports/URBAN_SEASONAL_TRANSFER_20261116.md']
    paths += [ROOT/'scripts'/name for name in ['review_urban_seasonal_transfer.py','replay_urban_transfer_1981.py',
        'review_urban_transfer_1981.py','urban_seasonal_transfer_controls.py','restore_urban_transfer_winds.py',
        'diagnose_urban_transfer_identity.py']]
    paths+=list((ROOT/'calibration/urban_diagnosis_20261116').glob('seasonal_transfer*.json'))
    identities={str(p.relative_to(ROOT)):sha(p) for p in paths}
    artifacts={str(p.relative_to(OUT)):sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='results.json'}
    # Explicitly retain the two result files excluded by the basename filter.
    for folder in ['greek','wind_1981/greek','wind_1981/low']:
        p=OUT/folder/'results.json';artifacts[str(p.relative_to(OUT))]=sha(p)
    result=dict(status='reviewed_Earth_annual_controls_exact_seasonal_calendar_recovery_next',
        sources_sha256=identities,files_sha256=artifacts,protected_sha256=r['protected_sha256'],
        qualified_directory='wind_1981',qualified_annual_cases=6,independent_primary_flow_settings=100,
        independent_preserved_failed_flow_settings=200,
        historical_input_diagnosis=dict(cause='Unversioned1991–2020 fallback substituted for the1981–2010 product explicitly named in the annual protocol',
            wrong_period_greece_e95=first['variants']['greece']['decision']['e95_all_at_L_used'],
            qualified_greece_e95=last['variants']['greece']['decision']['e95_all_at_L_used'],
            same_sources_work_demands=True,first_failure_preserved=True,
            limit='Whole archived annual result identity is established. Original ignored wind-file hashes and original full route arrays were not retained; no claim to recover their bytes.'),
        harvest_calendar_missing_production_share=1.,seasonal_trial_ready=False,seasonal_trial_performed=False,
        next='Committed seasonal_transfer_calendar_recovery.json: recover original model calendars and floodplain crop provenance with exact annual-energy checks before declaring a seasonal pilot.',
        new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False)
    (OUT/'results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],flush=True)


if __name__=='__main__':main()
