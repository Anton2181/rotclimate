from pathlib import Path
import json
import pytest
from scripts.check_vapor_flux import screening


def cases():
    plan=json.loads(Path('calibration/vapor_flux_20261026/plan.json').read_text())
    rows=[]
    for name in plan['profiles']:
        for region in plan['regions']:
            rows.append(dict(name=name,region=region,status='passed',legacy_exact=name=='reference',
                case_identity=region,temperature=dict(monthly_mae_C=2 if name=='reference' else 1.98),
                rain=dict(loss=1 if name=='reference' else .9),sst=dict(cells=10,monthly_mae_C=2),
                column_speed=dict(maximum_ms=20,p95_ms=10),params=dict(flux_convergence=0,moisture_transport_form='flux'),
                numerics=dict(all_checks_passed=True,vapor_flux_budget=dict(horizontal_transport_conservative=True,
                              max_relative_transport_cancellation=1e-15))))
    return plan,rows


def test_diagnostic_improvement_cannot_select_an_ineligible_partial_scheme():
    plan,rows=cases();reviews=screening(rows,plan)
    assert reviews['flux_conservative_storm']['qualifies']
    assert all(not r['qualifies'] for n,r in reviews.items() if n!='flux_conservative_storm')


def test_missing_ledger_or_false_solver_certificate_cannot_qualify():
    plan,rows=cases()
    row=next(r for r in rows if r['name']=='flux_conservative_storm')
    row['numerics']['vapor_flux_budget']['horizontal_transport_conservative']=False
    assert not screening(rows,plan)['flux_conservative_storm']['qualifies']
    row['numerics']['vapor_flux_budget']['horizontal_transport_conservative']=True
    row['numerics']['all_checks_passed']=False
    assert not screening(rows,plan)['flux_conservative_storm']['qualifies']


def test_regional_or_ocean_regression_rejects_better_global_means():
    plan,rows=cases()
    row=next(r for r in rows if r['name']=='flux_conservative_storm' and r['region']=='japan')
    row['sst']['monthly_mae_C']=2.03
    assert not screening(rows,plan)['flux_conservative_storm']['qualifies']
    row['sst']['monthly_mae_C']=2
    row['rain']['loss']=1.2
    assert not screening(rows,plan)['flux_conservative_storm']['qualifies']
