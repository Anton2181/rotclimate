"""Exercise finite service work on unchanged, food-constrained atlas residents."""
import gzip
import json
from pathlib import Path
import sys
import numpy as np
from scipy.sparse import eye

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from audit_roman_rural_preparation import sha,write
from harvest.food_stocks import periodic_food_year
from polity.settlement_support import SettlementPlan
from polity.service_demand import allocate_requests
from polity.service_capacity import supported_staff_hours,fulfil_services

OUT=ROOT/'output/settlement_service_capacity_20261111'
PLAN=ROOT/'calibration/settlement_service_capacity_20261111/plan.json'
MODELS={'raw':ROOT/'atlases/earth_fit/data/settled_reach.json.gz',
        'corrected':ROOT/'atlases/earth_fit/data/corrected/settled_reach.json.gz'}


def main():
    OUT.mkdir(parents=True,exist_ok=True);sources={str(p.relative_to(ROOT)):sha(p) for p in MODELS.values()}
    results=[];food_checks=[];fields={}
    for climate,path in MODELS.items():
        model=json.loads(gzip.decompress(path.read_bytes()));spec=model['specification'];n=len(model['sites'])
        sites=model['sites'];fields[climate+'__nodes']=np.array([s['node'] for s in sites],int)
        for case in model['cases']:
            if not case.get('food_constrained'):continue
            name=case['id'];prefix=climate+'__'+name
            civil=np.array(case['civilian_people'],float);staff=np.array(case['institutional_people'],float);people=civil+staff
            arrivals=np.array(case['monthly_arrivals_kcal'],float).T;need=np.array(case['monthly_need_kcal'],float).T
            expected=np.broadcast_to(people*spec['ration_kcal_person_day']*spec['year_days']/12,(12,n))
            if arrivals.shape!=(12,n) or need.shape!=(12,n) or not np.allclose(need,expected,rtol=1e-12,atol=1e-6):raise ValueError('Stored need differs from same resident ledger')
            year=periodic_food_year(arrivals,need,people*spec['ration_kcal_person_day']*spec['destination_store_demand_days'],
                loss_fraction_year=spec['annual_stored_energy_loss_fraction'],step_days=spec['year_days']/12,record=True)
            for attr,key in [('consumed','resident_consumed_kcal'),('spoiled','destination_loss_kcal'),('overflow','destination_unused_kcal')]:
                if not np.isclose(getattr(year,attr).sum(),case['ledger'][key],rtol=1e-10,atol=.01):raise ValueError('Recorded periodic food ledger changed: '+key)
            plan=SettlementPlan(np.array(case['food_ceiling_people']),civil,staff,people,
                np.array(case['institutional_active']),np.array(case['community_viable']),year)
            before={key:np.array(value,copy=True) for key,value in [('people',people),('staff',staff),('consumed',year.consumed)]}
            fields[prefix+'__people']=people;fields[prefix+'__staff']=staff
            choice=allocate_requests(eye(n,format='csr'),people,np.ones(n))
            food_checks.append(dict(climate=climate,case=name,sites=n,residents=float(people.sum()),supported_staff=float(staff.sum()),
                periodic_resident_consumption_kcal=float(year.consumed.sum()),destination_loss_kcal=float(year.spoiled.sum()),
                destination_unused_kcal=float(year.overflow.sum()),maximum_food_unmet_kcal=float(year.unmet.max(initial=0)),
                maximum_food_ledger_residual_kcal=float(abs(year.ledger_residual).max(initial=0))))
            for fraction in [0.,.5,1.]:
                budget=supported_staff_hours(plan,hours_per_staff=600.,committed_hours=staff*600.*fraction)
                served=fulfil_services([choice,choice],staff_hours=budget.available_hours,hours_per_request=[[1.],[2.]])
                tag=prefix+f'__committed{int(100*fraction)}'
                for suffix,value in [('served',served.origin_served),('unmet',served.origin_unmet),('unreachable',served.origin_unreachable),
                    ('capacity_unmet',served.origin_capacity_unmet),('provider_hours',served.provider_hours_by_channel),
                    ('unused_hours',served.unused_provider_hours),('available_hours',budget.available_hours)]:fields[tag+'__'+suffix]=value
                requested=np.array([people.sum(),people.sum()]);fulfilled=served.origin_served.sum(axis=1)
                results.append(dict(climate=climate,case=name,committed_fraction=fraction,sites=n,residents=float(people.sum()),
                    supported_staff=float(staff.sum()),gross_staff_hours=float(budget.gross_hours.sum()),
                    committed_staff_hours=float(budget.committed_hours.sum()),available_staff_hours=float(budget.available_hours.sum()),
                    used_staff_hours=float(served.provider_hours_by_channel.sum()),unused_staff_hours=float(served.unused_provider_hours.sum()),
                    requested_by_channel=requested.tolist(),fulfilled_by_channel=fulfilled.tolist(),unmet_by_channel=served.origin_unmet.sum(axis=1).tolist(),
                    unreachable_by_channel=served.origin_unreachable.sum(axis=1).tolist(),
                    fulfilled_request_fraction=float(fulfilled.sum()/requested.sum()) if requested.sum()>0 else None,
                    maximum_origin_request_balance_error=float(abs(served.origin_served+served.origin_unmet-people[None,:]).max(initial=0)),
                    maximum_provider_hour_excess=float(np.maximum(served.provider_hours_by_channel.sum(axis=0)-budget.available_hours,0).max(initial=0))))
            for key,value in [('people',people),('staff',staff),('consumed',year.consumed)]:
                if not np.array_equal(before[key],value):raise ValueError('Service consumer mutated resident/food inputs')
        print(climate,'food cases complete',flush=True)
    for path,digest in sources.items():
        if sha(ROOT/path)!=digest:raise ValueError('Atlas source modified')
    np.savez_compressed(OUT/'fields.npz',**fields)
    paths=[Path(__file__),ROOT/'polity/service_capacity.py',ROOT/'polity/service_demand.py',ROOT/'polity/settlement_support.py',ROOT/'harvest/food_stocks.py']
    write(OUT/'results.json',dict(status='shared_service_work_implementation_diagnostic',adopt=False,earth_calibrated_service_rates=False,
        plan_sha256=sha(PLAN),fields_sha256=sha(OUT/'fields.npz'),sources=sources,
        producers={str(p.relative_to(ROOT)):sha(p) for p in paths},food_replays=food_checks,scenarios=results,
        population_food_staff_control_changed=False,chosen_scenario=None,
        units='Same annual residents;2neutral potential requests/person/year,cost1and2hours;600grosshours/supportedstaff/year,0/50/100%alreadycommitted;identitylocalchoice only.',
        limits='Single-pass rationing,no rerouting/maxflow,dated roles,market/patrol inference or actual service observations. Staff envelope and requests are stress units,not ancient empirical rates. Other-duty commitments remain unquantified in production;no free-budget default adopted.'))
    print(len(food_checks),'food replays and',len(results),'shared work scenarios.')


if __name__=='__main__':main()
