"""Fixed recycling/turning ablations on two spent development regions."""
import csv
import json
from pathlib import Path
import subprocess
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'scripts')]
from rotclimate import earth
from rotclimate.koppen import monthly_stats
from earth_benchmark import load_params
from benchmark_local import temperature_metrics
from rainfall_metrics import local_metrics
from local_benchmark_protocol import case_hash,file_hash,freeze,write_json

PLAN=ROOT/'calibration/somalia_mechanism_20261126/plan.json'
OUT=ROOT/'output/somalia_mechanism_20261126'
REFERENCE=ROOT/'output/ppe_20261126/ref58'


def main():
    plan=json.loads(PLAN.read_text());assert len(plan['regions'])==2 and len(plan['variants'])==4
    assert subprocess.check_output(['git','show','HEAD:'+str(PLAN.relative_to(ROOT))],cwd=ROOT)==PLAN.read_bytes()
    assert not (OUT/'results.json').exists(),'Preserve completed diagnostic'
    parts=['sealed_S18','sealed_U18'];specs={};refrows={};reference_paths={}
    paths=[PLAN,Path(__file__),ROOT/'calibration/local_accuracy_20261023/r58_params.json',
           ROOT/'scripts/local_benchmark_protocol.py',ROOT/'scripts/benchmark_local.py',ROOT/'scripts/rainfall_metrics.py',
           ROOT/'scripts/earth_benchmark.py',ROOT/'output/climate_runtime_20261126/qualification.json']
    for part in parts:
        path=ROOT/('calibration/sealed_20261123S18/regions.json' if part=='sealed_S18' else 'calibration/sealed_20261124U18/regions.json')
        paths.append(path);specs.update(json.loads(path.read_text()))
        summary=REFERENCE/f'r58_{part}/summary.json';paths.append(summary)
        for name,row in json.loads(summary.read_text())['regions'].items():
            if name in plan['regions']:
                refrows[name]=row;reference_paths[name]=summary.parent/'cells'/f'{name}.npz';paths.append(reference_paths[name])
    earth.REGIONS.update({n:specs[n] for n in plan['regions']})
    qualification=json.loads((ROOT/'output/climate_runtime_20261126/qualification.json').read_text())
    paths.extend(ROOT/n for n in qualification['shared_inputs_sha256'])
    paths.extend(sorted((ROOT/'rotclimate').glob('*.py')))
    sources={str(p.relative_to(ROOT)):file_hash(p) for p in paths}
    OUT.mkdir(parents=True,exist_ok=True)
    freeze(OUT/'preparation.json',dict(plan=plan,sources_sha256=sources,reference_regions=2,model_integrations=8))
    base=load_params(ROOT/'calibration/local_accuracy_20261023/r58_params.json')
    rows=[];months=[];files={};controls=0
    for region in plan['regions']:
        for variant,overrides in plan['variants'].items():
            folder=OUT/region/variant;folder.mkdir(parents=True,exist_ok=True)
            result_path=folder/'result.json';field_path=folder/'fields.npz'
            if result_path.exists():
                row=json.loads(result_path.read_text());assert file_hash(field_path)==row['fields_sha256']
            else:
                p=base.replace(**overrides);case=earth.region_case(region,56.,1100.)
                identity=case_hash(case);assert identity==refrows[region]['case_identity']
                result=earth.run_case(p,case,steps=p.steps_per_year)
                assert result.numerics.get('all_checks_passed') is True
                pr=result.params
                args=dict(year_days=pr.year_days,summer_solstice=pr.winter_solstice_day+pr.year_days/2)
                stats=monthly_stats(result.T,result.P,result.days,**args)
                fields=dict(T=stats['Tm'],P=np.maximum(stats['Pm'],0),obs_T=case.obs_T,obs_P=case.obs_P)
                for key in ['E','W','u','v']:
                    field=getattr(result,key)
                    monthly=monthly_stats(field,field,result.days,**args)
                    fields[key]=monthly['Pm' if key=='E' else 'Tm']
                mask=case.grid.inmap&case.grid.land&np.isfinite(case.obs_T).all(0)&np.isfinite(case.obs_P).all(0)
                fields.update(mask=mask,land=case.grid.land,inmap=case.grid.inmap,lat=case.grid.lat,lon=case.lon)
                if variant=='control':
                    with np.load(reference_paths[region]) as old:
                        for key,archived in [('T','Ts'),('P','Ps'),('obs_T','To'),('obs_P','Po')]:
                            np.testing.assert_array_equal(fields[key][:,mask].astype(np.float32),old[archived])
                np.savez_compressed(field_path,**fields)
                rain=local_metrics(fields['P'],np.nan_to_num(case.obs_P),mask)
                temp=temperature_metrics(fields['T'][:,mask],case.obs_T[:,mask])
                row=dict(region=region,variant=variant,overrides=overrides,case_identity=identity,
                    numeric_certificate=result.numerics,fields_sha256=file_hash(field_path),rain_loss=rain['loss'],
                    annual_temperature_mae_C=temp['monthly_mae_C'],annual_temperature_bias_C=temp['annual_bias_C'],
                    annual_rain_mm=float(fields['P'][:,mask].sum(0).mean()),
                    observed_annual_rain_mm=float(case.obs_P[:,mask].sum(0).mean()),
                    all_months=[dict(month=m+1,observed_rain_mm=float(case.obs_P[m,mask].mean()),
                        simulated_rain_mm=float(fields['P'][m,mask].mean()),
                        evaporation_mm=float(fields['E'][m,mask].mean()),column_water_mm=float(fields['W'][m,mask].mean()),
                        surface_u_ms=float(fields['u'][m,mask].mean()),surface_v_ms=float(fields['v'][m,mask].mean()),
                        temperature_bias_C=float((fields['T'][m,mask]-case.obs_T[m,mask]).mean())) for m in range(12)],
                    counterfactual_not_adopted=True)
                write_json(result_path,row)
            if variant=='control':
                assert row['rain_loss']==refrows[region]['rain']['loss']
                assert row['annual_temperature_mae_C']==refrows[region]['temperature']['monthly_mae_C']
                controls+=1
            rows.append(row)
            months.extend(dict(region=region,variant=variant,**r) for r in row['all_months'])
            for path in [result_path,field_path]:files[str(path.relative_to(OUT))]=file_hash(path)
            print(region,variant,'rain_mm',round(row['annual_rain_mm'],1),'loss',round(row['rain_loss'],4),flush=True)
    effects=[]
    for region in plan['regions']:
        r={x['variant']:x for x in rows if x['region']==region}
        P={key:v['annual_rain_mm'] for key,v in r.items()}
        effects.append(dict(region=region,control_annual_rain_mm=P['control'],observed_annual_rain_mm=r['control']['observed_annual_rain_mm'],
            no_recycling_change_mm=P['no_local_recycling']-P['control'],turning_change_mm=P['minimum_turning']-P['control'],
            both_change_mm=P['both']-P['control'],factorial_interaction_mm=P['both']-P['minimum_turning']-P['no_local_recycling']+P['control']))
    with (OUT/'months.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(months[0]));writer.writeheader();writer.writerows(months)
    files['months.csv']=file_hash(OUT/'months.csv')
    for n,h in sources.items():assert file_hash(ROOT/n)==h,n
    write_json(OUT/'results.json',dict(status='completed_fixed_Somali_recycling_turning_diagnostic',
        sources_sha256=sources,files_sha256=files,controls_exact=controls,strict_numerical_cases=8,integrations=8,
        rows=rows,effects=effects,calibrated_parameter=False,candidate_adopted=False,W18c_changed=False,sealed_AA_opened=False))


if __name__=='__main__':main()
