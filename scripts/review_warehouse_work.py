"""Independent scalar work-budget identities and absolute-floor limit diagnostics."""
import csv
import math
from pathlib import Path
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from audit_warehouse_work import OUT,WORK,MONTHLY,CAL,sha,read,write


def main():
    assert not (OUT/'review.json').exists(),'Preserve independent work-readiness review'
    r=read(OUT/'results.json');assert r['status']=='completed_read_only_original_work_budget_and_handling_readiness_audit'
    for name,digest in {**r['sources_sha256'],**r['protected_sha256']}.items():assert sha(ROOT/name)==digest,name
    for name,digest in r['files_sha256'].items():assert sha(OUT/name)==digest,name
    rows=list(csv.DictReader((OUT/'contracts.csv').open()));assert len(rows)==10
    for row in rows:assert row['exact_quote'] in ' '.join((ROOT/row['source']).read_text().split())
    schemas=read(OUT/'schemas.json');assert len(schemas)==4
    for name,fields in schemas.items():
        with np.load(ROOT/name) as archive:assert set(fields)==set(archive.files)
    with np.load(CAL) as archive:source=archive['source_indices']
    stats=read(OUT/'budgets.json');assert len(stats)==2;diagnostics=[]
    for statistic in stats:
        reading=statistic['reading']
        with np.load(WORK/'hours600/cases'/f'{reading}.npz') as archive:
            b={key:archive[key] for key in ['rural','B_workers','B_annual_available','B_annual_used','B_peak_available',
                'B_monthly_peak_used','B_required_listed','B_required_reaping','B_retained']}
        with np.load(MONTHLY/'cases'/reading/'fields.npz') as archive:
            np.testing.assert_array_equal(source,archive['source_indices']);np.testing.assert_array_equal(b['rural'],archive['rural'])
        positive=annual_at=absolute_peak_near=relative_peak_at=0;unused=[];annual=[];used=[];workers=[];unlocated=[];reaping=[];peak_near_allowance=[]
        max_peak=0.
        for i,population in enumerate(b['rural']):
            worker=float(population)*.4;a=worker*600;p=min(a,worker*30*8)
            assert worker==b['B_workers'][i] and a==b['B_annual_available'][i] and p==b['B_peak_available'][i]
            u=float(b['B_annual_used'][i]);peaks=b['B_monthly_peak_used'][:,i]
            tol=1e-8*max(1,a);ptol=1e-8*max(1,p)
            assert a-u>=-tol and max(peaks)<=p+ptol
            assert np.all(b['B_required_reaping'][:,i]<=b['B_required_listed'][:,i])
            reap=math.fsum(peaks);listed_reap=math.fsum(b['B_required_reaping'][:,i])*float(b['B_retained'][i])
            assert abs(reap-listed_reap)<=tol and u-reap>=-tol
            annual.append(a);used.append(u);unused.append(a-u);workers.append(worker);reaping.append(reap);unlocated.append(u-reap)
            if worker>0:
                positive+=1;annual_at+=int(a-u<=tol)
                ratios=peaks/p;max_peak=max(max_peak,float(max(ratios)))
                near=any(abs(float(v)-p)<=ptol for v in peaks)
                absolute_peak_near+=int(near);relative_peak_at+=int(any(float(v)>=1-1e-8 for v in ratios))
                if near:peak_near_allowance.append(p)
        totals={key:math.fsum(values) for key,values in [('workers',workers),('listed_annual_allowance_hours',annual),
            ('listed_annual_used_hours',used),('unused_listed_allowance_hours',unused),('reaping_hours',reaping),
            ('listed_nonreaping_hours_without_monthly_schedule',unlocated)]}
        for key,value in totals.items():assert math.isclose(value,statistic[key],rel_tol=1e-8,abs_tol=1e-8),key
        assert statistic['physical_sources']==len(source) and statistic['positive_workforce_sources']==positive
        assert statistic['sources_at_annual_limit']==annual_at and statistic['sources_at_reaping_limit']==absolute_peak_near
        assert statistic['max_reaping_peak_utilization']==max_peak and relative_peak_at==0
        assert max_peak<.385 and max(peak_near_allowance)<2e-8
        diagnostics.append(dict(reading=reading,absolute_tolerance_near_reaping_limit_sources=absolute_peak_near,
            relative_utilization_at_reaping_limit_sources=relative_peak_at,max_reaping_utilization=max_peak,
            max_allowance_among_absolute_near_cells_hours=max(peak_near_allowance),
            total_allowance_among_absolute_near_cells_hours=math.fsum(peak_near_allowance),
            listed_nonreaping_fraction_without_monthly_schedule=totals['listed_nonreaping_hours_without_monthly_schedule']/totals['listed_annual_used_hours'],
            interpretation='Absolute-near counts come from the existing tolerance floor on minute workforce budgets;not a binding reaping constraint. No budgets or tolerances changed.'))
    write(OUT/'limit_diagnostics.json',diagnostics)
    for key in ['component_work_calls','food_kernel_calls','stock_solves','graph_rebuilds','dijkstra_calls','new_Earth_food_scenarios','new_staff_allocations']:assert r[key]==0
    write(OUT/'review.json',dict(status='passed_independent_original_work_budget_and_limit_interpretation_checks',
        reviewer_sha256=sha(Path(__file__)),results_sha256=sha(OUT/'results.json'),diagnostics_sha256=sha(OUT/'limit_diagnostics.json'),
        original_cases=2,source_rows_checked=len(source)*2,exact_source_population_alignment=True,
        source_contract_quotes=10,complete_monthly_work_schedule_present=False,unused_allowance_is_staff=False,
        component_work_calls=0,food_kernel_calls=0,stock_solves=0,graph_rebuilds=0,dijkstra_calls=0,
        new_Earth_food_scenarios=0,new_staff_allocations=0,handling_rate_adopted=False,new_fit=False,new_validation_claim=False,adopt=False))
    print('Independent scalar work-budget checks passed;zero relative reaping constraints binding',flush=True)


if __name__=='__main__':main()
