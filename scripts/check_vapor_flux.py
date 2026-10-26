"""Frozen conservative-vapor pilot with separated diagnostic controls."""
from pathlib import Path
from multiprocessing import Pool
import importlib.metadata
import argparse
import json
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'scripts'))
from local_benchmark_protocol import file_hash,freeze,write_json
from paired_physics_pilot import run_one
from benchmark_local import DEV12_SPECS
from rotclimate import earth


def screening(rows,plan):
    reference={r['region']:r for r in rows if r['name']=='reference'}
    if set(reference)!=set(plan['regions']) or any(r['status']!='passed' or not r['legacy_exact'] for r in reference.values()):
        raise ValueError('All exact reference controls are required')
    reviews={}
    for name in plan['profiles']:
        if name=='reference':continue
        own={r['region']:r for r in rows if r['name']==name}
        failures=[];ratios={}
        if set(own)!=set(reference) or any(r['status']!='passed' for r in own.values()):
            reviews[name]=dict(qualifies=False,failures=['Incomplete or failed numerical comparison'],
                               eligible_profile=name in plan['eligible_profiles'])
            continue
        for region,b in reference.items():
            c=own[region]
            if b['case_identity']!=c['case_identity']:
                raise ValueError('Unpaired Earth inputs')
            t=c['temperature']['monthly_mae_C']/b['temperature']['monthly_mae_C']
            rain=c['rain']['loss']/b['rain']['loss']
            ratios[region]=dict(temperature=t,rain=rain,S=.5*(t+rain))
            if region=='north_india' and rain>.95:failures.append('North India improvement below5%')
            elif region=='iran_plateau' and rain>1.02:failures.append('Iran rain protection failed')
            elif region not in ['north_india','iran_plateau'] and .5*(t+rain)>1.02:
                failures.append(region+': local error protection failed')
            if (b['sst'] is None)!=(c['sst'] is None):raise ValueError('Sea mask changed')
            if b['sst'] and (c['sst']['cells']!=b['sst']['cells'] or c['sst']['monthly_mae_C']>b['sst']['monthly_mae_C']+.02):
                failures.append(region+': ocean protection failed')
            if c['column_speed']['maximum_ms']>60 or c['column_speed']['p95_ms']>25:
                failures.append(region+': wind-speed limit failed')
            if c.get('numerics',{}).get('all_checks_passed') is not True:
                failures.append(region+': missing numerical certificate')
            if region in plan.get('circulation_regions',[]):
                group=plan['circulation_groups'][region]
                base_wind=b['circulation']['scores']['q925_300'][group]
                wind=c['circulation']['scores']['q925_300'][group]
                if (wind is None or base_wind is None or wind['native_cells']!=base_wind['native_cells']
                        or wind['area_km2']!=base_wind['area_km2']):
                    raise ValueError('Changed native circulation footprint')
                wind_ratio=wind['vector_rmse_ms']/base_wind['vector_rmse_ms']
                ratios[region]['circulation_vector_rmse_ratio']=wind_ratio
                if name in plan['eligible_profiles'] and wind_ratio>(.95 if region=='north_india' else 1.02):
                    failures.append(region+': outside-reference circulation protection failed')
            if name in plan['eligible_profiles']:
                if plan.get('require_two_layer_transport'):
                    branches=c.get('numerics',{}).get('two_layer_transport',{})
                    if (c.get('params',{}).get('moisture_two_layer') is not True
                            or branches.get('max_scaled_dry_mass_divergence',float('inf'))>1e-10):
                        failures.append(region+': missing two-layer dry-air evidence')
                    if (branches.get('maximum_branch_speed_ms',float('inf'))>60
                            or branches.get('p95_branch_speed_ms',float('inf'))>25):
                        failures.append(region+': separate branch wind-speed limit failed')
                if plan.get('require_column_mass_balance'):
                    mass=c.get('numerics',{}).get('column_mass_balance',{})
                    if (c.get('params',{}).get('moisture_mass_balance') is not True
                            or mass.get('max_scaled_mass_divergence',float('inf'))>1e-10):
                        failures.append(region+': missing stationary column-mass evidence')
                ledger=c.get('numerics',{}).get('vapor_flux_budget',{})
                if (ledger.get('horizontal_transport_conservative') is not True
                        or ledger.get('max_relative_transport_cancellation',float('inf'))>1e-10
                        or c.get('params',{}).get('flux_convergence')!=0
                        or c.get('params',{}).get('moisture_transport_form')!='flux'):
                    failures.append(region+': missing conservative-transport evidence')
        t=sum(r['temperature']['monthly_mae_C'] for r in own.values())/sum(r['temperature']['monthly_mae_C'] for r in reference.values())
        rain=sum(r['rain']['loss'] for r in own.values())/sum(r['rain']['loss'] for r in reference.values())
        if .5*(t+rain)>.995:failures.append('Mean combined improvement below0.5%')
        if rain>.99:failures.append('Mean rain improvement below1%')
        if t>1.01:failures.append('Mean temperature worsens by more than1%')
        eligible=name in plan['eligible_profiles']
        reviews[name]=dict(eligible_profile=eligible,qualifies=eligible and not failures,failures=failures,
                           S=.5*(t+rain),temperature_ratio=t,rain_ratio=rain,regions=ratios)
    return reviews


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'calibration/vapor_flux_20261026/plan.json')
    parser.add_argument('--out',type=Path,default=ROOT/'output/vapor_flux_20261026')
    args=parser.parse_args()
    path=args.plan.resolve();plan=json.loads(path.read_text())
    out=args.out.resolve();out.mkdir(exist_ok=True)
    sources=list((ROOT/'rotclimate').glob('*.py'))+[path,Path(__file__),DEV12_SPECS,ROOT/plan['physics'],earth.WOA_SST,
        ROOT/'scripts/paired_physics_pilot.py',ROOT/'scripts/benchmark_local.py',ROOT/'scripts/earth_benchmark.py',
        ROOT/'scripts/rainfall_metrics.py',ROOT/'scripts/local_benchmark_protocol.py',
        ROOT/'scripts/check_surface_momentum.py',ROOT/'scripts/check_constrained_blend.py',ROOT/'scripts/gate_local.py',
        ROOT/'calibration/local_accuracy_20261023/policy_v2.json']
    sources += [earth.WORLDCLIM/f'wc2.1_5m_{key}.zip' for key in ['tavg','prec','elev','vapr']]
    if plan.get('circulation_regions'):
        from circulation_reference import acquire
        reference_plan=ROOT/plan['circulation_reference_plan']
        _,references=acquire(ROOT,json.loads(reference_plan.read_text()))
        sources += [reference_plan,ROOT/'scripts/circulation_reference.py',ROOT/'scripts/earth_calendar.py',
                    ROOT/'experiments/v10_forcing_audit.py']
        sources += [ROOT/name for name in references]
        sources += list((ROOT/'rotclimate_v10').glob('*.py'))+[ROOT/'experiments/v10_thermodynamics.py']
        sources += [ROOT/'output/circulation_audit_20261026'/f'{r}.npz' for r in plan['circulation_regions']]
    for region in plan['regions']:sources += [ROOT/plan['archive']/'cases'/f'{region}.json',ROOT/plan['archive']/'cells'/f'{region}.npz']
    for folder in plan.get('profile_control_archives',{}).values():
        for region in plan['regions']:
            sources += [ROOT/folder/f'{region}.json',ROOT/folder/f'{region}.npz']
    identity=freeze(out/'protocol.json',dict(plan=plan,sources={str(p.relative_to(ROOT)):file_hash(p) for p in sources},
        packages={name:importlib.metadata.version(name) for name in ['numpy','scipy','numba']}))
    rows=[]
    with Pool(2) as pool:
        for name,updates in plan['profiles'].items():
            rows += pool.map(run_one,[(name,region,updates,plan,identity,str(out)) for region in plan['regions']])
            write_json(out/'progress.json',dict(complete=False,records=rows))
            if name=='reference' and any(r['status']!='passed' for r in rows):
                raise SystemExit('Preserve failed exact controls; do not run candidates')
            if name in plan.get('profile_control_archives',{}) and any(r['status']!='passed' for r in rows if r['name']==name):
                raise SystemExit('Preserve failed historical physical controls; do not run candidates')
    reviews=screening(rows,plan)
    selected=sorted((name for name,row in reviews.items() if row['qualifies']),key=lambda name:reviews[name]['S'])
    selected=selected[:plan.get('maximum_finalists',1)]
    final=dict(complete=True,identity=identity,screen=reviews,development_finalists=selected,
               all_per_step_checks_passed=all(r['status']=='passed' for r in rows),physics_or_atlas_adoption=False)
    write_json(out/'review.json',final);write_json(out/'progress.json',dict(complete=True,records=rows))
    if selected:
        generated=dict(plan,candidates={name:plan['profiles'][name] for name in selected},
                       candidate_numerics={name:plan.get('profile_numerics',{}).get(name,{}) for name in selected},
                       parent=str(out.relative_to(ROOT)),note='Generated only from the predeclared eligible screening qualifier')
        generated_path=out/'full_plan.json';write_json(generated_path,generated)
        command=[sys.executable,'-u','-I',str(ROOT/'scripts/check_surface_momentum.py'),
                 '--plan',str(generated_path),'--out',str(out/'full')]
        with (out/'full.log').open('a') as stream:
            subprocess.run(command,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,check=True)
    print(json.dumps(final,indent=2),flush=True)


if __name__=='__main__':main()
