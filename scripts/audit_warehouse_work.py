"""Read-only original B600 work budgets and missing logistics input contracts."""
import csv
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_warehouse_no_hold import sha,read,write
from audit_shared_store_readiness import schema

OUT=ROOT/'output/urban_warehouse_work_20261117'
WORK=ROOT/'output/urban_component_work_20261116'
MONTHLY=ROOT/'output/urban_earth_monthly_20261116'
CAL=ROOT/'output/urban_earth_calendars_20261116/calendars.npz'
PLAN=ROOT/'calibration/urban_diagnosis_20261117/warehouse_work_readiness.json'

CONTRACTS=[
    ('one_physical_workforce','polity/earth_component_work.py','workers=rural*.4','One source rural population;not additional warehouse staff.'),
    ('listed_annual_allowance','polity/earth_component_work.py','annual_available=workers*hours','Existing600h is a listed cereal-work scenario,not a complete annual occupation model.'),
    ('reaping_peak','polity/earth_component_work.py','peak_available=np.minimum(annual_available,workers*30*8)','Reaping-window constraint uses the SAME workers,not another additive annual budget.'),
    ('listed_includes_reaping','polity/earth_component_work.py','np.any(reaping>listed)','Reaping is part of listed work;do not subtract it a second time from the annual allowance.'),
    ('one_annual_charge','polity/earth_component_work.py','annual_required=required_listed.sum(0)','Annual crop tasks share one physical source budget.'),
    ('partial_monthly_timing','polity/earth_component_work.py','np.add.at(peak_required,(boundary[component,ok],source),required_reaping[component,ok])','Only reaping is timed by the archived monthly peak fields;other listed tasks have no full monthly schedule.'),
    ('positional_source_order','scripts/urban_component_work.py',"source=cal['source_indices']",'Component archive has positional arrays;source ordering requires pinned calendar recipe.'),
    ('original_monthly_rural','scripts/urban_earth_monthly.py',"rural=a['rural'][source]",'Monthly source population stays at the original physical source.'),
    ('handling_not_certified','polity/warehouse_roles.py','handling_work_certified=False','Shared grain/capacity does not certify handler tasks or staffing.'),
    ('deposit_funding_not_certified','polity/warehouse_roles.py','upstream_rural_work_certified=False','A funded consignment receipt alone does not certify rural/work source conditions.')]


def main():
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert not (OUT/'results.json').exists(),'Preserve completed work-readiness audit'
    sources={};protected={}
    for folder in [ROOT/'output/urban_warehouse_roles_20261117',WORK,MONTHLY]:
        q=read(folder/'qualification.json');assert q['status'].startswith('passed_')
        for key,prefix in [('sources_sha256',ROOT),('files_sha256',folder),('protected_sha256',ROOT)]:
            for name,digest in q[key].items():assert sha(prefix/name)==digest,name
        sources[str((folder/'qualification.json').relative_to(ROOT))]=sha(folder/'qualification.json');protected.update(q['protected_sha256'])
    OUT.mkdir(exist_ok=True)
    rows=[]
    for key,name,quote,meaning in CONTRACTS:
        assert quote in ' '.join((ROOT/name).read_text().split()),(key,name)
        rows.append(dict(contract=key,source=name,exact_quote=quote,interpretation=meaning));sources[name]=sha(ROOT/name)
    with (OUT/'contracts.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    with np.load(CAL) as archive:source=archive['source_indices']
    schemas={};statistics=[]
    fields=['rural','B_workers','B_annual_available','B_annual_used','B_peak_available','B_monthly_peak_used',
        'B_required_listed','B_required_reaping','B_retained','B_monthly_peak_required']
    for reading in ['central','low']:
        path=WORK/'hours600/cases'/f'{reading}.npz';monthly=MONTHLY/'cases'/reading/'fields.npz'
        for p in [path,monthly]:sources[str(p.relative_to(ROOT))]=sha(p);schemas[str(p.relative_to(ROOT))]=schema(p)
        with np.load(path) as archive:b={key:archive[key] for key in fields}
        with np.load(monthly) as archive:population=archive['rural'];monthly_source=archive['source_indices']
        np.testing.assert_array_equal(monthly_source,source);np.testing.assert_array_equal(b['rural'],population)
        np.testing.assert_array_equal(b['B_workers'],population*.4)
        np.testing.assert_array_equal(b['B_annual_available'],b['B_workers']*600)
        np.testing.assert_array_equal(b['B_peak_available'],np.minimum(b['B_annual_available'],b['B_workers']*30*8))
        np.testing.assert_array_equal(b['B_annual_used'],b['B_required_listed'].sum(0)*b['B_retained'])
        np.testing.assert_array_equal(b['B_monthly_peak_used'],b['B_monthly_peak_required']*b['B_retained'])
        annual=b['B_annual_available'];used=b['B_annual_used'];peak=b['B_peak_available'];peak_used=b['B_monthly_peak_used']
        unused=annual-used;tol=1e-8*np.maximum(1,annual);ptol=1e-8*np.maximum(1,peak)
        assert np.all(unused>=-tol) and np.all(peak_used<=peak[None,:]+ptol[None,:])
        positive=b['B_workers']>0
        annual_at=positive&(unused<=tol);peak_at=positive&np.any(abs(peak_used-peak[None,:])<=ptol[None,:],axis=0)
        reaping=peak_used.sum(0);unlocated=used-reaping
        assert np.all(unlocated>=-tol)
        # Summations describe already-archived task amounts, never newly allocated work.
        total=lambda a:float(np.asarray(a).sum())
        statistics.append(dict(reading=reading,physical_sources=len(source),rural_people=total(population),workers=total(b['B_workers']),
            listed_annual_allowance_hours=total(annual),listed_annual_used_hours=total(used),unused_listed_allowance_hours=total(unused),
            unused_fraction_of_listed_allowance=total(unused)/total(annual),positive_workforce_sources=int(positive.sum()),
            sources_at_annual_limit=int(annual_at.sum()),sources_at_reaping_limit=int(peak_at.sum()),
            max_reaping_peak_utilization=float(np.divide(peak_used,peak[None,:],out=np.zeros_like(peak_used),where=peak[None,:]>0).max()),
            min_raw_unused_hours=float(unused.min()),max_negative_unused_roundoff_hours=float(max(0,-unused.min())),
            reaping_hours_by_bin=peak_used.sum(1).tolist(),reaping_hours=total(reaping),
            listed_nonreaping_hours_without_monthly_schedule=total(unlocated),
            unused_allowance_is_logistics_staff=False,complete_monthly_work_schedule_present=False,
            task_timing_missing=True,handling_rate_qualified=False,handler_affiliation_qualified=False))
    write(OUT/'schemas.json',schemas);write(OUT/'budgets.json',statistics)
    paths=[Path(__file__),PLAN,CAL,ROOT/'scripts/audit_shared_store_readiness.py',ROOT/'scripts/audit_warehouse_no_hold.py']
    sources.update({str(p.relative_to(ROOT)):sha(p) for p in paths})
    for name,digest in protected.items():assert sha(ROOT/name)==digest,name
    write(OUT/'results.json',dict(status='completed_read_only_original_work_budget_and_handling_readiness_audit',
        sources_sha256=sources,protected_sha256=protected,files_sha256={p.name:sha(p) for p in OUT.iterdir() if p.is_file()},
        contracts=10,archive_schemas=4,original_work_cases=2,component_work_calls=0,food_kernel_calls=0,stock_solves=0,
        graph_rebuilds=0,dijkstra_calls=0,new_Earth_food_scenarios=0,new_staff_allocations=0,handling_rate_adopted=False,
        actual_warehouse_mappings=0,actual_population_changed=False,new_fit=False,new_validation_claim=False,adopt=False,main_atlas_changed=False))
    print([{k:s[k] for k in ['reading','unused_fraction_of_listed_allowance','sources_at_annual_limit','sources_at_reaping_limit','max_reaping_peak_utilization']} for s in statistics],flush=True)


if __name__=='__main__':main()
